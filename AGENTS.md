# Agent Notes

## Project Shape
- Backend lives in `backend/`; run backend commands from that directory so `sqlite:///./autopaperreader.db` resolves to `backend/autopaperreader.db`.
- Frontend lives in `frontend/`; Vite proxies `/api` to `http://127.0.0.1:8000` via `frontend/vite.config.ts`.
- FastAPI entrypoint is `backend/app/main.py`; startup creates tables, seeds defaults, and starts the APScheduler job.

## Commands
- Backend setup: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env`.
- Backend dev server: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`.
- Backend tests: `cd backend && .venv/bin/pytest -q`; `pytest.ini` sets `pythonpath = .`, so do not run from repo root unless passing the right path/env.
- Backend syntax check: `cd backend && .venv/bin/python -m compileall app tests`.
- Frontend setup/build: `cd frontend && npm install && npm run build`; build runs `tsc -b && vite build`.
- Frontend dev server: `cd frontend && npm run dev`.

## Must Do
- After code changes, update `PROGRESS.md` with the user-facing implementation status and update `ARCHITECTURE.md` when the system structure, data model, API surface, routes, jobs, auth, or analysis flow changes.

## Runtime Config
- AI uses an OpenAI-compatible chat completions endpoint configured in `backend/.env`: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`.
- Default arXiv query is seeded as `navigation`; users can edit it through `/settings`.
- Daily refresh runs at `SCHEDULE_HOUR`; manual trigger endpoint is `POST /api/jobs/run-scheduled-refresh`.

## Data And Analysis Gotchas
- PDF full text is intentionally not persisted: `analysis_service.analyze_paper()` downloads/parses via `fetch_pdf_text()`, sends text to the LLM, then only stores answers and `pdf_url`.
- AI analysis uses active prompts in DB: `relevance`, `category`, `tech_route`, `trend`, `quality`, `tech_summary`, and `trend_merge`; do not hard-code prompt text in services.
- The editable domain knowledge base is used as analysis context and can be auto-updated through the `knowledge_update` prompt; preserve this flow when changing analysis behavior.
- Papers outside the target VLN/robot navigation topic are deleted during analysis and should not remain in the library.
- AI labels are assigned by a second LLM pass: send `agent_answer` plus existing `label_definitions` to the model, parse strict JSON, replace `source=ai` labels, and preserve `source=manual` labels.
- `LLMClient` must tolerate OpenAI-compatible variants: standard SDK objects, dict responses, string responses, and list content parts are covered by `extract_chat_content()` tests.

## API / UI Notes
- Paper list endpoints return labels and accept repeated `label_ids`: `GET /api/papers` returns target-topic papers, `GET /api/papers/daily` returns today's target-topic papers, and `GET /api/papers/monthly-trends` returns current-month trend, quality, and imported-paper sections.
- Frontend user-facing text should be Chinese except product names, protocol names, endpoint/tool names, and other proper nouns.
- Paper cards are intentionally compact: list pages show title, date, status, labels, authors, and review/delete actions; details belong on `/papers/:id`.
