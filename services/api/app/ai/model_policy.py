"""Model tiering policy.

Short, low-stakes generations (an SMS blast, a hashtag list, a one-line calendar
idea) don't need the flagship model — routing them to a cheaper model cuts the AI
bill substantially without hurting the content that matters. Returning None means
"use the provider's default model" (`ai_default_model`).

Provider-agnostic: this only picks a model *id*; the provider layer resolves it.
Callers set the returned id on `AIRequest.model`.
"""
from __future__ import annotations

from app.ai.base import TaskType
from app.core.config import get_settings
from app.models.enums import ContentType

# Content types that are short and low-stakes enough for the cheap tier.
CHEAP_CONTENT_TYPES: set[str] = {
    ContentType.SMS.value,
    ContentType.CAPTIONS.value,
    ContentType.HASHTAGS.value,
    ContentType.CTA.value,
}


def select_model(*, task: TaskType, content_type: str | None = None) -> str | None:
    """Pick a model id for this generation, or None for the default model.

    - Calendar ideas (one concise line each) → cheap tier.
    - Cheap content types (SMS/captions/hashtags/CTA) → cheap tier.
    - Everything else (social posts, blogs, email, review replies, insights) →
      default (premium) model.
    """
    settings = get_settings()
    if not settings.ai_tiering_enabled:
        return None
    if task == TaskType.CALENDAR:
        return settings.ai_cheap_model
    # Industry trend briefs are short, structured, and refreshed in bulk — the
    # cheap tier (Haiku) is the right fit for the cost.
    if task == TaskType.INDUSTRY_TRENDS:
        return settings.ai_cheap_model
    if task == TaskType.CONTENT and content_type in CHEAP_CONTENT_TYPES:
        return settings.ai_cheap_model
    return None
