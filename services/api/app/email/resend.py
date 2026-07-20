"""Email via the Resend HTTPS API (https://resend.com/docs/api-reference).

Uses port 443, so it works on hosts that block outbound SMTP ports (Railway,
Render, Fly, etc.) — the common reason SMTP "times out" in the cloud.
"""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.email.base import EmailMessage

_ENDPOINT = "https://api.resend.com/emails"


class ResendEmailProvider:
    def send(self, message: EmailMessage) -> None:
        s = get_settings()
        if not s.resend_api_key:
            raise RuntimeError("RESEND_API_KEY not set")

        payload: dict = {
            "from": s.email_from,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text,
        }
        if message.html:
            payload["html"] = message.html

        resp = httpx.post(
            _ENDPOINT,
            headers={"Authorization": f"Bearer {s.resend_api_key}"},
            json=payload,
            timeout=15,
        )
        # Surface Resend's own error text (unverified domain, test-mode recipient
        # restriction, bad key, …) so the failure is diagnosable from the logs.
        if resp.status_code >= 400:
            raise RuntimeError(f"Resend API {resp.status_code}: {resp.text}")
