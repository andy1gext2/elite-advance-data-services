"""Platform-operator detection at the tenant level.

A business is "operator-owned" when any of its members is a configured platform
admin (PLATFORM_ADMIN_EMAILS). Operator-owned tenants BYPASS usage quotas so the
operator can freely stress-test paid features (text/image/video generation)
without being capped by the business's subscription plan. This is intentionally
independent of the plan: being the platform admin is enough."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.business import Business
from app.models.membership import Membership
from app.models.user import User


def is_operator_business(db: Session, business: Business) -> bool:
    """True if any member of this business is a configured platform admin."""
    admins = get_settings().admin_emails
    if not admins:
        return False
    match = db.scalar(
        select(User.id)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.business_id == business.id,
            func.lower(User.email).in_(admins),
        )
        .limit(1)
    )
    return match is not None
