# Limitations, Constraints & Risks

An honest account of what will slow this project down. Grouped by type. These are not blockers to *starting* — they shape sequencing and expectations.

## 1. Local environment (immediate)
- **No Node/npm** → the Next.js frontend can't be installed, built, or run until Node 20+ is installed.
- **No Docker** → Postgres, Redis, and Celery workers can't run via containers locally. (Alternatives: native installs, or a hosted dev DB like Neon/Supabase + Upstash Redis.)
- **No git** → no version control/history yet. Install Git for Windows to enable commits.
- **Windows + PowerShell** → some tooling assumes Unix. Notably **Celery's default prefork pool doesn't work well on Windows** (use `--pool=solo`/`gevent` in dev, or run workers in WSL/Docker/Linux).
- **Python 3.12 is present** → backend work can proceed now.

## 2. Third-party platform access (biggest external risk)
Most integrations are gated by approval, verification, cost, or maturity — the code is the easy part:
- **Meta (Instagram/Facebook/Threads):** App Review + Business Verification; Instagram publishing needs Business/Creator accounts via Graph API; Threads API is new and limited.
- **LinkedIn:** Community Management API is partner-gated; default access is minimal.
- **Google Business Profile:** API access requires an approved request; reviews/posts are behind that gate. No open Google reviews API; scraping violates ToS.
- **X (Twitter):** meaningful posting/reading requires a **paid** API tier; costs rise steeply with volume.
- **TikTok:** Content Posting API requires audit/approval.
- **YouTube:** uploads consume large, limited daily quota.
- **Consequence:** file for API access **early and in parallel**; approvals take days–weeks and block features regardless of code readiness. Build against mock connectors so progress isn't gated on approvals.

## 3. AI cost, quality & safety
- **Cost at scale:** thousands of businesses generating multi-platform content + review responses + analytics summaries = significant token spend. Needs per-tenant quotas, caching, model tiering (Haiku for cheap tasks, Opus for hard reasoning), and batching.
- **Auto-publishing risk:** fully automated posts/review responses can produce off-brand or inappropriate output. Recommend human-in-the-loop approval by default, especially for negative-review responses.
- **Platform policy:** automated posting/engagement must respect each platform's automation rules to avoid account suspension.
- **Provider-agnostic ≠ free:** the abstraction adds value but each provider has different capabilities/prompt behavior; "swap without changes" holds for orchestration, not always for prompt quality.

## 4. Scale & infrastructure
- 10,000+ tenants and millions of events demand partitioning/rollups, connection pooling, horizontal scaling, CDN, and caching — real infra + cost, not just code. Don't query raw `metric_event` live; use rollups.
- Background load (scheduled publishes, review polling, report generation) needs a robust Celery/queue setup with retries, idempotency, and rate-limit awareness.

## 5. Compliance & security
- **SOC 2 / GDPR / CCPA readiness** is largely organizational process (policies, DPAs, audits, data-subject workflows), not something code alone satisfies. Build the technical controls (encryption, audit logs, RBAC, data export/delete) early; the certifications are a separate track.
- Storing OAuth tokens for many platforms concentrates risk — encryption at rest, rotation, and least-privilege scopes are mandatory.

## 6. Scope & product risk
- The brief spans content, scheduling, reputation, analytics, insights, billing, multi-tenant admin — each a product on its own. **Sequencing matters more than breadth.** See [roadmap.md](roadmap.md); the fastest valuable slice needs zero external approvals.
- "Real-time KPIs" and "trend prediction/competitor analysis" depend on data you can legally obtain — often limited by the same API gates above.

## What to do about it (summary)
1. Install Node, Docker, git (or use hosted DB/Redis) to unblock the full stack.
2. Start with the **approval-free vertical slice**: onboarding → AI repurposed content → approve.
3. File for every needed platform API **now**, in parallel, behind mock connectors.
4. Bake in AI quotas, human approval, encryption, and audit logging from Phase 1 — retrofitting them is painful.
