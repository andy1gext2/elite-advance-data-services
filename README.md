# Elite Advance Data Services

An enterprise-grade **AI Marketing & Reputation Management** SaaS platform — the business owner's AI marketing, social media, and reputation manager in one product.

Full product specification: [docs/master-prompt.md](docs/master-prompt.md).

## Architecture at a glance

| Layer | Tech | Location |
|-------|------|----------|
| Frontend | Next.js · React · TypeScript · Tailwind | [apps/web/](apps/web/) |
| Backend API | Python · FastAPI · JWT/OAuth | [services/api/](services/api/) |
| Database | PostgreSQL | — |
| Cache / Queue | Redis | — |
| Async workers | Celery | [services/api/](services/api/) |
| AI | Provider-agnostic orchestration (default: Anthropic Claude) | `services/api/app/ai/` |
| Integrations | Isolated per-platform connectors | `services/api/app/connectors/` |

See [docs/architecture.md](docs/architecture.md) for the request/data flow and module boundaries.

## Getting started

Prerequisites: Python 3.12+ (installed). For the full stack you also need **Node 20+**, **Docker**, and **git** (not yet installed on this machine — see [docs/limitations.md](docs/limitations.md)).

### Backend (runnable now)

```powershell
cd services/api
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\..\.env.example ..\..\.env   # then edit .env
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive API.

### Frontend (after installing Node)

```powershell
cd apps/web
npm install
npm run dev
```

### Local infra (after installing Docker)

```powershell
docker compose -f infra/docker-compose.yml up
```

## Documentation

- [docs/master-prompt.md](docs/master-prompt.md) — product source of truth
- [docs/architecture.md](docs/architecture.md) — system design & module boundaries
- [docs/data-model.md](docs/data-model.md) — core entities & multi-tenancy
- [docs/integrations.md](docs/integrations.md) — platform connectors & OAuth status
- [docs/roadmap.md](docs/roadmap.md) — phased build plan (MVP → enterprise)
- [docs/limitations.md](docs/limitations.md) — real-world constraints & risks

Built to work with [Claude Code](https://claude.ai/code); see [CLAUDE.md](CLAUDE.md).
