"""Phase 4: review sync/dedup, sentiment + escalation, AI responses, report, RBAC."""
from __future__ import annotations

API = "/api/v1"


def _owner(client, email="rep@example.com"):
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


def _sync(client, h, bid):
    return client.post(f"{API}/businesses/{bid}/reviews/sync", json={}, headers=h)


def test_sync_ingests_and_dedupes(client):
    h, bid = _owner(client)
    r = _sync(client, h, bid)
    assert r.status_code == 200, r.text
    assert r.json() == {"fetched": 6, "new": 6}

    # Re-sync sees the same reviews but ingests none (stable external ids).
    again = _sync(client, h, bid).json()
    assert again == {"fetched": 6, "new": 0}

    reviews = client.get(f"{API}/businesses/{bid}/reviews", headers=h).json()
    assert len(reviews) == 6
    # Enrichment ran: every review has a sentiment + keyword list.
    assert all(rv["sentiment"] in {"positive", "neutral", "negative"} for rv in reviews)
    assert any(rv["keywords"] for rv in reviews)


def test_sentiment_and_escalation(client):
    h, bid = _owner(client)
    _sync(client, h, bid)
    reviews = client.get(f"{API}/businesses/{bid}/reviews", headers=h).json()

    by_rating = {rv["rating"]: rv for rv in reviews}
    # 5-star reads positive; 1-star reads negative and is flagged for attention.
    assert by_rating[5]["sentiment"] == "positive"
    assert by_rating[1]["sentiment"] == "negative"
    assert by_rating[1]["needs_attention"] is True
    assert by_rating[5]["needs_attention"] is False

    # Filters: two low/negative reviews need attention.
    flagged = client.get(
        f"{API}/businesses/{bid}/reviews", params={"needs_attention": True}, headers=h
    ).json()
    assert len(flagged) == 2
    negative = client.get(
        f"{API}/businesses/{bid}/reviews", params={"sentiment": "negative"}, headers=h
    ).json()
    assert len(negative) == 2


def test_generate_and_post_response(client):
    h, bid = _owner(client)
    _sync(client, h, bid)
    reviews = client.get(f"{API}/businesses/{bid}/reviews", headers=h).json()
    one_star = next(rv for rv in reviews if rv["rating"] == 1)

    gen = client.post(
        f"{API}/businesses/{bid}/reviews/{one_star['id']}/respond/generate", headers=h
    )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert body["response_text"]
    assert "sorry" in body["response_text"].lower()  # apology for a 1-star
    assert body["status"] == "new"  # drafting doesn't post

    # Posting the reply marks it responded and clears the escalation flag.
    posted = client.post(
        f"{API}/businesses/{bid}/reviews/{one_star['id']}/respond", headers=h
    ).json()
    assert posted["status"] == "responded"
    assert posted["needs_attention"] is False


def test_cannot_post_without_a_drafted_response(client):
    h, bid = _owner(client)
    _sync(client, h, bid)
    rv = client.get(f"{API}/businesses/{bid}/reviews", headers=h).json()[0]
    blocked = client.post(f"{API}/businesses/{bid}/reviews/{rv['id']}/respond", headers=h)
    assert blocked.status_code == 400


def test_reputation_report(client):
    h, bid = _owner(client)
    _sync(client, h, bid)
    report = client.get(f"{API}/businesses/{bid}/reputation/report", headers=h).json()

    assert report["total_reviews"] == 6
    assert report["average_rating"] == round(20 / 6, 2)
    assert report["sentiment"] == {"positive": 3, "neutral": 1, "negative": 2}
    assert report["needs_attention"] == 2
    assert report["response_rate"] == 0.0
    # Complaints come from negative reviews' keywords.
    assert isinstance(report["top_complaints"], list)


def test_reviews_rbac_and_isolation(client):
    owner_h, bid = _owner(client, email="repowner@example.com")
    _sync(client, owner_h, bid)

    # Viewer can read but not sync.
    client.post(f"{API}/auth/signup", json={"email": "repviewer@example.com", "password": "password123"})
    client.post(
        f"{API}/businesses/{bid}/members",
        json={"email": "repviewer@example.com", "role": "viewer"}, headers=owner_h,
    )
    viewer_h = {"Authorization": "Bearer " + client.post(
        f"{API}/auth/login", json={"email": "repviewer@example.com", "password": "password123"}
    ).json()["access_token"]}
    assert client.get(f"{API}/businesses/{bid}/reviews", headers=viewer_h).status_code == 200
    assert _sync(client, viewer_h, bid).status_code == 403

    # A different tenant can't see these reviews at all.
    other_h, _ = _owner(client, email="repother@example.com")
    assert client.get(f"{API}/businesses/{bid}/reviews", headers=other_h).status_code == 404


def test_scheduled_poller_syncs_only_connected_tenants(client):
    """The Celery review poller (poll_all_businesses) syncs tenants that have a
    connected account and skips those that don't — so it never fabricates reviews
    for accounts that never connected anything."""
    from app.core.db import get_db
    from app.services import reputation_service

    # Tenant A connects an account; tenant B does not.
    h_a, bid_a = _owner(client, email="pollA@example.com")
    client.post(
        f"{API}/businesses/{bid_a}/integrations/accounts",
        json={"platform": "google_business", "display_name": "Acme GBP"}, headers=h_a,
    )
    _owner(client, email="pollB@example.com")  # no account connected

    db = next(client.app.dependency_overrides[get_db]())
    try:
        summary = reputation_service.poll_all_businesses(db)
        db.commit()
    finally:
        db.close()

    # Only the one connected tenant is polled; the mock returns its sample set.
    assert summary["businesses_polled"] == 1
    assert summary["fetched"] == 6 and summary["new"] == 6

    # Those reviews are now visible on tenant A without anyone clicking "Sync".
    assert len(client.get(f"{API}/businesses/{bid_a}/reviews", headers=h_a).json()) == 6
