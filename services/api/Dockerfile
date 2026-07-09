# API + worker image (same image, different start command per Railway service).
# Build context is services/api (Railway service root directory).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source (see .dockerignore for exclusions).
COPY . .

EXPOSE 8000

# Default = the web API (migrate, seed idempotently, then serve). Railway's
# worker service overrides this with the Celery command (see DEPLOY.md).
CMD ["sh", "-c", "alembic upgrade head && python scripts/seed_plans.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
