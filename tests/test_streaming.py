import asyncio
import json
from types import SimpleNamespace

import pytest

from app.router import IntentDecision
from app.streaming import sse_encode, stream_answer


class FakeStream:
    def __init__(self, contents):
        self.contents = list(contents)
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.contents:
            raise StopAsyncIteration
        content = self.contents.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])

    async def aclose(self):
        self.closed = True


class FakeClient:
    def __init__(self, contents):
        self.stream = FakeStream(contents)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        return self.stream


class FailingClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        raise RuntimeError("upstream unavailable")


def decision():
    return IntentDecision("wallet.withdrawal.status.01", 0.92, True, ["user_id"], None)


@pytest.mark.asyncio
async def test_stream_emits_intent_tokens_done_and_sse_is_valid():
    client = FakeClient(["你的提现", "正在处理中。"])
    events = [event async for event in stream_answer(
        "提现到哪里了？", decision(), {
            "session_id": "s1", "references": [], "data_source": "mock_platform", "actions": []
        }, client,
    )]

    assert [event["type"] for event in events] == ["intent", "token", "token", "done"]
    assert events[-1]["session_id"] == "s1"
    assert json.loads(sse_encode(events[1])[6:]) == events[1]


@pytest.mark.asyncio
async def test_stream_error_is_structured():
    events = [event async for event in stream_answer("问题", decision(), {}, FailingClient())]
    assert events[-1]["type"] == "error"
    assert "upstream unavailable" in events[-1]["message"]


@pytest.mark.asyncio
async def test_closing_generator_closes_upstream_stream():
    client = FakeClient(["token"])
    generator = stream_answer("问题", decision(), {}, client)
    assert (await generator.__anext__())["type"] == "intent"
    assert (await generator.__anext__())["type"] == "token"
    await generator.aclose()
    assert client.stream.closed is True

@pytest.mark.asyncio
async def test_collect_answer_returns_done_payload():
    from app.streaming import collect_answer

    client = FakeClient(["完成"])
    payload = await collect_answer("问题", decision(), {"session_id": "s2"}, client)

    assert payload["answer"] == "完成"
    assert payload["session_id"] == "s2"
