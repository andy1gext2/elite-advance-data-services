# Phased Build Plan

The spec is ~60 features. Building it all at once is not viable. Ship in phases; each phase is independently useful and testable. **Prove the vertical slice before widening.**

## Phase 0 — Foundation (mostly done)
- [x] Repo structure, docs, CLAUDE.md
- [x] Runnable FastAPI skeleton (health, config, AI base + router stubs)
- [x] SQLAlchemy models + Alembic migration (portable Postgres/SQLite)
- [x] **Node installed** (v24.18.0 / npm 11.16.0) — frontend unblocked
- [ ] Install Docker, git (still missing — blocks containerized infra/VCS)
- [ ] Postgres + Redis via docker-compose (dev currently runs on SQLite)
- [x] **Next.js app scaffolded** (App Router, TS strict, Tailwind, dark/light shell) — `apps/web/`. Browser talks same-origin to Next, which proxies `/api/*` to FastAPI (no CORS). See "First working slice" below.

## Phase 1 — Accounts & tenancy ✅ (done, tested)
- [x] Auth: signup/login, JWT access+refresh (`/api/v1/auth/*`)
- [x] Business (tenant) creation + onboarding fields (industry, brand voice, audience, goals…)
- [x] Memberships + RBAC (owner/admin/editor/viewer) with tenant isolation
- [x] Plans (starter→enterprise) + feature-gating (max_users enforced on invite)
- [ ] Password reset + email verification (deferred)
- [ ] Audit-log wiring on sensitive actions (model exists; hook it up)

## Phase 2 — AI content generation (the core wedge) ✅ (backend done, tested)
- [x] AI orchestration: `AIRouter` + Content module + provider registry
- [x] Providers: Anthropic (Claude, default `claude-opus-4-8`) + Mock (keyless dev/tests)
- [x] RAG: retrieve business profile/brand/tone before generating (`rag_service`)
- [x] Single-platform generation (`POST …/content/generate`) → **repurposing** (`…/repurpose`, 12 variants)
- [x] Blog / email / SMS / caption / hashtag / CTA content types
- [x] Draft → approve/reject flow + per-tenant monthly AI quota gating (402)
- [x] Content review/approve **UI** — first frontend slice: signup/login → onboard business → repurpose one idea → approve/reject items (`apps/web/`, wired to the real API, verified end-to-end)
- [x] Content **library + inline editing** — status/channel filters (server-side) and edit-in-place via new `PATCH …/content/{id}` (editing a reviewed item reverts it to draft)
- [ ] Prompt tiering (Haiku for cheap types) — currently all default to the configured model

## Phase 3 — Calendar & scheduling ✅ (backend done, tested)
- [x] AI content calendar (week→year) with timing/platform/idea recommendations (`…/calendar/plan`)
- [x] **Calendar UI** — horizon pills (week/month/quarter/year) + theme → agenda timeline of dated slots (channel, recommended time, AI topic). Content/Calendar tabs in the business workspace. (`apps/web/`, verified against the endpoint)
- [x] **Calendar → scheduling bridge** (`POST …/calendar/schedule-slot`) — one click on a slot generates a content item from its topic and schedules it at the slot's date/time on the channel's connected account (auto-resolved; 400 with a connect-account hint if none). Verified end-to-end.
- [x] Schedule + PublishJob + SocialAccount models (encrypted tokens) + migration 0003
- [x] Publish engine `run_due` (idempotent, retries, reposting) — the code Celery beat calls
- [x] Scheduling API: connect account, schedule, bulk, cancel, list (calendar), `run-due`
- [x] Celery app + `publish_due` beat task (needs Redis broker; `--pool=solo` on Windows)
- [x] **Connector layer end-to-end via MockConnector** (real per-platform connectors register in `app/connectors/registry.py` as APIs are approved)
- [x] **Scheduling & publishing UI** — connect (mock) accounts, schedule approved content (datetime + optional repost), schedule list with status/cancel, and a "run publish engine" button that fires `run-due`. Local time is sent as tz-aware ISO so UTC storage is correct. (`apps/web/`, verified: connect → schedule → publish → content flips to published)
- [x] **OAuth connect scaffold, end-to-end** — real "Connect with {platform}" flow: `POST …/integrations/oauth/{platform}/start` (signed-JWT `state`) → provider consent → `GET …/oauth/{platform}/callback` exchanges the code and stores an encrypted token → redirects back to the app (`?connected=` / `?oauth_error=`). Runs against a mock consent screen today; a live connector's `authorize_url`/`exchange_code` drops in unchanged. UI: "Connect with {platform}" button + return banner.
- [ ] Live platform connectors + real OAuth **credentials/app review** (blocked on platform API approvals — the flow above is ready for them; see integrations.md)

