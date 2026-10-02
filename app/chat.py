"""聊天请求编排。

本模块把意图路由、实时 Mock 数据和 Chroma 检索串成一个统一上下文。
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field

from .catalog import Catalog
from .config import Settings
from .mock_platform import MockData, get_mock_data
from .retrieval import RetrievedChunk, classify_rule_scope, retrieve
from .router import IntentDecision, route_intent


_CASUAL_PATTERNS = (
    r"^(你好|您好|嗨|哈喽|hello|hi|hey|早上好|晚上好|晚安)[!！,，。.?？\s]*$",
    r"^(谢谢|感谢|辛苦了|多谢)[!！,，。.?？\s]*$",
    r"^(你是谁|你能做什么|你叫什么|在吗|陪我聊聊|讲个笑话)[!！,，。.?？\s]*$",
)


def is_casual_chat(question: str) -> bool:
    """识别明确的日常寒暄，避免把它们误当成平台业务查询。"""

    normalized = re.sub(r"\s+", "", question).strip().lower()
    return any(re.fullmatch(pattern, normalized) for pattern in _CASUAL_PATTERNS)


class AssistantRequest(BaseModel):
    """前端调用 `/api/assistant/chat` 时提交的请求体。"""

    question: str = Field(min_length=1)
    # 当前仅原样回传会话标识，不保存或自动加载历史对话。
    session_id: str | None = None
    page_context: dict[str, Any] = Field(default_factory=dict)
    # 原型由前端提供上下文；此字段不代表后端已认证的用户身份。
    user_context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = True


@dataclass
class AssistantDependencies:
    """API 编排所需的客户端和可替换适配器。"""

    settings: Settings
    catalog: Catalog
    router_client: Any
    answer_client: Any
    embedding_client: Any = None
    mock_data_fn: Callable[[str, dict[str, Any], dict[str, Any]], MockData] = get_mock_data


def _build_knowledge_context(chunks: list[RetrievedChunk]) -> dict[str, Any]:
    """把召回结果整理成平台规则优先的回答上下文。"""

    def rule_info(chunk: RetrievedChunk) -> tuple[str, int]:
        scope = chunk.metadata.get("rule_scope")
        priority = chunk.metadata.get("rule_priority")
        if scope is None or priority is None:
            return classify_rule_scope(chunk.content)
        return str(scope), int(priority)

    annotated = [(chunk, *rule_info(chunk)) for chunk in chunks]
    selected = sorted(
        annotated,
        key=lambda chunk: (
            -chunk[2],
            -(chunk[0].score if chunk[0].score is not None else -1),
        ),
    )[:5]
    platform_rules = [chunk.content for chunk, scope, _ in selected if scope == "platform"]
    industry_guidance = [
        chunk.content for chunk, scope, _ in selected if scope != "platform"
    ]
    references = [
        {
            "source": chunk.source,
            "chunk_id": chunk.chunk_id,
            "score": chunk.score,
            "content": chunk.content,
            "rule_scope": scope,
        }
        for chunk, scope, _ in selected
    ]
    return {
        "knowledge_chunks": [chunk.content for chunk, _, _ in selected],
        "platform_rules": platform_rules,
        "industry_guidance": industry_guidance,
        "references": references,
        "data_source": "chroma" if selected else "none",
    }


async def prepare_context(
    request: AssistantRequest,
    deps: AssistantDependencies,
) -> tuple[IntentDecision, dict[str, Any]]:
    """完成意图判断，并准备回答模型所需的可信上下文。"""

    # 同步 OpenAI 客户端放到线程中，避免阻塞 FastAPI 的事件循环。
    decision = await asyncio.to_thread(
        route_intent,
        request.question,
        request.page_context,
        request.user_context,
        deps.catalog,
        deps.router_client,
        deps.settings.deepseek_model,
        deps.settings.router_confidence_threshold,
    )
    context: dict[str, Any] = {
        "session_id": request.session_id,
        "references": [],
        "data_source": "none",
        "actions": [],
        "conversation_mode": "business",
    }
    if is_casual_chat(request.question):
        # 闲聊不触发平台数据查询，即使路由模型误选了业务意图也要回到安全的对话模式。
        decision = IntentDecision("global.fallback", decision.confidence, False, [], None)
        context["conversation_mode"] = "casual"
        return decision, context
    if decision.clarification:
        # 先澄清问题，此路径不访问 Mock 或向量库。
        return decision, context

    if decision.need_realtime_data:
        # 首版使用确定性的 Mock；未来只替换 mock_data_fn 即可接真实平台。
        mock: MockData = deps.mock_data_fn(decision.id, request.user_context, request.page_context)
        context.update(
            {
                "verified_data": mock.data,
                "data_source": mock.data_source,
                "actions": mock.actions or [],
            }
        )
        return decision, context

    chunks: list[RetrievedChunk] = []
    if deps.embedding_client is not None:
        # 检索同样是同步 SDK 调用，因此放到线程中执行。
        chunks = await asyncio.to_thread(retrieve, request.question, deps.settings, deps.embedding_client, 20)
    context.update(_build_knowledge_context(chunks))
    context["actions"] = [decision.action] if decision.action else []
    return decision, context
