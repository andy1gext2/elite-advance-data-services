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
    # Model tiering: route short, low-stakes generations to a cheaper model to
    # cut cost without hurting the high-value output. Set enabled=False to send
    # everything to the default model.
    ai_cheap_model: str = "claude-haiku-4-5"
    ai_tiering_enabled: bool = True
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # Image generation (provider-agnostic; default "mock" runs keyless with a
    # stylized placeholder). Set image_provider=gemini + gemini_api_key to go live.
    image_provider: str = "mock"
    image_model: str = "gemini-2.5-flash-image"
    gemini_api_key: str | None = None

    # Video generation (async; default "mock" runs keyless). Set video_provider=veo
    # + a PAID Gemini API key (reuses gemini_api_key) to go live. Veo needs billing
    # enabled — a free AI-Studio key / consumer Google One plan won't have access.
    video_provider: str = "mock"
    video_model: str = "veo-3.1-fast-generate-preview"

    # Social OAuth. Real Meta (Facebook/Instagram) + Google Business connectors
    # activate automatically when these are set; otherwise the mock consent flow is
    # used. Real connect also needs the redirect URI registered with each provider
    # (see api_base_url + docs/integrations.md) and platform app review.
    meta_app_id: str | None = None
    meta_app_secret: str | None = None
    meta_graph_version: str = "v21.0"
    google_client_id: str | None = None
    google_client_secret: str | None = None

    # Billing (Stripe). Disabled until stripe_secret_key is set — endpoints then
    # 503 / fall back to dev grants. The webhook is the source of truth for plan +
    # credit changes. Price IDs come from the Stripe dashboard (per tier + credits).
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_starter: str | None = None
    stripe_price_professional: str | None = None
    stripe_price_agency: str | None = None
    stripe_credits_price_id: str | None = None
    stripe_credits_per_pack: int = 10

    # File storage (product photos + generated images). "local" writes to disk and
    # serves under /media (dev); "s3" uploads to S3/S3-compatible (R2, etc.).
    storage_backend: str = "local"
    media_root: str = "./media"
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_endpoint_url: str | None = None  # for S3-compatible providers
    s3_public_base: str | None = None   # CDN / public base URL
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # Email (password-reset codes, notifications). "mock" logs the message (dev —
    # the reset code also appears in the API response in non-production). Set
    # email_provider=smtp + the SMTP_* vars (e.g. Resend/SendGrid/SES/Gmail) to
    # actually deliver mail. email_from must be a verified sender on your provider.
    email_provider: str = "mock"
    email_from: str = "Elite Advance <no-reply@example.com>"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True

    # Password reset codes.
    reset_code_ttl_minutes: int = 15
    reset_max_attempts: int = 5

    # Operator/admin. Comma-separated emails allowed to see the cross-tenant cost
    # dashboard (GET /admin/usage). Defaults to the platform owner.
    platform_admin_emails: str = "andy1gext2@gmail.com"

    # Media cost estimates (USD) for the operator cost dashboard. Text (Claude) cost
    # is computed exactly from stored token counts; image/video providers bill per
    # asset, so these are tunable estimates (Gemini image ~ a few cents; a Veo clip
    # is a few dollars). Adjust to your real provider pricing.
    cost_per_image_usd: float = 0.04
    cost_per_video_usd: float = 2.00

    @property
    def admin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.platform_admin_emails.split(",") if e.strip()}

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