## Phase 4 — Reputation management ✅ (backend done + UI, tested)
- [x] Review polling via the connector layer (`MockConnector.fetch_reviews`) + `Review` model/storage (migration 0004), deduped per tenant by (business, platform, external_id)
- [x] Sentiment + keyword analysis (`services/text_analysis.py` — heuristic, deterministic; replaceable by the AI SENTIMENT module) + escalation flag (`needs_attention`)
- [x] AI review responses (positive/negative) via `ReviewResponseModule` (RAG-grounded) → draft → edit → post
- [x] Reputation report (`…/reputation/report`): avg rating, rating distribution, sentiment breakdown, response rate, top compliments/complaints, month-over-month trend
- [x] **Reputation UI** — Reputation tab: sync, report summary (stat tiles, sentiment bar, keyword chips), filterable review list (status/sentiment/needs-attention), AI reply generate/edit/post (`apps/web/`, verified end-to-end)
- [ ] Live GBP/Facebook connectors + real polling (blocked on platform API approvals)
- [ ] Scheduled/automatic polling (Celery beat, like `publish_due`) — today sync is on-demand

## Phase 5 — Analytics & insights ✅ (backend done + UI, tested)
- [x] Analytics rollups (`analytics_service.dashboard`) computed from real internal signals — content output, publishing, reviews/sentiment, AI usage — with weekly time series + month-over-month trends. (Social metrics — followers/reach/engagement — intentionally NOT fabricated; they await live connectors.)
- [x] **Dashboard UI** — KPI tiles, single-hue weekly bar charts, channel distribution, diverging sentiment bar (palette validated via the dataviz skill's `validate_palette.js`), responsive + dark/light. First workspace tab.
- [x] AI Business Insights ("How is my business doing?", `…/insights/generate`) via `BusinessInsightsModule` grounded in the metrics snapshot + a deterministic, grounded recommendations feed (`…/analytics/dashboard`)
- [ ] Rollup tables for scale (currently aggregates on read — fine at dev scale; move to precomputed rollups for 10k+ tenants)
- [ ] Real social/engagement/follower metrics (blocked on live platform connectors)

## Phase 6 — Hardening & scale
- [x] **Deployment scaffolding (Railway + Vercel)** — API/worker Dockerfile, `railway.json` (migrate→seed→serve, `/health`), psycopg3 URL normalization for managed Postgres, secret generator, `.env.production.example`, and a click-by-click [DEPLOY.md](../DEPLOY.md). Going live = create hosts + push (needs git installed).
- [ ] Audit logs, rate limiting, monitoring/logging, caching
- [ ] Billing integration (Stripe), full plan enforcement
- [ ] SOC 2 / GDPR / CCPA readiness (process + technical controls)
- [ ] Horizontal scaling, CDN, high availability

## Later (future roadmap)
AI images/videos, ad creation/optimization, competitor analysis, trend prediction, local SEO, website audits, ROI forecasting, CRM, lead nurturing, email/SMS automation, voice/phone AI, appointment booking, workflow automation, integrations marketplace, mobile apps, white-label/agency, multi-location.

## First working slice ✅ (built + verified 2026-07-08)
**Onboard a business → generate a repurposed post set from one idea → approve it.** Exercises tenancy, RAG, the AI layer, and the content model without any external platform approval. Now live in `apps/web/` end-to-end (signup/login, onboarding, dashboard, content studio with approve/reject), verified against the running backend via the Next `/api/*` proxy.

Run both together:
```
# terminal 1 — backend (keyless: .env has AI_DEFAULT_PROVIDER=mock, sqlite)
cd services/api; .venv\Scripts\Activate.ps1; uvicorn app.main:app --reload
# terminal 2 — frontend
cd apps/web; npm run dev   # http://127.0.0.1:3000
```

### Next frontend steps
Widen from the slice: content list filters + editing, the AI content calendar view, the scheduling/publishing calendar UI, then Phase 4/5 screens (reputation, analytics dashboard) as those backends land.
