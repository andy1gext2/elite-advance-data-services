"""Connector selection. Real per-platform connectors activate automatically once
their OAuth credentials are configured; without creds every platform resolves to
the MockConnector (so dev works out of the box). See docs/integrations.md."""
from __future__ import annotations

from app.connectors.base import PlatformConnector
from app.connectors.mock import MockConnector
from app.core.config import get_settings

_META_PLATFORMS = {"facebook", "instagram"}


def get_connector(platform: str) -> PlatformConnector:
    s = get_settings()

    if platform in _META_PLATFORMS and s.meta_app_id and s.meta_app_secret:
        from app.connectors.meta import MetaConnector

        return MetaConnector(platform)

    if platform == "google_business" and s.google_client_id and s.google_client_secret:
        from app.connectors.google_business import GoogleBusinessConnector

        return GoogleBusinessConnector()

    return MockConnector(platform)
