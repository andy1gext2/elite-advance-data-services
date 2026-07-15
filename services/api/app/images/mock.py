"""Deterministic placeholder image generator — proves the whole image pipeline
(prompt → generate → persist → render) end-to-end without any paid image API.
Returns an on-brand gradient SVG as a data URI. A real provider is a drop-in."""
from __future__ import annotations

import hashlib

from app.images.base import ImageProvider, ImageResult, ReferenceImage

_SIZES = {"1:1": (1080, 1080), "16:9": (1200, 675), "9:16": (675, 1200)}


class MockImageProvider(ImageProvider):
    name = "mock"

    def generate(
        self, *, prompt: str, aspect: str = "1:1", reference: ReferenceImage | None = None
    ) -> ImageResult:
        h = int(hashlib.sha256(prompt.encode("utf-8")).hexdigest(), 16)
        a = h % 360
        b = (a + 45 + (h % 60)) % 360
        w, ht = _SIZES.get(aspect, _SIZES["1:1"])
        badge = "📦" if reference else "🎨"  # product-grounded vs from-scratch
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{ht}">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="hsl({a},70%,52%)"/>'
            f'<stop offset="1" stop-color="hsl({b},72%,42%)"/></linearGradient></defs>'
            f'<rect width="100%" height="100%" fill="url(#g)"/>'
            f'<text x="50%" y="53%" font-size="{int(ht * 0.30)}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="rgba(255,255,255,0.92)">{badge}</text>'
            f'</svg>'
        )
        return ImageResult(
            data=svg.encode("utf-8"),
            mime="image/svg+xml",
            provider=self.name,
            model="mock-image",
            prompt=prompt,
        )
