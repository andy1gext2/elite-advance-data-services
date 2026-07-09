"""Connector selection. Every platform currently resolves to the MockConnector;
real per-platform connectors register here as their API access is approved
(see docs/integrations.md for the approval status of each)."""
from __future__ import annotations

from app.connectors.base import PlatformConnector
from app.connectors.mock import MockConnector

# As live connectors land: _CONNECTORS[Platform.INSTAGRAM.value] = InstagramConnector()
_CONNECTORS: dict[str, PlatformConnector] = {}


def get_connector(platform: str) -> PlatformConnector:
    return _CONNECTORS.get(platform) or MockConnector(platform)
