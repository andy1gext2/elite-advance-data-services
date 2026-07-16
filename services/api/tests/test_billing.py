"""Billing scaffolding: public plans, gated checkout/webhook, dev credit fallback."""
from __future__ import annotations

API = "/api/v1"


def _owner(client, email="billing@example.com"):
    tokens = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bid = client.post(f"{API}/businesses", json={"name": "Acme"}, headers=h).json()["id"]
    return h, bid


def test_plans_are_public_and_priced(client):
    plans = client.get(f"{API}/plans").json()
    tiers = {p["tier"]: p for p in plans}
    assert set(tiers) == {"starter", "professional", "growth", "enterprise"}
    assert tiers["starter"]["price_monthly"] == 39
    assert tiers["professional"]["video_monthly_quota"] == 8
    assert tiers["growth"]["name"] == "Agency"


def test_billing_status_reports_disabled_and_plan(client):
    h, bid = _owner(client, "bs@example.com")
    st = client.get(f"{API}/businesses/{bid}/billing/status", headers=h).json()
    assert st["enabled"] is False          # no Stripe key in tests
    assert st["plan_tier"] == "starter"
    assert st["video_credits"] == 0


def test_subscription_checkout_503_when_disabled(client):
    h, bid = _owner(client, "co@example.com")
    r = client.post(
        f"{API}/businesses/{bid}/billing/checkout", json={"tier": "professional"}, headers=h
    )
    assert r.status_code == 503


def test_credits_checkout_falls_back_to_dev_grant(client):
    h, bid = _owner(client, "cc@example.com")
    r = client.post(f"{API}/businesses/{bid}/billing/credits-checkout", headers=h)
    assert r.status_code == 200
    assert r.json()["url"] is None  # granted directly (no Stripe redirect)
    q = client.get(f"{API}/businesses/{bid}/content/video-quota", headers=h).json()
    assert q["credits"] == 10  # stripe_credits_per_pack default


def test_webhook_503_when_disabled(client):
    r = client.post(
        f"{API}/billing/webhook", content=b"{}", headers={"stripe-signature": "x"}
    )
    assert r.status_code == 503
