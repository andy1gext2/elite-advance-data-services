"""Async video generation: start a job, poll it, get a stored clip. RBAC + isolation."""
from __future__ import annotations

API = "/api/v1"


def _owner(client, email="video@example.com"):
    tokens = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bid = client.post(f"{API}/businesses", json={"name": "Acme Co"}, headers=h).json()["id"]
    item = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "New winter menu"}, headers=h,
    ).json()
    return h, bid, item["id"]


def test_start_then_poll_produces_a_video(client):
    h, bid, item_id = _owner(client)

    started = client.post(f"{API}/businesses/{bid}/content/{item_id}/video", headers=h)
    assert started.status_code == 202, started.text
    job = started.json()
    assert job["status"] == "processing"
    assert job["content_item_id"] == item_id
    # Claude wrote an 8-second shot brief that Veo renders from.
    assert job["prompt"] and job["prompt"].strip()

    # Poll — the mock renders instantly and stores the clip.
    polled = client.get(f"{API}/businesses/{bid}/content/{item_id}/video", headers=h)
    assert polled.status_code == 200, polled.text
    done = polled.json()
    assert done["status"] == "succeeded"
    assert done["video_url"].startswith("/media/")

    # The content item now carries the video_url.
    item = client.get(f"{API}/businesses/{bid}/content/{item_id}", headers=h).json()
    assert item["video_url"] == done["video_url"]


def test_video_quota_guard(client):
    import uuid as u
    from app.core.db import get_db
    from app.models.business import Business

    h, bid, item_id = _owner(client, email="videoquota@example.com")

    # Tighten this tenant's plan to a single render this month.
    db = next(client.app.dependency_overrides[get_db]())
    try:
        biz = db.get(Business, u.UUID(bid))
        biz.plan.video_monthly_quota = 1
        db.commit()
    finally:
        db.close()

    assert client.get(f"{API}/businesses/{bid}/content/video-quota", headers=h).json() == {
        "used": 0, "limit": 1, "remaining": 1, "unlimited": False, "credits": 0,
    }

    # First render allowed; the second is blocked by the cost guard.
    assert client.post(f"{API}/businesses/{bid}/content/{item_id}/video", headers=h).status_code == 202
    assert client.post(f"{API}/businesses/{bid}/content/{item_id}/video", headers=h).status_code == 402

    q = client.get(f"{API}/businesses/{bid}/content/video-quota", headers=h).json()
    assert q["used"] == 1 and q["remaining"] == 0


def test_video_credits_overflow_past_monthly_quota(client):
    import uuid as u
    from app.core.db import get_db
    from app.models.business import Business

    h, bid, item_id = _owner(client, email="videocredits@example.com")
    db = next(client.app.dependency_overrides[get_db]())
    try:
        biz = db.get(Business, u.UUID(bid))
        biz.plan.video_monthly_quota = 1
        biz.video_credits = 0
        db.commit()
    finally:
        db.close()

    V = f"{API}/businesses/{bid}/content/{item_id}/video"
    # 1 monthly render, then blocked (no credits).
    assert client.post(V, headers=h).status_code == 202
    assert client.post(V, headers=h).status_code == 402

    # Buy 2 credits (billing placeholder), then renders overflow onto credits.
    bought = client.post(f"{API}/businesses/{bid}/content/video-credits", json={"quantity": 2}, headers=h)
    assert bought.status_code == 200, bought.text
    assert bought.json()["credits"] == 2

    assert client.post(V, headers=h).status_code == 202  # spends 1 credit
    assert client.get(f"{API}/businesses/{bid}/content/video-quota", headers=h).json()["credits"] == 1


def test_preview_and_render_edited_vision(client):
    h, bid, item_id = _owner(client, email="videoscript@example.com")

    # Preview the AI vision (no render, no quota use).
    s = client.post(f"{API}/businesses/{bid}/content/{item_id}/video/script", headers=h)
    assert s.status_code == 200, s.text
    assert s.json()["prompt"].strip()

    # Render with an EDITED vision — it's used verbatim.
    edited = "A neon city skyline at dusk, slow cinematic dolly toward the storefront."
    started = client.post(
        f"{API}/businesses/{bid}/content/{item_id}/video", json={"prompt": edited}, headers=h
    )
    assert started.status_code == 202, started.text
    assert started.json()["prompt"] == edited

    done = client.get(f"{API}/businesses/{bid}/content/{item_id}/video", headers=h).json()
    assert done["status"] == "succeeded"


def test_poll_without_a_job_404s(client):
    h, bid, item_id = _owner(client, email="video2@example.com")
    assert client.get(f"{API}/businesses/{bid}/content/{item_id}/video", headers=h).status_code == 404


def test_video_rbac_and_isolation(client):
    owner_h, bid, item_id = _owner(client, email="videoowner@example.com")

    # Viewer can't start a render.
    client.post(f"{API}/auth/signup", json={"email": "videoviewer@example.com", "password": "password123"})
    client.post(
        f"{API}/businesses/{bid}/members",
        json={"email": "videoviewer@example.com", "role": "viewer"}, headers=owner_h,
    )
    viewer_h = {"Authorization": "Bearer " + client.post(
        f"{API}/auth/login", json={"email": "videoviewer@example.com", "password": "password123"}
    ).json()["access_token"]}
    assert client.post(
        f"{API}/businesses/{bid}/content/{item_id}/video", headers=viewer_h
    ).status_code == 403

    # Other tenant can't touch this business's content.
    other_h, _, _ = _owner(client, email="videoother@example.com")
    assert client.post(
        f"{API}/businesses/{bid}/content/{item_id}/video", headers=other_h
    ).status_code == 404
