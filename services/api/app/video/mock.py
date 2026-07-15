"""Deterministic placeholder video generator — proves the whole async pipeline
(start → poll → persist → render) without any paid video API. It 'succeeds'
immediately and returns a tiny placeholder clip. A real provider (Veo) is a
drop-in replacement; the mock's bytes are not a playable video (dev/test only)."""
from __future__ import annotations

import hashlib

from app.video.base import VideoPoll, VideoProvider


class MockVideoProvider(VideoProvider):
    name = "mock"
    model = "mock-video"

    def start(self, *, prompt: str, aspect: str = "16:9") -> str:
        digest = hashlib.sha256(f"{prompt}|{aspect}".encode("utf-8")).hexdigest()[:16]
        return f"mock-op:{digest}"

    def poll(self, operation_ref: str) -> VideoPoll:
        # Mock renders instantly. The bytes are a placeholder, not a real MP4.
        return VideoPoll(
            status="succeeded",
            model=self.model,
            data=b"MOCK_VIDEO_PLACEHOLDER_" + operation_ref.encode("utf-8"),
            mime="video/mp4",
        )
