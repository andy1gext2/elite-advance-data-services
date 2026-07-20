"""Real email via SMTP (stdlib smtplib — no extra dependency). Works with any
SMTP relay: Resend, SendGrid, Amazon SES, Postmark, or Gmail (app password)."""
from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings
from app.email.base import EmailMessage


class SMTPEmailProvider:
    def send(self, message: EmailMessage) -> None:
        s = get_settings()
        if not s.smtp_host:
            raise RuntimeError("SMTP not configured (set SMTP_HOST)")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = s.email_from
        msg["To"] = message.to
        msg.attach(MIMEText(message.text, "plain"))
        if message.html:
            msg.attach(MIMEText(message.html, "html"))

        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
            if s.smtp_use_tls:
                server.starttls()
            if s.smtp_user and s.smtp_password:
                server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
