"""Brand logo upload/remove on a business."""
from __future__ import annotations

import io

API = "/api/v1"

# Minimal valid 1x1 PNG.
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)


def _owner(client, email="logo@example.com"):
    tokens = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bid = client.post(f"{API}/businesses", json={"name": "Acme"}, headers=h).json()["id"]
    return h, bid


def test_upload_and_remove_logo(client):
    h, bid = _owner(client)

    # No logo initially.
    assert client.get(f"{API}/businesses/{bid}", headers=h).json()["logo_url"] is None

    r = client.post(
        f"{API}/businesses/{bid}/logo",
        files={"file": ("logo.png", io.BytesIO(_PNG), "image/png")},
        headers=h,
    )
    assert r.status_code == 200, r.text
    url = r.json()["logo_url"]
    assert url and url.startswith("/media/")
    # Persisted on the business.
    assert client.get(f"{API}/businesses/{bid}", headers=h).json()["logo_url"] == url

    # Remove it.
    r = client.delete(f"{API}/businesses/{bid}/logo", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["logo_url"] is None


def test_logo_rejects_non_image(client):
    h, bid = _owner(client, email="logo2@example.com")
    r = client.post(
        f"{API}/businesses/{bid}/logo",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=h,
    )
    assert r.status_code == 400, r.text
