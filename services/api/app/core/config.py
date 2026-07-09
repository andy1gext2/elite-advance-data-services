"""Application settings, loaded from environment / .env (pydantic-settings).

Provider-agnostic: no vendor SDK is imported here. Business logic reads Settings,
never os.environ directly.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),  # repo-root .env when run from services/api
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_secret_key: str = "change-me"
    api_base_url: str = "http://127.0.0.1:8000"
    web_base_url: str = "http://127.0.0.1:3000"

    # Auth / JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_days: int = 30

    # Data
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/elite"
    redis_url: str = "redis://localhost:6379/0"

    # Secrets encryption
    fernet_key: str | None = None

    # AI
    ai_default_provider: str = "anthropic"
    ai_default_model: str = "claude-opus-4-8"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @property
    def sqlalchemy_url(self) -> str:
        """The DATABASE_URL normalized to SQLAlchemy's psycopg3 dialect.

        Managed hosts (Railway, Heroku, …) hand out `postgres://` or
        `postgresql://` URLs, which SQLAlchemy would route to psycopg2. We ship
        psycopg3, so rewrite the scheme. SQLite and already-qualified URLs pass
        through untouched.
        """
        url = self.database_url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
