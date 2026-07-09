"""Content generation use-cases: single generate, repurpose, approve — with
per-tenant AI quota enforcement. All operations are tenant-scoped by business."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.base import AIRequest, TaskType
from app.ai.router import AIRouter
from app.models.ai_usage import AiUsage
from app.models.business import Business
from app.models.content import ContentIdea, ContentItem
from app.models.enums import UNLIMITED, Channel, ContentStatus, ContentType
from app.services.rag_service import build_business_context

# One idea -> these platform-tailored variants. Each is a separate, optimized
# generation (not a copy). Order mirrors the product's repurposing pipeline.
REPURPOSE_TARGETS: list[tuple[Channel, ContentType]] = [
    (Channel.INSTAGRAM, ContentType.SOCIAL_POST),
    (Channel.FACEBOOK, ContentType.SOCIAL_POST),
    (Channel.LINKEDIN, ContentType.SOCIAL_POST),
    (Channel.THREADS, ContentType.SOCIAL_POST),
    (Channel.X, ContentType.SOCIAL_POST),
    (Channel.BLOG, ContentType.BLOG_ARTICLE),
    (Channel.EMAIL, ContentType.EMAIL),
    (Channel.SMS, ContentType.SMS),
    (Channel.VIDEO, ContentType.VIDEO_SCRIPT),
    (Channel.GENERIC, ContentType.CAPTIONS),
    (Channel.GENERIC, ContentType.HASHTAGS),
    (Channel.GENERIC, ContentType.CTA),
]


class AiQuotaExceeded(Exception):
    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"monthly AI quota ({limit}) reached")


class ContentNotFound(Exception):
    ...


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def usage_this_month(db: Session, business_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count(AiUsage.id)).where(
            AiUsage.business_id == business_id,
            AiUsage.created_at >= _month_start(),
        )
    ) or 0


def _check_quota(db: Session, business: Business) -> None:
    limit = business.plan.ai_monthly_quota if business.plan else UNLIMITED
    if limit != UNLIMITED and usage_this_month(db, business.id) >= limit:
        raise AiQuotaExceeded(limit)


def _generate_item(
    db: Session,
    *,
    router: AIRouter,
    business: Business,
    context: dict,
    channel: Channel,
    content_type: ContentType,
    brief: str,
    created_by: uuid.UUID | None,
    idea_id: uuid.UUID | None = None,
) -> ContentItem:
    request = AIRequest(
        task=TaskType.CONTENT,
        prompt=brief,
        business_id=str(business.id),
        context={"business": context, "channel": channel.value, "content_type": content_type.value},
    )
    resp = router.handle(request)

    item = ContentItem(
        business_id=business.id,
        idea_id=idea_id,
        channel=channel.value,
        content_type=content_type.value,
        body=resp.text,
        meta={"provider": resp.provider, "model": resp.model},
        status=ContentStatus.DRAFT.value,
        created_by=created_by,
    )
    db.add(item)
    db.add(AiUsage(
        business_id=business.id,
        module=TaskType.CONTENT.value,
        provider=resp.provider,
        model=resp.model,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
    ))
    db.flush()
    return item


def generate_single(
    db: Session, *, router: AIRouter, business: Business,
    channel: Channel, content_type: ContentType, brief: str,
    created_by: uuid.UUID | None,
) -> ContentItem:
    _check_quota(db, business)
    context = build_business_context(business)
    return _generate_item(
        db, router=router, business=business, context=context,
        channel=channel, content_type=content_type, brief=brief, created_by=created_by,
    )


def repurpose(
    db: Session, *, router: AIRouter, business: Business, idea_text: str,
    created_by: uuid.UUID | None,
    targets: list[tuple[Channel, ContentType]] | None = None,
) -> tuple[ContentIdea, list[ContentItem]]:
    """One idea -> a set of platform-optimized items. Stops early if the tenant's
    monthly AI quota is reached mid-run (partial set returned)."""
    context = build_business_context(business)
    idea = ContentIdea(business_id=business.id, brief=idea_text, created_by=created_by)
    db.add(idea)
    db.flush()

    items: list[ContentItem] = []
    for channel, content_type in (targets or REPURPOSE_TARGETS):
        try:
            _check_quota(db, business)
        except AiQuotaExceeded:
            break
        items.append(_generate_item(
            db, router=router, business=business, context=context,
            channel=channel, content_type=content_type, brief=idea_text,
            created_by=created_by, idea_id=idea.id,
        ))
    return idea, items


def list_items(
    db: Session, *, business_id: uuid.UUID,
    status: str | None = None, channel: str | None = None,
) -> list[ContentItem]:
    stmt = select(ContentItem).where(ContentItem.business_id == business_id)
    if status:
        stmt = stmt.where(ContentItem.status == status)
    if channel:
        stmt = stmt.where(ContentItem.channel == channel)
    return list(db.scalars(stmt.order_by(ContentItem.created_at.desc())).all())


def get_item(db: Session, *, business_id: uuid.UUID, item_id: uuid.UUID) -> ContentItem:
    item = db.scalar(
        select(ContentItem).where(
            ContentItem.id == item_id, ContentItem.business_id == business_id
        )
    )
    if not item:
        raise ContentNotFound(str(item_id))
    return item


def set_status(
    db: Session, *, business_id: uuid.UUID, item_id: uuid.UUID, status: ContentStatus
) -> ContentItem:
    item = get_item(db, business_id=business_id, item_id=item_id)
    item.status = status.value
    db.flush()
    return item


# Statuses that must go back through review once the copy is edited.
_REVIEWED = {ContentStatus.APPROVED.value, ContentStatus.REJECTED.value}


def update_item(
    db: Session, *, business_id: uuid.UUID, item_id: uuid.UUID,
    title: str | None = None, body: str | None = None,
) -> ContentItem:
    """Edit a piece's copy. `None` means "leave unchanged". Editing an item that
    was already approved/rejected sends it back to draft — the edited copy is no
    longer the reviewed one."""
    item = get_item(db, business_id=business_id, item_id=item_id)
    if title is not None:
        item.title = title or None
    if body is not None:
        item.body = body
    if (title is not None or body is not None) and item.status in _REVIEWED:
        item.status = ContentStatus.DRAFT.value
    db.flush()
    return item
