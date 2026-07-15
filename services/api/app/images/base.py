"""Provider-agnostic image generation contract.

Mirrors the AI text layer: business logic depends only on `ImageProvider`, never
on a vendor SDK. Swapping Gemini → OpenAI/Stability is one class + a config change.
`url` is either a hosted URL or a `data:` URI, so it drops straight into an <img>.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ReferenceImage:
    """A product photo fed in as the baseline/subject for generation."""
    data: bytes
    mime: str


@dataclass
class ImageResult:
    data: bytes  # raw image bytes (persisted via the storage layer)
    mime: str
    provider: str
    model: str
    prompt: str


class ImageProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(
        self, *, prompt: str, aspect: str = "1:1", reference: "ReferenceImage | None" = None
    ) -> ImageResult:  # pragma: no cover - interface
        ...
