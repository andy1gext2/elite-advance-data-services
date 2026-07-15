"""Generate an on-brand visual for a content item and persist it via storage.

Builds a prompt from the business profile + the post, optionally grounds it on an
uploaded product photo, renders it via the image provider, and stores the bytes
(returning a URL). Provider- and storage-agnostic."""
from __future__ import annotations

import uuid

from app.images.base import ImageProvider, ReferenceImage
from app.models.business import Business
from app.models.content import ContentItem
from app.storage.base import Storage

_SQUARE_CHANNELS = {"instagram", "threads"}
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg"}


def build_prompt(business: Business, item: ContentItem, grounded: bool) -> str:
    first_line = (item.body or "").strip().splitlines()[0][:220] if item.body else ""
    parts = [f"Professional social media photo for {business.name}."]
    if business.industry:
        parts.append(f"Industry: {business.industry}.")
    if business.tone:
        parts.append(f"Mood: {business.tone}.")
    if business.brand_voice:
        parts.append(f"Brand character: {business.brand_voice}.")
    if first_line:
        parts.append(f"Concept: {first_line}")
    if grounded:
        parts.append("Feature the product prominently and true to life.")
    parts.append(
        "Style: clean, modern, high-quality, on-brand, natural lighting, "
        "no text or logos overlaid. Keep a consistent visual style with the brand's "
        "previous approved posts."
    )
    return " ".join(parts)


def generate_image(
    db, *, provider: ImageProvider, storage: Storage, business: Business,
    item: ContentItem, reference: ReferenceImage | None = None,
) -> ContentItem:
    prompt = build_prompt(business, item, grounded=reference is not None)
    aspect = "1:1" if item.channel in _SQUARE_CHANNELS else "16:9"
    result = provider.generate(prompt=prompt, aspect=aspect, reference=reference)

    ext = _EXT.get(result.mime, "png")
    key = f"content/{item.business_id}/{uuid.uuid4().hex}.{ext}"
    url = storage.save(key=key, data=result.data, content_type=result.mime)

    item.image_url = url
    item.image_prompt = prompt
    db.flush()
    return item
