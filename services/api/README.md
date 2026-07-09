# API (FastAPI backend)

Python + FastAPI backend for the platform. Runnable today (Python 3.12 is installed).

## Run
```powershell
cd services/api
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```
- API: http://127.0.0.1:8000
- Interactive docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

Env comes from the repo-root `.env` (copy `.env.example`). `app/core/config.py` reads it.

## Current state (Phases 1–2)
- **Auth & tenancy:** `app/api/auth.py`, `app/api/businesses.py`; RBAC + tenant scoping in `app/api/deps.py`.
- **Models:** `app/models/*` (all `business_id`-scoped) + Alembic migrations `migrations/versions/0001`, `0002`.
- **AI layer:** `app/ai/base.py` (interface) · `app/ai/router.py` (dispatch) · `app/ai/modules/content.py` · `app/ai/providers/{mock,anthropic_provider}.py` · `app/ai/registry.py` (provider selection).
- **Content:** `app/api/content.py` — `generate`, `repurpose`, list, approve/reject; `app/services/content_service.py` + `rag_service.py`.

### Generate content without an API key
Set `AI_DEFAULT_PROVIDER=mock` in `.env` to run the full content pipeline deterministically (no Anthropic key). For real output, set `AI_DEFAULT_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`.

Key endpoints: `POST /api/v1/businesses/{id}/content/generate` · `POST …/content/repurpose` · `POST …/content/{item_id}/approve`.

## To be built (see ../../docs/roadmap.md)
`app/ai/modules/*` (strategy, review_response, sentiment, insights, …) · `app/connectors/*` (platform OAuth/publish) · `app/workers/*` (Celery: scheduling, review polling, analytics).

## Conventions
- Routers stay thin; business logic lives in `app/services`.
- Every DB query is tenant-scoped by `business_id`.
- No vendor SDK imported outside `app/ai/providers/*` and `app/connectors/*`.
- On Windows, run Celery workers with `--pool=solo` (prefork is unreliable) or use WSL/Docker.
