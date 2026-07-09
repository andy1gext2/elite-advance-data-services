"""Phase 3: AI content-calendar planning."""
from __future__ import annotations

API = "/api/v1"


def _owner(client, email="cal@example.com"):
    tokens = client.post(f"{API}/auth/signup", json={"email": email, "password": "password123"}).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bid = client.post(f"{API}/businesses", json={"name": "Acme Co", "tone": "warm"}, headers=h).json()["id"]
    return h, bid


def test_month_plan_has_slots_with_timing(client):
    h, bid = _owner(client)
    r = client.post(
        f"{API}/businesses/{bid}/calendar/plan",
        json={"timeframe": "month", "theme": "promote our loyalty program"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["timeframe"] == "month"
    assert len(data["slots"]) == 8
    slot = data["slots"][0]
    assert slot["channel"] and slot["recommended_time"] and slot["topic"]
    # Recommended time is a HH:MM heuristic.
    assert ":" in slot["recommended_time"]


def test_week_plan_is_shorter(client):
    h, bid = _owner(client, email="cal2@example.com")
    data = client.post(
        f"{API}/businesses/{bid}/calendar/plan",
        json={"timeframe": "week", "theme": "grand opening"}, headers=h,
    ).json()
    assert len(data["slots"]) == 3


def _slot_body(channel="instagram"):
    return {
        "channel": channel,
        "content_type": "social_post",
        "topic": "Behind-the-scenes of our new autumn blend",
        "scheduled_at": "2026-08-01T11:00:00+00:00",
    }


def test_schedule_slot_bridges_to_a_scheduled_post(client):
    h, bid = _owner(client, email="cal3@example.com")
    # Connect a matching account so the slot can be auto-scheduled onto it.
    client.post(
        f"{API}/businesses/{bid}/integrations/accounts",
        json={"platform": "instagram", "display_name": "@acme"}, headers=h,
    )

    r = client.post(
        f"{API}/businesses/{bid}/calendar/schedule-slot", json=_slot_body(), headers=h
    )
    assert r.status_code == 201, r.text
    data = r.json()
    # It generated a real content item for the channel...
    assert data["content_item"]["channel"] == "instagram"
    assert "autumn blend" in data["content_item"]["body"]
    # ...and scheduled it (pending, linked to the same content item).
    assert data["schedule"]["status"] == "pending"
    assert data["schedule"]["content_item_id"] == data["content_item"]["id"]

    # It now shows up on the schedule list.
    scheds = client.get(f"{API}/businesses/{bid}/schedules", headers=h).json()
    assert any(s["id"] == data["schedule"]["id"] for s in scheds)


def test_schedule_slot_requires_a_connected_account(client):
    h, bid = _owner(client, email="cal4@example.com")
    # No account connected for this channel -> a helpful 400.
    r = client.post(
        f"{API}/businesses/{bid}/calendar/schedule-slot", json=_slot_body("linkedin"), headers=h
    )
    assert r.status_code == 400
    assert "linkedin" in r.json()["detail"].lower()
