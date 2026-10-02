"""针对外部模型、索引重建和流式生命周期的可靠性测试。"""

import asyncio
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as S

import pytest
from app.config import load_settings
from app.catalog import load_catalog
from app.router import route_intent, IntentDecision
from app.retrieval import build_index, retrieve, get_collection, _embeddings, iter_documents, chunk_document
from app.streaming import stream_answer

ROOT = Path(__file__).resolve().parents[1]

class Embeddings:
    """返回固定二维向量并记录调用，用于验证分批入库和响应校验。"""
    def __init__(self):
        self.calls = []
        self.embeddings = S(create=self.create)
    def create(self, **kw):
        self.calls.append(kw)
        return S(data=[S(index=i, embedding=[1.0, 0.0]) for i, t in enumerate(kw['input'])])

@pytest.mark.parametrize('payload', [[], None, {'intent':'made.up','confidence':1}, {'intent':'wallet.turnover.04','confidence':float('nan')}, {'intent':'wallet.turnover.04','confidence':2}])
def test_malformed_route_always_clarifies(payload):
    """异常模型输出不能绕过意图白名单或触发实时数据。"""
    llm=S(chat=S(completions=S(create=lambda **kw:S(choices=[S(message=S(content=json.dumps(payload)))]))))
    d=route_intent('question', {}, {}, load_catalog(ROOT/'catalog/intent-tree-v1.json'), llm)
    assert d.id=='global.fallback' and d.clarification and not d.need_realtime_data

def test_embeddings_request_dimension_and_batches(tmp_path):
    """Embedding 请求应按批次发送并携带目标维度。"""
    cfg=replace(load_settings(tmp_path), embedding_dimension=2)
    api=Embeddings()
    assert len(_embeddings(api,cfg,['x']*25))==25
    assert all(c['dimensions']==2 and len(c['input'])<=10 for c in api.calls)

@pytest.mark.parametrize('kind', ['missing','nonfinite','zero'])
def test_bad_embedding_rejected(tmp_path, kind):
    """缺失、非有限或全零向量都应被拒绝。"""
    cfg=replace(load_settings(tmp_path), embedding_dimension=2)
    vectors={'missing':[], 'nonfinite':[S(index=0,embedding=[float('nan'),0])], 'zero':[S(index=0,embedding=[0,0])]}
    api=S(embeddings=S(create=lambda **kw:S(data=vectors[kind])))
    with pytest.raises(ValueError): _embeddings(api,cfg,['x'])

def test_duplicate_names_are_distinct_and_heading_is_retained(tmp_path):
    """同名文件也要有不同 ID，并保留 Markdown 标题。"""
    for d in ['one','two']:
        (tmp_path/d).mkdir()
        (tmp_path/d/'faq.md').write_text('# Heading\n\nFirst paragraph.\n\nSecond paragraph.',encoding='utf-8')
    chunks=[c for doc in iter_documents(tmp_path) for c in chunk_document(doc)]
    assert len(set(c.id for c in chunks))==len(chunks)
    assert all(c.metadata.get('title')=='Heading' for c in chunks)

def test_failed_rebuild_keeps_old_index(tmp_path):
    """新索引构建失败时，旧索引仍应可查询。"""
    cfg=replace(load_settings(tmp_path),embedding_dimension=2)
    cfg.documents_dir.mkdir()
    doc=cfg.documents_dir/'test.md'
    doc.write_text('old knowledge',encoding='utf-8')
    build_index(cfg,Embeddings())
    doc.write_text('new knowledge',encoding='utf-8')
    def broken(**kw): raise RuntimeError('service down')
    with pytest.raises(RuntimeError): build_index(cfg,S(embeddings=S(create=broken)))
    found=retrieve('x',cfg,Embeddings())
    assert found and 'old knowledge' in found[0].content

@pytest.mark.asyncio
async def test_sdk_close_and_done_metadata():
    """验证生成器提前关闭时，支持调用 SDK 风格的异步 close 方法。"""
    class Stream:
        closed=False
        def __aiter__(self): return self
        async def __anext__(self): return S(choices=[S(delta=S(content='x'),finish_reason=None)])
        async def close(self): self.closed=True
    stream=Stream()
    async def create(**kw): return stream
    llm=S(chat=S(completions=S(create=create)))
    gen=stream_answer('x',IntentDecision('test',1,True,[],None),{'data_source':'mock_platform','verified_data':{'x':1}},llm)
    await anext(gen)
    await anext(gen)
    # 继续消费一个 token，确保从模型流迭代过程中提前关闭。
    if not hasattr(llm,'consumed'): await anext(gen)
    await gen.aclose()
    assert stream.closed

@pytest.mark.asyncio
async def test_no_evidence_never_calls_model():
    """无召回依据时直接返回安全提示，不调用回答模型。"""
    async def create(**kw): raise AssertionError('no evidence must not generate')
    d=IntentDecision('sports.rules.odds.01',1,False,[],None)
    events=[e async for e in stream_answer('x',d,{'data_source':'none','references':[]},S(chat=S(completions=S(create=create))))]
    assert events[-1]['type']=='done' and events[-1]['references']==[]
    assert '确认' in events[-1]['answer']

@pytest.mark.asyncio
async def test_errors_do_not_expose_upstream_secrets():
    """上游错误事件不能把 Bearer/API Key 原文返回给客户端。"""
    async def create(**kw): raise RuntimeError('Authorization Bearer sk-test-secret /private/config')
    d=IntentDecision('test',1,True,[],None)
    events=[e async for e in stream_answer('x',d,{'data_source':'mock_platform','verified_data':{'x':1}},S(chat=S(completions=S(create=create))))]
    assert events[-1]['type']=='error' and 'sk-test-secret' not in json.dumps(events)
