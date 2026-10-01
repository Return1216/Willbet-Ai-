"""FastAPI 应用入口。

这里负责 HTTP、CORS 和 SSE 响应，业务编排委托给 `chat` 与 `streaming` 模块。
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from openai import AsyncOpenAI, OpenAI

from .catalog import load_catalog
from .chat import AssistantDependencies, AssistantRequest, prepare_context
from .config import Settings, load_settings
from .streaming import _safe_error_message, collect_answer, sse_encode, stream_answer


def _client_key(value: str) -> str:
    """让应用可以启动并提供健康检查，真正调用时仍会由服务端校验密钥。"""

    return value or "missing-key-for-local-startup"


def _default_dependencies(settings: Settings) -> AssistantDependencies:
    """创建生产路径使用的同步路由、异步回答和 Embedding 客户端。"""

    return AssistantDependencies(
        settings=settings,
        catalog=load_catalog(settings.catalog_path),
        router_client=OpenAI(
            api_key=_client_key(settings.deepseek_api_key),
            base_url=settings.deepseek_base_url,
        ),
        answer_client=AsyncOpenAI(
            api_key=_client_key(settings.deepseek_api_key),
            base_url=settings.deepseek_base_url,
        ),
        embedding_client=OpenAI(
            api_key=_client_key(settings.embedding_api_key),
            base_url=settings.embedding_base_url,
        ),
    )


def create_app(deps: AssistantDependencies | None = None) -> FastAPI:
    """创建 FastAPI 实例；传入依赖可用于测试或替换平台适配器。"""

    settings = deps.settings if deps else load_settings()
    deps = deps or _default_dependencies(settings)
    app = FastAPI(title="RAG_AGENT", version="0.1.0")
    app.state.dependencies = deps
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["*"]
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """返回进程存活状态，不触发模型或向量库调用。"""

        return {"status": "ok"}

    @app.post("/api/assistant/chat")
    async def chat(request: AssistantRequest):
        """统一聊天接口：默认 SSE，`stream=false` 返回最终 JSON。"""

        if request.stream:
            async def event_stream() -> AsyncIterator[str]:
                # 生成器会在浏览器断开时收到取消信号，并由下游关闭模型流。
                try:
                    decision, context = await prepare_context(request, deps)
                    async for event in stream_answer(
                        request.question,
                        decision,
                        context,
                        deps.answer_client,
                        settings.deepseek_model,
                    ):
                        yield sse_encode(event)
                    yield sse_encode("[DONE]")
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    yield sse_encode({"type": "error", "message": _safe_error_message(exc)})
                    yield sse_encode("[DONE]")

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        try:
            decision, context = await prepare_context(request, deps)
            payload = await collect_answer(
                request.question,
                decision,
                context,
                deps.answer_client,
                settings.deepseek_model,
            )
            payload["intent"] = {
                "id": decision.id,
                "confidence": decision.confidence,
                "need_realtime_data": decision.need_realtime_data,
            }
            return JSONResponse(payload)
        except Exception as exc:
            return JSONResponse({"type": "error", "message": _safe_error_message(exc)}, status_code=502)

    return app


app = create_app()
