"""SSE 事件顺序、错误和上游流关闭测试。"""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.router import IntentDecision
from app.streaming import _answer_messages, sse_encode, stream_answer


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


def test_answer_prompt_requires_warm_tone_and_evidence_priority():
    """回答提示词应同时约束语气和业务事实边界。"""
    messages = _answer_messages(
        "为什么还不能提现？",
        {
            "data_source": "chroma",
            "knowledge_chunks": ["有效流水规则"],
            "conversation_mode": "business",
        },
    )
    system = messages[0]["content"]
    assert "温和" in system
    assert "实时数据" in system
    assert "知识片段" in system
    assert "不能编造" in system


def test_answer_prompt_hides_internal_sources_and_resolves_rule_scope():
    """回答模型只接收整理后的证据，并以平台规则作为唯一业务结论。"""
    messages = _answer_messages(
        "为什么不能提现？",
        {
            "data_source": "chroma",
            "verified_data": {"remaining_turnover": "45 USDT"},
            "platform_rules": ["WillBet 需要完成剩余有效流水后才能提现。"],
            "industry_guidance": ["行业中通常也会设置流水条件。"],
            "references": [{"source": "internal.md", "content": "不要直接暴露"}],
            "knowledge_chunks": ["不要直接暴露"],
        },
    )
    system = messages[0]["content"]
    payload = json.loads(messages[1]["content"])

    assert "不要向用户提及" in system
    assert "平台规则优先" in system
    assert "references" not in payload["context"]
    assert "knowledge_chunks" not in payload["context"]
    assert payload["context"]["platform_rules"] == ["WillBet 需要完成剩余有效流水后才能提现。"]
    assert payload["context"]["industry_guidance"] == ["行业中通常也会设置流水条件。"]


@pytest.mark.asyncio
async def test_casual_mode_without_evidence_uses_answer_model():
    """日常闲聊没有知识片段时仍应交给回答模型自然处理。"""
    client = FakeClient(["你好，很高兴认识你！"])
    events = [event async for event in stream_answer(
        "你好",
        IntentDecision("global.fallback", 0.99, False, [], None),
        {"data_source": "none", "conversation_mode": "casual"},
        client,
    )]

    assert events[-1]["type"] == "done"
    assert events[-1]["answer"] == "你好，很高兴认识你！"
