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
