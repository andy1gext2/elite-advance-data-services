# Web (Next.js frontend)

React + Next.js 15 (App Router) + TypeScript (strict) + Tailwind CSS, with dark/light theming.
**Scaffolded and running.** First vertical slice is live and wired to the FastAPI backend.

## Run

```powershell
# 1. Backend (keyless dev: repo-root .env sets AI_DEFAULT_PROVIDER=mock + sqlite)
cd ..\..\services\api
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload            # http://127.0.0.1:8000

# 2. Frontend (separate terminal)
cd apps\web
npm install                              # first time only
npm run dev                              # http://127.0.0.1:3000
```

Open http://127.0.0.1:3000 → sign up → onboard a business → generate a repurposed
post set from one idea → approve/reject items.

## How it talks to the backend (no CORS)

The browser only ever calls the Next origin. `next.config.mjs` rewrites `/api/*`
(and `/health`) to the FastAPI backend server-side, so there is no cross-origin
request. Point at a different backend with `API_PROXY_TARGET` (see `.env.local.example`).

## Structure

- `src/app/` — routes: `/login`, `/signup`, `/onboarding`, `/dashboard`,
  `/businesses/[id]/content` (the content studio).
- `src/lib/api.ts` — typed client for the backend; transparent token refresh on 401.
- `src/lib/auth.tsx` — auth context (tokens in localStorage, `/me` hydration).
- `src/lib/types.ts` — mirrors the FastAPI response schemas.
- `src/components/` — `ui.tsx` primitives (Button/Input/Card/Badge…), `AppShell`,
  `AuthLayout`, `ThemeToggle`.
- Theming: Tailwind `darkMode: "class"`; semantic CSS-variable tokens in
  `globals.css`; no-flash theme script in `layout.tsx`.

## Design philosophy (from the spec)

Premium, modern, intelligent. Avoid clutter. Prioritize speed. Smooth animations.
Show actionable insights, not raw data dumps. The owner should feel they hired an
entire AI marketing department.

## Next steps

Widen from the slice: content list filters/editing, the AI content calendar view,
the scheduling/publishing calendar UI, then Phase 4/5 screens (reputation,
analytics dashboard) as those backends land.
