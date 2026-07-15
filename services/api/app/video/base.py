"""Provider-agnostic video generation contract.

Video generation is async: a render takes tens of seconds to minutes, so the
provider exposes `start` (kick off, return an opaque operation ref) and `poll`
(check that ref). Business logic persists the ref in a VideoJob and polls until
done — the same shape whether the backend is Veo, Runway, or the mock. Swapping
providers is one class + a config change, exactly like the AI and image layers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class VideoPoll:
    """The state of an in-flight (or finished) generation."""
    status: Literal["processing", "succeeded", "failed"]
    model: str
    data: bytes | None = None      # raw video bytes when succeeded
    mime: str | None = None        # e.g. "video/mp4"
    error: str | None = None


class VideoProvider(ABC):
    name: str = "base"
    model: str = "base"

    @abstractmethod
    def start(self, *, prompt: str, aspect: str = "16:9") -> str:  # pragma: no cover - interface
        """Kick off a generation; return an opaque operation ref to poll later."""
        ...

    @abstractmethod
    def poll(self, operation_ref: str) -> VideoPoll:  # pragma: no cover - interface
        ...
