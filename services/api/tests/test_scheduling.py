"""Phase 3: connect account, schedule, publish engine, reposting, RBAC, isolation."""
from __future__ import annotations

PAST = "2020-01-01T09:00:00Z"
FUTURE = "2999-01-01T09:00:00Z"
API = "/api/v1"


def _setup(client, email="sched@example.com"):
    """Owner + business + one content item + one connected account."""
    tokens = client.post(f"{API}/auth/signup", json={"email": email, "password": "password123"}).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bid = client.post(f"{API}/businesses", json={"name": "Acme Co", "tone": "warm"}, headers=h).json()["id"]
    item = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "New winter menu"}, headers=h,
    ).json()
    acct = client.post(
        f"{API}/businesses/{bid}/integrations/accounts",
        json={"platform": "instagram", "display_name": "@acme"}, headers=h,
    )
    assert acct.status_code == 201, acct.text
    return h, bid, item["id"], acct.json()["id"]


def test_connect_account_and_list(client):
    h, bid, _, acct_id = _setup(client)
    accounts = client.get(f"{API}/businesses/{bid}/integrations/accounts", headers=h).json()
    assert [a["id"] for a in accounts] == [acct_id]
    assert accounts[0]["platform"] == "instagram"


def test_schedule_then_publish_due(client):
    h, bid, item_id, acct_id = _setup(client)
    sched = client.post(
        f"{API}/businesses/{bid}/schedules",
        json={"content_item_id": item_id, "social_account_id": acct_id, "scheduled_at": PAST},
        headers=h,
    )
    assert sched.status_code == 201, sched.text
    assert sched.json()["status"] == "pending"

    run = client.post(f"{API}/businesses/{bid}/schedules/run-due", headers=h)
    assert run.status_code == 200, run.text
    assert run.json() == {"due": 1, "published": 1, "failed": 0}

    # Schedule is published; the content item flips to published too.
    published = client.get(f"{API}/businesses/{bid}/schedules", params={"status": "published"}, headers=h).json()
    assert [s["id"] for s in published] == [sched.json()["id"]]
    item = client.get(f"{API}/businesses/{bid}/content/{item_id}", headers=h).json()
    assert item["status"] == "published"


def test_future_schedule_not_published(client):
    h, bid, item_id, acct_id = _setup(client)
    client.post(
        f"{API}/businesses/{bid}/schedules",
        json={"content_item_id": item_id, "social_account_id": acct_id, "scheduled_at": FUTURE},
        headers=h,
    )
    run = client.post(f"{API}/businesses/{bid}/schedules/run-due", headers=h).json()
    assert run == {"due": 0, "published": 0, "failed": 0}


def test_account_connection_status(client):
    h, bid, _, _ = _setup(client, email="status@example.com")
    accts = client.get(f"{API}/businesses/{bid}/integrations/accounts", headers=h).json()
    a = accts[0]
    # Dev mock connector -> connected, but flagged simulated (not a live provider).
    assert a["connection"] == "connected"
    assert a["live"] is False
    assert a["can_publish"] is True
    assert "simulated" in a["detail"].lower()


