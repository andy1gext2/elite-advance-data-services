"""Video-provider selection + FastAPI dependency. Mirrors the image registry:
`VIDEO_PROVIDER` picks the concrete provider; in non-production a Veo selection
with no key falls back to the mock so the app runs out of the box."""
from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import get_settings
from app.video.base import VideoProvider
from app.video.mock import MockVideoProvider

logger = logging.getLogger(__name__)


@lru_cache
def get_video_provider() -> VideoProvider:
    settings = get_settings()
    name = settings.video_provider.lower()

    if name == "mock":
        return MockVideoProvider()

    if name == "veo":
        if not settings.gemini_api_key:
            if settings.is_production:
                raise RuntimeError("GEMINI_API_KEY is required when VIDEO_PROVIDER=veo")
            logger.warning("GEMINI_API_KEY not set — falling back to MockVideoProvider (dev).")
            return MockVideoProvider()
        from app.video.veo import GeminiVeoProvider

        return GeminiVeoProvider(settings.gemini_api_key, settings.video_model)

    raise ValueError(f"Unknown video provider: {settings.video_provider!r}")


def get_video_provider_dep() -> VideoProvider:
    """FastAPI dependency. Override in tests to inject a mock provider."""
    return get_video_provider()
