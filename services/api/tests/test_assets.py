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
    assert asset["kind"] == "product"

    listed = client.get(f"{API}/businesses/{bid}/assets", headers=h).json()
    assert len(listed) == 1

    assert client.delete(f"{API}/businesses/{bid}/assets/{asset['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/businesses/{bid}/assets", headers=h).json() == []


def test_service_asset_needs_no_photo(client):
    h, bid = _owner(client, email="svc@example.com")

    # A service is described in copy — no file required.
    r = client.post(
        f"{API}/businesses/{bid}/assets",
        data={"kind": "service", "name": "Gutter Cleaning",
              "description": "Full-home gutter clearing + inspection. $149 flat."},
        headers=h,
    )
    assert r.status_code == 201, r.text
    asset = r.json()
    assert asset["kind"] == "service"
    assert asset["url"] is None
    assert asset["name"] == "Gutter Cleaning"

    # A product still requires a photo.
    bad = client.post(
        f"{API}/businesses/{bid}/assets",
        data={"kind": "product", "name": "No photo"},
        headers=h,
    )
    assert bad.status_code == 400

    # An empty service (no name/description) is rejected.
    empty = client.post(
        f"{API}/businesses/{bid}/assets", data={"kind": "service"}, headers=h
    )
    assert empty.status_code == 400


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


def test_service_image_is_a_poster(client):
    h, bid = _owner(client, email="svcimg@example.com")
    # A photo-less service.
    aid = client.post(
        f"{API}/businesses/{bid}/assets",
        data={"kind": "service", "name": "Gutter Cleaning",
              "description": "Same-week gutter clearing. Flat $149."},
        headers=h,
    ).json()["id"]
    item = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "promote gutter cleaning"}, headers=h,
    ).json()

    r = client.post(
        f"{API}/businesses/{bid}/content/{item['id']}/image",
        params={"asset_id": aid}, headers=h,
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["image_url"].startswith("/media/")
    # The service is marketed as a designed poster, not a plain product photo.
    assert "POSTER" in (out["image_prompt"] or "")


def test_generate_flyer_for_service(client):
    h, bid = _owner(client, email="flyer@example.com")
    aid = client.post(
        f"{API}/businesses/{bid}/assets",
        data={"kind": "service", "name": "Lawn Care",
              "description": "Weekly mow, edge & blow. $60/visit."},
        headers=h,
    ).json()["id"]

    # No image yet.
    assert client.get(f"{API}/businesses/{bid}/assets", headers=h).json()[0]["url"] is None

    r = client.post(f"{API}/businesses/{bid}/assets/{aid}/flyer", headers=h)
    assert r.status_code == 200, r.text
    flyer = r.json()
    assert flyer["kind"] == "service"
    assert flyer["url"].startswith("/media/")

    # Persisted on the asset.
    assert client.get(f"{API}/businesses/{bid}/assets", headers=h).json()[0]["url"] == flyer["url"]


def test_service_flyer_is_reused_across_campaign(client):
    h, bid = _owner(client, email="reuse@example.com")
    aid = client.post(
        f"{API}/businesses/{bid}/assets",
        data={"kind": "service", "name": "House Painting",
              "description": "Interior + exterior. Free color consult."},
        headers=h,
    ).json()["id"]
    flyer_url = client.post(f"{API}/businesses/{bid}/assets/{aid}/flyer", headers=h).json()["url"]

    camp = client.post(
        f"{API}/businesses/{bid}/campaigns/propose",
        json={"theme": "Spring painting special", "timeframe": "week", "product_asset_id": aid},
        headers=h,
    )
    assert camp.status_code == 201, camp.text
    items = camp.json()["items"]
    assert len(items) > 1
    # Every platform's post carries the EXACT same generated flyer.
    assert all(it["image_url"] == flyer_url for it in items)


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
