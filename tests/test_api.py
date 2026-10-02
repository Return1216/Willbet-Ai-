"""FastAPI 接口的流式、非流式、低置信度和错误路径测试。"""

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.chat import AssistantDependencies
from app.config import load_settings
from app.main import create_app


class RouterClient:
    """返回指定 JSON 的同步路由替身，不请求远程模型。"""
    def __init__(self, payload):
        self.payload = payload
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))])


class AnswerStream:
    """只产生一个文本块的异步流，并记录是否已被关闭。"""
    def __init__(self, content="答案"):
        self.content = content
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.content is None:
            raise StopAsyncIteration
        content, self.content = self.content, None
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])

    async def aclose(self):
        self.closed = True


class AnswerClient:
    """模拟异步 OpenAI 客户端的 chat.completions.create 接口。"""
    def __init__(self, content="答案"):
        self.content = content
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        return AnswerStream(self.content)


def make_app(router_payload, answer_client=None, embedding_client=None):
    """构造带固定路由和回答替身的 FastAPI 应用。"""
    # 使用假的路由和回答客户端，测试 HTTP 编排而不依赖远程模型。
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root)
    deps = AssistantDependencies(
        settings=settings,
        catalog=load_catalog(settings.catalog_path),
        router_client=RouterClient(router_payload),
        answer_client=answer_client or AnswerClient(),
        embedding_client=embedding_client,
    )
    return create_app(deps)


def test_streaming_chat_returns_sse_events():
    """默认请求应返回合法的 SSE 事件流。"""
    app = make_app({"intent": "wallet.withdrawal.status.01", "confidence": 0.95})
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"question": "提现到哪里了？", "user_context": {"user_id": "demo"}})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type":"intent"' in response.text
    assert '"type":"token"' in response.text
    assert '"type":"done"' in response.text
    assert '"data_source":"mock_platform"' in response.text


def test_non_stream_chat_returns_final_json():
    """stream=false 应返回带意图和最终答案的 JSON。"""
    app = make_app({"intent": "wallet.withdrawal.status.01", "confidence": 0.95})
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"question": "提现到哪里了？", "stream": False})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "答案"
    assert body["intent"]["id"] == "wallet.withdrawal.status.01"
    assert body["data_source"] == "mock_platform"


def test_low_confidence_does_not_call_mock_data():
    """低置信度路由只澄清，不读取实时数据。"""
    app = make_app({"intent": "wallet.withdrawal.status.01", "confidence": 0.50})
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"question": "不能提现"})

    assert response.status_code == 200
    assert '"type":"clarification"' in response.text
    assert 'mock_platform' not in response.text


def test_casual_chat_uses_answer_model_without_knowledge():
    """问候语不应被固定的无依据提示拦截。"""
    app = make_app({"intent": "global.fallback", "confidence": 0.99})
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"question": "你好"})

    assert response.status_code == 200
    assert '"type":"token"' in response.text
    assert "答案" in response.text


def test_casual_chat_skips_embedding_retrieval(monkeypatch):
    """闲聊即使配置了 Embedding，也不能召回无关知识片段。"""
    def fail_retrieve(*args, **kwargs):
        raise AssertionError("casual chat should not retrieve knowledge")

    monkeypatch.setattr("app.chat.retrieve", fail_retrieve)
    app = make_app({"intent": "global.fallback", "confidence": 0.99}, embedding_client=object())
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"question": "你好"})

    assert response.status_code == 200
    assert '"data_source":"none"' in response.text

class FailingAnswerClient:
    """模拟模型请求失败，供 SSE 错误路径测试。"""
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        raise RuntimeError("answer provider unavailable")


def test_streaming_upstream_error_is_an_event():
    """回答模型失败时，SSE 仍返回结构化 error 事件。"""
    app = make_app({"intent": "wallet.withdrawal.status.01", "confidence": 0.95}, FailingAnswerClient())
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"question": "提现到哪里了？"})

    assert response.status_code == 200
    assert '"type":"error"' in response.text
    assert "answer provider unavailable" in response.text
