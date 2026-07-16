"""Billing schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CheckoutIn(BaseModel):
    tier: str = Field(pattern="^(starter|professional|growth)$")


class UrlOut(BaseModel):
    # null when billing is disabled and the action was applied directly (dev grant).
    url: str | None = None


class BillingStatusOut(BaseModel):
    enabled: bool
    plan_tier: str | None = None
    plan_name: str | None = None
    subscription_status: str | None = None
    video_credits: int = 0


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier: str
    name: str
    price_monthly: int
    max_users: int
    max_social_accounts: int
    max_locations: int
    ai_monthly_quota: int
    image_monthly_quota: int
    video_monthly_quota: int
    features: dict
