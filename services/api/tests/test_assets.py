"""Product-image uploads + product-grounded image generation."""
from __future__ import annotations

import io

API = "/api/v1"

# Minimal valid 1x1 PNG.
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)


def _owner(client, email="asset@example.com"):
    tokens = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bid = client.post(f"{API}/businesses", json={"name": "Acme Coffee"}, headers=h).json()["id"]
    return h, bid


def _upload(client, h, bid, name="product.png", ctype="image/png", data=_PNG):
    return client.post(
        f"{API}/businesses/{bid}/assets",
        files={"file": (name, io.BytesIO(data), ctype)},
        headers=h,
    )


def test_upload_list_delete_asset(client):
    h, bid = _owner(client)
    r = _upload(client, h, bid)
    assert r.status_code == 201, r.text
    asset = r.json()
    assert asset["url"].startswith("/media/")
    assert asset["kind"] == "product_image"

    listed = client.get(f"{API}/businesses/{bid}/assets", headers=h).json()
    assert len(listed) == 1

    assert client.delete(f"{API}/businesses/{bid}/assets/{asset['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/businesses/{bid}/assets", headers=h).json() == []


def test_reject_non_image_upload(client):
    h, bid = _owner(client, email="asset2@example.com")
    r = _upload(client, h, bid, name="notes.txt", ctype="text/plain", data=b"hello")
    assert r.status_code == 400


def test_generate_image_grounded_on_product(client):
    h, bid = _owner(client, email="asset3@example.com")
    aid = _upload(client, h, bid).json()["id"]
    item = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "showcase our beans"}, headers=h,
    ).json()

    # Ground the generated image on the uploaded product.
    r = client.post(
        f"{API}/businesses/{bid}/content/{item['id']}/image",
        params={"asset_id": aid}, headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["image_url"].startswith("/media/")

    # A bad asset id 404s.
    import uuid
    bad = client.post(
        f"{API}/businesses/{bid}/content/{item['id']}/image",
        params={"asset_id": str(uuid.uuid4())}, headers=h,
    )
    assert bad.status_code == 404


def test_assets_rbac_and_isolation(client):
    owner_h, bid = _owner(client, email="assetowner@example.com")
    _upload(client, owner_h, bid)

    # Viewer can list but not upload.
    client.post(f"{API}/auth/signup", json={"email": "assetviewer@example.com", "password": "password123"})
    client.post(
        f"{API}/businesses/{bid}/members",
        json={"email": "assetviewer@example.com", "role": "viewer"}, headers=owner_h,
    )
    viewer_h = {"Authorization": "Bearer " + client.post(
        f"{API}/auth/login", json={"email": "assetviewer@example.com", "password": "password123"}
    ).json()["access_token"]}
    assert client.get(f"{API}/businesses/{bid}/assets", headers=viewer_h).status_code == 200
    assert _upload(client, viewer_h, bid).status_code == 403

    # Other tenant can't see these assets.
    other_h, _ = _owner(client, email="assetother@example.com")
    assert client.get(f"{API}/businesses/{bid}/assets", headers=other_h).status_code == 404
