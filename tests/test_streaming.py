"""SSE 事件顺序、错误和上游流关闭测试。"""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.router import IntentDecision
from app.streaming import sse_encode, stream_answer


class FakeStream:
    """按给定顺序输出文本，记录关闭状态以验证资源释放。"""
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
    """返回预设流的异步模型客户端替身。"""
    def __init__(self, contents):
        self.stream = FakeStream(contents)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        return self.stream


class FailingClient:
    """创建流时直接抛异常，模拟上游不可用。"""
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        raise RuntimeError("upstream unavailable")


def decision():
    """构造这些流式测试共用的已识别提现意图。"""
    return IntentDecision("wallet.withdrawal.status.01", 0.92, True, ["user_id"], None)


@pytest.mark.asyncio
async def test_stream_emits_intent_tokens_done_and_sse_is_valid():
    """正常回答应先发意图，再发 token，最后发 done。"""
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
    """模型异常应转换为 error 事件，而不是让连接崩溃。"""
    events = [event async for event in stream_answer("问题", decision(), {}, FailingClient())]
    assert events[-1]["type"] == "error"
    assert "upstream unavailable" in events[-1]["message"]


@pytest.mark.asyncio
async def test_closing_generator_closes_upstream_stream():
    """客户端断开时，服务端要释放上游流。"""
    client = FakeClient(["token"])
    generator = stream_answer("问题", decision(), {}, client)
    assert (await generator.__anext__())["type"] == "intent"
    assert (await generator.__anext__())["type"] == "token"
    await generator.aclose()
    assert client.stream.closed is True

@pytest.mark.asyncio
async def test_collect_answer_returns_done_payload():
    """非流式收集器应返回完整答案和会话 ID。"""
    from app.streaming import collect_answer

    client = FakeClient(["完成"])
    payload = await collect_answer("问题", decision(), {"session_id": "s2"}, client)

    assert payload["answer"] == "完成"
    assert payload["session_id"] == "s2"
