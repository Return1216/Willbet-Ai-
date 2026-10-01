"""Markdown/TXT 文档切分、Embedding 和 Chroma 检索。

索引采用“新集合写完后再发布 manifest”的方式，重建失败时保留旧索引。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

@dataclass(frozen=True)
class SourceDocument:
    """相对于 documents 根目录的源文件。"""

    path: Path
    text: str

@dataclass(frozen=True)
class Chunk:
    """待写入向量库的文本块及其来源元数据。"""

    id: str
    text: str
    metadata: dict[str, Any]

@dataclass(frozen=True)
class RetrievedChunk:
    """向量召回结果，包含相似度和可展示的来源信息。"""

    content: str
    source: str
    chunk_id: str
    score: float | None
    metadata: dict[str, Any]

COLLECTION_NAME = "rag_agent_documents"

def iter_documents(root: Path) -> Iterator[SourceDocument]:
    """递归读取 documents 下的 Markdown/TXT，忽略其他扩展名。"""

    root=Path(root).resolve()
    if not root.exists(): return
    for path in sorted(root.rglob('*')):
        if path.is_file() and path.suffix.lower() in {'.md','.txt'}:
            if not path.resolve().is_relative_to(root):
                raise ValueError('Document symlink leaves documents directory')
            yield SourceDocument(path.relative_to(root),path.read_text(encoding='utf-8-sig'))


def chunk_document(document: SourceDocument,max_chars=1200,overlap=150) -> list[Chunk]:
    """先按空行分段，再按字符数切分长段；重叠只发生在同一段内。"""

    if max_chars<=0 or not 0<=overlap<max_chars: raise ValueError('Invalid chunk size or overlap')
    source=document.path.as_posix()
    title=''
    chunks=[]
    text=document.text.replace('\r\n','\n')
    # 最近的 Markdown 标题存入 metadata；当前不会自动拼进其他片段正文。
    for paragraph_no, paragraph in enumerate(re.split(r'\n\s*\n',text)):
        paragraph=paragraph.strip()
        if not paragraph: continue
        headings=re.findall(r'^#{1,6}\s+(.+)$',paragraph,re.M)
        if headings: title=headings[-1]
        for start in range(0,len(paragraph),max_chars-overlap):
            body=paragraph[start:start+max_chars]
            idx=len(chunks)
            # 相对路径参与哈希，避免不同子目录里的同名文档出现 ID 冲突。
            chunk_id=hashlib.sha256(f'{source}:{idx}:{body}'.encode()).hexdigest()
            chunks.append(Chunk(chunk_id,body,{'source':source,'title':title,
                'chunk_index':idx,'paragraph_index':paragraph_no}))
            if start+max_chars>=len(paragraph): break
    return chunks


def _client(settings):
    """创建关闭匿名遥测的持久化 Chroma 客户端。"""

    import chromadb
    from chromadb.config import Settings as ChromaSettings
    settings.chroma_dir.mkdir(parents=True,exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_dir),
        settings=ChromaSettings(anonymized_telemetry=False))


def get_collection(settings):
    """读取当前索引 manifest，并校验 Embedding 配置没有改变。"""

    manifest=settings.chroma_dir/'active-index.json'
    client=_client(settings)
    if not manifest.exists():
        return client.get_or_create_collection(COLLECTION_NAME,embedding_function=None,
                                               metadata={'hnsw:space':'cosine'})
    active=json.loads(manifest.read_text(encoding='utf-8'))
    expected=[settings.embedding_base_url.rstrip('/'),settings.embedding_model,settings.embedding_dimension]
    # 不同模型或维度的向量不能直接混用，必须重新构建索引。
    if active['embedding']!=expected:
        raise ValueError('Embedding configuration changed; rebuild the document index')
    return client.get_collection(active['collection'],embedding_function=None)


def _embeddings(client,settings,texts):
    """分批调用 Embedding API，并严格校验数量、维度和数值有效性。"""

    vectors=[]
    size=settings.embedding_batch_size
    if not 1<=size<=10: raise ValueError('EMBEDDING_BATCH_SIZE must be between 1 and 10')
    for start in range(0,len(texts),size):
        batch=texts[start:start+size]
        response=client.embeddings.create(model=settings.embedding_model,input=batch,
            dimensions=settings.embedding_dimension,encoding_format='float')
        data=sorted(response.data,key=lambda x:x.index)
        # 按服务返回的 index 恢复输入顺序，避免向量与文档错配。
        if [d.index for d in data]!=list(range(len(batch))):
            raise ValueError('Embedding response count/index mismatch')
        for item in data:
            vec=list(item.embedding)
            if len(vec)!=settings.embedding_dimension or any(not math.isfinite(x) for x in vec) or not any(vec):
                raise ValueError('Invalid embedding vector or dimension mismatch')
            vectors.append(vec)
    return vectors


def build_index(settings,embedding_client,max_chars=1200,overlap=150):
    """重建索引并原子发布；返回写入的文本块数量。"""

    chunks=[c for doc in iter_documents(settings.documents_dir) for c in chunk_document(doc,max_chars,overlap)]
    if not chunks:
        # 空目录不删除仍可用的旧索引，避免误操作造成数据丢失。
        return 0
    client=_client(settings)
    name='rag_agent_'+uuid4().hex
    collection=client.create_collection(name,embedding_function=None,metadata={'hnsw:space':'cosine'})
    manifest_tmp=settings.chroma_dir/(name+'.json')
    try:
        # 先写完新集合，最后替换 manifest，查询过程不会看到半成品。
        for start in range(0,len(chunks),settings.embedding_batch_size):
            batch=chunks[start:start+settings.embedding_batch_size]
            collection.add(ids=[c.id for c in batch],documents=[c.text for c in batch],
                embeddings=_embeddings(embedding_client,settings,[c.text for c in batch]),
                metadatas=[c.metadata for c in batch])
        manifest_tmp.write_text(json.dumps({'collection':name,'embedding':[
            settings.embedding_base_url.rstrip('/'),settings.embedding_model,settings.embedding_dimension]},ensure_ascii=False),encoding='utf-8')
        os.replace(manifest_tmp,settings.chroma_dir/'active-index.json')
    except BaseException:
        client.delete_collection(name)
        manifest_tmp.unlink(missing_ok=True)
        raise
    # ponytail: 旧集合保留给进行中的查询；多次重建占用过多磁盘时再加显式清理。
    return len(chunks)


def retrieve(question,settings,embedding_client,top_k=20) -> list[RetrievedChunk]:
    """召回 Top-K，再按最低相似度阈值过滤无关片段。"""

    if top_k<1: raise ValueError('top_k must be positive')
    collection=get_collection(settings)
    count=collection.count()
    if count==0: return []
    result=collection.query(query_embeddings=_embeddings(embedding_client,settings,[question]),
                            n_results=min(top_k,count))
    output=[]
    for chunk_id,doc,meta,dist in zip(result['ids'][0],result['documents'][0],result['metadatas'][0],result['distances'][0]):
        # 集合使用余弦距离；1 - distance 是相似度，不是答案正确率。
        score=1.0-float(dist)
        if not math.isfinite(score) or score<settings.retrieval_min_score: continue
        output.append(RetrievedChunk(doc,meta['source'],chunk_id,score,meta))
    return output
