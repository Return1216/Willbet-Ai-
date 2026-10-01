# RAG_AGENT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local Python RAG service with DeepSeek intent routing, Qwen-compatible embeddings, Chroma retrieval, all-intent Mock platform data, and SSE streaming through `POST /api/assistant/chat`.

**Architecture:** FastAPI owns one assistant endpoint. A catalog-backed router asks DeepSeek for a validated intent JSON; realtime intents use a deterministic Mock adapter, while knowledge intents use Qwen embeddings and Chroma. A final DeepSeek call streams answer tokens as SSE and sends references, data source, actions, and session metadata in a final `done` event.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Pydantic, OpenAI-compatible Python client, Chroma, python-dotenv, pytest.

**Spec:** `C:\Users\Lyy\Desktop\RAG_AGENT\docs\superpowers\specs\2026-10-01-rag-agent-design.md`

## Global Constraints

- Run locally on Windows.
- Read only `.md` and `.txt` files from `documents/`.
- Use Qwen-compatible `text-embedding-v3` with dimension `1024`.
- Use persistent Chroma storage under `storage/chroma/`.
- Use the 127-intent `intent-tree-v1.json` catalog.
- Default endpoint is `POST /api/assistant/chat` with SSE output.
- `stream=false` returns the same final payload as JSON.
- First release uses deterministic Mock platform data for all intents.
- Rerank is not called in the first release, but the retrieval boundary must leave a replacement point.
- Secrets stay in `.env` and never enter responses or frontend code.

## Review Focus

- Invalid or hallucinated intent IDs must fall back instead of invoking a data source; test in Task 2.
- Low-confidence routing must emit `clarification` and no realtime call; test in Task 2 and Task 6.
- Empty documents and no-match retrieval must return an explicit no-evidence result; test in Task 3.
- Upstream DeepSeek/embedding errors must produce a structured SSE `error` event; test in Task 5 and Task 6.
- Client disconnect must stop streaming and avoid continuing model consumption; test in Task 5.

---

### Task 1: Project scaffold and configuration

**Files:**
- Create: `C:\Users\Lyy\Desktop\RAG_AGENT\app\__init__.py`
- Create: `C:\Users\Lyy\Desktop\RAG_AGENT\app\config.py`
- Create: `C:\Users\Lyy\Desktop\RAG_AGENT\requirements.txt`
- Create: `C:\Users\Lyy\Desktop\RAG_AGENT\.env.example`
- Create: `C:\Users\Lyy\Desktop\RAG_AGENT\catalog\intent-tree-v1.json` (copy existing catalog)
- Create: `C:\Users\Lyy\Desktop\RAG_AGENT\documents\.gitkeep`
- Create: `C:\Users\Lyy\Desktop\RAG_AGENT\storage\chroma\.gitkeep`
- Test: `C:\Users\Lyy\Desktop\RAG_AGENT\tests\test_config.py`

**Interfaces:**
- Produce `Settings` with DeepSeek, embedding, Chroma, catalog, documents, and `ROUTER_CONFIDENCE_THRESHOLD=0.75` values.
- Produce `load_settings() -> Settings` that reads `.env` and validates required keys only when the corresponding feature is called.

- [ ] **Step 1: Write the failing configuration test**

Assert that defaults point to `documents/`, `storage/chroma/`, and threshold `0.75`, while API keys come from environment variables.

- [ ] **Step 2: Run the test and confirm it fails**

Run: `pytest tests/test_config.py -q`
Expected: FAIL because `app.config` does not exist.

- [ ] **Step 3: Implement the minimal settings module and dependency list**

Use `pydantic-settings` or a small Pydantic model with `python-dotenv`; do not make import-time API calls.

- [ ] **Step 4: Run the test and confirm it passes**

