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


def test_model_tiering_routes_cheap_types_to_cheap_model(client):
    h, bid = _owner(client, email="tiering@example.com")

    def gen(content_type):
        return client.post(
            f"{API}/businesses/{bid}/content/generate",
            json={"channel": "instagram", "content_type": content_type, "brief": "Fall sale"},
            headers=h,
        ).json()

    # Cheap, short types route to the cheap tier (Haiku by default).
    for ct in ("hashtags", "sms", "captions", "cta"):
        assert gen(ct)["meta"]["model"] == "claude-haiku-4-5", ct

    # High-value content stays on the default model (the mock's default id here).
    for ct in ("social_post", "blog_article", "email"):
        assert gen(ct)["meta"]["model"] != "claude-haiku-4-5", ct


def test_generate_image_sets_image_url(client):
    h, bid = _owner(client, email="image@example.com")
    item = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "Autumn latte launch"}, headers=h,
    ).json()
    assert item["image_url"] is None

    r = client.post(f"{API}/businesses/{bid}/content/{item['id']}/image", headers=h)
    assert r.status_code == 200, r.text
    updated = r.json()
    # Image is stored via the storage layer and served under /media; prompt stored too.
    assert updated["image_url"].startswith("/media/")
    assert "Acme Coffee" in updated["image_prompt"]


def test_approved_posts_become_brand_examples(client):
    """Approving a post makes it a brand exemplar for future generations (learning)."""
    import uuid
    from app.core.db import get_db
    from app.services import rag_service

    h, bid = _owner(client, email="learn@example.com")
    gen = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "Signature line: cozy autumn vibes"},
        headers=h,
    ).json()

    db = next(client.app.dependency_overrides[get_db]())
    try:
        # Draft (unapproved) content is NOT used as an exemplar.
        assert rag_service.approved_examples(db, uuid.UUID(bid)) == []
    finally:
        db.close()

    client.post(f"{API}/businesses/{bid}/content/{gen['id']}/approve", headers=h)

    db = next(client.app.dependency_overrides[get_db]())
    try:
        examples = rag_service.approved_examples(db, uuid.UUID(bid), channel="instagram")
        # The mock echoes the brief into the body, so the phrase surfaces as an exemplar.
        assert any("cozy autumn vibes" in e for e in examples)
    finally:
        db.close()


def test_image_quota_guard(client):
    import uuid as u
    from app.core.db import get_db
    from app.models.business import Business

    h, bid = _owner(client, email="imgquota@example.com")
    item = client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "Latte art"}, headers=h,
    ).json()

    db = next(client.app.dependency_overrides[get_db]())
    try:
        db.get(Business, u.UUID(bid)).plan.image_monthly_quota = 1
        db.commit()
    finally:
        db.close()

    assert client.get(f"{API}/businesses/{bid}/content/image-quota", headers=h).json() == {
        "used": 0, "limit": 1, "remaining": 1, "unlimited": False,
    }
    # First image allowed; the second is blocked by the image cost guard.
    assert client.post(f"{API}/businesses/{bid}/content/{item['id']}/image", headers=h).status_code == 200
    assert client.post(f"{API}/businesses/{bid}/content/{item['id']}/image", headers=h).status_code == 402
    # Images meter separately — they don't burn the text/content quota.
    q = client.get(f"{API}/businesses/{bid}/content/image-quota", headers=h).json()
    assert q["used"] == 1 and q["remaining"] == 0


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
