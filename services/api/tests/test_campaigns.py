"""Campaigns + autopilot: propose (approve-first) → approve → schedules; RBAC; cadence."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import campaign_service
from app.ai.router import AIRouter
from app.ai.providers.mock import MockProvider

API = "/api/v1"


def _owner(client, email="camp@example.com"):
    tokens = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bid = client.post(
        f"{API}/businesses", json={"name": "Acme Coffee", "tone": "warm", "goals": "grow foot traffic"},
        headers=h,
    ).json()["id"]
    return h, bid


def _connect(client, h, bid, platform):
    client.post(
        f"{API}/businesses/{bid}/integrations/accounts",
        json={"platform": platform, "display_name": f"@{platform}"}, headers=h,
    )


def test_propose_drafts_but_does_not_schedule(client):
    h, bid = _owner(client)
    r = client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "Fall seasonal menu launch", "timeframe": "week"}, headers=h,
    )
    assert r.status_code == 201, r.text
    camp = r.json()
    assert camp["status"] == "proposed"
    assert camp["source"] == "manual"
    assert len(camp["items"]) == 15  # 3 posting days × 5 platforms (all channels)
    # Each item has generated content...
    assert all(i["body"] for i in camp["items"])
    # ...but nothing is scheduled yet (approve-first).
    assert client.get(f"{API}/businesses/{bid}/schedules", headers=h).json() == []


def test_day_campaign_is_one_post_per_platform(client):
    h, bid = _owner(client, email="campday@example.com")
    r = client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "Flash sale today", "timeframe": "day"}, headers=h,
    )
    assert r.status_code == 201, r.text
    camp = r.json()
    assert camp["timeframe"] == "day"
    # One unique post per rotation platform, all dated today.
    assert len(camp["items"]) == 5
    dates = {i["scheduled_at"][:10] for i in camp["items"]}
    assert len(dates) == 1  # same day
    channels = {i["channel"] for i in camp["items"]}
    assert len(channels) == 5  # one per platform


def test_product_grounds_the_campaign(client):
    import io
    h, bid = _owner(client, email="campprod@example.com")
    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c6360000002000100ffff03000006000557bfabd400"
        "00000049454e44ae426082"
    )
    asset = client.post(
        f"{API}/businesses/{bid}/assets",
        files={"file": ("beans.png", io.BytesIO(png), "image/png")},
        data={"name": "Ethiopia Single-Origin", "description": "Bright citrusy light roast"},
        headers=h,
    ).json()
    assert asset["name"] == "Ethiopia Single-Origin"
    assert "citrusy" in asset["description"]

    camp = client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "Promote our beans", "timeframe": "day",
              "product_asset_id": asset["id"]}, headers=h,
    ).json()
    # The mock echoes the brief, so the product name/description reach the copy.
    assert any("Ethiopia Single-Origin" in i["body"] for i in camp["items"])

    # Bad product id 404s.
    import uuid
    assert client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "x", "timeframe": "day", "product_asset_id": str(uuid.uuid4())},
        headers=h,
    ).status_code == 404


def test_campaign_calendar_lists_dated_posts(client):
    h, bid = _owner(client, email="campcal@example.com")
    client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "Week plan", "timeframe": "week"}, headers=h,
    )
    cal = client.get(f"{API}/businesses/{bid}/campaigns/calendar", headers=h)
    assert cal.status_code == 200, cal.text
    entries = cal.json()
    assert len(entries) == 15  # 3 posting days × 5 platforms
    e = entries[0]
    assert e["campaign_name"] == "Week plan"
    assert e["channel"] and e["scheduled_at"] and e["body"]
    # content_item_id lets the calendar open the post for editing.
    assert e["content_item_id"]


def test_reject_deletes_post_and_calendar_entry(client):
    h, bid = _owner(client, email="del@example.com")
    camp = client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "Del", "timeframe": "day"}, headers=h,
    ).json()
    cid = camp["items"][0]["content_item_id"]
    assert cid
    cal = client.get(f"{API}/businesses/{bid}/campaigns/calendar", headers=h).json()
    assert any(e["content_item_id"] == cid for e in cal)

    # Reject == delete: gone from the library and the calendar.
    assert client.delete(f"{API}/businesses/{bid}/content/{cid}", headers=h).status_code == 204
    assert client.get(f"{API}/businesses/{bid}/content/{cid}", headers=h).status_code == 404
    cal2 = client.get(f"{API}/businesses/{bid}/campaigns/calendar", headers=h).json()
    assert not any(e["content_item_id"] == cid for e in cal2)


def test_approve_books_post_on_calendar(client):
    h, bid = _owner(client, email="book@example.com")
    _connect(client, h, bid, "instagram")
    camp = client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "Book", "timeframe": "day"}, headers=h,
    ).json()
    ig = next(i for i in camp["items"] if i["channel"] == "instagram")
    cid = ig["content_item_id"]

    r = client.post(f"{API}/businesses/{bid}/content/{cid}/approve", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # A real schedule now exists (instagram is connected)...
    scheds = client.get(f"{API}/businesses/{bid}/schedules", headers=h).json()
    assert any(s["content_item_id"] == cid for s in scheds)
    # ...and the calendar slot is booked (scheduled, not proposed).
    cal = client.get(f"{API}/businesses/{bid}/campaigns/calendar", headers=h).json()
    entry = next(e for e in cal if e["content_item_id"] == cid)
    assert entry["status"] == "scheduled"


def test_campaign_targets_only_connected_platforms(client):
    h, bid = _owner(client, email="camp2@example.com")
    # The studio learns which platforms are connected and generates only for those.
    _connect(client, h, bid, "instagram")
    _connect(client, h, bid, "linkedin")

    camp = client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "Launch week", "timeframe": "week"}, headers=h,
    ).json()

    channels = {i["channel"] for i in camp["items"]}
    assert channels == {"instagram", "linkedin"}  # only the connected platforms
    assert len(camp["items"]) == 6  # 2 connected channels × 3 posting days

    approved = client.post(
        f"{API}/businesses/{bid}/campaigns/{camp['id']}/approve", headers=h
    ).json()
    assert approved["status"] == "scheduled"
    # Every generated post is for a connected channel, so all get scheduled.
    assert all(i["status"] == "scheduled" for i in approved["items"])

    scheds = client.get(f"{API}/businesses/{bid}/schedules", headers=h).json()
    assert len(scheds) == 6
    assert all(s["status"] == "pending" for s in scheds)


def test_reject_leaves_nothing_scheduled(client):
    h, bid = _owner(client, email="camp3@example.com")
    _connect(client, h, bid, "instagram")
    camp = client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "x", "timeframe": "week"}, headers=h,
    ).json()
    rej = client.post(f"{API}/businesses/{bid}/campaigns/{camp['id']}/reject", headers=h).json()
    assert rej["status"] == "rejected"
    # Can't approve a rejected campaign.
    assert client.post(
        f"{API}/businesses/{bid}/campaigns/{camp['id']}/approve", headers=h
    ).status_code == 409
    assert client.get(f"{API}/businesses/{bid}/schedules", headers=h).json() == []


def test_autopilot_config_and_run(client):
    h, bid = _owner(client, email="camp4@example.com")
    # Enable autopilot.
    cfg = client.put(
        f"{API}/businesses/{bid}/autopilot",
        json={"autopilot_enabled": True, "autopilot_theme": "weekly specials",
              "autopilot_frequency_days": 7, "autopilot_timeframe": "week"},
        headers=h,
    )
    assert cfg.status_code == 200
    assert cfg.json()["autopilot_enabled"] is True

    # Run the autopilot engine directly (as the beat task would).
    from app.core.db import get_db  # use the same overridden session
    db = next(client.app.dependency_overrides[get_db]())
    try:
        first = campaign_service.run_autopilot(db, router=AIRouter(MockProvider()))
        db.commit()
        assert first["proposed"] == 1  # one due tenant proposed
        # Immediately running again: cadence not elapsed -> nothing proposed.
        second = campaign_service.run_autopilot(db, router=AIRouter(MockProvider()))
        db.commit()
        assert second["proposed"] == 0
    finally:
        db.close()

    # The proposed campaign is waiting for approval, tagged autopilot.
    camps = client.get(
        f"{API}/businesses/{bid}/campaigns", params={"status": "proposed"}, headers=h
    ).json()
    assert len(camps) == 1
    assert camps[0]["source"] == "autopilot"


def test_autopilot_skips_disabled_and_not_due(client):
    h, bid = _owner(client, email="camp5@example.com")
    # Disabled by default -> not eligible.
    from app.core.db import get_db
    db = next(client.app.dependency_overrides[get_db]())
    try:
        result = campaign_service.run_autopilot(db, router=AIRouter(MockProvider()))
        db.commit()
        assert result["proposed"] == 0
    finally:
        db.close()


def test_campaign_rbac(client):
    owner_h, bid = _owner(client, email="campowner@example.com")
    client.post(f"{API}/auth/signup", json={"email": "campviewer@example.com", "password": "password123"})
    client.post(
        f"{API}/businesses/{bid}/members",
        json={"email": "campviewer@example.com", "role": "viewer"}, headers=owner_h,
    )
    viewer_h = {"Authorization": "Bearer " + client.post(
        f"{API}/auth/login", json={"email": "campviewer@example.com", "password": "password123"}
    ).json()["access_token"]}

    # Viewer can list but not propose or change autopilot.
    assert client.get(f"{API}/businesses/{bid}/campaigns", headers=viewer_h).status_code == 200
    assert client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "x", "timeframe": "week"}, headers=viewer_h,
    ).status_code == 403
    assert client.put(
        f"{API}/businesses/{bid}/autopilot",
        json={"autopilot_enabled": True, "autopilot_frequency_days": 7, "autopilot_timeframe": "week"},
        headers=viewer_h,
    ).status_code == 403
