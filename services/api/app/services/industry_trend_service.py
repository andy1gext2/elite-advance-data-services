"""Industry trend briefs — cached, shared across tenants, refreshed monthly.

Haiku generates a compact, structured brief per industry (trending keywords, hot
products/services, seasonal items, and concrete post ideas) grounded in the current
month for seasonality. Results are cached per normalized industry slug and reused
across every business in that industry; a brief is regenerated when the calendar
month rolls over (so seasonal guidance stays current). Provider-agnostic — the
cheap tier is selected via model_policy."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIRequest, TaskType
from app.ai.model_policy import select_model
from app.ai.router import AIRouter
from app.data import industries
from app.models.industry_trend import IndustryTrend

_SYSTEM = (
    "You are a marketing trends analyst for small businesses. For the given industry "
    "and month, produce a concise, practical brief of what's resonating right now — "
    "leaning on seasonal relevance for the month. Return ONLY a JSON object with these "
    "keys and no prose:\n"
    '{"keywords": [up to 6 short trending words/phrases or hashtags],\n'
    ' "products": [up to 5 popular products for this industry right now],\n'
    ' "services": [up to 5 in-demand services for this industry right now],\n'
    ' "seasonal": [up to 5 seasonal/timely items or themes for THIS month],\n'
    ' "post_ideas": [3-5 objects {"title": short post idea, "why": one-sentence rationale, '
    '"channel": one of instagram|facebook|linkedin|x|threads|google_business}]}\n'
    "Keep every string short and specific. Do not claim real-time data; give strong, "
    "seasonally-aware guidance a local owner can act on."
)

# Cap list sizes so a runaway model response can't bloat the cached payload.
_LIMITS = {"keywords": 6, "products": 5, "services": 5, "seasonal": 5, "post_ideas": 5}
_CHANNELS = {"instagram", "facebook", "linkedin", "x", "threads", "google_business"}


def current_period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _month_name() -> str:
    return datetime.now(timezone.utc).strftime("%B")


def _clean_list(value, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip()[:120])
        if len(out) >= limit:
            break
    return out


def _clean_ideas(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()[:160]
        if not title:
            continue
        channel = str(item.get("channel", "")).strip().lower()
        out.append({
            "title": title,
            "why": str(item.get("why", "")).strip()[:200],
            "channel": channel if channel in _CHANNELS else "instagram",
        })
        if len(out) >= _LIMITS["post_ideas"]:
            break
    return out


def _sanitize(payload: dict) -> dict:
    return {
        "keywords": _clean_list(payload.get("keywords"), _LIMITS["keywords"]),
        "products": _clean_list(payload.get("products"), _LIMITS["products"]),
        "services": _clean_list(payload.get("services"), _LIMITS["services"]),
        "seasonal": _clean_list(payload.get("seasonal"), _LIMITS["seasonal"]),
        "post_ideas": _clean_ideas(payload.get("post_ideas")),
    }


def _parse(text: str) -> dict | None:
    """Parse the model's JSON, tolerating markdown fences / surrounding prose."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1] if raw.count("```") >= 2 else raw.strip("`")
        if raw.lstrip().lower().startswith("json"):
            raw = raw.lstrip()[4:]
    # Fall back to the outermost {...} span if there's extra text around it.
    if not raw.strip().startswith("{"):
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            raw = raw[start : end + 1]
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def _fallback_payload(display: str) -> dict:
    """A useful (if generic) brief when parsing fails, so the card is never empty."""
    low = display.lower()
    return {
        "keywords": [f"{low} tips", f"local {low}", "small business", "community"],
        "products": ["signature offering", "seasonal special", "gift bundle"],
        "services": ["free consultation", "loyalty rewards", "same-day service"],
        "seasonal": [f"{_month_name()} promotion", f"{_month_name()} feature"],
        "post_ideas": [
            {"title": "Share a behind-the-scenes look", "why": "Builds trust and personality.", "channel": "instagram"},
            {"title": f"Highlight a {_month_name()} seasonal offer", "why": "Timely relevance drives engagement.", "channel": "facebook"},
            {"title": "Post a customer testimonial", "why": "Social proof converts nearby prospects.", "channel": "google_business"},
        ],
    }


def generate(db: Session, *, router: AIRouter, industry: str) -> IndustryTrend:
    """Generate (or regenerate) the brief for an industry and upsert the cache row."""
    slug = industries.normalize(industry)
    display = industries.display_name(slug, fallback=industry)
    period = current_period()

    resp = router.handle(AIRequest(
        task=TaskType.INDUSTRY_TRENDS,
        prompt=f"Industry: {display}. Month: {_month_name()}.",
        business_id=f"industry:{slug}",  # shared brief — not tenant-scoped
        context={"industry": display, "month": _month_name(), "period": period},
        system=_SYSTEM,
        model=select_model(task=TaskType.INDUSTRY_TRENDS),
        max_tokens=800,
        temperature=0.7,
    ))
    parsed = _parse(resp.text)
    payload = _sanitize(parsed) if parsed else _fallback_payload(display)
    if not payload["post_ideas"]:  # never surface an empty card
        payload = _fallback_payload(display)

    row = db.scalar(select(IndustryTrend).where(IndustryTrend.industry == slug))
    if row is None:
        row = IndustryTrend(industry=slug, display_industry=display, period=period, payload=payload)
        db.add(row)
    else:
        row.display_industry = display
        row.period = period
        row.payload = payload
    db.flush()
    return row


def get_or_generate(db: Session, *, router: AIRouter, industry: str) -> IndustryTrend:
    """Return the cached brief for an industry, regenerating it when missing or when
    the calendar month has rolled over (keeps seasonal guidance current)."""
    slug = industries.normalize(industry)
    row = db.scalar(select(IndustryTrend).where(IndustryTrend.industry == slug))
    if row is not None and row.period == current_period():
        return row
    return generate(db, router=router, industry=industry)


def refresh_stale(db: Session, *, router: AIRouter) -> dict:
    """Worker entry point: regenerate every cached brief whose period is not the
    current month. Cheap and bounded (one row per industry ever generated)."""
    period = current_period()
    stale = list(db.scalars(
        select(IndustryTrend).where(IndustryTrend.period != period)
    ).all())
    for row in stale:
        generate(db, router=router, industry=row.industry)
    return {"refreshed": len(stale)}


def as_dict(row: IndustryTrend) -> dict:
    return {
        "industry": row.industry,
        "display_industry": row.display_industry,
        "period": row.period,
        "generated_at": row.updated_at.isoformat() if row.updated_at else None,
        **row.payload,
    }
