"""DeepSeek 流式回答和 SSE 事件转换。"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from collections.abc import AsyncIterator
from typing import Any

from .router import IntentDecision


def sse_encode(event: dict[str, Any] | str) -> str:
    """把一个事件编码成浏览器可消费的 SSE data 帧。"""

    payload = event if isinstance(event, str) else json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    return f"data: {payload}\n\n"


def _content_from_chunk(chunk: Any) -> str:
    """从 OpenAI Chat Completions 流式 chunk 提取增量文本。"""

    choices = getattr(chunk, "choices", None) or []
    if not choices:
        return ""
    delta = getattr(choices[0], "delta", None)
    return str(getattr(delta, "content", None) or "")


def _answer_messages(question: str, context: dict[str, Any]) -> list[dict[str, str]]:
    """生成兼顾自然语气和事实边界的回答提示词。"""

    return [
        {
            "role": "system",
            "content": (
                "你是 WillBet AI，一位耐心、真诚、懂业务的中文陪伴助手。"
                "回答语气温和、自然、有温度，先回应用户真正想解决的问题，再给清晰结论和下一步建议；"
                "避免机械复述、冷冰冰的模板句和不必要的长篇大论。"
                "业务问题必须遵守证据优先：verified_data 是平台实时数据的唯一依据，"
                "knowledge_chunks 和 references 是平台规则与说明的依据。"
                "不能编造余额、流水、订单状态、时间、金额、赔率或任何平台事实；"
                "知识片段没有覆盖时要坦诚说明暂时没有找到依据，并引导用户补充信息或联系客服。"
                "当 conversation_mode 为 casual 时，可以自然进行问候、感谢和日常聊天，"
                "但不要把闲聊内容说成平台事实，也不要借闲聊猜测用户账户状态。"
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


def _has_evidence(context: dict[str, Any]) -> bool:
    """判断上下文是否包含 Mock 数据或有效知识片段。"""

    return bool(
        context.get("references")
        or context.get("knowledge_chunks")
        or context.get("verified_data")
    )


def _safe_error_message(exc: Exception) -> str:
    """遮盖 Authorization Bearer 和 sk- 前缀令牌，保留其余错误文本。"""

    # 这里只匹配下面两类格式，不是针对任意密钥和敏感路径的通用过滤器。
    message = str(exc)
    sanitized = re.sub(r"(?i)(authorization\s+bearer\s+)[^\s]+", r"\1[redacted]", message)
    sanitized = re.sub(r"\bsk-[A-Za-z0-9_-]+\b", "[redacted]", sanitized)
    return sanitized


async def stream_answer(
    question: str,
    decision: IntentDecision,
    context: dict[str, Any],
    llm_client: Any,
    model: str = "deepseek-flash",
) -> AsyncIterator[dict[str, Any]]:
    """产生路由、澄清或答案事件；SSE 的 [DONE] 标记由 main.py 添加。"""

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

    if (
        context.get("data_source") == "none"
        and not _has_evidence(context)
        and context.get("conversation_mode") != "casual"
    ):
        # 没有依据时不调用回答模型，避免模型凭空编造业务数据。
        answer = "暂时没有找到足够的依据来回答这个问题。"
        yield {"type": "token", "content": answer}
        yield {
            "type": "done",
            "session_id": context.get("session_id"),
            "answer": answer,
            "references": [],
            "data_source": "none",
            "actions": context.get("actions", []),
        }
        return

    upstream = None
    answer = ""
    try:
        upstream = await llm_client.chat.completions.create(
            model=model,
            messages=_answer_messages(question, context),
            temperature=0.45,
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
        yield {"type": "error", "message": _safe_error_message(exc)}
    finally:
        if upstream is not None:
            # OpenAI SDK 和测试替身分别可能提供 aclose 或 close。
            close = getattr(upstream, "aclose", None) or getattr(upstream, "close", None)
            if close is not None:
                result = close()
                if inspect.isawaitable(result):
                    await result

async def collect_answer(
    question: str,
    decision: IntentDecision,
    context: dict[str, Any],
    llm_client: Any,
    model: str = "deepseek-flash",
) -> dict[str, Any]:
    """消费完整事件流，提取非流式接口需要的最终事件。"""

    final: dict[str, Any] = {}
    async for event in stream_answer(question, decision, context, llm_client, model):
        if event["type"] in {"done", "error", "clarification"}:
            final = event if event["type"] != "clarification" else {"answer": event["content"]}
    return final
