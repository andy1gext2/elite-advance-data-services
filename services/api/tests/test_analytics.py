"""Phase 5: analytics dashboard rollups, grounded recommendations, AI insights, RBAC."""
from __future__ import annotations

API = "/api/v1"


def _owner(client, email="ana@example.com"):
    tokens = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    biz = client.post(
        f"{API}/businesses",
        json={"name": "Acme Coffee", "industry": "Cafe", "tone": "warm"},
        headers=h,
    ).json()
    return h, biz["id"]


def test_dashboard_rolls_up_real_signals(client):
    h, bid = _owner(client)
    # Produce some real activity: content + reviews.
    client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "Autumn launch"}, headers=h,
    )
    client.post(f"{API}/businesses/{bid}/reviews/sync", json={}, headers=h)

    dash = client.get(f"{API}/businesses/{bid}/analytics/dashboard", headers=h)
    assert dash.status_code == 200, dash.text
    d = dash.json()

    assert d["kpis"]["total_content"] == 1
    assert d["kpis"]["total_reviews"] == 6
    assert d["kpis"]["ai_generations_this_month"] >= 1
    assert d["content_by_channel"].get("instagram") == 1
    assert d["sentiment"] == {"positive": 3, "neutral": 1, "negative": 2}
    # 8-week series, most recent week last.
    assert len(d["timeseries"]["content_per_week"]) == 8
    assert d["timeseries"]["content_per_week"][-1]["count"] == 1


def test_recommendations_are_grounded(client):
    h, bid = _owner(client)
    client.post(f"{API}/businesses/{bid}/reviews/sync", json={}, headers=h)
    d = client.get(f"{API}/businesses/{bid}/analytics/dashboard", headers=h).json()
    joined = " ".join(d["recommendations"])
    # Two synced reviews need attention -> a concrete escalation recommendation.
    assert "need" in joined.lower()
    assert any("2" in r for r in d["recommendations"])


def test_insights_generation(client):
    h, bid = _owner(client)
    client.post(f"{API}/businesses/{bid}/reviews/sync", json={}, headers=h)
    r = client.post(f"{API}/businesses/{bid}/insights/generate", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]
    assert "Acme Coffee" in body["summary"]  # grounded in business context
    assert isinstance(body["recommendations"], list)


def test_dashboard_rbac_and_isolation(client):
    owner_h, bid = _owner(client, email="anaowner@example.com")

    # Viewer can read the dashboard but not generate insights (AI cost -> editor+).
    client.post(f"{API}/auth/signup", json={"email": "anaviewer@example.com", "password": "password123"})
    client.post(
        f"{API}/businesses/{bid}/members",
        json={"email": "anaviewer@example.com", "role": "viewer"}, headers=owner_h,
    )
    viewer_h = {"Authorization": "Bearer " + client.post(
        f"{API}/auth/login", json={"email": "anaviewer@example.com", "password": "password123"}
    ).json()["access_token"]}
    assert client.get(f"{API}/businesses/{bid}/analytics/dashboard", headers=viewer_h).status_code == 200
    assert client.post(f"{API}/businesses/{bid}/insights/generate", headers=viewer_h).status_code == 403

    # A different tenant can't see this dashboard.
    other_h, _ = _owner(client, email="anaother@example.com")
    assert client.get(f"{API}/businesses/{bid}/analytics/dashboard", headers=other_h).status_code == 404
