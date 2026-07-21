# Deploying Elite Advance Data Services

Goal: take the app from local-only to live on the internet.
**Stack:** API + Celery worker + Postgres + Redis on **Railway**; Next.js frontend on **Vercel**.

The browser only ever talks to the Vercel frontend, which proxies `/api/*` to the
Railway API server-side — so there is **no CORS to configure** in production.

---

## 0. Prerequisites (one-time, on your machine)

These are missing on the current machine — install them first:

- **git** — <https://git-scm.com/download/win>. Every host deploys from a git repo.
- A **GitHub** account (free).
- A **Railway** account and a **Vercel** account (both have free tiers; Railway needs a card for the databases).
- (Optional but recommended) an **Anthropic API key** for real AI — otherwise set `AI_DEFAULT_PROVIDER=mock`.

Put the code on GitHub:

```powershell
cd "C:\Users\sales\OneDrive\Desktop\Elite advance data services"
git init
git add .
git commit -m "Initial commit"
# create an empty repo on github.com first, then:
git remote add origin https://github.com/<you>/elite-advance-data-services.git
git branch -M main
git push -u origin main
```

`.env`, `.venv/`, and `node_modules/` are already git-ignored. Confirm no real
secrets are staged before pushing.

---

## 1. Generate production secrets

```powershell
cd services\api ; .venv\Scripts\Activate.ps1
py ..\..\scripts\gen_secrets.py
```

Copy the three values (`APP_SECRET_KEY`, `JWT_SECRET`, `FERNET_KEY`). You'll paste
them into Railway. See [.env.production.example](.env.production.example) for the full list.

> ⚠️ `FERNET_KEY` encrypts stored OAuth tokens. Set it **once** and keep it — rotating
> it means every connected account must reconnect.

---

## 2. Railway — databases

1. New Project → **Add Postgres** (Deploy a Postgres database).
2. In the same project → **Add Redis**.

Railway now exposes `${{ Postgres.DATABASE_URL }}` and `${{ Redis.REDIS_URL }}` as
reference variables you'll wire into the services below.

---

## 3. Railway — API service

1. **New → Deploy from GitHub repo** → pick your repo.
2. **Settings → Root Directory:** `services/api`
   (Railway then uses [services/api/Dockerfile](services/api/Dockerfile) and
   [services/api/railway.json](services/api/railway.json) — which run
   `alembic upgrade head` → seed plans → `uvicorn` on deploy, with a `/health` check.)
3. **Variables** — add:

   | Key | Value |
   |-----|-------|
   | `APP_ENV` | `production` |
   | `APP_SECRET_KEY` | *(from step 1)* |
   | `JWT_SECRET` | *(from step 1)* |
   | `FERNET_KEY` | *(from step 1)* |
   | `DATABASE_URL` | `${{ Postgres.DATABASE_URL }}` |
   | `REDIS_URL` | `${{ Redis.REDIS_URL }}` |
   | `AI_DEFAULT_PROVIDER` | `anthropic` (or `mock` to launch keyless) |
   | `ANTHROPIC_API_KEY` | *(your key, if using anthropic)* |
   | `WEB_BASE_URL` | *(Vercel URL — fill after step 5, then redeploy)* |
   | `API_BASE_URL` | *(this service's public URL — see below)* |

4. **Settings → Networking → Generate Domain.** Copy it (e.g.
   `https://elite-api-production.up.railway.app`) and set it as `API_BASE_URL`.
   (Used to build OAuth redirect URIs.)
5. Deploy. Check the logs show `alembic ... running upgrade → 0004` and
   `Application startup complete`, then open `https://<api-domain>/health` → `{"status":"ok"}`.

---

## 4. Railway — worker service (Celery)

The publish engine + review polling run on a schedule via Celery beat.

1. In the **same project → New → GitHub repo** (same repo again).
2. **Root Directory:** `services/api`
3. **Settings → Config-as-code → Railway Config File:** `railway.worker.json`
   (relative to the root directory). This is the key step: the worker uses
   [services/api/railway.worker.json](services/api/railway.worker.json) — which
   sets the Celery start command and, by declaring **no** `healthcheckPath`, skips
   the health check (the worker has no web server, so `/health` would fail-loop).
   Do **not** rely on a dashboard start command — the repo config file overrides it.
4. **Variables:** same as the API service — at minimum `DATABASE_URL`, `REDIS_URL`,
   `FERNET_KEY` (must match the API's exactly, or it can't decrypt stored tokens),
   `JWT_SECRET`, `APP_SECRET_KEY`, `APP_ENV=production`, and the `AI_*` keys. The
   worker needs no public domain. The safest way is reference variables pointing at
   the other services, e.g. `${{ Postgres.DATABASE_URL }}`, `${{ Redis.REDIS_URL }}`,
   and `${{ <api-service-name>.FERNET_KEY }}`.
5. Deploy. Logs should show `celery@... ready` and `beat: Starting`.

---

## 5. Vercel — frontend

1. **Add New → Project** → import the same GitHub repo.
2. **Root Directory:** `apps/web` (Vercel auto-detects Next.js).
3. **Environment Variables:**

   | Key | Value |
   |-----|-------|
   | `API_PROXY_TARGET` | your Railway API domain, e.g. `https://elite-api-production.up.railway.app` |

   ([next.config.mjs](apps/web/next.config.mjs) rewrites `/api/*` and `/health` to this.)
4. Deploy. Copy the Vercel URL (e.g. `https://elite-advance.vercel.app`).
5. Back in **Railway → API service**, set `WEB_BASE_URL` to that URL and redeploy
   (so OAuth callbacks redirect to the right place).

---

## 6. Smoke test the live site

1. Open the Vercel URL → the marketing page loads.
2. **Get started** → sign up → onboard a business.
3. Generate a repurposed post set → approve one.
4. Dashboard shows real KPIs; Reputation → **Sync reviews**.
5. Schedule tab → **Connect with Instagram** → (mock) consent → lands back connected.

If all of that works, you're live.

---

## What is NOT production-ready yet (do before charging money / real posting)

- **Billing** — the pricing page is display-only; no Stripe. Sign-ups are free.
- **Real social publishing** — connectors are mocks; posts won't appear on real
  platforms until each platform's API is approved and its connector is implemented
  (the OAuth flow + connector seam are already in place — see `docs/integrations.md`).
- **Rate limiting, audit-log wiring, monitoring/alerting** — Phase 6 (`docs/roadmap.md`).
- **Custom domain + email verification / password reset** — add when ready.

## Rolling out updates

`git push` to `main` → Railway and Vercel auto-redeploy. API migrations run
automatically on each deploy (`alembic upgrade head` is idempotent).
