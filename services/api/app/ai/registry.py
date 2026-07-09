"""Provider selection + the AIRouter FastAPI dependency.

`AI_DEFAULT_PROVIDER` picks the concrete provider. In non-production, an
`anthropic` selection with no API key falls back to the mock provider so the app
runs out of the box; in production a missing key is a hard error.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.ai.base import AIProvider
from app.ai.providers.mock import MockProvider
from app.ai.router import AIRouter
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_provider() -> AIProvider:
    settings = get_settings()
    name = settings.ai_default_provider.lower()
    model = settings.ai_default_model

    if name == "mock":
        return MockProvider(model)

    if name == "anthropic":
        if not settings.anthropic_api_key:
            if settings.is_production:
                raise RuntimeError("ANTHROPIC_API_KEY is required in production")
            logger.warning("ANTHROPIC_API_KEY not set — falling back to MockProvider (dev).")
            return MockProvider(model)
        from app.ai.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(api_key=settings.anthropic_api_key, default_model=model)

    raise ValueError(f"Unknown AI provider: {settings.ai_default_provider!r}")


def get_ai_router() -> AIRouter:
    """FastAPI dependency. Override in tests to inject a mock-backed router."""
    return AIRouter(get_provider())
