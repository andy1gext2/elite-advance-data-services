#!/usr/bin/env sh
# Production start script (Railway). Run as `sh start.sh` so ${PORT} is always
# shell-expanded, regardless of whether the platform execs the start command
# directly or via a shell. Migrations are idempotent; seeding is best-effort so
# a seed hiccup never blocks the web server (which the healthcheck depends on).
set -e

echo "== boot: migrate =="
alembic upgrade head

echo "== boot: seed plans =="
python scripts/seed_plans.py || echo "!! seed failed, continuing to serve"

echo "== boot: serve on port ${PORT:-8000} =="
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
