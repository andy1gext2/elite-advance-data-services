"""Analytics & Insights: roll up real internal signals into a dashboard, a grounded
recommendations feed, and an AI "how is my business doing?" assessment.

Metrics come only from data we actually hold (content, publishing, reviews, AI
usage) — social-platform metrics (followers/reach/engagement) await live connectors
and are deliberately not fabricated. Aggregation is computed on read; at scale this
moves to rollup tables (see roadmap Phase 5)."""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.base import AIRequest, TaskType
from app.ai.router import AIRouter
from app.models.ai_usage import AiUsage
from app.models.business import Business
from app.models.content import ContentItem
from app.models.enums import UNLIMITED, ContentStatus, ScheduleStatus
from app.models.review import Review
from app.models.schedule import Schedule
from app.connectors.base import ConnectorError
from app.connectors.registry import get_connector
from app.services import reputation_service, scheduling_service
from app.services.content_service import AiQuotaExceeded, usage_this_month
from app.services.rag_service import build_business_context


def _month_of(dt: datetime | None) -> tuple[int, int] | None:
    if not dt:
        return None
    d = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return (d.year, d.month)


def _weekly(rows, keyfn, weeks: int = 8) -> list[dict]:
    """Count rows per ISO week (Monday-anchored) for the last `weeks` weeks."""
    # UTC to match created_at/reviewed_at (avoids a local-vs-UTC week-boundary skew).
    today = datetime.now(timezone.utc).date()
    this_week = today - timedelta(days=today.weekday())
    buckets = [this_week - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    counts: dict[date, int] = {b: 0 for b in buckets}
    for r in rows:
        val = keyfn(r)
        if not val:
            continue
        d = val.date() if isinstance(val, datetime) else val
        ws = d - timedelta(days=d.weekday())
        if ws in counts:
            counts[ws] += 1
    return [{"week": b.isoformat(), "count": counts[b]} for b in buckets]


def _recommendations(
    *, content_by_status: dict, pending_schedules: int, published_posts: int,
    rep: dict, content_this_week: int, unanswered: int,
) -> list[str]:
    """Concrete, grounded next steps derived from the real numbers."""
    recs: list[str] = []
    if rep["needs_attention"] > 0:
        recs.append(f"Respond to {rep['needs_attention']} review(s) flagged as needing attention.")
    if unanswered > 0:
        recs.append(f"You have {unanswered} unanswered review(s) — reply to keep engagement high.")
    approved = content_by_status.get(ContentStatus.APPROVED.value, 0)
    if approved > 0 and pending_schedules == 0:
        recs.append(f"You have {approved} approved post(s) not yet scheduled — schedule them to publish.")
    drafts = content_by_status.get(ContentStatus.DRAFT.value, 0)
    if drafts > 0:
        recs.append(f"{drafts} draft(s) are awaiting review and approval.")
    if content_this_week == 0:
        recs.append("You haven't created content this week — generate a fresh post set to stay active.")
    if rep["total_reviews"] > 0 and rep["average_rating"] >= 4.5:
        recs.append("Your average rating is excellent — turn a 5-star review into a testimonial post.")
    return recs


def dashboard(db: Session, *, business_id: uuid.UUID) -> dict:
    content = list(db.scalars(
        select(ContentItem).where(ContentItem.business_id == business_id)
    ).all())
    schedules = list(db.scalars(
        select(Schedule).where(Schedule.business_id == business_id)
    ).all())
    reviews = list(db.scalars(
        select(Review).where(Review.business_id == business_id)
    ).all())

    content_by_status = dict(Counter(c.status for c in content))
    content_by_channel = dict(Counter(c.channel for c in content))
    published_posts = sum(1 for s in schedules if s.status == ScheduleStatus.PUBLISHED.value)
    pending_schedules = sum(1 for s in schedules if s.status == ScheduleStatus.PENDING.value)

    rep = reputation_service.report(db, business_id=business_id)
    unanswered = rep["total_reviews"] - round(rep["response_rate"] * rep["total_reviews"])

    ai_total = db.scalar(
        select(func.count(AiUsage.id)).where(AiUsage.business_id == business_id)
    ) or 0
    ai_this_month = usage_this_month(db, business_id)

    now = datetime.now(timezone.utc)
    this_m, prev_m = (now.year, now.month), (
        (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
    )
    content_this_month = sum(1 for c in content if _month_of(c.created_at) == this_m)
    content_last_month = sum(1 for c in content if _month_of(c.created_at) == prev_m)

    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=today.weekday())
    content_this_week = sum(
        1 for c in content
        if c.created_at and (c.created_at.date() if isinstance(c.created_at, datetime) else c.created_at) >= week_start
    )

    return {
        "kpis": {
            "total_content": len(content),
            "published_posts": published_posts,
            "pending_schedules": pending_schedules,
            "total_reviews": rep["total_reviews"],
            "average_rating": rep["average_rating"],
            "response_rate": rep["response_rate"],
            "needs_attention": rep["needs_attention"],
            "ai_generations_total": ai_total,
            "ai_generations_this_month": ai_this_month,
        },
        "content_by_status": content_by_status,
        "content_by_channel": content_by_channel,
        "sentiment": rep["sentiment"],
        "timeseries": {
            "content_per_week": _weekly(content, lambda c: c.created_at),
            "reviews_per_week": _weekly(reviews, lambda r: r.reviewed_at or r.created_at),
        },
        "trends": {
            "content_this_month": content_this_month,
            "content_last_month": content_last_month,
            "reviews_this_month": rep["reviews_this_month"],
            "reviews_last_month": rep["reviews_last_month"],
        },
        "recommendations": _recommendations(
            content_by_status=content_by_status,
            pending_schedules=pending_schedules,
            published_posts=published_posts,
            rep=rep,
            content_this_week=content_this_week,
            unanswered=unanswered,
        ),
    }


def _pct(part: int, whole: int) -> float:
    return round(part / whole * 100, 1) if whole else 0.0


def platform_analytics(db: Session, *, business: Business) -> dict:
    """Per-platform engagement metrics (reach, impressions, engagement rate, CTR,
    profile visits, and Google Business actions) pulled from each connected account
    via its connector. The mock connector returns clearly-labeled *simulated* data
    (`simulated: true`); once live Meta/GBP connectors are approved they return the
    same shape from the real Insights / Performance APIs — plug and play."""
    accounts = scheduling_service.list_accounts(db, business_id=business.id)

    social = Counter()   # impressions, reach, engagements, likes/comments/shares/saves, link_clicks, profile_visits, followers, follower_growth
    local = Counter()    # views_search, views_maps, searches, website_clicks, direction_requests, calls, photo_views
    per_platform: list[dict] = []
    series_platforms: list[dict] = []  # weekly trend, one entry per social account
    simulated = False

    weeks = 8
    week_labels = [
        (date.today() - timedelta(days=7 * i)).strftime("%m/%d")
        for i in range(weeks - 1, -1, -1)
    ]

    for acct in accounts:
        connector = get_connector(acct.platform)
        token = acct.external_id or str(acct.id)
        if not connector.live:
            simulated = True
        try:
            m = connector.fetch_metrics(account_token=token)
        except (ConnectorError, NotImplementedError):
            continue  # connector can't fetch yet (pending approval) — skip

        kind = m.get("kind")
        if kind == "social":
            try:
                pts = connector.fetch_timeseries(account_token=token, weeks=weeks)
            except (ConnectorError, NotImplementedError):
                pts = []
            if pts:
                series_platforms.append({
                    "platform": acct.platform,
                    "display_name": acct.display_name,
                    "reach": [p.get("reach", 0) for p in pts],
                    "engagement": [p.get("engagement", 0) for p in pts],
                    "clicks": [p.get("clicks", 0) for p in pts],
                    "mentions": [p.get("mentions", 0) for p in pts],
                })

        if kind == "local":
            for key in ("views_search", "views_maps", "searches", "website_clicks",
                        "direction_requests", "calls", "photo_views"):
                local[key] += m.get(key, 0)
            per_platform.append({
                "platform": acct.platform,
                "display_name": acct.display_name,
                "kind": "local",
                "views": m.get("views_search", 0) + m.get("views_maps", 0),
                "actions": m.get("website_clicks", 0) + m.get("direction_requests", 0) + m.get("calls", 0),
            })
        elif kind == "social":
            for key in ("impressions", "reach", "engagements", "likes", "comments",
                        "shares", "saves", "link_clicks", "profile_visits",
                        "followers", "follower_growth"):
                social[key] += m.get(key, 0)
            per_platform.append({
                "platform": acct.platform,
                "display_name": acct.display_name,
                "kind": "social",
                "impressions": m.get("impressions", 0),
                "reach": m.get("reach", 0),
                "engagements": m.get("engagements", 0),
                "engagement_rate": _pct(m.get("engagements", 0), m.get("impressions", 0)),
                "link_clicks": m.get("link_clicks", 0),
                "ctr": _pct(m.get("link_clicks", 0), m.get("impressions", 0)),
                "followers": m.get("followers", 0),
                "follower_growth": m.get("follower_growth", 0),
            })

    return {
        "has_accounts": bool(accounts),
        "simulated": simulated,
        "social": {
            **dict(social),
            "engagement_rate": _pct(social["engagements"], social["impressions"]),
            "ctr": _pct(social["link_clicks"], social["impressions"]),
        },
        "local": {
            **dict(local),
            "views": local["views_search"] + local["views_maps"],
            "actions": local["website_clicks"] + local["direction_requests"] + local["calls"],
        },
        "per_platform": per_platform,
        "series": {
            "weeks": week_labels,
            "metrics": ["reach", "engagement", "clicks", "mentions"],
            "platforms": series_platforms,
        },
    }


def _check_quota(db: Session, business: Business) -> None:
    limit = business.plan.ai_monthly_quota if business.plan else UNLIMITED
    if limit != UNLIMITED and usage_this_month(db, business.id) >= limit:
        raise AiQuotaExceeded(limit)


def generate_insights(db: Session, *, router: AIRouter, business: Business) -> dict:
    """AI consultant assessment grounded in the current dashboard stats."""
    _check_quota(db, business)
    stats = dashboard(db, business_id=business.id)
    resp = router.handle(AIRequest(
        task=TaskType.BUSINESS_INSIGHTS,
        prompt="How is my business doing?",
        business_id=str(business.id),
        context={"business": build_business_context(business), "stats": stats},
    ))
    db.add(AiUsage(
        business_id=business.id, module=TaskType.BUSINESS_INSIGHTS.value,
        provider=resp.provider, model=resp.model,
        input_tokens=resp.input_tokens, output_tokens=resp.output_tokens,
    ))
    db.flush()
    return {"summary": resp.text, "recommendations": stats["recommendations"]}
