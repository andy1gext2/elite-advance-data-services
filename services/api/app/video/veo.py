"""Google Veo video provider (via the `google-genai` SDK — the only place it's
imported). Veo generation is a long-running operation: `generate_videos` returns
an operation handle; we return its `name` so the job layer can poll it across
requests. `poll` re-fetches the operation and, when done, downloads the bytes.

Isolated to this one class, so the model id / call shape is a one-file change.
NOTE: Veo on the Gemini API requires a PAID API tier (billing enabled) — a free
AI-Studio key (or a consumer Google One plan) will get a permission error here.
"""
from __future__ import annotations

from app.video.base import VideoPoll, VideoProvider


class GeminiVeoProvider(VideoProvider):
    name = "veo"

    def __init__(self, api_key: str, model: str = "veo-3.1-fast-generate-preview") -> None:
        from google import genai  # lazy: keep the dep out of paths that don't use it

        self._client = genai.Client(api_key=api_key)
        self.model = model

    def start(self, *, prompt: str, aspect: str = "16:9") -> str:
        from google.genai import types

        operation = self._client.models.generate_videos(
            model=self.model,
            prompt=prompt,
            config=types.GenerateVideosConfig(aspect_ratio=aspect, number_of_videos=1),
        )
        # The operation's name is the durable handle we re-fetch to poll.
        return operation.name

    def poll(self, operation_ref: str) -> VideoPoll:
        from google.genai import types

        operation = self._client.operations.get(
            types.GenerateVideosOperation(name=operation_ref)
        )
        if not getattr(operation, "done", False):
            return VideoPoll(status="processing", model=self.model)
        if getattr(operation, "error", None):
            return VideoPoll(status="failed", model=self.model, error=str(operation.error))

        video = operation.response.generated_videos[0].video
        # Populate `.video_bytes` (downloads if the SDK returned only a file ref).
        try:
            self._client.files.download(file=video)
        except Exception:  # noqa: BLE001 - bytes may already be present
            pass
        data = getattr(video, "video_bytes", None)
        if not data:
            return VideoPoll(status="failed", model=self.model, error="no video bytes returned")
        return VideoPoll(status="succeeded", model=self.model, data=data, mime="video/mp4")
