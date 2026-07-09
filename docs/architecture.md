# Architecture

## Principles
1. **Multi-tenant by default** — every domain entity is scoped by `business_id`. Tenancy is enforced at the query/repository layer, not left to callers.
2. **Provider-agnostic** — AI providers and social platforms sit behind interfaces. Business logic never imports a vendor SDK directly.
3. **RAG over memory** — generation always retrieves business context (profile, brand voice, history) from Postgres first.
4. **Isolated connectors** — one platform's API change touches exactly one module.
5. **Async-first** — anything slow or third-party (publishing, review polling, analytics rollups, AI batch jobs) runs on Celery, not in the request path.

## Request / data flow
```
Browser (Next.js)
   │  HTTPS + JWT
   ▼
FastAPI (REST)  ──►  Auth / RBAC / rate limit / audit
   │
   ├─► AI Orchestration Layer
   │      Router → task classification → specialized module
   │      (Content, Strategy, ReviewResponse, Sentiment, Insights, Analytics, Campaign, SEO)
   │      each module: retrieve business context (RAG) → call provider → persist
   │
   ├─► Connector Layer (per platform: IG, FB, LinkedIn, Google, TikTok, YouTube, X, Threads)
   │      OAuth tokens (encrypted) → publish / read reviews / read metrics
   │
   ├─► PostgreSQL (system of record)   ◄── Redis (cache, sessions, rate limits)
   │
   └─► Celery workers (Redis broker): scheduled publish, review polling,
          analytics pipeline, monthly reports, AI batch generation
```

## Backend module map (`services/api/app/`)
```
main.py            app factory, router registration
core/              config, security (JWT), db session, logging, tenancy
api/               HTTP routers (thin) grouped by domain
  health, auth, businesses, content, calendar, scheduling,
  reviews, insights, analytics, integrations, billing
services/          business logic (use-cases), tenant-scoped
ai/                orchestration layer
  base.py          AIProvider interface + AIRequest/AIResponse
  router.py        task classification → module dispatch
  modules/         content, strategy, review_response, sentiment,
                   insights, analytics_summary, campaign, seo
  providers/       anthropic (default), openai, ... (implement AIProvider)
connectors/        per-platform: base.py + instagram.py, facebook.py, ...
models/            SQLAlchemy models (all carry business_id)
schemas/           Pydantic request/response
workers/           Celery app + tasks
```
> The current repo ships a runnable subset (health, config, AI base + router stubs). The rest is built out per [roadmap.md](roadmap.md).

## AI orchestration
- `AIProvider` is the single interface every provider implements (`generate(request) -> response`).
- The **Router** classifies an incoming task (content vs. review-response vs. insight, target platform, tone) and dispatches to a **specialized module**.
- Each module owns its prompt templates, retrieves business context via RAG, calls the configured provider, validates/persists output.
- Swapping providers = config change (`AI_DEFAULT_PROVIDER`) + a provider class. No module changes.
- Default provider: **Anthropic Claude** (Opus 4.8 for hard reasoning/insights, Sonnet 5 for general generation, Haiku 4.5 for cheap high-volume tasks).

## Connector contract
Each connector implements a `PlatformConnector` base: `authorize_url()`, `exchange_code()`, `refresh()`, `publish(post)`, `fetch_reviews()`, `fetch_metrics()`. Unsupported operations raise `NotSupported` rather than leaking platform quirks upward.

## Cross-cutting
- **Security:** JWT access/refresh, RBAC per business, Fernet-encrypted OAuth tokens, audit log table, HTTPS in prod, secure gateway.
- **Scale:** stateless API (horizontal scale), Redis cache, Celery for fan-out, connection pooling, per-tenant + per-provider rate limiting, structured logging + metrics.
- **Billing/plans:** feature gating middleware reads the tenant's plan and enforces limits (users, connected accounts, locations, AI usage, analytics tier).
