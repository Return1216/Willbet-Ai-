import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.chat import AssistantDependencies
from app.config import load_settings
from app.main import create_app


class RouterClient:
    def __init__(self, payload):
        self.payload = payload
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))])


class AnswerStream:
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
    def __init__(self, content="答案"):
        self.content = content
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        return AnswerStream(self.content)


def make_app(router_payload, answer_client=None):
    root = Path(r"C:\Users\Lyy\Desktop\RAG_AGENT")
    settings = load_settings(root)
    deps = AssistantDependencies(
        settings=settings,
        catalog=load_catalog(settings.catalog_path),
        router_client=RouterClient(router_payload),
        answer_client=answer_client or AnswerClient(),
        embedding_client=None,
    )
    return create_app(deps)


def test_streaming_chat_returns_sse_events():
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
    app = make_app({"intent": "wallet.withdrawal.status.01", "confidence": 0.95})
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"question": "提现到哪里了？", "stream": False})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "答案"
    assert body["intent"]["id"] == "wallet.withdrawal.status.01"
    assert body["data_source"] == "mock_platform"


def test_low_confidence_does_not_call_mock_data():
    app = make_app({"intent": "wallet.withdrawal.status.01", "confidence": 0.50})
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"question": "不能提现"})

    assert response.status_code == 200
    assert '"type":"clarification"' in response.text
    assert 'mock_platform' not in response.text

class FailingAnswerClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        raise RuntimeError("answer provider unavailable")


def test_streaming_upstream_error_is_an_event():
    app = make_app({"intent": "wallet.withdrawal.status.01", "confidence": 0.95}, FailingAnswerClient())
    with TestClient(app) as client:
        response = client.post("/api/assistant/chat", json={"question": "提现到哪里了？"})

    assert response.status_code == 200
    assert '"type":"error"' in response.text
    assert "answer provider unavailable" in response.text
