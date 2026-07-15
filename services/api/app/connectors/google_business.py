"""Google Business Profile connector — real OAuth via Google's OAuth 2.0.

Activated by GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET (else the registry falls back to
the mock). NOTE: the Business Profile API is access-restricted — you must request
access (allowlist) from Google before the identity/publish calls will succeed; the
OAuth handshake itself works with any OAuth client.

Publishing (local posts) isn't implemented yet and returns a clear failure.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from app.connectors.base import PlatformConnector, PublishResult
from app.core.config import get_settings

_SCOPE = "https://www.googleapis.com/auth/business.manage"


class GoogleBusinessConnector(PlatformConnector):
    platform = "google_business"

    def supports_publish(self) -> bool:
        return False  # GBP local posts pending Business Profile API access

    def authorize_url(self, *, redirect_uri: str, state: str) -> str:
        s = get_settings()
        params = urlencode({
            "client_id": s.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": _SCOPE,
            "state": state,
            "access_type": "offline",   # get a refresh token
            "prompt": "consent",
            "include_granted_scopes": "true",
        })
        return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    def exchange_code(self, *, code: str, redirect_uri: str) -> dict:
        import httpx

        s = get_settings()
        with httpx.Client(timeout=30) as client:
            r = client.post("https://oauth2.googleapis.com/token", data={
                "code": code,
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            })
            r.raise_for_status()
            tok = r.json()
            access = tok["access_token"]
            expires_in = tok.get("expires_in")
            display, external = self._identity(client, access)

        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            if expires_in else None
        )
        return {
            "access_token": access,
            "refresh_token": tok.get("refresh_token"),  # persisted for long-term access
            "external_id": external,
            "display_name": display,
            "expires_at": expires_at,
        }

    def refresh(self, *, refresh_token: str | None, access_token: str) -> dict | None:
        if not refresh_token:
            return None
        import httpx

        s = get_settings()
        with httpx.Client(timeout=30) as client:
            r = client.post("https://oauth2.googleapis.com/token", data={
                "refresh_token": refresh_token,
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "grant_type": "refresh_token",
            })
            if not r.is_success:
                return None
            tok = r.json()
        expires_in = tok.get("expires_in")
        return {
            "access_token": tok["access_token"],
            "refresh_token": refresh_token,  # Google reuses the same refresh token
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
                if expires_in else None
            ),
        }

    def _identity(self, client, access: str) -> tuple[str | None, str | None]:
        try:
            r = client.get(
                "https://mybusinessaccountmanagement.googleapis.com/v1/accounts",
                headers={"Authorization": f"Bearer {access}"},
            )
            accounts = (r.json().get("accounts") or []) if r.is_success else []
            if accounts:
                a = accounts[0]
                return (a.get("accountName") or "Google Business", a.get("name"))
        except Exception:  # noqa: BLE001 - Business Profile API may be gated
            pass
        return ("Google Business Profile", None)

    def publish(self, *, account_token: str, body: str, meta: dict) -> PublishResult:
        return PublishResult(
            ok=False,
            error="Google Business posting is not implemented yet (needs Business Profile API access).",
        )
