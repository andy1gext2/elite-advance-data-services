"""Reputation use-cases: poll reviews, analyze, respond, report.

Reviews are ingested through the connector layer (MockConnector today), enriched
with heuristic sentiment/keywords, optionally answered with an AI-drafted reply,
and rolled up into a reputation report. All operations are tenant-scoped."""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIRequest, TaskType
from app.ai.router import AIRouter
from app.connectors.base import NotSupported
from app.connectors.registry import get_connector
from app.core.crypto import decrypt
from app.models.ai_usage import AiUsage
from app.models.business import Business
from app.models.enums import UNLIMITED, Platform, ReviewStatus
from app.models.review import Review
from app.models.social_account import SocialAccount
from app.services.content_service import AiQuotaExceeded, usage_this_month
from app.services.rag_service import build_business_context
from app.services.text_analysis import (
    analyze_sentiment,
    extract_keywords,
    needs_attention,
)


class ReviewNotFound(Exception):
    ...


class NothingToPost(Exception):
    ...


class ReviewReplyFailed(Exception):
    """A live connector rejected the review reply (e.g. API error / access not
    yet granted). Surfaced to the caller so the reply isn't marked as posted."""


def _check_quota(db: Session, business: Business) -> None:
    limit = business.plan.ai_monthly_quota if business.plan else UNLIMITED
    if limit != UNLIMITED and usage_this_month(db, business.id) >= limit:
        raise AiQuotaExceeded(limit)


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ── Sync / ingest ───────────────────────────────────
def _ingest_one(db: Session, business_id: uuid.UUID, platform: str, raw: dict) -> bool:
    """Insert one review if unseen. Returns True when newly created."""
    ext = str(raw.get("external_id"))
    existing = db.scalar(
        select(Review).where(
            Review.business_id == business_id,
            Review.platform == platform,
            Review.external_id == ext,
        )
    )
    if existing:
        return False

    rating = int(raw.get("rating", 3))
    body = raw.get("body", "") or ""
    sentiment = analyze_sentiment(body, rating)
    db.add(Review(
        business_id=business_id,
        platform=platform,
        external_id=ext,
        author_name=raw.get("author_name"),
        rating=rating,
        body=body,
        sentiment=sentiment,
        keywords=extract_keywords(body),
        status=ReviewStatus.NEW.value,
        needs_attention=needs_attention(rating, sentiment),
        reviewed_at=_parse_dt(raw.get("reviewed_at")),
    ))
    return True


def sync_reviews(
    db: Session, *, business: Business, platform: str | None = None
) -> dict:
    """Poll reviews via the connector layer and ingest new ones.

    Targets the given platform, else every connected account's platform, else a
    default (Google Business) so the flow works before any account is connected."""
    if platform:
        targets: list[tuple[str, str]] = [(platform, "mock-token")]
    else:
        accounts = list(db.scalars(
            select(SocialAccount).where(SocialAccount.business_id == business.id)
        ).all())
        targets = [
            (a.platform, decrypt(a.access_token_enc) if a.access_token_enc else "")
            for a in accounts
        ]
        if not targets:
            targets = [(Platform.GOOGLE_BUSINESS.value, "mock-token")]

    fetched = new = 0
    for plat, token in targets:
        connector = get_connector(plat)
        try:
            raw_reviews = connector.fetch_reviews(account_token=token)
        except NotSupported:
            continue
        for raw in raw_reviews:
            fetched += 1
            if _ingest_one(db, business.id, plat, raw):
                new += 1
    db.flush()
    return {"fetched": fetched, "new": new}


# ── Read ────────────────────────────────────────────
def list_reviews(
    db: Session, *, business_id: uuid.UUID,
    status: str | None = None, sentiment: str | None = None,
    needs_attention_only: bool = False,
) -> list[Review]:
    stmt = select(Review).where(Review.business_id == business_id)
    if status:
        stmt = stmt.where(Review.status == status)
    if sentiment:
        stmt = stmt.where(Review.sentiment == sentiment)
    if needs_attention_only:
        stmt = stmt.where(Review.needs_attention.is_(True))
    # Most recent first (fall back to ingest order when reviewed_at is null).
    return list(db.scalars(
        stmt.order_by(Review.reviewed_at.desc().nullslast(), Review.created_at.desc())
    ).all())


def get_review(db: Session, *, business_id: uuid.UUID, review_id: uuid.UUID) -> Review:
    review = db.scalar(
        select(Review).where(Review.id == review_id, Review.business_id == business_id)
    )
    if not review:
        raise ReviewNotFound(str(review_id))
    return review


