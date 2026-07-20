"""Content generation routes. Tenant-scoped; generation/approval require editor+."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.registry import get_ai_router
from app.ai.router import AIRouter
from app.api.deps import TenantContext, get_membership_ctx, require_role
from app.core.db import get_db
from app.models.enums import ContentStatus, Role
from app.schemas.content import (
    ContentItemOut,
    ContentUpdateIn,
    GenerateIn,
    RepurposeIn,
    RepurposeOut,
    VideoCreditsIn,
    VideoJobOut,
    VideoScriptOut,
    VideoStartIn,
)
from app.images.base import ImageProvider, ReferenceImage
from app.images.registry import get_image_provider_dep
from app.services import asset_service, content_service, image_service, video_service
from app.storage.base import Storage
from app.storage.registry import get_storage_dep
from app.video.base import VideoProvider
from app.video.registry import get_video_provider_dep

router = APIRouter(prefix="/businesses/{business_id}/content", tags=["content"])


@router.post("/generate", response_model=ContentItemOut, status_code=status.HTTP_201_CREATED)
def generate(
    body: GenerateIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    try:
        item = content_service.generate_single(
            db, router=ai, business=ctx.business,
            channel=body.channel, content_type=body.content_type,
            brief=body.brief, created_by=ctx.membership.user_id,
        )
    except content_service.AiQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade to generate more.",
        )
    db.commit()
    db.refresh(item)
    return item


_MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB (videos)


@router.post("/upload", response_model=list[ContentItemOut], status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    storage: Storage = Depends(get_storage_dep),
    db: Session = Depends(get_db),
) -> list[ContentItemOut]:
    """Post the owner's own photo/video, exactly as uploaded, to every connected
    platform — one scheduled post each (default: 1 day out). Not a campaign."""
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 100 MB)")
    try:
        items = content_service.create_from_upload(
            db, storage=storage, business=ctx.business, data=data,
            content_type=file.content_type or "", caption=caption,
            created_by=ctx.membership.user_id,
        )
    except content_service.UnsupportedUpload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a PNG, JPG, WEBP, GIF image or an MP4/MOV/WEBM video.")
    except content_service.NoConnectedAccounts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connect at least one social account (Schedule tab) before posting your own media.")
    db.commit()
    for item in items:
        db.refresh(item)
    return items


class PostMediaIn(BaseModel):
    asset_id: uuid.UUID
    scheduled_date: date


@router.post("/post-media", response_model=list[ContentItemOut], status_code=status.HTTP_201_CREATED)
def post_media(
    body: PostMediaIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> list[ContentItemOut]:
    """Post a saved 'customized media' asset to every connected platform on the
    chosen day, with an AI-drafted caption from its description."""
    try:
        asset = asset_service.get_asset(db, business_id=ctx.business.id, asset_id=body.asset_id)
    except asset_service.AssetNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if asset.kind != "media":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a customized-media asset")
    try:
        items = content_service.post_media_asset(
            db, router=ai, business=ctx.business, asset=asset,
            scheduled_date=body.scheduled_date, created_by=ctx.membership.user_id,
        )
    except content_service.NoConnectedAccounts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connect at least one social account (Schedule tab) first.")
    except content_service.AiQuotaExceeded as exc:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade to generate more.")
    except content_service.UnsupportedUpload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That media can't be posted.")
    db.commit()
    for item in items:
        db.refresh(item)
    return items


@router.post("/repurpose", response_model=RepurposeOut, status_code=status.HTTP_201_CREATED)
def repurpose(
    body: RepurposeIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> RepurposeOut:
    targets = (
        [(t.channel, t.content_type) for t in body.targets] if body.targets else None
    )
    idea, items = content_service.repurpose(
        db, router=ai, business=ctx.business, idea_text=body.idea,
        created_by=ctx.membership.user_id, targets=targets,
    )
    db.commit()
    db.refresh(idea)
    for item in items:
        db.refresh(item)
    return RepurposeOut(idea=idea, items=items)


@router.get("", response_model=list[ContentItemOut])
def list_content(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    channel: str | None = Query(default=None),
) -> list[ContentItemOut]:
    return content_service.list_items(
        db, business_id=ctx.business.id, status=status_filter, channel=channel
    )


@router.get("/video-quota")
def video_quota(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> dict:
    """The tenant's monthly video-render allowance + credits (for the cost-guard confirm)."""
    return video_service.quota(db, ctx.business)


