"""Provider-agnostic blob storage.

Business logic stores/reads bytes by key and gets back a URL; it never knows
whether that's local disk or S3. `save` returns a URL usable directly in an
<img> (a relative /media/… path for local, an absolute CDN URL for S3)."""
from __future__ import annotations

from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        """Persist bytes under `key`; return a public URL."""

    @abstractmethod
    def load(self, key: str) -> bytes | None:
        """Read bytes back (used to feed a product photo into image generation)."""

    @abstractmethod
    def delete(self, key: str) -> None:
        ...
