"""使用假的外部客户端验证知识和实时两条端到端路径。"""

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.chat import AssistantDependencies
from app.config import load_settings
from app.main import create_app
from app.retrieval import build_index


class EmbeddingClient:
    """返回指定维度的固定向量，只验证检索流程，不衡量召回准确率。"""
    def __init__(self, dimension):
        self.dimension = dimension
        self.embeddings = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        texts = kwargs["input"]
        return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=[1.0] + [0.0] * (self.dimension - 1)) for i, _ in enumerate(texts)])


class RouterClient:
    """直接返回指定意图，让两条业务路径可稳定复现。"""
    def __init__(self, intent):
        self.intent = intent
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"intent": self.intent, "confidence": 0.99})))])


class AnswerStream:
    """模拟输出一个文本块后正常结束的模型流。"""
    def __init__(self):
        self.done = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.done:
            raise StopAsyncIteration
        self.done = True
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Smoke answer"))])

    async def aclose(self):
        pass


class AnswerClient:
    """为每个请求创建独立的回答流。"""
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        return AnswerStream()


def make_app(root, intent):
    """从临时目录创建应用，避免读写用户现有知识库索引。"""
    settings = load_settings(root)
    deps = AssistantDependencies(
        settings=settings,
        catalog=load_catalog(settings.catalog_path),
        router_client=RouterClient(intent),
        answer_client=AnswerClient(),
        embedding_client=EmbeddingClient(settings.embedding_dimension),
    )
    return create_app(deps)


def test_end_to_end_knowledge_and_realtime(tmp_path):
    """知识问题走 Chroma，实时问题走 Mock，并返回流式 token。"""
    root = tmp_path
    (root / "catalog").mkdir()
    shutil.copy((Path(__file__).resolve().parents[1] / "catalog" / "intent-tree-v1.json"), root / "catalog" / "intent-tree-v1.json")
    (root / "documents").mkdir()
    (root / "documents" / "faq.md").write_text("# 提现规则\n\n提现需要完成有效流水。", encoding="utf-8")
    settings = load_settings(root)
    build_index(settings, EmbeddingClient(settings.embedding_dimension))

    with TestClient(make_app(root, "sports.rules.odds.01")) as client:
        knowledge = client.post("/api/assistant/chat", json={"question": "赔率规则"})
    assert knowledge.status_code == 200
    assert '"data_source":"chroma"' in knowledge.text
    assert '"type":"token"' in knowledge.text

    with TestClient(make_app(root, "wallet.withdrawal.status.01")) as client:
        realtime = client.post("/api/assistant/chat", json={"question": "提现状态"})
    assert realtime.status_code == 200
    assert '"data_source":"mock_platform"' in realtime.text
