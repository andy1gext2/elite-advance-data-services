"""Default subscription plans + lookup. Seeded idempotently."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import UNLIMITED, PlanTier
from app.models.plan import Plan

DEFAULT_PLANS: list[dict] = [
    {
        "tier": PlanTier.STARTER.value, "name": "Starter", "price_monthly": 5999,
        "max_users": 2, "max_social_accounts": 5, "max_locations": 1,
        "ai_monthly_quota": 150, "image_monthly_quota": 40, "video_monthly_quota": 1,
        "features": {"advanced_analytics": False, "white_label": False,
                     "priority_support": False, "enterprise_integrations": False,
                     "autopilot": False},
    },
    {
        "tier": PlanTier.PROFESSIONAL.value, "name": "Professional", "price_monthly": 14999,
        "max_users": 5, "max_social_accounts": 15, "max_locations": 3,
        "ai_monthly_quota": 1000, "image_monthly_quota": 250, "video_monthly_quota": 8,
        "features": {"advanced_analytics": True, "white_label": False,
                     "priority_support": False, "enterprise_integrations": False,
                     "autopilot": True},
    },
    {
        "tier": PlanTier.GROWTH.value, "name": "Growth", "price_monthly": 39999,
        "max_users": 15, "max_social_accounts": 60, "max_locations": 20,
        "ai_monthly_quota": 5000, "image_monthly_quota": 1000, "video_monthly_quota": 30,
        "features": {"advanced_analytics": True, "white_label": True,
                     "priority_support": True, "enterprise_integrations": False,
                     "autopilot": True},
    },
    {
        "tier": PlanTier.ENTERPRISE.value, "name": "Enterprise", "price_monthly": 0,
        "max_users": UNLIMITED, "max_social_accounts": UNLIMITED, "max_locations": UNLIMITED,
        "ai_monthly_quota": UNLIMITED, "image_monthly_quota": UNLIMITED, "video_monthly_quota": UNLIMITED,
        "features": {"advanced_analytics": True, "white_label": True,
                     "priority_support": True, "enterprise_integrations": True,
                     "autopilot": True},
    },
]


def seed_default_plans(db: Session) -> None:
    existing = {p.tier: p for p in db.scalars(select(Plan)).all()}
    for spec in DEFAULT_PLANS:
        current = existing.get(spec["tier"])
        if current is None:
            db.add(Plan(**spec))
        else:
            # DEFAULT_PLANS is the single source of truth: sync every field (quotas,
            # limits, features, price, name) onto already-seeded rows on restart.
            # This self-heals plans that drifted from the spec — e.g. an Enterprise
            # row whose video_monthly_quota isn't UNLIMITED, or a Starter row still
            # carrying an old migration default. `tier` is the key, so never touch it.
            for field, value in spec.items():
                if field != "tier":
                    setattr(current, field, value)
    db.flush()


def get_plan_by_tier(db: Session, tier: str) -> Plan | None:
    return db.scalar(select(Plan).where(Plan.tier == tier))
