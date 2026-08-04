# AutoPaperReader

AutoPaperReader is a local-first web application for collecting arXiv papers and analyzing them with an OpenAI-compatible LLM. It supports arbitrary research fields: the first-run setup wizard defines the workspace scope, arXiv query, optional categories, labels, knowledge base, and analysis language.

PDF text is downloaded temporarily for analysis and is never stored in the database.

## Release Model

- Local desktop deployment with SQLite.
- One local workspace per installation.
- Separate API, worker, and scheduler processes.
- Durable SQLite-backed jobs: browser requests do not wait for PDF downloads or LLM analysis.
- A clean release does not include a database. The app creates `backend/autopaperreader.db` at first API start.
- Existing database files are intentionally ignored, not deleted or migrated. Start the release with a new database file.

## Requirements

- Python 3.11 or later
- Node.js 20 or later
- An OpenAI-compatible chat-completions endpoint

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `ADMIN_PASSWORD`, and a long random `SESSION_SECRET` in `backend/.env`.

```bash
cd frontend
npm ci
```

## Run Locally

Open three terminals:

```bash
cd backend && source .venv/bin/activate && uvicorn app.main:app
cd backend && source .venv/bin/activate && python -m app.worker
cd backend && source .venv/bin/activate && python -m app.scheduler_process
```

Then run the frontend:

```bash
cd frontend && npm run dev
```

Open the Vite URL, log in as administrator, and visit `/setup`. The wizard creates the first local workspace. Until setup completes, searches and scheduled refreshes are unavailable.

## Workflow

1. Define the research field, arXiv query, categories, and scope in setup.
2. Search arXiv or queue an immediate refresh from Settings.
3. The worker imports/analyzes queued papers in the background.
4. Accepted papers appear in the library; rejected papers retain their relevance decision and run history in the database for auditing.
5. Edit generic prompts, labels, and the knowledge base to refine the workspace taxonomy.

## Commands

- Backend tests: `cd backend && .venv/bin/pytest -q`
- Backend syntax check: `cd backend && .venv/bin/python -m compileall app tests`
- Frontend build: `cd frontend && npm run build`
- Frontend production preview: `cd frontend && npm run preview`

## Security and Limits

- Keep `.env` and SQLite databases out of version control.
- For HTTPS deployments, set `SESSION_COOKIE_SECURE=true` and configure `CORS_ORIGINS` explicitly.
- PDF retrieval only permits arXiv hosts, validates redirects/content type, and enforces configured byte/page limits.
- Prompts, knowledge base, job logs, and configuration are administrator operations.

## Limitations

- This release is designed for one local installation, not a multi-user server.
- SQLite does not provide distributed worker coordination; run one worker and one scheduler process.
- Knowledge-base auto-update is disabled by default. Enable it only after reviewing the workspace prompts and provider trust boundary.
