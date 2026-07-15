"""OAuth connect flow for social accounts.

Production-shaped and provider-agnostic: `start` mints a signed `state` and asks
the platform's connector for its authorize URL; the platform redirects the browser
back to our callback, which validates `state`, exchanges the code for a token via
the connector, and stores it encrypted. Real connectors slot in unchanged — only
`authorize_url`/`exchange_code` differ per platform (see connectors/).

`state` is a short-lived signed JWT carrying the tenant + platform, so the callback
(which the platform calls without our auth header) is safe against forgery/CSRF."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.connectors.registry import get_connector
from app.core.config import get_settings
from app.services import scheduling_service

STATE_TYPE = "oauth_state"
STATE_TTL = timedelta(minutes=10)


class BadState(Exception):
    ...


def _settings():
    return get_settings()


def callback_uri(platform: str) -> str:
    """The redirect URI the platform sends the browser back to (must match the one
    registered with the provider). Absolute so it works as an external redirect."""
    return f"{_settings().api_base_url}/api/v1/integrations/oauth/{platform}/callback"


def make_state(business_id: uuid.UUID, platform: str) -> str:
    now = datetime.now(timezone.utc)
    s = _settings()
    return jwt.encode(
        {
            "sub": str(business_id),
            "platform": platform,
            "type": STATE_TYPE,
            "iat": now,
            "exp": now + STATE_TTL,
            "jti": uuid.uuid4().hex,
        },
        s.jwt_secret,
        algorithm=s.jwt_algorithm,
    )


def read_state(token: str | None) -> tuple[uuid.UUID, str]:
    if not token:
        raise BadState("missing state")
    s = _settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        if payload.get("type") != STATE_TYPE:
            raise BadState("wrong token type")
        return uuid.UUID(payload["sub"]), payload["platform"]
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise BadState(str(exc)) from exc


def authorize_url_for(business_id: uuid.UUID, platform: str) -> str:
    """Build the provider consent URL to redirect the user's browser to."""
    state = make_state(business_id, platform)
    return get_connector(platform).authorize_url(
        redirect_uri=callback_uri(platform), state=state
    )


def complete(db, *, platform: str, code: str, business_id: uuid.UUID):
    """Exchange the auth code for a token and persist the connected account."""
    tokens = get_connector(platform).exchange_code(
        code=code, redirect_uri=callback_uri(platform)
    )
    return scheduling_service.upsert_oauth_account(
        db,
        business_id=business_id,
        platform=platform,
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        external_id=tokens.get("external_id"),
        display_name=tokens.get("display_name"),
        expires_at=tokens.get("expires_at"),
    )
