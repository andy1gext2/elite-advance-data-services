"""Provider-agnostic connector contract.

Each platform gets an isolated connector implementing this interface, so an API
change on one platform touches exactly one module. Unsupported/pending operations
raise rather than leaking platform quirks upward, letting the UI show accurate
per-account status.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ConnectorError(Exception):
    ...


class NotSupported(ConnectorError):
    """The platform/connector does not implement this operation."""


class PendingApproval(ConnectorError):
    """The platform API is behind an approval/verification not yet granted."""


@dataclass
class PublishResult:
    ok: bool
    external_id: str | None = None
    error: str | None = None


class PlatformConnector(ABC):
    platform: str = "base"
    # True for real providers; the mock sets this False (simulated dev connector).
    live: bool = True

    @abstractmethod
    def publish(self, *, account_token: str, body: str, meta: dict) -> PublishResult:
        ...

    def supports_publish(self) -> bool:
        """Whether this connector can actually publish yet (vs pending approval)."""
        return True

    # Read paths land in later phases (reputation, analytics).
    def fetch_reviews(self, *, account_token: str) -> list[dict]:
        raise NotSupported(f"{self.platform}: fetch_reviews not implemented")

    def fetch_metrics(self, *, account_token: str) -> dict:
        raise NotSupported(f"{self.platform}: fetch_metrics not implemented")

    # OAuth handshake — real connectors implement these; see docs/integrations.md.
    def authorize_url(self, *, redirect_uri: str, state: str) -> str:
        raise NotSupported(f"{self.platform}: OAuth not implemented")

    def exchange_code(self, *, code: str, redirect_uri: str) -> dict:
        raise NotSupported(f"{self.platform}: OAuth not implemented")

    def refresh(self, *, refresh_token: str | None, access_token: str) -> dict | None:
        """Return a fresh {access_token, expires_at, refresh_token?} or None if the
        provider's token isn't refreshable / this connector doesn't support it."""
        return None
