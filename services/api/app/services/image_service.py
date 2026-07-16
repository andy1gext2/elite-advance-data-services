"""Generate an on-brand visual for a content item and persist it via storage.

Builds a prompt from the business profile + the post, optionally grounds it on an
uploaded product photo, renders it via the image provider, and stores the bytes
(returning a URL). Provider- and storage-agnostic."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.images.base import ImageProvider, ReferenceImage
from app.models.ai_usage import AiUsage
from app.models.business import Business
from app.models.content import ContentItem
from app.models.enums import UNLIMITED
from app.storage.base import Storage

_SQUARE_CHANNELS = {"instagram", "threads"}
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/svg+xml": "svg"}

# AiUsage.module tag for image renders — kept separate from text so each meters on
# its own quota (images cost ~2x text; see plan.image_monthly_quota).
IMAGE_MODULE = "image"


class ImageQuotaExceeded(Exception):
    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"monthly image quota ({limit}) reached")


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def usage_this_month(db: Session, business_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count(AiUsage.id)).where(
            AiUsage.business_id == business_id,
            AiUsage.module == IMAGE_MODULE,
            AiUsage.created_at >= _month_start(),
        )
    ) or 0


def quota(db: Session, business: Business) -> dict:
    limit = business.plan.image_monthly_quota if business.plan else UNLIMITED
    used = usage_this_month(db, business.id)
    unlimited = limit == UNLIMITED
    return {
        "used": used,
        "limit": None if unlimited else limit,
        "remaining": None if unlimited else max(0, limit - used),
        "unlimited": unlimited,
    }


def _check_quota(db: Session, business: Business) -> None:
    limit = business.plan.image_monthly_quota if business.plan else UNLIMITED
    if limit != UNLIMITED and usage_this_month(db, business.id) >= limit:
        raise ImageQuotaExceeded(limit)


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
        parts.append(
            "The uploaded product MUST appear in the image as the clear focal subject, "
            "matching the reference photo exactly — same colors, materials, and design "
            "details. Never omit, replace, or restyle it. If the product is apparel, "
            "footwear, eyewear, jewelry, a bag, or any wearable item, show a real person "
            "naturally wearing/using it in a lifestyle setting; otherwise feature the "
            "product prominently, in-use, in an appropriate real-world scene."
        )
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
    """Generate + store an on-brand visual. Enforces the tenant's monthly image
    quota (raises ImageQuotaExceeded)."""
    _check_quota(db, business)
    prompt = build_prompt(business, item, grounded=reference is not None)
    aspect = "1:1" if item.channel in _SQUARE_CHANNELS else "16:9"
    result = provider.generate(prompt=prompt, aspect=aspect, reference=reference)

    ext = _EXT.get(result.mime, "png")
    key = f"content/{item.business_id}/{uuid.uuid4().hex}.{ext}"
    url = storage.save(key=key, data=result.data, content_type=result.mime)

    item.image_url = url
    item.image_prompt = prompt
    db.add(AiUsage(
        business_id=business.id, module=IMAGE_MODULE,
        provider=result.provider, model=result.model, input_tokens=0, output_tokens=0,
    ))
    db.flush()
    return item
