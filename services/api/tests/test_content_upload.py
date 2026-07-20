"""Post the owner's own media to every connected platform, scheduled 1 day out."""
from __future__ import annotations

import io

API = "/api/v1"

_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)


def _owner(client, email="upload@example.com"):
    tokens = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bid = client.post(f"{API}/businesses", json={"name": "Acme"}, headers=h).json()["id"]
    return h, bid


def _connect(client, h, bid, platform):
    client.post(
        f"{API}/businesses/{bid}/integrations/accounts",
        json={"platform": platform, "display_name": f"@acme-{platform}"}, headers=h,
    )


def test_upload_posts_to_all_connected_platforms(client):
    h, bid = _owner(client)
    _connect(client, h, bid, "instagram")
    _connect(client, h, bid, "facebook")

    r = client.post(
        f"{API}/businesses/{bid}/content/upload",
        files={"file": ("photo.png", io.BytesIO(_PNG), "image/png")},
        data={"caption": "Our own photo"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    items = r.json()
    # One post per connected platform, all with the same uploaded media + caption.
    assert {i["channel"] for i in items} == {"instagram", "facebook"}
    assert all(i["status"] == "scheduled" for i in items)
    assert all(i["image_url"] and i["image_url"].startswith("/media/") for i in items)
    assert all(i["body"] == "Our own photo" for i in items)

    # Each post is scheduled (posts show up on the Schedule tab).
    schedules = client.get(f"{API}/businesses/{bid}/schedules", headers=h).json()
    assert len(schedules) == 2


def test_upload_requires_a_connected_account(client):
    h, bid = _owner(client, email="upload2@example.com")
    r = client.post(
        f"{API}/businesses/{bid}/content/upload",
        files={"file": ("photo.png", io.BytesIO(_PNG), "image/png")},
        headers=h,
    )
    assert r.status_code == 400, r.text
    assert "connect" in r.json()["detail"].lower()


def test_upload_rejects_unsupported_type(client):
    h, bid = _owner(client, email="upload3@example.com")
    _connect(client, h, bid, "instagram")
    r = client.post(
        f"{API}/businesses/{bid}/content/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hi"), "text/plain")},
        headers=h,
    )
    assert r.status_code == 400, r.text
