"""Dev email provider — logs the message instead of sending. Keyless default so
password-reset works locally without an email account configured."""
from __future__ import annotations

import logging

from app.email.base import EmailMessage

logger = logging.getLogger("app.email")

# In-memory record of everything the mock "sent" — lets tests read back the code
# without a real inbox. Never used by the SMTP provider (real delivery).
sent: list[EmailMessage] = []


class MockEmailProvider:
    def send(self, message: EmailMessage) -> None:
        sent.append(message)
        logger.info(
            "[mock-email] to=%s subject=%r\n%s",
            message.to, message.subject, message.text,
        )
