"""Stripe billing — subscriptions (plan tiers) + one-time video-credit packs.

Gated on STRIPE_SECRET_KEY: when it's unset, `is_enabled()` is False and the API
falls back (dev grants) or 503s. The **webhook is the source of truth** — plan and
credit changes are applied there, not optimistically on redirect. The `stripe` SDK
is imported lazily so the app runs without it when billing is off.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.business import Business
from app.models.enums import PlanTier
from app.services import plan_service, video_service


def is_enabled() -> bool:
    return bool(get_settings().stripe_secret_key)


def _stripe():
    import stripe  # lazy: only needed when billing is configured

    stripe.api_key = get_settings().stripe_secret_key
    return stripe


def price_for_tier(tier: str) -> str | None:
    s = get_settings()
    return {
        PlanTier.STARTER.value: s.stripe_price_starter,
        PlanTier.PROFESSIONAL.value: s.stripe_price_professional,
        PlanTier.GROWTH.value: s.stripe_price_agency,
    }.get(tier)


def tier_for_price(price_id: str | None) -> str | None:
    if not price_id:
        return None
    s = get_settings()
    return {
        s.stripe_price_starter: PlanTier.STARTER.value,
        s.stripe_price_professional: PlanTier.PROFESSIONAL.value,
        s.stripe_price_agency: PlanTier.GROWTH.value,
    }.get(price_id)


# ── Checkout / portal ───────────────────────────────
def subscription_checkout(business: Business, *, tier: str, success_url: str, cancel_url: str) -> str:
    price = price_for_tier(tier)
    if not price:
        raise ValueError(f"No Stripe price configured for tier '{tier}'")
    kwargs = {
        "mode": "subscription",
        "line_items": [{"price": price, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(business.id),
        "metadata": {"business_id": str(business.id), "tier": tier, "kind": "subscription"},
        "subscription_data": {"metadata": {"business_id": str(business.id), "tier": tier}},
    }
    if business.stripe_customer_id:
        kwargs["customer"] = business.stripe_customer_id
    return _stripe().checkout.Session.create(**kwargs).url


def credits_checkout(business: Business, *, success_url: str, cancel_url: str) -> str:
    s = get_settings()
    if not s.stripe_credits_price_id:
        raise ValueError("No Stripe price configured for video credits")
    kwargs = {
        "mode": "payment",
        "line_items": [{"price": s.stripe_credits_price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(business.id),
        "metadata": {"business_id": str(business.id), "kind": "credits"},
    }
    if business.stripe_customer_id:
        kwargs["customer"] = business.stripe_customer_id
    return _stripe().checkout.Session.create(**kwargs).url


def portal(business: Business, *, return_url: str) -> str:
    if not business.stripe_customer_id:
        raise ValueError("No Stripe customer for this business yet")
    return _stripe().billing_portal.Session.create(
        customer=business.stripe_customer_id, return_url=return_url
    ).url


# ── Webhook (source of truth) ───────────────────────
def handle_webhook(db: Session, *, payload: bytes, signature: str | None) -> str:
    s = get_settings()
    event = _stripe().Webhook.construct_event(payload, signature, s.stripe_webhook_secret)
    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        _on_checkout(db, obj)
    elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        _on_subscription(db, obj, deleted=etype.endswith("deleted"))
    db.commit()
    return etype


def _business_from(db: Session, obj: dict) -> Business | None:
    bid = (obj.get("metadata") or {}).get("business_id") or obj.get("client_reference_id")
    if bid:
        try:
            return db.get(Business, uuid.UUID(bid))
        except (ValueError, TypeError):
            pass
    sub = obj.get("id") if obj.get("object") == "subscription" else obj.get("subscription")
    if sub:
        return db.scalar(select(Business).where(Business.stripe_subscription_id == sub))
    return None


def _on_checkout(db: Session, obj: dict) -> None:
    business = _business_from(db, obj)
    if business is None:
        return
    if obj.get("customer"):
        business.stripe_customer_id = obj["customer"]

    kind = (obj.get("metadata") or {}).get("kind")
    if kind == "credits" or obj.get("mode") == "payment":
        video_service.add_credits(db, business, get_settings().stripe_credits_per_pack)
        return

    # Subscription checkout completed → activate the plan.
    if obj.get("subscription"):
        business.stripe_subscription_id = obj["subscription"]
    business.subscription_status = "active"
    tier = (obj.get("metadata") or {}).get("tier")
    plan = plan_service.get_plan_by_tier(db, tier) if tier else None
    if plan:
        business.plan_id = plan.id


def _on_subscription(db: Session, obj: dict, *, deleted: bool) -> None:
    business = _business_from(db, obj)
    if business is None:
        return
    if deleted:
        business.subscription_status = "canceled"
        starter = plan_service.get_plan_by_tier(db, PlanTier.STARTER.value)
        if starter:
            business.plan_id = starter.id  # downgrade to the base plan
        return

    business.subscription_status = obj.get("status") or business.subscription_status
    items = (obj.get("items") or {}).get("data") or []
    price_id = (items[0].get("price") or {}).get("id") if items else None
    tier = tier_for_price(price_id)
    plan = plan_service.get_plan_by_tier(db, tier) if tier else None
    if plan:
        business.plan_id = plan.id
