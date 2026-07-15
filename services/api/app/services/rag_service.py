"""Retrieval for RAG: pull a business's brand/profile context before generation.

The AI never relies on memory across requests — every generation call is grounded
in the tenant's current profile fetched from Postgres here. As more brand tables
land (products, approved hashtags, custom prompts), extend this builder.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.business import Business
from app.models.content import ContentItem
from app.models.enums import ContentStatus


def build_business_context(business: Business) -> dict:
    """A flat, JSON-serializable snapshot of the business for prompt grounding."""
    return {
        "name": business.name,
        "industry": business.industry,
        "website": business.website,
        "description": business.description,
        "target_audience": business.target_audience,
        "brand_voice": business.brand_voice,
        "tone": business.tone,
        "goals": business.goals,
    }


def approved_examples(
    db: Session, business_id: uuid.UUID, *, channel: str | None = None, limit: int = 4
) -> list[str]:
    """Owner-approved past posts, used as brand exemplars for future generations —
    the AI learns the approved voice by example (RAG, not memory). Prefers posts on
    the same channel, then fills with the most recent approved posts on any channel.
    Each is trimmed so several fit the prompt cheaply."""
    def _query(same_channel: bool):
        stmt = select(ContentItem).where(
            ContentItem.business_id == business_id,
            ContentItem.status == ContentStatus.APPROVED.value,
            ContentItem.body.isnot(None),
        )
        if channel and same_channel:
            stmt = stmt.where(ContentItem.channel == channel)
        return db.scalars(stmt.order_by(ContentItem.created_at.desc()).limit(limit)).all()

    seen: set[uuid.UUID] = set()
    picked: list[ContentItem] = []
    for rows in ((_query(True) if channel else []), _query(False)):
        for item in rows:
            if item.id not in seen and item.body and item.body.strip():
                seen.add(item.id)
                picked.append(item)
            if len(picked) >= limit:
                break
        if len(picked) >= limit:
            break

    return [item.body.strip()[:400] for item in picked]
