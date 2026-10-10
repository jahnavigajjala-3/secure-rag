# SecureRAG AI coding guide

## Project shape
- This repo is a FastAPI backend for a secure enterprise RAG app. The app entrypoint is `app/main.py`; it initializes the database, seeds dev users, bootstraps an admin, registers routers, and exposes `/health` and `/health/ready`.
- Main domain modules: `app/api/` (HTTP routes), `app/database/` (SQLAlchemy models + DB setup), `app/auth/` (JWT + auth guards), `app/retrieval/` (RBAC-aware document filtering), `app/generation/` (Gemini answer generation), `app/ingestion/` (document ingestion pipeline), `app/vectorstore/` (Chroma metadata + retrieval).
- The app is role-driven: `User.roles` and `Document.roles` map to `Role` records; backend access decisions happen in SQL/DB filters, not in the UI.

## Auth and security
- JWT auth is implemented in `app/auth/security.py` and enforced in `app/auth/dependencies.py` with `HTTPBearer` and `get_current_user()`. Missing/invalid/expired tokens return 401.
- Admin-only routes use `get_current_admin_user()` and check `Role.name == "admin"` on the current DB user.
- Tokens include `user_id`, `sub`, `email`, and `role` and are issued by `create_access_token()`.
- Registration is in `app/api/auth.py`; role assignment is not chosen on the client. The backend creates an `employee` role by default or `admin` if the valid admin key/invitation is provided.
- Do not add client-side permission logic as a security control; the backend is the source of truth.

## Core business flow
- `POST /auth/login` returns `{ access_token, token_type, user: { id, email, role } }`.
- `GET /auth/me` returns the current user identity and role.
- `POST /api/query` / `POST /api/rag/query` authenticate the caller, resolve authorized document IDs via RBAC, query Chroma with a metadata filter, and generate a grounded answer with citations.
- Document access is controlled by `document_roles` and `user_roles` in `app/database/models.py`.
- `app/retrieval/retriever.py` uses the PostgreSQL auth graph to restrict retrieval before hitting Chroma.

## Document ingestion pipeline
- `app/api/documents.py` validates uploads (`.pdf`, `.txt`, `.docx`), stores files under `data/documents`, records a `Document`, and calls `ingest_document_by_id()`.
- `app/ingestion/pipeline.py` transitions `Document.status` through `PROCESSING -> READY` or `FAILED`, then upserts its chunks into Chroma.
- `Document.status` values are important: `PROCESSING`, `READY`, `FAILED`; UI logic should not assume a file is usable before it is `READY`.
- `admin_router` endpoints under `/admin/documents` are for admin-only document management and role assignment.

## Data + environment conventions
- Dev DB defaults to SQLite via `settings.DATABASE_URL` in `app/config.py`; production expects Postgres.
- Local bootstrap users are seeded in `app/database/seed.py`: `admin@example.com / admin123` and `employee@example.com / employee123`.
- `app/config.py` loads env values including `JWT_SECRET_KEY`, `GEMINI_API_KEY`, `ADMIN_SIGNUP_KEY`, and CORS origins.
- Secret handling stays in backend env vars; do not invent frontend-only auth state or bypass the server.

## Validation and testing workflow
- Use `pytest` for backend tests (`tests/test_auth.py`, `tests/test_query.py`, etc.).
- Typical local checks:
  - `source .venv/bin/activate`
  - `uvicorn app.main:app --reload`
  - `pytest -q`
- The app is tested through FastAPI `TestClient`, so API contract regressions should be validated at the HTTP layer.

## Coding conventions
- Favor explicit route/DB/service boundaries already present: `api/` for HTTP, `database/models.py` for schema, `auth/` for security, `services/` for audit logic, `retrieval/` for permissioned retrieval.
- Keep access checks on the backend. If a route is restricted, implement the check in the dependency or service layer, not in a caller.
- When adding a new endpoint, match the repo’s existing style: Pydantic request/response models in `app/schemas/`, SQLAlchemy models in `app/database/models.py`, and role-aware authorization in the route handler.
- Audit events are recorded via `app/services/audit.py`; avoid logging secrets or raw tokens.

## Important examples
- Auth flow: `app/api/auth.py` -> `app/auth/dependencies.py` -> `app/auth/security.py`.
- RBAC flow: `app/database/models.py` -> `app/api/rbac.py` -> `app/retrieval/retriever.py` -> `app/api/query.py`.
- Document lifecycle: `app/api/documents.py` -> `app/ingestion/pipeline.py` -> `app/vectorstore/store.py`.
