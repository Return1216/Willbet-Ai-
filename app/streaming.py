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


def _model_context(context: dict[str, Any]) -> dict[str, Any]:
    """只把整理后的证据交给模型，隐藏检索实现字段。"""

    industry_guidance = context.get("industry_guidance")
    if industry_guidance is None:
        industry_guidance = context.get("knowledge_chunks", [])
    return {
        "conversation_mode": context.get("conversation_mode", "business"),
        "verified_data": context.get("verified_data", {}),
        "platform_rules": context.get("platform_rules", []),
        "industry_guidance": industry_guidance,
        "actions": context.get("actions", []),
    }


def _answer_messages(question: str, context: dict[str, Any]) -> list[dict[str, str]]:
    """生成兼顾自然语气和事实边界的回答提示词。"""

    return [
        {
            "role": "system",
            "content": (
                "你是 WillBet 官方 AI 助手，一位耐心、真诚、懂业务的中文陪伴助手。"
                "你站在 WillBet 内部向用户提供帮助；平台称呼统一使用 WillBet 平台或我们平台，"
                "禁止使用“你们平台”“你们系统”“你们客服”等外部视角称呼。"
                "回答语气温和、自然、有温度，先回应用户真正想解决的问题，再给清晰结论和下一步建议；"
                "避免机械复述、冷冰冰的模板句和不必要的长篇大论。"
                "你收到的是内部证据，只能用来组织面向用户的回答；不要向用户提及知识库、检索、"
                "上下文、参考片段、knowledge_chunks、references 或模型判断等内部实现。"
                "知识片段只作为内部证据使用，不是回答对象。"
                "业务事实优先级固定为：verified_data（平台实时数据）最高，其次是 platform_rules，最后是 industry_guidance。"
                "platform_rules 非空时，只能以平台规则给出最终业务结论；industry_guidance 只能补充术语或背景，"
                "不能和平台规则并列成另一个结论。也就是说，平台规则优先。"
                "不能编造余额、流水、订单状态、时间、金额、赔率或任何平台事实。"
                "证据不足时，要自然说明暂时无法确认，并引导用户补充页面提示、订单信息或联系客服。"
                "同一个问题只给一个明确结论，不要把互相冲突的规则都交给用户自己选择。"
                "当 conversation_mode 为 casual 时，可以自然进行问候、感谢和日常聊天，"
                "但不要把闲聊内容说成平台事实，也不要借闲聊猜测用户账户状态。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {"question": question, "context": _model_context(context)},
                ensure_ascii=False,
            ),
        },
    ]


def _has_evidence(context: dict[str, Any]) -> bool:
    """判断上下文是否包含 Mock 数据或有效知识片段。"""

    return bool(
        context.get("references")
        or context.get("knowledge_chunks")
        or context.get("platform_rules")
        or context.get("industry_guidance")
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
        answer = "我暂时还无法确认这件事。你可以补充页面提示、订单信息或所在功能，我再帮你一起核对。"
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
