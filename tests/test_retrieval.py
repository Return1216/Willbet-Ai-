"""文档发现、分块和空集合检索测试。"""

from pathlib import Path
from types import SimpleNamespace

from app.config import load_settings
from app.retrieval import SourceDocument, chunk_document, iter_documents, retrieve


def test_iter_documents_ignores_unsupported_files(tmp_path):
    """只读取 Markdown/TXT，忽略 PDF 等不支持格式。"""
    (tmp_path / "guide.md").write_text("# 充值\n\n充值需要完成验证。", encoding="utf-8")
    (tmp_path / "faq.txt").write_text("提现需要有效流水。", encoding="utf-8")
    (tmp_path / "ignored.pdf").write_bytes(b"pdf")

    docs = list(iter_documents(tmp_path))

    assert [doc.path.name for doc in docs] == ["faq.txt", "guide.md"]


def test_chunk_document_keeps_source_and_ordinal():
    """分块应保留来源和顺序元数据。"""
    doc = SourceDocument(Path("guide.md"), "第一段。\n\n第二段。\n\n第三段。")

    chunks = chunk_document(doc, max_chars=6, overlap=0)

    assert chunks
    assert chunks[0].metadata["source"] == "guide.md"
    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[0].metadata["rule_scope"] == "industry"
    assert all(chunk.text for chunk in chunks)


def test_chunk_document_prioritizes_explicit_platform_rules():
    """包含平台生效描述的片段应标记为平台规则。"""
    doc = SourceDocument(Path("guide.md"), "WillBet 平台当前以系统返回结果为准。")

    chunks = chunk_document(doc, max_chars=100, overlap=0)

    assert chunks[0].metadata["rule_scope"] == "platform"
    assert chunks[0].metadata["rule_priority"] > 0


def test_retrieve_empty_collection_returns_empty_list(monkeypatch, tmp_path):
    """空集合查询返回空列表，不应抛出异常。"""
    class EmptyCollection:
        def count(self):
            return 0

    monkeypatch.setattr("app.retrieval.get_collection", lambda settings: EmptyCollection())
    settings = load_settings(tmp_path)
    client = SimpleNamespace(embeddings=SimpleNamespace(create=lambda **kwargs: None))

    assert retrieve("问题", settings, client) == []
