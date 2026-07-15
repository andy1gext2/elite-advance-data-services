"""Google Gemini image provider (the "Nano Banana" family: gemini-2.5-flash-image).
The only place the `google-genai` SDK is imported. Returns the generated image as
a data: URI (MVP — production should upload to object storage/CDN).

Uses `generate_content` with an IMAGE response modality, which is how AI-Studio
Gemini keys generate images (Imagen's `generate_images`/predict needs Vertex AI).
Isolated to this one class, so tweaking the model/call is a one-file change.
"""
from __future__ import annotations

import base64

from app.images.base import ImageProvider, ImageResult, ReferenceImage


class GeminiImageProvider(ImageProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-image") -> None:
        from google import genai  # lazy: keep the dep out of paths that don't use it

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(
        self, *, prompt: str, aspect: str = "1:1", reference: ReferenceImage | None = None
    ) -> ImageResult:
        from google.genai import types

        # Nano Banana takes aspect as a prompt hint, not a config field. A product
        # photo is passed as an image part so the model uses it as the baseline.
        if reference:
            full_prompt = (
                f"Using the attached product photo as the subject, {prompt} "
                f"Keep the product's real appearance. Composition: {aspect} aspect ratio."
            )
            contents = [
                types.Part.from_bytes(data=reference.data, mime_type=reference.mime),
                full_prompt,
            ]
        else:
            full_prompt = f"{prompt} Composition: {aspect} aspect ratio."
            contents = full_prompt

        resp = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )
        for candidate in resp.candidates or []:
            for part in (candidate.content.parts or []):
                inline = getattr(part, "inline_data", None)
                if inline and inline.data:
                    raw = inline.data
                    data = raw if isinstance(raw, bytes) else base64.b64decode(raw)
                    return ImageResult(
                        data=data,
                        mime=inline.mime_type or "image/png",
                        provider=self.name,
                        model=self._model,
                        prompt=prompt,
                    )
        raise RuntimeError("Gemini returned no image for the prompt")
