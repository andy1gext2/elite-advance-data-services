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
- [x] **Prompt tiering** — short/low-stakes generations (SMS, captions, hashtags, CTAs, calendar ideas) route to a cheap model (`AI_CHEAP_MODEL`, default Haiku 4.5) via `app/ai/model_policy.py`; high-value content (social posts, blogs, email, review replies, insights) stays on `AI_DEFAULT_MODEL`. Toggle with `AI_TIERING_ENABLED`.
- [x] **Brand learning from approved posts** (in-context, not fine-tuning) — `rag_service.approved_examples` feeds the owner's recently-**approved** posts into every `content` generation as brand exemplars (`ContentModule` system prompt), so Claude matches the approved voice; the image prompt (`image_service`) carries brand voice + "consistent with previous approved posts" so Gemini holds a steady visual style. Prefers same-channel exemplars. The more the owner approves, the tighter the brand narrative.

## Phase 3 — Calendar & scheduling ✅ (backend done, tested)
- [x] AI content calendar (week→year) with timing/platform/idea recommendations (`…/calendar/plan`)
- [x] AI planner endpoint (`…/calendar/plan`, horizon + theme → dated slots) + schedule-slot bridge — still live in the backend. The **Calendar tab UI** has since been repurposed into the campaign bird's-eye month grid (see Autopilot campaigns below); campaign creation moved to the Content tab.
- [x] **Calendar → scheduling bridge** (`POST …/calendar/schedule-slot`) — one click on a slot generates a content item from its topic and schedules it at the slot's date/time on the channel's connected account (auto-resolved; 400 with a connect-account hint if none). Verified end-to-end.
- [x] Schedule + PublishJob + SocialAccount models (encrypted tokens) + migration 0003
- [x] Publish engine `run_due` (idempotent, retries, reposting) — the code Celery beat calls
- [x] Scheduling API: connect account, schedule, bulk, cancel, list (calendar), `run-due`
- [x] Celery app + `publish_due` beat task (needs Redis broker; `--pool=solo` on Windows)
- [x] **Connector layer end-to-end via MockConnector** (real per-platform connectors register in `app/connectors/registry.py` as APIs are approved)
- [x] **Scheduling & publishing UI** — connect (mock) accounts, schedule approved content (datetime + optional repost), schedule list with status/cancel, and a "run publish engine" button that fires `run-due`. Local time is sent as tz-aware ISO so UTC storage is correct. (`apps/web/`, verified: connect → schedule → publish → content flips to published)
- [x] **Reschedule (edit when/where)** — `PATCH …/schedules/{id}` (`scheduling_service.reschedule`, `RescheduleIn`) moves a PENDING post's date/time and/or destination account; the Schedule tab's post cards get a "Reschedule" control (and now parse stored naive-UTC as UTC for correct local display).
- [x] **OAuth connect scaffold, end-to-end** — real "Connect with {platform}" flow: `POST …/integrations/oauth/{platform}/start` (signed-JWT `state`) → provider consent → `GET …/oauth/{platform}/callback` exchanges the code and stores an encrypted token → redirects back to the app (`?connected=` / `?oauth_error=`). Runs against a mock consent screen today; a live connector's `authorize_url`/`exchange_code` drops in unchanged. UI: "Connect with {platform}" button + return banner.
- [x] **Real Meta + Google OAuth connectors** (`connectors/meta.py`, `connectors/google_business.py`) — actual authorize-URL + code-exchange against Facebook Login (serves both `facebook` and `instagram`) and Google OAuth 2.0 (`business.manage`). The registry activates them when `META_APP_ID`/`META_APP_SECRET` / `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are set, else falls back to the mock (dev works keyless).
- [x] **Real Facebook Page publishing** — `MetaConnector.publish` (facebook) fetches the Page + its Page token via `/me/accounts` and posts to `/{page}/feed` via the Graph API. (Instagram = media-container flow, GBP = Business Profile API — still stubbed with clear errors; both need platform approvals.)
- [x] **Token refresh keeps sessions alive** — `social_accounts.refresh_token_enc` (migration 0011, encrypted) stores the OAuth refresh token; `scheduling_service.ensure_fresh_token` refreshes an expired/near-expiry token before every publish (Google refresh-token grant; Meta long-lived-token re-exchange), updating the stored token + expiry. Requires app credentials + **App Review / Business Profile API access** to run against the live providers.
- [x] **Connection status per account** — `scheduling_service.account_status` computes live health surfaced on `SocialAccountOut` (`connection`, `can_publish`, `live`, `detail`): **connected** / **expiring soon** / **reconnect needed** (expired + no refresh token) / **pending approval** (connected but that platform's publishing is stubbed), plus a *simulated* flag for the dev mock. The Schedule tab shows a colored badge + detail per account and a **Reconnect** button when a session needs re-auth. See setup steps in [integrations.md](integrations.md).
- [x] **Connect accounts in onboarding** — a 2-step onboarding (business details → **Connect your accounts**) with connect buttons for Facebook, Instagram, Google Business, LinkedIn, X, Threads, using the OAuth start flow. Clients connect during setup (or skip to the workspace and connect later on Schedule).
- [x] **Studio targets connected platforms** — `campaign_service.propose` generates only for the channels the business has **connected accounts** for (`_connected_channels`; falls back to the full rotation if none connected). Connect Facebook + Google Business → campaigns produce only FB + GBP posts, each in that platform's format.

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
- [x] **Command-center redesign** (chosen from 3 Gemini-generated visual directions) — KPI accent-tile row → a performance chart + share-by-channel **donut** (single-hue by share, labeled legend) + a tall **activity feed** rail (reviews / upcoming posts / fresh drafts) + an **upcoming-posts strip** (from `…/campaigns/calendar`), then sentiment, recommendations, and the AI consultant surfaced at the top.
- [x] **Left-sidebar workspace shell** (`WorkspaceShell` + `businesses/[id]/layout.tsx`) — Direction B's fixed icon sidebar (desktop) / top-bar + scroll-nav (mobile) now frames *every* workspace tab; replaced the old per-page top `BusinessTabs`. A shared `PageHeader` gives all tabs (Dashboard, Content, Calendar, Campaigns, Schedule, Reputation, Products) a consistent title/subtitle/action row. Non-workspace pages (business list, onboarding) keep the simpler `AppShell`.
- [x] AI Business Insights ("How is my business doing?", `…/insights/generate`) via `BusinessInsightsModule` grounded in the metrics snapshot + a deterministic, grounded recommendations feed (`…/analytics/dashboard`)
- [ ] Rollup tables for scale (currently aggregates on read — fine at dev scale; move to precomputed rollups for 10k+ tenants)
- [ ] Real social/engagement/follower metrics (blocked on live platform connectors)

## Phase 6 — Hardening & scale
- [x] **Deployment scaffolding (Railway + Vercel)** — API/worker Dockerfile, `railway.json` (migrate→seed→serve, `/health`), psycopg3 URL normalization for managed Postgres, secret generator, `.env.production.example`, and a click-by-click [DEPLOY.md](../DEPLOY.md). Going live = create hosts + push (needs git installed).
- [ ] Audit logs, rate limiting, monitoring/logging, caching
- [ ] Billing integration (Stripe), full plan enforcement
- [ ] SOC 2 / GDPR / CCPA readiness (process + technical controls)
- [ ] Horizontal scaling, CDN, high availability

## Autopilot campaigns ✅ (backend done + UI, tested)
- [x] **Campaign engine** (`campaign_service`) — `propose` drafts a whole campaign (AI calendar plan → one generated content item per slot → resolved connected account) as PROPOSED; `approve` turns each item with a connected account into a real Schedule (publish engine posts them); `reject` blocks. Models: `Campaign`, `CampaignItem` (migration 0005).
- [x] **Campaign duration + product from the Content tab** — the content studio *is* the campaign builder: pick a product to promote, a duration (**day** · **week** · **month**), and a brief → `propose` with `timeframe` + `product_asset_id` (migration 0008). The product's name + description steer the plan and every post.
- [x] **All-platforms cadence** (`calendar_service.campaign_plan` + `CAMPAIGN_CADENCE`) — every posting day hits **all** platforms at once, spaced **every other day** (one shared AI idea per day, tailored per channel). Day counts capped per horizon (day=1, week=3, month=6 posting days → ×5 channels) so a whole-campaign draft stays a bounded number of generations. NOTE: a month draft is ~30 synchronous AI calls — fine at dev scale, but `propose` should move to a background job before heavy production use.
- [x] **Campaign calendar (bird's-eye)** — `GET …/campaigns/calendar` flattens every campaign's posts into dated entries; the **Calendar tab** renders them on a navigable month grid (channel, time, status dot) — the schedule at a glance.
- [x] **Content is a review queue** — the Content tab shows only **draft** posts, each stamped with its publish date (Today for day-campaigns, the scheduled date for week/month). **Approve** (`content_service.approve_item`) books the post onto the calendar (proposed→scheduled) and creates a real publish `Schedule` where an account is connected — the card swipes right (green) and leaves the queue. **Reject** (`DELETE …/content/{id}`, `content_service.delete_item`) deletes the post for good — from the library, the calendar, and any schedules — the card swipes left.
- [x] **Autopilot (approve-first)** — per-tenant config on `businesses` (enabled, theme, frequency, timeframe); `run_autopilot` proposes campaigns for due tenants; Celery beat task `propose_campaigns` (hourly check). Proposals wait for human approval — nothing publishes autonomously.
- [x] **Campaigns UI** — tab with autopilot settings, "draft a campaign now", and a campaign list with expandable review (per-post content/time/channel) + Approve/Reject. (`apps/web/`, verified end-to-end: propose → 0 schedules → approve → schedules created)
- [ ] Full-auto mode (schedule+publish without review) — deliberately not built; approve-first only for now
- [ ] Notifications when autopilot drafts a campaign (email/in-app)

## Media
- [x] **Platform post previews** — each generated post renders as native Instagram/Facebook/LinkedIn/X/Threads chrome (with a video-styled slot for video content) alongside the copy in the Content library (`apps/web/components/PostPreview.tsx`). Each preview carries the **platform's brand logo top-left** (`PlatformLogo`). The Content library is ordered most-popular-platform-first (IG/FB/X) and has a **flip-through platform tab bar** (All + per-platform sections with ‹ › arrows), so you can page through each platform's posts.
- [x] **Image generation (live via Gemini)** — provider-agnostic `ImageProvider` (mock → `GeminiImageProvider`, `gemini-2.5-flash-image`), `POST …/content/{id}/image` generates a brand-grounded visual shown in the preview (`image_url`, migration 0006). `IMAGE_PROVIDER=gemini` + `GEMINI_API_KEY`.
- [x] **Universal post editor** (`components/PostEditModal`) — one modal edits a post's copy (title/body) + image (regenerate, product-grounded) and is reused everywhere posts appear: the Content library, the Campaigns review list, and by clicking a post in the Calendar month-grid. Saves via `PATCH …/content/{id}`; editing a reviewed post sends it back to draft. Owners can change anything, wherever they see it.
- [x] **Object storage layer** (`app/storage/`) — provider-agnostic `Storage` (LocalStorage dev + S3/R2 seam); generated images + uploads are stored as files (served at `/media`, proxied), not inline base64. `STORAGE_BACKEND=s3` for production.
- [x] **Product uploads with descriptions** — `assets` table (migrations 0007–0008) gains `name` + `description`; `POST/GET/DELETE …/assets` (multipart, name/description fields). A **Products tab** (renamed from Brand) uploads each product with a short description the AI uses as its **navigator**. Product-grounded image generation (`?asset_id=` → Gemini uses the product photo as the baseline) is unchanged.
- [x] **AI video generation — LIVE via Veo 3.1** — provider-agnostic `VideoProvider` seam (`app/video/`, mock → `GeminiVeoProvider`) with an **async start→poll** design for long renders: `POST …/content/{id}/video` creates a `VideoJob` (migration 0009), `GET …/content/{id}/video` polls it; on success the clip is stored (object-storage layer) and the post's `video_url` is set and rendered as a native `<video>` in the preview. Frontend `VideoButton` (generate + poll) sits beside Generate image in the Content card + edit modal. **Verified end-to-end against the real Google API** (`VIDEO_PROVIDER=veo`, `veo-3.1-fast-generate-preview`): a render completes in ~70s and returns a real ~4 MB MP4, served under `/media`. Available models on this key: `veo-3.1-generate-preview` / `-fast-` / `-lite-` (config `VIDEO_MODEL`). Mock remains the keyless default for dev/tests. Cost note: each clip is a real (paid) Veo generation.
- [x] **Video cost guard + confirmation** — per-tenant **monthly video quota** on the plan (`plans.video_monthly_quota`, migration 0010: Starter 5 / Pro 30 / Growth 100 / Enterprise ∞); `video_service` enforces it on start (`VideoQuotaExceeded` → 402) and exposes `GET …/content/video-quota` (used/limit/remaining). The frontend `VideoButton` opens a **confirmation dialog** before every render showing the paid-render warning + remaining allowance, and disables Generate when the cap is hit.
- [x] **Celery worker for video (long-term path)** — `advance_video_jobs` beat task (every 30s) polls in-flight renders server-side via `video_service.advance_processing_jobs`, so clips finish without the browser polling. Wired into the beat schedule; needs Redis to run (the on-demand GET poll remains the dev fallback since Redis isn't installed here).

## Later (future roadmap)
Ad creation/optimization, competitor analysis, trend prediction, local SEO, website audits, ROI forecasting, CRM, lead nurturing, email/SMS automation, voice/phone AI, appointment booking, workflow automation, integrations marketplace, mobile apps, white-label/agency, multi-location.

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
