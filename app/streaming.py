from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from .router import IntentDecision


def sse_encode(event: dict[str, Any] | str) -> str:
    payload = event if isinstance(event, str) else json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    return f"data: {payload}\n\n"


def _content_from_chunk(chunk: Any) -> str:
    choices = getattr(chunk, "choices", None) or []
    if not choices:
        return ""
    delta = getattr(choices[0], "delta", None)
    return str(getattr(delta, "content", None) or "")


def _answer_messages(question: str, context: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是 WillBet AI。只根据提供的已验证数据或知识片段回答。"
                "不能自行编造余额、流水、订单状态、时间或金额。"
                "如果上下文没有依据，明确说明暂时没有找到依据。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {"question": question, "context": context},
                ensure_ascii=False,
            ),
        },
    ]


async def stream_answer(
    question: str,
    decision: IntentDecision,
    context: dict[str, Any],
    llm_client: Any,
    model: str = "deepseek-chat",
) -> AsyncIterator[dict[str, Any]]:
    yield {
        "type": "intent",
        "intent": {
            "id": decision.id,
            "confidence": decision.confidence,
            "need_realtime_data": decision.need_realtime_data,
        },
    }
    if decision.clarification:
        yield {"type": "clarification", "content": decision.clarification}
        yield {
            "type": "done",
            "session_id": context.get("session_id"),
            "answer": decision.clarification,
            "references": context.get("references", []),
            "data_source": context.get("data_source", "none"),
            "actions": context.get("actions", []),
        }
        return

    upstream = None
    answer = ""
    try:
        upstream = await llm_client.chat.completions.create(
            model=model,
            messages=_answer_messages(question, context),
            temperature=0.2,
            stream=True,
        )
        async for chunk in upstream:
            content = _content_from_chunk(chunk)
            if content:
                answer += content
                yield {"type": "token", "content": content}
        yield {
            "type": "done",
            "session_id": context.get("session_id"),
            "answer": answer,
            "references": context.get("references", []),
            "data_source": context.get("data_source", "none"),
            "actions": context.get("actions", []),
        }
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        yield {"type": "error", "message": str(exc)}
    finally:
        if upstream is not None:
            close = getattr(upstream, "aclose", None)
            if close is not None:
                await close()

async def collect_answer(
    question: str,
    decision: IntentDecision,
    context: dict[str, Any],
    llm_client: Any,
    model: str = "deepseek-chat",
) -> dict[str, Any]:
    final: dict[str, Any] = {}
    async for event in stream_answer(question, decision, context, llm_client, model):
        if event["type"] in {"done", "error", "clarification"}:
            final = event if event["type"] != "clarification" else {"answer": event["content"]}
    return final
