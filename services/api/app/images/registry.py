"""Image-provider selection + FastAPI dependency. Mirrors the AI text registry:
`IMAGE_PROVIDER` picks the concrete provider; in non-production a Gemini selection
with no key falls back to the mock so the app runs out of the box."""
from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_settings
from app.images.base import ImageProvider
from app.images.mock import MockImageProvider

logger = logging.getLogger(__name__)


@lru_cache
def get_image_provider() -> ImageProvider:
    settings = get_settings()
    name = settings.image_provider.lower()

    if name == "mock":
        return MockImageProvider()

    if name == "gemini":
        if not settings.gemini_api_key:
            if settings.is_production:
                raise RuntimeError("GEMINI_API_KEY is required when IMAGE_PROVIDER=gemini")
            logger.warning("GEMINI_API_KEY not set — falling back to MockImageProvider (dev).")
            return MockImageProvider()
        from app.images.gemini import GeminiImageProvider

        return GeminiImageProvider(settings.gemini_api_key, settings.image_model)

    raise ValueError(f"Unknown image provider: {settings.image_provider!r}")


def get_image_provider_dep() -> ImageProvider:
    """FastAPI dependency. Override in tests to inject a mock provider."""
    return get_image_provider()
