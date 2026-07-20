"""Meta (Facebook + Instagram) connector — real OAuth via Facebook Login.

Both Facebook Pages and Instagram Business accounts authenticate through Facebook
Login (an IG Business account is linked to a Page), so one connector serves both
`facebook` and `instagram`. Activated by META_APP_ID/META_APP_SECRET (else the
registry falls back to the mock).

Publishing is not implemented yet — it needs Page access tokens (and, for IG, the
media-container flow) plus Meta App Review for `pages_manage_posts` /
`instagram_content_publish`. `publish` returns a clear failure rather than raising
so the publish engine stays healthy.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from app.connectors.base import PlatformConnector, PublishResult
from app.core.config import get_settings

# Permissions requested per platform. Advanced perms require Meta App Review.
#
# Reputation note: Facebook's star-rating/Recommendations *reviews* API is
# deprecated, so sentiment + AI responses on Meta run off Page COMMENTS and
# @-mentions instead of star reviews. We therefore request, up front (so no
# re-consent is needed after App Review):
#   • pages_read_engagement    — read reactions/comments on the Page's own posts
#   • pages_read_user_content  — read user-generated comments/posts/mentions (sentiment)
#   • pages_manage_engagement  — reply to comments AS the Page (AI responds to customers)
#   • instagram_manage_comments — read + reply to IG comments and mentions
_SCOPES = {
    "facebook": [
        "public_profile", "pages_show_list", "pages_read_engagement",
        "pages_read_user_content", "pages_manage_engagement",
        "pages_manage_posts", "business_management",
    ],
    "instagram": [
        "public_profile", "pages_show_list", "instagram_basic",
        "instagram_manage_comments", "instagram_content_publish",
        "business_management",
    ],
}


class MetaConnector(PlatformConnector):
    def __init__(self, platform: str) -> None:
        self.platform = platform  # "facebook" | "instagram"

    def supports_publish(self) -> bool:
        # Facebook Page posting is live; Instagram (media-container flow) is pending.
        return self.platform == "facebook"

    def _v(self) -> str:
        return get_settings().meta_graph_version

    def authorize_url(self, *, redirect_uri: str, state: str) -> str:
        s = get_settings()
        params = urlencode({
            "client_id": s.meta_app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": ",".join(_SCOPES.get(self.platform, _SCOPES["facebook"])),
        })
        return f"https://www.facebook.com/{self._v()}/dialog/oauth?{params}"

    def exchange_code(self, *, code: str, redirect_uri: str) -> dict:
        import httpx

        s = get_settings()
        base = f"https://graph.facebook.com/{self._v()}"
        with httpx.Client(timeout=30) as client:
            # 1) code -> short-lived user token
            r = client.get(f"{base}/oauth/access_token", params={
                "client_id": s.meta_app_id,
                "client_secret": s.meta_app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            })
            r.raise_for_status()
            token = r.json()["access_token"]

            # 2) exchange for a long-lived token (~60 days)
            r2 = client.get(f"{base}/oauth/access_token", params={
                "grant_type": "fb_exchange_token",
                "client_id": s.meta_app_id,
                "client_secret": s.meta_app_secret,
                "fb_exchange_token": token,
            })
            long = r2.json() if r2.is_success else {}
            access = long.get("access_token", token)
            expires_in = long.get("expires_in")

            # 3) who did we connect? (best-effort — don't fail the connect on this)
            display, external = self._identity(client, base, access)

        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
            if expires_in else None
        )
        return {
            "access_token": access,
            "external_id": external,
            "display_name": display,
            "expires_at": expires_at,
        }

    def _identity(self, client, base: str, access: str) -> tuple[str | None, str | None]:
        try:
            me = client.get(f"{base}/me", params={"fields": "id,name", "access_token": access})
            data = me.json() if me.is_success else {}
            label = "Instagram" if self.platform == "instagram" else "Facebook"
            name = data.get("name")
            return (f"{name} ({label})" if name else f"{label} Account", data.get("id"))
        except Exception:  # noqa: BLE001 - identity is a nicety, not required to connect
            return (f"{self.platform.title()} Account", None)

    def refresh(self, *, refresh_token: str | None, access_token: str) -> dict | None:
        """Meta has no refresh token; re-exchange the current long-lived user token
        for another long-lived token (~60 days) to keep the session alive."""
        import httpx

        s = get_settings()
        with httpx.Client(timeout=30) as client:
            r = client.get(f"https://graph.facebook.com/{self._v()}/oauth/access_token", params={
                "grant_type": "fb_exchange_token",
                "client_id": s.meta_app_id,
                "client_secret": s.meta_app_secret,
                "fb_exchange_token": access_token,
            })
            if not r.is_success:
                return None
            tok = r.json()
        if "access_token" not in tok:
            return None
        expires_in = tok.get("expires_in")
        return {
            "access_token": tok["access_token"],
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))
                if expires_in else None
            ),
        }

    def publish(self, *, account_token: str, body: str, meta: dict) -> PublishResult:
        if self.platform != "facebook":
            # Instagram publishing is a 2-step media-container flow needing a public
            # image URL + the IG Business account id — a separate build.
            return PublishResult(
                ok=False,
                error="Instagram publishing needs the media-container flow (not yet implemented).",
            )
        if not body.strip():
            return PublishResult(ok=False, error="empty content")

        import httpx

        base = f"https://graph.facebook.com/{self._v()}"
        try:
            with httpx.Client(timeout=30) as client:
                # The user token can't post to a Page — fetch the Page + its own token.
                pages = client.get(f"{base}/me/accounts", params={
                    "fields": "id,name,access_token",
                    "access_token": account_token,
                })
                data = (pages.json().get("data") or []) if pages.is_success else []
                if not data:
                    return PublishResult(ok=False, error="No Facebook Page found on this account.")
                page = data[0]
                posted = client.post(f"{base}/{page['id']}/feed", data={
                    "message": body,
                    "access_token": page["access_token"],
                })
            if posted.is_success:
                return PublishResult(ok=True, external_id=posted.json().get("id"))
            return PublishResult(ok=False, error=f"Facebook API: {posted.text[:200]}")
        except Exception as exc:  # noqa: BLE001 - never crash the publish engine
            return PublishResult(ok=False, error=f"Facebook publish failed: {exc}")
