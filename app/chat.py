"""聊天请求编排。

本模块把意图路由、实时 Mock 数据和 Chroma 检索串成一个统一上下文。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field

from .catalog import Catalog
from .config import Settings
from .mock_platform import MockData, get_mock_data
from .retrieval import RetrievedChunk, retrieve
from .router import IntentDecision, route_intent


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
    }
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
    # 对外只暴露前 5 个片段；完整召回数量由检索层控制。
    references = [
        {
            "source": chunk.source,
            "chunk_id": chunk.chunk_id,
            "score": chunk.score,
            "content": chunk.content,
        }
        for chunk in chunks[:5]
    ]
    context.update(
        {
            "knowledge_chunks": [chunk.content for chunk in chunks[:5]],
            "references": references,
            "data_source": "chroma" if chunks else "none",
            "actions": [decision.action] if decision.action else [],
        }
    )
    return decision, context
