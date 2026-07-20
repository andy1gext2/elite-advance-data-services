"""Billing routes — Stripe checkout (subscriptions + credit packs), the customer
portal, a public plans list, and the webhook (source of truth). All gated on
billing being configured; without Stripe keys, checkout falls back to dev grants
and the webhook 503s. Checkout/portal require admin+."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import TenantContext, get_membership_ctx, require_role
from app.core.config import get_settings
from app.core.db import get_db
from app.models.enums import Role
from app.models.plan import Plan
from app.schemas.billing import BillingStatusOut, CheckoutIn, PlanOut, UrlOut
from app.services import billing_service, video_service

router = APIRouter(prefix="/businesses/{business_id}/billing", tags=["billing"])
public = APIRouter(tags=["billing"])

logger = logging.getLogger("app.billing")


def _urls(business_id) -> tuple[str, str]:
    base = f"{get_settings().web_base_url}/businesses/{business_id}/billing"
    return f"{base}?checkout=success", f"{base}?checkout=cancel"


@router.get("/status", response_model=BillingStatusOut)
def billing_status(ctx: TenantContext = Depends(get_membership_ctx)) -> BillingStatusOut:
    b = ctx.business
    return BillingStatusOut(
        enabled=billing_service.is_enabled(),
        plan_tier=b.plan.tier if b.plan else None,
        plan_name=b.plan.name if b.plan else None,
        subscription_status=b.subscription_status,
        video_credits=b.video_credits,
    )


@router.post("/checkout", response_model=UrlOut)
def subscription_checkout(
    body: CheckoutIn,
    ctx: TenantContext = Depends(require_role(Role.ADMIN)),
) -> UrlOut:
    if not billing_service.is_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Billing is not configured")
    success, cancel = _urls(ctx.business.id)
    try:
        url = billing_service.subscription_checkout(
            ctx.business, tier=body.tier, success_url=success, cancel_url=cancel
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 — surface the Stripe error instead of a blank 500
        logger.exception("Stripe subscription checkout failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment provider error: {exc}",
        )
    return UrlOut(url=url)


@router.post("/credits-checkout", response_model=UrlOut)
def credits_checkout(
    ctx: TenantContext = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
) -> UrlOut:
    s = get_settings()
    if billing_service.is_enabled() and s.stripe_credits_price_id:
        success, cancel = _urls(ctx.business.id)
        try:
            return UrlOut(url=billing_service.credits_checkout(ctx.business, success_url=success, cancel_url=cancel))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Stripe credits checkout failed")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Payment provider error: {exc}")
    # Dev fallback (no Stripe): grant the pack directly so the flow is testable.
    video_service.add_credits(db, ctx.business, s.stripe_credits_per_pack)
    db.commit()
    return UrlOut(url=None)


@router.post("/portal", response_model=UrlOut)
def customer_portal(ctx: TenantContext = Depends(require_role(Role.ADMIN))) -> UrlOut:
    if not billing_service.is_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Billing is not configured")
    return_url = f"{get_settings().web_base_url}/businesses/{ctx.business.id}/billing"
    try:
        url = billing_service.portal(ctx.business, return_url=return_url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return UrlOut(url=url)


@public.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)) -> list[PlanOut]:
    """Public pricing tiers (for the billing/pricing page)."""
    return list(db.scalars(select(Plan).order_by(Plan.price_monthly)).all())


@public.post("/billing/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Stripe calls this after checkout / subscription changes. Signature-verified;
    the only place plan + credit changes are actually applied."""
    s = get_settings()
    if not (billing_service.is_enabled() and s.stripe_webhook_secret):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Billing webhook not configured")
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        etype = billing_service.handle_webhook(db, payload=payload, signature=signature)
    except Exception as exc:  # noqa: BLE001 - Stripe raises many verification errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Webhook error: {exc}")
    return {"received": True, "type": etype}
