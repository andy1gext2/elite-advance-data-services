"""Industry trends: curated list, cached per-industry brief, dashboard endpoint."""
from __future__ import annotations

API = "/api/v1"


def _owner(client, email="trends@example.com", industry="Coffee shop / Cafe"):
    tok = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    bid = client.post(
        f"{API}/businesses", json={"name": "Bean There", "industry": industry}, headers=h
    ).json()["id"]
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
    tok = client.post(
        f"{API}/auth/signup", json={"email": "noind@example.com", "password": "password123"}
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    bid = client.post(f"{API}/businesses", json={"name": "Mystery Co"}, headers=h).json()["id"]
    assert client.get(f"{API}/businesses/{bid}/trends", headers=h).status_code == 400
