"""Operator cost dashboard: admin-only access + cross-tenant cost aggregation."""
from __future__ import annotations

API = "/api/v1"

# The default platform admin (see Settings.platform_admin_emails).
ADMIN_EMAIL = "andy1gext2@gmail.com"


def _signup(client, email):
    r = client.post(f"{API}/auth/signup", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_me_reports_platform_admin_flag(client):
    admin = _signup(client, ADMIN_EMAIL)
    other = _signup(client, "someone@example.com")

    assert client.get(f"{API}/auth/me", headers=admin).json()["is_platform_admin"] is True
    assert client.get(f"{API}/auth/me", headers=other).json()["is_platform_admin"] is False


def test_admin_usage_requires_platform_admin(client):
    other = _signup(client, "nonadmin@example.com")
    assert client.get(f"{API}/admin/usage", headers=other).status_code == 403


def test_admin_can_set_business_plan(client):
    admin = _signup(client, ADMIN_EMAIL)
    other = _signup(client, "planuser@example.com")
    bid = client.post(f"{API}/businesses", json={"name": "Acme"}, headers=other).json()["id"]

    # Non-admin cannot override plans.
    assert client.post(f"{API}/admin/businesses/{bid}/plan",
                       json={"tier": "enterprise"}, headers=other).status_code == 403

    # Operator sets the business to Enterprise (unlimited quotas).
    r = client.post(f"{API}/admin/businesses/{bid}/plan",
                    json={"tier": "enterprise"}, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["tier"] == "enterprise"

    status = client.get(f"{API}/businesses/{bid}/billing/status", headers=other).json()
    assert status["plan_tier"] == "enterprise"


def test_admin_usage_aggregates_costs(client):
    admin = _signup(client, ADMIN_EMAIL)
    # A business with one generated post → one text-AI row → non-zero cost.
    bid = client.post(f"{API}/businesses", json={"name": "Acme"}, headers=admin).json()["id"]
    client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "Launch"}, headers=admin,
    )

    r = client.get(f"{API}/admin/usage", headers=admin)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["totals"]["businesses"] >= 1
    row = next(b for b in data["businesses"] if b["business_id"] == bid)
    assert row["text_generations"] == 1
    assert row["total_cost_usd"] >= 0
    # Starter plan advertised at $59.99 → MRR reflects it.
    assert row["mrr_usd"] == 59.99
    assert row["margin_usd"] == round(row["mrr_usd"] - row["total_cost_usd"], 2)
