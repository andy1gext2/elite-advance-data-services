"""Default subscription plans + lookup. Seeded idempotently."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import UNLIMITED, PlanTier
from app.models.plan import Plan

DEFAULT_PLANS: list[dict] = [
    {
        "tier": PlanTier.STARTER.value, "name": "Starter", "price_monthly": 39,
        "max_users": 2, "max_social_accounts": 5, "max_locations": 1,
        "ai_monthly_quota": 150, "image_monthly_quota": 40, "video_monthly_quota": 1,
        "features": {"advanced_analytics": False, "white_label": False,
                     "priority_support": False, "enterprise_integrations": False,
                     "autopilot": False},
    },
    {
        "tier": PlanTier.PROFESSIONAL.value, "name": "Professional", "price_monthly": 119,
        "max_users": 5, "max_social_accounts": 15, "max_locations": 3,
        "ai_monthly_quota": 1000, "image_monthly_quota": 250, "video_monthly_quota": 8,
        "features": {"advanced_analytics": True, "white_label": False,
                     "priority_support": False, "enterprise_integrations": False,
                     "autopilot": True},
    },
    {
        "tier": PlanTier.GROWTH.value, "name": "Agency", "price_monthly": 349,
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
    existing = {p.tier for p in db.scalars(select(Plan)).all()}
    for spec in DEFAULT_PLANS:
        if spec["tier"] not in existing:
            db.add(Plan(**spec))
    db.flush()


def get_plan_by_tier(db: Session, tier: str) -> Plan | None:
    return db.scalar(select(Plan).where(Plan.tier == tier))
