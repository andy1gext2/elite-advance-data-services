"""Pick the email provider from config (EMAIL_PROVIDER)."""
from __future__ import annotations

from app.core.config import get_settings
from app.email.base import EmailProvider
from app.email.mock import MockEmailProvider
from app.email.resend import ResendEmailProvider
from app.email.smtp import SMTPEmailProvider


def get_email_provider() -> EmailProvider:
    provider = get_settings().email_provider.lower()
    if provider == "resend":
        return ResendEmailProvider()
    if provider == "smtp":
        return SMTPEmailProvider()
    return MockEmailProvider()