# ── Respond ─────────────────────────────────────────
def generate_response(
    db: Session, *, router: AIRouter, business: Business, review: Review
) -> Review:
    """Draft an on-brand AI reply and store it (does not post it)."""
    _check_quota(db, business)
    context = build_business_context(business)
    resp = router.handle(AIRequest(
        task=TaskType.REVIEW_RESPONSE,
        prompt=review.body,
        business_id=str(business.id),
        context={
            "business": context,
            "rating": review.rating,
            "sentiment": review.sentiment,
            "author_name": review.author_name,
        },
    ))
    review.response_text = resp.text
    db.add(AiUsage(
        business_id=business.id, module=TaskType.REVIEW_RESPONSE.value,
        provider=resp.provider, model=resp.model,
        input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
    ))
    db.flush()
    return review


def set_response(
    db: Session, *, business_id: uuid.UUID, review_id: uuid.UUID, response_text: str
) -> Review:
    """Edit the draft reply (e.g. after human tweaks)."""
    review = get_review(db, business_id=business_id, review_id=review_id)
    review.response_text = response_text
    db.flush()
    return review


def _post_reply_via_connector(db: Session, business_id: uuid.UUID, review: Review) -> None:
    """Best-effort: post the stored reply through the review's platform connector.

    Degrades gracefully when there's no live account for the platform, or the
    connector doesn't implement review replies yet (mock/dev, or Meta whose reviews
    API is deprecated) — those cases fall through so the reply is still marked as
    handled locally. Only a *live* connector that actively rejects the reply raises
    ReviewReplyFailed, so real API errors aren't silently swallowed."""
    account = db.scalar(
        select(SocialAccount).where(
            SocialAccount.business_id == business_id,
            SocialAccount.platform == review.platform,
        )
    )
    if not account or not account.access_token_enc:
        return  # nothing connected for this platform — local mark only
    connector = get_connector(review.platform)
    token = decrypt(account.access_token_enc)
    try:
        result = connector.reply_to_review(
            account_token=token, review_ref=review.external_id,
            reply_text=review.response_text or "",
        )
    except NotSupported:
        return  # connector can't reply yet — degrade to a local mark
    if not result.ok:
        if getattr(connector, "live", False):
            raise ReviewReplyFailed(result.error or "reply rejected by platform")
        return  # non-live (mock) rejection — don't block the flow


def mark_responded(
    db: Session, *, business_id: uuid.UUID, review_id: uuid.UUID
) -> Review:
    """Post the stored reply through the connector (when a live account is
    connected) and clear the escalation flag. Falls back to a local mark when the
    platform can't be posted to yet — see _post_reply_via_connector."""
    review = get_review(db, business_id=business_id, review_id=review_id)
    if not (review.response_text and review.response_text.strip()):
        raise NothingToPost("no response drafted for this review")
    _post_reply_via_connector(db, business_id, review)
    review.status = ReviewStatus.RESPONDED.value
    review.needs_attention = False
    db.flush()
    return review


# ── Report ──────────────────────────────────────────
def report(db: Session, *, business_id: uuid.UUID) -> dict:
    reviews = list(db.scalars(
        select(Review).where(Review.business_id == business_id)
    ).all())
    total = len(reviews)

    dist = {str(i): 0 for i in range(1, 6)}
    sentiment = {"positive": 0, "neutral": 0, "negative": 0}
    compliments: Counter = Counter()
    complaints: Counter = Counter()
    responded = attention = 0

    now = datetime.now(timezone.utc)
    prev_year, prev_month = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
    this_month = last_month = 0

    for r in reviews:
        dist[str(r.rating)] = dist.get(str(r.rating), 0) + 1
        sentiment[r.sentiment] = sentiment.get(r.sentiment, 0) + 1
        if r.status == ReviewStatus.RESPONDED.value:
            responded += 1
        if r.needs_attention:
            attention += 1
        if r.sentiment == "positive":
            compliments.update(r.keywords or [])
        elif r.sentiment == "negative":
            complaints.update(r.keywords or [])

        when = _aware(r.reviewed_at or r.created_at) if (r.reviewed_at or r.created_at) else None
        if when:
            if when.year == now.year and when.month == now.month:
                this_month += 1
            elif when.year == prev_year and when.month == prev_month:
                last_month += 1

    return {
        "total_reviews": total,
        "average_rating": round(sum(r.rating for r in reviews) / total, 2) if total else 0.0,
        "response_rate": round(responded / total, 2) if total else 0.0,
        "needs_attention": attention,
        "rating_distribution": dist,
        "sentiment": sentiment,
        "top_compliments": [{"keyword": k, "count": c} for k, c in compliments.most_common(5)],
        "top_complaints": [{"keyword": k, "count": c} for k, c in complaints.most_common(5)],
        "reviews_this_month": this_month,
        "reviews_last_month": last_month,
    }
