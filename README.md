# Secure RAG

Secure RAG is a demo project that implements an RBAC-aware Retrieval-Augmented Generation (RAG) system. It combines a FastAPI backend, a React + Vite frontend, and a pgvector-compatible vector store to deliver grounded answers from documents users are authorized to access.

## Key capabilities
- Per-user RBAC filtering of document retrieval
- Deterministic chunking, ingestion, and embedding pipeline
- Grounded answer generation with source citations (Gemini LLM or local fallback)

## Architecture overview
- Backend: FastAPI (app/) — handles auth, document upload, retrieval, and RAG query endpoints.
- Generation: `app/generation/generator.py` — calls Google Gemini (if `GEMINI_API_KEY` present) and provides a local grounded fallback.
- Retrieval & Ingestion: `app/retrieval` and `app/ingestion` — text extraction, chunking, embedding, and pgvector retrieval.
- Vector Store: PostgreSQL with `pgvector` (via SQLAlchemy / Supabase) — stores chunk embeddings and performs cosine distance similarity searches with RBAC document-level filtering.
- Frontend: `frontend/` — Vite + React TypeScript SPA that talks to the backend via `/api/*`.

## Quickstart

**Prereqs**
- Python 3.11+ and Node.js (for the frontend)
- A PostgreSQL instance (or use Docker Compose included)

1) Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GEMINI_API_KEY, DATABASE_URL, and other values
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 9000
```

2) Frontend setup

```bash
cd frontend
npm install
npm run dev
```

3) Docker (optional)

```bash
docker-compose up --build
```

## API endpoints (selected)
- `POST /api/rag/query` — Run an authenticated RAG query (see [app/api/query.py](app/api/query.py#L1)).
- `POST /api/documents/upload` — Upload documents for ingestion and RBAC metadata (see [app/api/documents.py](app/api/documents.py#L1)).

## Environment variables
- `GEMINI_API_KEY` — Google Gemini API key (required to use Gemini). If not present, the backend uses a grounded local fallback.
- `DATABASE_URL` — SQLAlchemy DB URL.
- `VITE_API_BASE_URL` — Backend URL used by the frontend (default in `.env` is `http://localhost:9000`).
- `ADMIN_SIGNUP_KEY`, `ADMIN_INVITATION_CODE` — admin bootstrap secrets used by the app.
- `ALLOWED_ORIGINS` — comma separated list of allowed origin URLs for CORS.

## Generation & model notes
- The generator logic lives in [app/generation/generator.py](app/generation/generator.py#L1). It currently calls Gemini using the model `gemini-3.8-flash` when `GEMINI_API_KEY` is configured. If the model call fails (rate limits, unavailable model), the code falls back to a concise, grounded summary plus relevant excerpts.
- To change the LLM model or move to the Interactions API, update `app/generation/generator.py`. Adding retry/backoff around the model call is recommended to handle transient 503/UNAVAILABLE errors.

## Testing

```bash
source .venv/bin/activate
pytest -q
```

## Troubleshooting
- If the app returns chunk lists instead of prose answers:
  - Ensure `GEMINI_API_KEY` is set and valid in your environment.
  - Confirm the configured model is supported and not temporarily unavailable.
  - For local development you can rely on the improved fallback; for production you should wire a supported model and add retries.

## Files of interest
- `app/main.py` — app startup and router registration.
- `app/api/query.py` — RAG query handler and response shaping ([app/api/query.py](app/api/query.py#L1)).
- `app/generation/generator.py` — generation and fallback behavior ([app/generation/generator.py](app/generation/generator.py#L1)).
- `frontend/src/pages/employee/AskAIPage.tsx` — chat UI and how responses are rendered ([frontend/src/pages/employee/AskAIPage.tsx](frontend/src/pages/employee/AskAIPage.tsx#L1)).

## Contributing
- PRs welcome. Keep changes scoped and run tests before submitting.

## License
- MIT-style (check project root for license details).

---

If you'd like, I can also:
- add retry/backoff logic around the Gemini call,
- switch the generator to use the Interactions API pattern, or
- add a short How-To in the repo explaining how to rotate `GEMINI_API_KEY` and supported model names.
