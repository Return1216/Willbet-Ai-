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
    question: str = Field(min_length=1)
    session_id: str | None = None
    page_context: dict[str, Any] = Field(default_factory=dict)
    user_context: dict[str, Any] = Field(default_factory=dict)
    stream: bool = True


@dataclass
class AssistantDependencies:
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
        return decision, context

    if decision.need_realtime_data:
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
        chunks = await asyncio.to_thread(retrieve, request.question, deps.settings, deps.embedding_client, 20)
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
