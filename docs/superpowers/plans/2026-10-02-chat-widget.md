# Chat Widget Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a same-origin floating chat widget at the FastAPI root so a ngrok link opens a usable WillBet AI conversation instead of Swagger UI.

**Architecture:** Keep the existing chat API unchanged. Add a dependency-free `frontend/` directory with HTML, CSS, and browser JavaScript, then mount it after the existing API routes so `/`, `/health`, `/docs`, and `/api/assistant/chat` coexist on port 8000. The browser reads the existing SSE stream and renders assistant tokens in place.

**Tech Stack:** FastAPI `StaticFiles`, vanilla HTML/CSS/JavaScript, Fetch Streams, pytest/TestClient.

**Spec:** `docs/superpowers/specs/2026-10-02-chat-widget-design.md`

## Global Constraints

- Preserve `/api/assistant/chat`, `/health`, and `/docs` behavior.
- Add no frontend build tool, runtime dependency, or API key to browser code.
- Use same-origin `/api/assistant/chat` and request `stream: true`.
- Keep chat history in browser memory only; no server persistence.
- Keep `.env`, `.venv`, Chroma data, and chat content out of Git.

## Review Focus

- A missing `frontend/index.html` must return a clear server error during startup/test rather than silently serving an empty page; test root content and asset references in Task 1.
- SSE events may contain multiline data or a final `[DONE]` marker; test the parser and completion state in Task 2.
- Empty or whitespace-only input must not send a request; test disabled submit behavior in Task 2.
- Network and server error events must leave the input usable and show a readable message; test the error branch in Task 2.
- Existing API endpoints must remain reachable after the root static mount; test `/health` in Task 1.

---

### Task 1: Mount the static frontend

**Files:**
- Create: `tests/test_frontend.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: existing `create_app(deps)` factory.
- Produces: `GET /` serving `frontend/index.html`; existing API routes remain unchanged.

- [ ] **Step 1: Write the failing route test**

  Add `test_root_serves_widget_and_health_survives` using the existing test dependency fixture pattern. Assert `GET /` is `200`, has `text/html`, contains `WillBet AI`, and `GET /health` returns `{"status": "ok"}`.

- [ ] **Step 2: Run the test to verify it fails**

  Run `\.venv\Scripts\python.exe -m pytest -q tests/test_frontend.py`. Expected: the root request is not yet served by the widget.

- [ ] **Step 3: Implement the static mount**

  In `create_app`, resolve the repository `frontend` directory from `settings.root_dir`, mount `StaticFiles(directory=..., html=True)` at `/` after the API route declarations, and raise a clear startup error if the directory is missing.

- [ ] **Step 4: Run the route test to verify it passes**

  Run `\.venv\Scripts\python.exe -m pytest -q tests/test_frontend.py` and expect PASS.

### Task 2: Build the floating chat widget

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/styles.css`
- Create: `frontend/app.js`
- Modify: `tests/test_frontend.py`

**Interfaces:**
- Consumes: `POST /api/assistant/chat` with `{question, session_id, stream: true}`.
- Produces: floating button, expandable chat panel, streamed assistant messages, clear and error interactions.

- [ ] **Step 1: Add browser behavior checks to the route test**

  Assert the HTML references `styles.css` and `app.js`, and the JavaScript contains the same-origin `/api/assistant/chat` path and `text/event-stream` handling marker.

- [ ] **Step 2: Implement the minimal HTML structure**

  Create semantic elements for the launcher button, panel header, message list, clear button, textarea, and submit button. Include accessible labels and `defer` script loading.

- [ ] **Step 3: Implement the visual system**

  Use CSS variables for the dark WillBet palette and purple accent; position the launcher and panel bottom-right; make the panel responsive below 480px.

- [ ] **Step 4: Implement SSE chat behavior**

  In `app.js`, keep messages in memory, prevent blank submits, append the user message, create an assistant placeholder, call `fetch('/api/assistant/chat', {method: 'POST', body: JSON.stringify({question, session_id, stream: true})})`, parse `data:` lines from the response stream, append `token` text, finish on `done` or `[DONE]`, and render readable errors while re-enabling controls.

- [ ] **Step 5: Run the route and full test suites**

  Run `\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q`. Expected: all existing tests plus the frontend checks pass.

### Task 3: Document and verify the demo path

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the root static page and current uvicorn/ngrok startup commands.
- Produces: clear local and public demo instructions.

- [ ] **Step 1: Document the widget URL**

  Add that `http://127.0.0.1:8000/` opens the floating assistant, `/docs` remains the API page, and the same root URL can be exposed through ngrok Basic Auth.

- [ ] **Step 2: Verify local and public behavior**

  Start uvicorn, request `/` and `/health`, then use the existing authenticated ngrok URL to request `/` and confirm the page returns `200` with the widget assets.

- [ ] **Step 3: Commit the implementation**

  Run `git diff --check`, inspect the staged file list for secrets, then commit with `feat: add floating chat widget`.
