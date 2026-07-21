"""Industry trends: curated list, cached per-industry brief, dashboard endpoint."""
from __future__ import annotations

API = "/api/v1"


def _set_tier(client, bid, tier):
    """Move a business onto a plan tier (industry trends need Professional+)."""
    import uuid as u
    from app.core.db import get_db
    from app.models.business import Business
    from app.services.plan_service import get_plan_by_tier

    db = next(client.app.dependency_overrides[get_db]())
    try:
        biz = db.get(Business, u.UUID(bid))
        biz.plan_id = get_plan_by_tier(db, tier).id
        db.commit()
    finally:
        db.close()


def _owner(client, email="trends@example.com", industry="Coffee shop / Cafe", tier="professional"):
    tok = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    bid = client.post(
        f"{API}/businesses", json={"name": "Bean There", "industry": industry}, headers=h
    ).json()["id"]
    if tier:
        _set_tier(client, bid, tier)  # default new businesses are Starter (no trends)
    return h, bid


def test_industries_list_is_public(client):
    r = client.get(f"{API}/industries")
    assert r.status_code == 200, r.text
    items = r.json()["industries"]
    assert any(i["slug"] == "cafe" for i in items)
    assert all({"slug", "label", "emoji"} <= set(i) for i in items)


def test_business_trends_returns_structured_brief(client):
    h, bid = _owner(client)
    r = client.get(f"{API}/businesses/{bid}/trends", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["industry"] == "cafe"  # "Coffee shop / Cafe" normalized
    for key in ("keywords", "products", "services", "seasonal", "post_ideas"):
        assert key in data and isinstance(data[key], list)
    assert len(data["post_ideas"]) >= 1
    idea = data["post_ideas"][0]
    assert idea["title"] and idea["channel"] in {
        "instagram", "facebook", "linkedin", "x", "threads", "google_business"
    }


def test_trends_are_cached_and_shared_across_tenants(client):
    from app.core.db import get_db
    from app.models.industry_trend import IndustryTrend
    from sqlalchemy import select, func

    # Two different cafes.
    h1, bid1 = _owner(client, email="cafe1@example.com", industry="Cafe")
    h2, bid2 = _owner(client, email="cafe2@example.com", industry="coffee shop")
    assert client.get(f"{API}/businesses/{bid1}/trends", headers=h1).status_code == 200
    assert client.get(f"{API}/businesses/{bid2}/trends", headers=h2).status_code == 200

    # Both normalize to "cafe" → exactly one cached row is shared.
    db = next(client.app.dependency_overrides[get_db]())
    try:
        count = db.scalar(
            select(func.count(IndustryTrend.id)).where(IndustryTrend.industry == "cafe")
        )
    finally:
        db.close()
    assert count == 1


def test_trends_requires_industry(client):
    # Professional business (has the feature) but no industry set → 400.
    h, bid = _owner(client, email="noind@example.com", industry="")
    assert client.get(f"{API}/businesses/{bid}/trends", headers=h).status_code == 400


def test_trends_gated_to_professional_and_above(client):
    # A Starter business (the default) is blocked with 402; upgrading unlocks it.
    h, bid = _owner(client, email="starter@example.com", tier="starter")
    r = client.get(f"{API}/businesses/{bid}/trends", headers=h)
    assert r.status_code == 402, r.text
    assert "Professional" in r.json()["detail"]

    _set_tier(client, bid, "professional")
    assert client.get(f"{API}/businesses/{bid}/trends", headers=h).status_code == 200