def test_expired_account_needs_reauth(client):
    import uuid as u
    from datetime import datetime, timedelta, timezone

    from app.core.db import get_db
    from app.services import scheduling_service

    h, bid, _, _ = _setup(client, email="reauth@example.com")
    db = next(client.app.dependency_overrides[get_db]())
    try:
        # Expired token, no refresh token -> can't auto-renew -> reconnect needed.
        scheduling_service.upsert_oauth_account(
            db, business_id=u.UUID(bid), platform="facebook", access_token="old",
            display_name="@fb", expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.commit()
    finally:
        db.close()

    accts = client.get(f"{API}/businesses/{bid}/integrations/accounts", headers=h).json()
    fb = next(a for a in accts if a["platform"] == "facebook")
    assert fb["connection"] == "needs_reauth"


def test_expired_token_is_refreshed(client):
    import uuid as u
    from datetime import datetime, timedelta, timezone

    from app.core.db import get_db
    from app.services import scheduling_service

    h, bid, _, _ = _setup(client, email="refresh@example.com")
    db = next(client.app.dependency_overrides[get_db]())
    try:
        # A connected account whose access token expired an hour ago.
        acct = scheduling_service.upsert_oauth_account(
            db, business_id=u.UUID(bid), platform="facebook",
            access_token="old-token", refresh_token="r1", display_name="@fb",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.commit()
        old_enc = acct.access_token_enc

        token = scheduling_service.ensure_fresh_token(db, acct)
        db.commit()

        # The mock connector mints a new token + a future expiry.
        assert token != "old-token"
        assert acct.access_token_enc != old_enc
        naive_utcnow = datetime.now(timezone.utc).replace(tzinfo=None)
        assert acct.expires_at is not None and acct.expires_at > naive_utcnow
    finally:
        db.close()


def test_reschedule_pending_changes_time_and_account(client):
    h, bid, item_id, acct_id = _setup(client, email="resched@example.com")
    sched = client.post(
        f"{API}/businesses/{bid}/schedules",
        json={"content_item_id": item_id, "social_account_id": acct_id, "scheduled_at": FUTURE},
        headers=h,
    ).json()
    # A second account to move the post to.
    acct2 = client.post(
        f"{API}/businesses/{bid}/integrations/accounts",
        json={"platform": "linkedin", "display_name": "@acme-li"}, headers=h,
    ).json()["id"]

    moved = client.patch(
        f"{API}/businesses/{bid}/schedules/{sched['id']}",
        json={"scheduled_at": "2999-06-06T15:30:00Z", "social_account_id": acct2},
        headers=h,
    )
    assert moved.status_code == 200, moved.text
    data = moved.json()
    assert data["social_account_id"] == acct2
    assert data["scheduled_at"].startswith("2999-06-06")

    # A canceled schedule can't be moved.
    client.post(f"{API}/businesses/{bid}/schedules/{sched['id']}/cancel", headers=h)
    blocked = client.patch(
        f"{API}/businesses/{bid}/schedules/{sched['id']}",
        json={"scheduled_at": FUTURE}, headers=h,
    )
    assert blocked.status_code == 409


def test_repost_reschedules_next(client):
    h, bid, item_id, acct_id = _setup(client)
    client.post(
        f"{API}/businesses/{bid}/schedules",
        json={"content_item_id": item_id, "social_account_id": acct_id,
              "scheduled_at": PAST, "repost_interval_days": 7},
        headers=h,
    )
    client.post(f"{API}/businesses/{bid}/schedules/run-due", headers=h)
    all_sched = client.get(f"{API}/businesses/{bid}/schedules", headers=h).json()
    statuses = sorted(s["status"] for s in all_sched)
    # One published + one freshly-queued repost.
    assert statuses == ["pending", "published"]


def test_cancel_schedule(client):
    h, bid, item_id, acct_id = _setup(client)
    sid = client.post(
        f"{API}/businesses/{bid}/schedules",
        json={"content_item_id": item_id, "social_account_id": acct_id, "scheduled_at": FUTURE},
        headers=h,
    ).json()["id"]
    canceled = client.post(f"{API}/businesses/{bid}/schedules/{sid}/cancel", headers=h)
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"
    # Canceled schedules are never published.
    assert client.post(f"{API}/businesses/{bid}/schedules/run-due", headers=h).json()["published"] == 0


def test_bulk_schedule(client):
    h, bid, item_id, acct_id = _setup(client)
    r = client.post(
        f"{API}/businesses/{bid}/schedules/bulk",
        json={"items": [
            {"content_item_id": item_id, "social_account_id": acct_id, "scheduled_at": FUTURE},
            {"content_item_id": item_id, "social_account_id": acct_id, "scheduled_at": PAST},
        ]},
        headers=h,
    )
    assert r.status_code == 201
    assert len(r.json()) == 2


def test_scheduling_rbac_and_isolation(client):
    owner_h, bid, item_id, acct_id = _setup(client, email="o@example.com")
    # A viewer can't connect accounts or schedule.
    client.post(f"{API}/auth/signup", json={"email": "v@example.com", "password": "password123"})
    client.post(f"{API}/businesses/{bid}/members", json={"email": "v@example.com", "role": "viewer"}, headers=owner_h)
    v_h = {"Authorization": "Bearer " + client.post(
        f"{API}/auth/login", json={"email": "v@example.com", "password": "password123"}
    ).json()["access_token"]}
    assert client.post(f"{API}/businesses/{bid}/integrations/accounts",
                       json={"platform": "x", "display_name": "@x"}, headers=v_h).status_code == 403

    # A different tenant can't see these schedules at all.
    other_h, *_ = _setup(client, email="other@example.com")
    assert client.get(f"{API}/businesses/{bid}/schedules", headers=other_h).status_code == 404