Run: `pytest tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 5: Checkpoint the scaffold**

If the directory is initialized as Git, commit with `chore: scaffold rag agent configuration`.

### Task 2: Catalog loader and DeepSeek intent router

**Files:**
- Create: `app/catalog.py`
- Create: `app/router.py`
- Test: `tests/test_router.py`

**Interfaces:**
- `load_catalog(path: Path) -> Catalog`
- `route_intent(question: str, page_context: dict, user_context: dict, catalog: Catalog, llm_client) -> IntentDecision`
- `IntentDecision` fields: `id: str`, `confidence: float`, `need_realtime_data: bool`, `required_context: list[str]`, `action: dict | None`, `clarification: str | None`.

- [ ] **Step 1: Write tests for valid routing, invalid IDs, and low confidence**

Use a fake LLM response for `wallet.withdrawal.status.01`; assert it is accepted. Return an unknown ID and assert `global.fallback`. Return confidence `0.50` and assert `clarification` is populated and realtime is disabled.

- [ ] **Step 2: Run `pytest tests/test_router.py -q` and confirm failure**

Expected: FAIL because the loader and router are missing.

- [ ] **Step 3: Implement catalog loading and strict decision validation**

Load only the compact routing fields (`id`, `domain`, `group`, `name`, `examples`, `need_realtime_data`, `required_context`, `action`). Build the DeepSeek prompt from the catalog and request JSON output. Validate IDs against the catalog before returning a decision.

- [ ] **Step 4: Run tests and confirm pass**

Run: `pytest tests/test_router.py -q`
Expected: PASS.

### Task 3: Markdown/TXT ingestion and Chroma retrieval

**Files:**
- Create: `app/ingest.py`
- Create: `app/retrieval.py`
- Test: `tests/test_retrieval.py`

**Interfaces:**
- `iter_documents(root: Path) -> Iterator[SourceDocument]`
- `chunk_document(document: SourceDocument, max_chars: int = 1200, overlap: int = 150) -> list[Chunk]`
- `build_index(settings: Settings, embedding_client) -> int`
- `retrieve(question: str, settings: Settings, embedding_client, top_k: int = 20) -> list[RetrievedChunk]`
- `RetrievedChunk` fields: `content`, `source`, `chunk_id`, `score`, `metadata`.

- [ ] **Step 1: Write tests for Markdown/TXT discovery, chunk metadata, and empty retrieval**

Create temporary Markdown/TXT files; assert unsupported extensions are ignored, each chunk keeps filename and ordinal metadata, and an empty collection returns `[]` without crashing.

- [ ] **Step 2: Run `pytest tests/test_retrieval.py -q` and confirm failure**

Expected: FAIL because ingestion and retrieval modules are missing.

- [ ] **Step 3: Implement deterministic chunking and persistent Chroma access**

Split on blank lines first, then enforce `max_chars` with overlap. Send batch texts to the configured OpenAI-compatible embedding endpoint. Store `source`, `chunk_id`, and title/paragraph metadata. Keep retrieval behind one function so a future reranker can replace the top-20-to-top-5 selection without changing the API layer.

- [ ] **Step 4: Add the manual indexing command**

Expose `python -m app.ingest` to rebuild the collection from `documents/` and print indexed chunk count.

- [ ] **Step 5: Run tests and confirm pass**

Run: `pytest tests/test_retrieval.py -q`
Expected: PASS.

### Task 4: Full intent-tree Mock platform adapter

**Files:**
- Create: `app/mock_platform.py`
- Test: `tests/test_mock_platform.py`

**Interfaces:**
- `get_mock_data(intent_id: str, user_context: dict, page_context: dict) -> MockData`
- `MockData` fields: `data`, `data_source="mock_platform"`, `actions`.

- [ ] **Step 1: Write tests for wallet, sports, casino, promotion, VIP, support, and global intents**

Assert every catalog intent resolves to a deterministic payload, every payload is marked `mock_platform`, and wallet withdrawal/turnover examples include the expected demo values.

- [ ] **Step 2: Run `pytest tests/test_mock_platform.py -q` and confirm failure**

Expected: FAIL because the adapter is missing.

- [ ] **Step 3: Implement one deterministic adapter with group-based defaults**

Use catalog prefixes to return concise, safe demo values. Keep the adapter interface independent of FastAPI so it can later be replaced with real platform clients.

- [ ] **Step 4: Run tests and confirm pass**

Run: `pytest tests/test_mock_platform.py -q`
Expected: PASS.

### Task 5: DeepSeek answer generation and SSE event stream

**Files:**
- Create: `app/generation.py`
- Create: `app/events.py`
- Test: `tests/test_streaming.py`

**Interfaces:**
- `stream_answer(question: str, decision: IntentDecision, context: AnswerContext, llm_client) -> AsyncIterator[dict]`
- `sse_encode(event: dict) -> str`
- Event types: `intent`, `token`, `done`, `clarification`, `error`.

- [ ] **Step 1: Write tests for event order, final metadata, error event, and disconnect cancellation**

Given a fake streaming client, assert the sequence is `intent`, one or more `token`, `done`, `[DONE]`; assert upstream failure emits `error`; assert cancellation stops iteration.

- [ ] **Step 2: Run `pytest tests/test_streaming.py -q` and confirm failure**

Expected: FAIL because generation and event helpers are missing.

- [ ] **Step 3: Implement streaming generation**

Use DeepSeek chat streaming and yield token events as soon as content arrives. Never put final references or actions only in token events; include them in `done`. Close/cancel the upstream iterator when the request task is cancelled. Provide a non-stream helper that returns the same final payload for `stream=false`.

- [ ] **Step 4: Run tests and confirm pass**

Run: `pytest tests/test_streaming.py -q`
Expected: PASS.

### Task 6: FastAPI `/api/assistant/chat` orchestration

**Files:**
- Create: `app/main.py`
- Create: `app/chat.py`
- Test: `tests/test_api.py`

**Interfaces:**
- `POST /api/assistant/chat`
- Request fields: `question`, `session_id`, `page_context`, `user_context`, optional `stream` defaulting to `true`.
- Streaming response media type: `text/event-stream`.
- Non-stream response: final JSON payload with `session_id`, `intent`, `answer`, `references`, `data_source`, and `actions`.

- [ ] **Step 1: Write API tests for streaming, non-streaming, low confidence, and upstream error**

Use dependency overrides/fakes; assert status 200, SSE content type, event payloads, and that low confidence returns `clarification` without calling the Mock adapter.

- [ ] **Step 2: Run `pytest tests/test_api.py -q` and confirm failure**

Expected: FAIL because the FastAPI app is missing.

- [ ] **Step 3: Implement orchestration and CORS for local frontend testing**

Load catalog and clients once at startup. Route the request, choose Mock or retrieval, build the answer context, and return `StreamingResponse` for `stream=true` or the final payload for `stream=false`. Keep CORS origins configurable and default to localhost only.

- [ ] **Step 4: Run tests and confirm pass**

Run: `pytest tests/test_api.py -q`
Expected: PASS.

### Task 7: Documentation and end-to-end verification

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `tests/test_smoke.py`
- Modify: `.env.example`

- [ ] **Step 1: Write the smoke test**

Start the app with fakes and assert one knowledge question streams at least one token and one realtime question returns `data_source=mock_platform`.

- [ ] **Step 2: Implement run and indexing instructions**

Document virtual environment setup, dependency installation, `.env` values, `python -m app.ingest`, `uvicorn app.main:app --reload`, curl examples for streaming and `stream=false`, and the future Mock-to-platform adapter replacement.

- [ ] **Step 3: Add secret-safe ignore rules**

Ignore `.env`, `storage/chroma/`, Python caches, and local logs. Keep `documents/` contents out of Git by default; include only `.gitkeep`.

- [ ] **Step 4: Run the complete verification**

Run: `pytest -q`
Expected: all tests pass.

Run: `uvicorn app.main:app --host 127.0.0.1 --port 8000`
Expected: `/docs` opens and `/api/assistant/chat` returns the documented SSE stream with configured or fake clients.

- [ ] **Step 5: Checkpoint the completed prototype**

If Git is initialized, commit with `feat: add streaming local rag agent`.
