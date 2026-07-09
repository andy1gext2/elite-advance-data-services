"""Mock connector — proves the publish loop end-to-end without any real platform
API or approval. Every real connector will implement the same interface, so the
scheduling/publish engine is unchanged when live connectors land."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from app.connectors.base import PlatformConnector, PublishResult

# Deterministic sample reviews (stable external_ids so re-sync dedupes cleanly).
# (external_id, author, rating, body, days_ago) — spans sentiment + recency.
_SAMPLE_REVIEWS = [
    ("rev-001", "Jordan P.", 5, "Absolutely love this place — the staff are so friendly and the coffee is amazing!", 2),
    ("rev-002", "Casey M.", 4, "Great atmosphere and fast, attentive service. Will definitely come back.", 9),
    ("rev-003", "Alex T.", 2, "Waited far too long and my order came out cold. Really disappointing.", 18),
    ("rev-004", "Sam R.", 1, "Rude staff and overpriced for what you get. Terrible experience overall.", 41),
    ("rev-005", "Riley K.", 3, "Decent spot but nothing special. The coffee was pretty average.", 46),
    ("rev-006", "Morgan L.", 5, "Best latte in town and the pastries are fresh — highly recommend!", 1),
]


class MockConnector(PlatformConnector):
    def __init__(self, platform: str) -> None:
        self.platform = platform

    def publish(self, *, account_token: str, body: str, meta: dict) -> PublishResult:
        if not body.strip():
            return PublishResult(ok=False, error="empty content")
        # Simulate a successful post with a platform-style id.
        return PublishResult(ok=True, external_id=f"{self.platform}_{uuid.uuid4().hex[:12]}")

    # ── OAuth (simulated) ───────────────────────────
    # A real connector points these at the platform's OAuth endpoints. The mock
    # points authorize_url at our own dev consent page (co-located with the
    # callback) and mints a fake token on exchange — same interface, so a live
    # connector is a drop-in replacement.
    def authorize_url(self, *, redirect_uri: str, state: str) -> str:
        # redirect_uri is ".../integrations/oauth/{platform}/callback"; the mock
        # consent screen lives at ".../integrations/oauth/_mock/authorize".
        base = redirect_uri.rsplit("/", 2)[0]
        return (
            f"{base}/_mock/authorize"
            f"?platform={self.platform}"
            f"&state={quote(state, safe='')}"
            f"&redirect_uri={quote(redirect_uri, safe='')}"
        )

    def exchange_code(self, *, code: str, redirect_uri: str) -> dict:
        return {
            "access_token": f"mock-oauth-token-{uuid.uuid4().hex}",
            "external_id": f"{self.platform}_{uuid.uuid4().hex[:10]}",
            "display_name": f"{self.platform.replace('_', ' ').title()} Account",
            "expires_at": None,
        }

    def fetch_reviews(self, *, account_token: str) -> list[dict]:
        """Return a fixed sample set. Stable external_ids let the ingest layer
        dedupe on re-sync, mirroring how a real polling connector behaves."""
        now = datetime.now(timezone.utc)
        return [
            {
                "external_id": ext,
                "author_name": author,
                "rating": rating,
                "body": body,
                "reviewed_at": (now - timedelta(days=days_ago)).isoformat(),
            }
            for ext, author, rating, body, days_ago in _SAMPLE_REVIEWS
        ]
