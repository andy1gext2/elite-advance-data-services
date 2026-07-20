"""Provider-agnostic email seam. Business logic depends on EmailProvider, never
a concrete SDK — swapping mock → SMTP → a hosted API touches only this package."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str | None = None


class EmailProvider(Protocol):
    def send(self, message: EmailMessage) -> None: ...
