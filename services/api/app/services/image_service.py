"""Generate an on-brand visual for a content item and persist it via storage.

Builds a prompt from the business profile + the post, optionally grounds it on an
uploaded product photo, renders it via the image provider, and stores the bytes
(returning a URL). Provider- and storage-agnostic."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.base import AIRequest, TaskType
from app.ai.model_policy import select_model
from app.ai.router import AIRouter
from app.images.base import ImageProvider, ReferenceImage
from app.models.ai_usage import AiUsage
from app.models.asset import Asset
from app.models.business import Business
from app.models.content import ContentItem
from app.models.enums import UNLIMITED
from app.services.content_service import AiQuotaExceeded
from app.services.content_service import usage_this_month as ai_usage_this_month
from app.services.rag_service import build_business_context
from app.storage.base import Storage

# Art-director system prompt: Claude drafts a concise image-generation prompt the
# owner can edit ("image vision"), mirroring the video vision.
_IMAGE_VISION_SYSTEM = (
    "You are an art director writing a concise image-generation prompt for a SINGLE "
    "on-brand social media photo. In 2-4 vivid sentences, describe the subject, "
    "composition, setting, lighting, mood, and visual style. Keep it realistic and "
    "brand-appropriate. Do NOT include overlaid text, captions, or logos. Output "
    "ONLY the prompt."
)

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


def build_prompt(
    business: Business, item: ContentItem, grounded: bool, poster: bool = False
) -> str:
    first_line = (item.body or "").strip().splitlines()[0][:220] if item.body else ""
    if poster:
        parts = [f"Design a clean, professional promotional POSTER advertising a service from {business.name}."]
    else:
        parts = [f"Professional social media photo for {business.name}."]
    if business.industry:
        parts.append(f"Industry: {business.industry}.")
    if business.tone:
        parts.append(f"Mood: {business.tone}.")
    if business.brand_voice:
        parts.append(f"Brand character: {business.brand_voice}.")
    if first_line:
        parts.append(f"Concept: {first_line}")

    if poster:
        # Services have no physical product to photograph — make a marketing poster
        # that sells the service, optionally staging any reference photo in-scene.
        parts.append(
            "Advertising-poster composition: strong visual hierarchy, a bold focal "
            "image that conveys the service being delivered (real people, real setting), "
            "and a short punchy headline rendered as crisp, correctly-spelled poster "
            "typography. Polished, modern graphic-design layout — like an agency-made ad."
        )
        if grounded:
            parts.append(
                "Incorporate the attached reference photo as the hero visual of the poster, "
                "matching it exactly — same colors, subject, and details; never omit or restyle it."
            )
    elif grounded:
        parts.append(
            "The uploaded product MUST appear in the image as the clear focal subject, "
            "matching the reference photo exactly — same colors, materials, and design "
            "details. Never omit, replace, or restyle it. If the product is apparel, "
            "footwear, eyewear, jewelry, a bag, or any wearable item, show a real person "
            "naturally wearing/using it in a lifestyle setting; otherwise feature the "
            "product prominently, in-use, in an appropriate real-world scene."
        )

    if poster:
        parts.append(
            "High-quality, on-brand, professional lighting. Keep a consistent visual "
            "style with the brand's previous approved posts."
        )
    else:
        parts.append(
            "Style: clean, modern, high-quality, on-brand, natural lighting, "
            "no text or logos overlaid. Keep a consistent visual style with the brand's "
            "previous approved posts."
        )
    return " ".join(parts)


def build_asset_flyer_prompt(business: Business, asset: Asset) -> str:
    """Poster/flyer prompt for a service asset — built from its name + description
    (its own copy), independent of any single post."""
    label = asset.name or asset.filename
    parts = [f"Design a clean, professional promotional FLYER/POSTER advertising a service from {business.name}."]
    if business.industry:
        parts.append(f"Industry: {business.industry}.")
    if business.tone:
        parts.append(f"Mood: {business.tone}.")
    if business.brand_voice:
        parts.append(f"Brand character: {business.brand_voice}.")
    parts.append(f"Service: {label}.")
    if asset.description:
        parts.append(asset.description)
    parts.append(
        "Advertising-poster composition: strong visual hierarchy, a bold focal image "
        "that conveys the service being delivered (real people, real setting), and a "
        "short punchy headline rendered as crisp, correctly-spelled poster typography. "
        "Polished, modern agency-made ad layout. High-quality and on-brand."
    )
    return " ".join(parts)


def generate_asset_flyer(
    db, *, provider: ImageProvider, storage: Storage, business: Business,
    asset: Asset, reference: ReferenceImage | None = None,
) -> Asset:
    """Generate an AI flyer/poster for a service and store it ON the asset (so the
    same image can be reused across a campaign's posts). Enforces the image quota."""
    _check_quota(db, business)
    prompt = build_asset_flyer_prompt(business, asset)
    result = provider.generate(prompt=prompt, aspect="1:1", reference=reference)

    ext = _EXT.get(result.mime, "png")
    key = f"assets/{asset.business_id}/{uuid.uuid4().hex}.{ext}"
    url = storage.save(key=key, data=result.data, content_type=result.mime)

    old_key = asset.storage_key
    asset.url = url
    asset.storage_key = key
    asset.content_type = result.mime
    db.add(AiUsage(
        business_id=business.id, module=IMAGE_MODULE,
        provider=result.provider, model=result.model, input_tokens=0, output_tokens=0,
    ))
    db.flush()
    # Drop the previous file (an earlier flyer) once the new one is safely stored.
    if old_key and old_key != key:
        storage.delete(old_key)
    return asset


def generate_image_vision(
    db: Session, *, router: AIRouter, business: Business, item: ContentItem
) -> str:
    """Claude drafts an editable image prompt ("image vision") the owner can tweak
    before generating — the visual counterpart to the video vision. Billable text
    call, so it respects the monthly AI text quota."""
    limit = business.plan.ai_monthly_quota if business.plan else UNLIMITED
    if limit != UNLIMITED and ai_usage_this_month(db, business.id) >= limit:
        raise AiQuotaExceeded(limit)

    lines = [f"Brand: {business.name}."]
    if business.industry:
        lines.append(f"Industry: {business.industry}.")
    if business.tone:
        lines.append(f"Tone/mood: {business.tone}.")
    if business.brand_voice:
        lines.append(f"Brand character: {business.brand_voice}.")
    if item.product_asset_id:
        product = db.get(Asset, item.product_asset_id)
        if product:
            note = f" {product.description}" if product.description else ""
            lines.append(f"Feature this product, true to life: {product.name or product.filename}.{note}")

    concept = "\n".join(p for p in (item.title, item.body) if p).strip()
    prompt = "\n".join(lines) + f"\n\nMarketing post:\n{concept}\n\nWrite the image prompt."

    resp = router.handle(AIRequest(
        task=TaskType.VIDEO_SCRIPT,  # raw provider call with our system prompt
        prompt=prompt,
        business_id=str(business.id),
        context={"business": build_business_context(business)},
        system=_IMAGE_VISION_SYSTEM,
        model=select_model(task=TaskType.VIDEO_SCRIPT),
        max_tokens=400,
        temperature=0.8,
    ))
    db.add(AiUsage(
        business_id=business.id, module="image_script",
        provider=resp.provider, model=resp.model,
        input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
    ))
    return resp.text.strip()


def generate_image(
    db, *, provider: ImageProvider, storage: Storage, business: Business,
    item: ContentItem, reference: ReferenceImage | None = None, poster: bool = False,
    prompt: str | None = None,
) -> ContentItem:
    """Generate + store an on-brand visual. Enforces the tenant's monthly image
    quota (raises ImageQuotaExceeded). `poster=True` renders a promotional poster
    for a service. Pass `prompt` (the owner's edited image vision) to override the
    auto-built prompt — grounding on a reference product is still appended so the
    product stays in-frame and the campaign stays locked in."""
    _check_quota(db, business)
    if prompt and prompt.strip():
        prompt = prompt.strip()
        if reference is not None:
            prompt += (
                " The uploaded product MUST appear as the clear focal subject, matching "
                "the reference photo exactly — same colors, materials, and details."
            )
    else:
        prompt = build_prompt(business, item, grounded=reference is not None, poster=poster)
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
