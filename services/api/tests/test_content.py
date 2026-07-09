"""Phase 2: content generation, repurposing, RBAC, tenant isolation, quota gating."""
from __future__ import annotations

API = "/api/v1"


def _owner(client, email="creator@example.com"):
    tokens = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    biz = client.post(
        f"{API}/businesses",
        json={"name": "Acme Coffee", "industry": "Cafe", "tone": "warm",
              "brand_voice": "friendly local roaster", "target_audience": "commuters"},
        headers=h,
    ).json()
    return h, biz["id"]


def test_generate_single_post(client):
    h, bid = _owner(client)
    r = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "content_type": "social_post",
              "brief": "Announce our new autumn pumpkin latte"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["channel"] == "instagram"
    assert item["status"] == "draft"
    # Mock provider echoes brand + brief, proving RAG context reached the model.
    assert "Acme Coffee" in item["body"]
    assert "pumpkin latte" in item["body"]
    assert item["meta"]["provider"] == "mock"


def test_repurpose_creates_platform_variants(client):
    h, bid = _owner(client)
    r = client.post(
        f"{API}/businesses/{bid}/content/repurpose",
        json={"idea": "Weekend buy-one-get-one on all pastries"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["idea"]["brief"].startswith("Weekend")
    items = data["items"]
    assert len(items) == 12  # full default pipeline
    channels = {i["channel"] for i in items}
    assert {"instagram", "linkedin", "x", "blog", "email", "sms"} <= channels
    # Every variant is linked back to the idea.
    assert all(i["idea_id"] == data["idea"]["id"] for i in items)


def test_list_and_approve_flow(client):
    h, bid = _owner(client)
    gen = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "facebook", "brief": "Grand reopening this Friday"},
        headers=h,
    ).json()

    listing = client.get(f"{API}/businesses/{bid}/content", headers=h)
    assert listing.status_code == 200
    assert any(i["id"] == gen["id"] for i in listing.json())

    approved = client.post(
        f"{API}/businesses/{bid}/content/{gen['id']}/approve", headers=h
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    # Filter by status reflects the change.
    only_approved = client.get(
        f"{API}/businesses/{bid}/content", params={"status": "approved"}, headers=h
    ).json()
    assert {i["id"] for i in only_approved} == {gen["id"]}


def test_edit_reverts_approved_item_to_draft(client):
    h, bid = _owner(client, email="editor2@example.com")
    gen = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "Fall menu is here"},
        headers=h,
    ).json()

    # Approve it, then edit the copy.
    client.post(f"{API}/businesses/{bid}/content/{gen['id']}/approve", headers=h)
    edited = client.patch(
        f"{API}/businesses/{bid}/content/{gen['id']}",
        json={"title": "Fall Menu", "body": "Our new fall menu just dropped ☕"},
        headers=h,
    )
    assert edited.status_code == 200, edited.text
    data = edited.json()
    assert data["title"] == "Fall Menu"
    assert data["body"] == "Our new fall menu just dropped ☕"
    # Editing a reviewed item sends it back through review.
    assert data["status"] == "draft"


def test_edit_requires_a_field_and_editor_role(client):
    owner_h, bid = _owner(client, email="owner4@example.com")
    gen = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "x", "brief": "hello world"}, headers=owner_h,
    ).json()

    # Empty payload is rejected (must provide title or body).
    assert client.patch(
        f"{API}/businesses/{bid}/content/{gen['id']}", json={}, headers=owner_h
    ).status_code == 422

    # A viewer cannot edit.
    client.post(f"{API}/auth/signup", json={"email": "viewer2@example.com", "password": "password123"})
    client.post(
        f"{API}/businesses/{bid}/members",
        json={"email": "viewer2@example.com", "role": "viewer"}, headers=owner_h,
    )
    viewer_h = {"Authorization": "Bearer " + client.post(
        f"{API}/auth/login", json={"email": "viewer2@example.com", "password": "password123"}
    ).json()["access_token"]}
    blocked = client.patch(
        f"{API}/businesses/{bid}/content/{gen['id']}",
        json={"body": "sneaky edit"}, headers=viewer_h,
    )
    assert blocked.status_code == 403


def test_viewer_cannot_generate_but_can_read(client):
    owner_h, bid = _owner(client, email="owner3@example.com")
    # Add a viewer to the business.
    client.post(f"{API}/auth/signup", json={"email": "viewer@example.com", "password": "password123"})
    client.post(
        f"{API}/businesses/{bid}/members",
        json={"email": "viewer@example.com", "role": "viewer"}, headers=owner_h,
    )
    viewer_h = {"Authorization": "Bearer " + client.post(
        f"{API}/auth/login", json={"email": "viewer@example.com", "password": "password123"}
    ).json()["access_token"]}

    # Viewer is blocked from generating (needs editor+)...
    blocked = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "x", "brief": "hi"}, headers=viewer_h,
    )
    assert blocked.status_code == 403
    # ...but can read.
    assert client.get(f"{API}/businesses/{bid}/content", headers=viewer_h).status_code == 200


def test_content_is_tenant_isolated(client):
    h1, bid1 = _owner(client, email="t1@example.com")
    h2, _ = _owner(client, email="t2@example.com")
    client.post(
        f"{API}/businesses/{bid1}/content/generate",
        json={"channel": "instagram", "brief": "secret sauce"}, headers=h1,
    )
    # A different tenant can't even see business 1's content endpoint (404).
    assert client.get(f"{API}/businesses/{bid1}/content", headers=h2).status_code == 404
