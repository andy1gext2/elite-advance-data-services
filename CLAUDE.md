# Elite Advance Data Services — AI Marketing & Reputation Management SaaS

> Project memory for Claude Code. Loaded into context at the start of every session. Keep concise and current.

## What this is

An enterprise-grade, multi-tenant SaaS platform that acts as a business owner's **AI Marketing Manager, Social Media Manager, and Reputation Manager** — one platform replacing many tools. Full product spec lives in [docs/master-prompt.md](docs/master-prompt.md); it is the source of truth.

- **Status:** Phases 1–5 complete (backend). P1: auth + multi-tenancy + RBAC + plans. P2: AI content generation — provider-agnostic `AIRouter` (Anthropic + Mock), RAG, `generate`/`repurpose`, draft→approve, AI quota gating. P3: AI content calendar (`…/calendar/plan`), scheduling (connect account w/ encrypted tokens, schedule/bulk/cancel), publish engine `run_due` (reposting, retries) via isolated connector layer (MockConnector), Celery `publish_due` beat task. P4: reputation — review sync via connector (`fetch_reviews`) + dedup, heuristic sentiment/keyword analysis + escalation flags, AI review responses (`ReviewResponseModule`), reputation report. P5: analytics — `analytics_service.dashboard` rollups from real internal signals (content/publishing/reviews/AI usage) + weekly timeseries + trends + grounded recommendations, AI Business Insights (`BusinessInsightsModule`, "how is my business doing?"). Calendar→scheduling bridge (`…/calendar/schedule-slot`) turns a plan slot into a generated+scheduled post. **OAuth connect scaffold** end-to-end (`…/integrations/oauth/{platform}/start` → provider consent → `…/oauth/{platform}/callback` stores an encrypted token, signed-JWT `state`) — runs against a mock consent screen; live connectors drop into `authorize_url`/`exchange_code` unchanged. DB via Alembic (0001→0004). **41 passing tests.** Dev on SQLite; `AI_DEFAULT_PROVIDER=mock` runs AI keyless. **Frontend: Next.js live** (signup/login → onboard business → workspace with Dashboard + Content + Calendar + Schedule + Reputation tabs). Dashboard: KPI tiles, weekly bar charts, channel + sentiment breakdowns, grounded recommendations, AI "how am I doing?" consultant. Content studio: repurpose → filter library → inline-edit → approve/reject. Calendar: horizon + theme → AI agenda of dated slots. Schedule: connect (mock) accounts → schedule → run publish engine. Reputation: sync reviews → report → AI reply generate/edit/post. All in [apps/web/](apps/web/), wired to the real API and verified end-to-end. Next: bridges (calendar→scheduling, scheduled review polling), live connectors (blocked on API approvals), or Phase 6 hardening. See [docs/roadmap.md](docs/roadmap.md).
- **Owner:** andy1gext2@gmail.com
- **Scale target:** 10,000+ businesses, millions of posts/reviews/analytics events

## Core capabilities (see master-prompt for full list)

1. **AI Social Media Manager** — generate platform-tailored content (IG, FB, LinkedIn, X, Threads, GBP), blogs, email, SMS, campaigns.
2. **Content Repurposing** — one idea → optimized variants per platform (not copy-paste).
3. **AI Content Calendar** — weekly→annual plans with timing/platform/trend recommendations.
4. **Scheduling** — draft, approve, schedule, auto-publish, bulk, cross-platform.
5. **Reputation Management** — monitor reviews, AI responses, sentiment, trends, reports.
6. **AI Business Insights** — consultant-style analytics + actionable recommendations.
7. **Dashboard** — real-time KPIs, graphs, dark/light, responsive.

## Tech stack (fixed by spec)

- **Frontend:** Next.js + React + TypeScript + Tailwind CSS → [apps/web/](apps/web/)
- **Backend:** Python + FastAPI (REST), OAuth + JWT auth → [services/api/](services/api/)
- **Data:** PostgreSQL (primary), Redis (cache/queue)
- **Async:** Celery + queue workers (scheduling, publishing, review polling, analytics)
- **AI:** provider-agnostic orchestration layer (AI Router → task classification → specialized modules). Default provider: Anthropic Claude. See [docs/architecture.md](docs/architecture.md).
- **Integrations:** isolated per-platform connectors (one API change ≠ system-wide change).

## Repository layout

```
/
  CLAUDE.md            this file
  README.md            human overview + setup
  .env.example         required env vars (copy to .env, never commit .env)
  docs/                architecture, data model, integrations, roadmap, limitations, master prompt
  apps/
    web/               Next.js frontend (to be scaffolded once Node is installed)
  services/
    api/               FastAPI backend — runnable skeleton (health, config, AI layer stubs)
  infra/
    docker-compose.yml local Postgres + Redis + api + worker (needs Docker)
  .claude/             Claude Code config
```

## Commands

Backend (works today — Python 3.12 is installed):
```
cd services/api
py -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs
python -m pytest -q                  # run the test suite
alembic upgrade head                 # apply migrations (Postgres or a sqlite:/// URL)
```
Dev DB: set `DATABASE_URL=sqlite:///./dev.db` in `.env` to run without Postgres. In
non-production the app auto-creates tables + seeds plans on startup; prod uses Alembic.

Frontend (works today — Node 24 is installed): `cd apps/web; npm install; npm run dev` → http://127.0.0.1:3000
  (Next proxies `/api/*` to the backend, so run the backend too — no CORS setup needed.)
Local infra (blocked — needs Docker): `docker compose -f infra/docker-compose.yml up`

## Environment realities (this machine)

- **OS:** Windows 11, shell is **PowerShell** — no `&&`/`||` chaining; use `;` and `if ($?) {}`.
- **Installed:** Python 3.12 + pip; **Node v24.18.0 + npm 11.16.0** (in Machine PATH — a terminal opened *before* the install has a stale PATH and needs a refresh/restart).
- **Missing:** Docker, git, psql, redis-cli. Containerized infra + version control are blocked until these are installed. See [docs/limitations.md](docs/limitations.md).

## Conventions

- **Multi-tenant everywhere:** every domain row is scoped by `business_id` (a.k.a. tenant/org). Never write a query that isn't tenant-scoped.
- **Provider-agnostic AI + connectors:** business logic depends on interfaces, not concrete SDKs. Swapping an AI provider or fixing a platform API must touch only that module.
- **RAG, not memory:** the AI retrieves business profile/brand/history from the DB before generating. Never rely on model memory across requests.
- **Secrets:** OAuth tokens and API keys are encrypted at rest; never logged, never committed. Use `.env` locally.
- Match surrounding code style; keep files small and single-purpose.

## Working agreement for Claude

- Build in **phases** (see [docs/roadmap.md](docs/roadmap.md)) — do not attempt the whole spec at once.
- When adding a feature, update the relevant `docs/` file and this layout if structure changes.
- Flag any feature that depends on a third-party API approval/cost before building it (many do — see limitations).