@router.post("/video-credits")
def buy_video_credits(
    body: VideoCreditsIn,
    ctx: TenantContext = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    """Add paid video-render credits. Placeholder for the billing/Stripe hook — for
    now it grants the credits directly. Admin+ only. Returns the updated allowance."""
    video_service.add_credits(db, ctx.business, body.quantity)
    db.commit()
    return video_service.quota(db, ctx.business)


@router.get("/image-quota")
def image_quota(
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> dict:
    """The tenant's monthly image-generation allowance."""
    return image_service.quota(db, ctx.business)


@router.get("/{item_id}", response_model=ContentItemOut)
def get_content(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(get_membership_ctx),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    try:
        return content_service.get_item(db, business_id=ctx.business.id, item_id=item_id)
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")


@router.patch("/{item_id}", response_model=ContentItemOut)
def update_content(
    item_id: uuid.UUID,
    body: ContentUpdateIn,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    try:
        item = content_service.update_item(
            db, business_id=ctx.business.id, item_id=item_id,
            title=body.title, body=body.body,
        )
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    db.commit()
    db.refresh(item)
    return item


class ImageGenerateIn(BaseModel):
    asset_id: uuid.UUID | None = None
    prompt: str | None = None  # the owner's edited "image vision" (optional)


@router.post("/{item_id}/image", response_model=ContentItemOut)
def generate_image(
    item_id: uuid.UUID,
    body: ImageGenerateIn | None = None,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    images: ImageProvider = Depends(get_image_provider_dep),
    storage: Storage = Depends(get_storage_dep),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    """Generate an on-brand visual for this post. Pass `asset_id` to ground the
    image on an uploaded product photo, and/or `prompt` (the edited image vision)
    to steer the visual."""
    payload = body or ImageGenerateIn()
    try:
        item = content_service.get_item(db, business_id=ctx.business.id, item_id=item_id)
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    # Ground on the explicitly-chosen product, else the post's own campaign product,
    # so a product post's image always features that product.
    aid = payload.asset_id if payload.asset_id is not None else item.product_asset_id
    reference = None
    poster = False
    if aid is not None:
        try:
            asset = asset_service.get_asset(db, business_id=ctx.business.id, asset_id=aid)
        except asset_service.AssetNotFound:
            if payload.asset_id is not None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product image not found")
            asset = None  # the campaign's product was deleted — generate ungrounded
        if asset is not None:
            # A service is marketed as a designed poster; a product as a grounded photo.
            poster = asset.is_service
            if asset.storage_key and asset.content_type:
                data = storage.load(asset.storage_key)
                if data:
                    reference = ReferenceImage(data=data, mime=asset.content_type)

    try:
        item = image_service.generate_image(
            db, provider=images, storage=storage, business=ctx.business,
            item=item, reference=reference, poster=poster, prompt=payload.prompt,
        )
    except image_service.ImageQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly image limit ({exc.limit}) reached. Upgrade your plan for more.",
        )
    db.commit()
    db.refresh(item)
    return item


class ImageVisionIn(BaseModel):
    current: str | None = None  # the text already in the box, to build on


@router.post("/{item_id}/image/vision", response_model=VideoScriptOut)
def write_image_vision(
    item_id: uuid.UUID,
    body: ImageVisionIn | None = None,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> VideoScriptOut:
    """Have Claude write an editable image prompt ("image vision") for this post,
    so the owner can steer the visual before generating. If `current` is provided,
    the rewrite builds on what the owner already typed."""
    payload = body or ImageVisionIn()
    try:
        item = content_service.get_item(db, business_id=ctx.business.id, item_id=item_id)
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    try:
        vision = image_service.generate_image_vision(
            db, router=ai, business=ctx.business, item=item, current=payload.current
        )
    except content_service.AiQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade to generate more.",
        )
    db.commit()
    return VideoScriptOut(prompt=vision)


@router.post("/{item_id}/video/script", response_model=VideoScriptOut)
def write_video_script(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> VideoScriptOut:
    """Have Claude write the 8-second video vision for this post (to preview/edit
    before rendering). Does not render or consume the video quota."""
    try:
        item = content_service.get_item(db, business_id=ctx.business.id, item_id=item_id)
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    try:
        script = video_service.generate_script(db, router=ai, business=ctx.business, item=item)
    except content_service.AiQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly AI quota ({exc.limit}) reached. Upgrade to generate more.",
        )
    db.commit()
    return VideoScriptOut(prompt=script)


@router.post("/{item_id}/video", response_model=VideoJobOut, status_code=status.HTTP_202_ACCEPTED)
def start_video(
    item_id: uuid.UUID,
    body: VideoStartIn | None = None,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    video: VideoProvider = Depends(get_video_provider_dep),
    ai: AIRouter = Depends(get_ai_router),
    db: Session = Depends(get_db),
) -> VideoJobOut:
    """Kick off an async video render for this post. Uses the edited vision in `prompt`
    if provided; otherwise Claude writes the 8-second shot brief. Veo executes it.
    Returns a job (status 'processing'); poll GET …/video until it succeeds."""
    try:
        item = content_service.get_item(db, business_id=ctx.business.id, item_id=item_id)
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    try:
        job = video_service.start_video(
            db, provider=video, router=ai, business=ctx.business, item=item,
            script=body.prompt if body else None,
        )
    except video_service.VideoQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly video limit ({exc.limit}) reached. Upgrade your plan for more renders.",
        )
    db.commit()
    db.refresh(job)
    return job


@router.get("/{item_id}/video", response_model=VideoJobOut)
def get_video(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    video: VideoProvider = Depends(get_video_provider_dep),
    storage: Storage = Depends(get_storage_dep),
    db: Session = Depends(get_db),
) -> VideoJobOut:
    """Poll the latest video job for this post, advancing it if still processing."""
    job = video_service.latest_job(db, business_id=ctx.business.id, content_item_id=item_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No video job for this post")
    job = video_service.poll_video(db, provider=video, storage=storage, job=job)
    db.commit()
    db.refresh(job)
    return job


def _set_status(db: Session, ctx: TenantContext, item_id: uuid.UUID, new: ContentStatus):
    try:
        item = content_service.set_status(
            db, business_id=ctx.business.id, item_id=item_id, status=new
        )
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/approve", response_model=ContentItemOut)
def approve(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    """Approve the post and book it onto the calendar (schedules it where an
    account is connected)."""
    try:
        item = content_service.approve_item(db, business_id=ctx.business.id, item_id=item_id)
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/reject", response_model=ContentItemOut)
def reject(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> ContentItemOut:
    return _set_status(db, ctx, item_id, ContentStatus.REJECTED)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(
    item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_role(Role.EDITOR)),
    db: Session = Depends(get_db),
) -> None:
    """Delete a post for good — removes it from the library, the calendar, and any
    schedules. This is what 'reject' does."""
    try:
        content_service.delete_item(db, business_id=ctx.business.id, item_id=item_id)
    except content_service.ContentNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    db.commit()
