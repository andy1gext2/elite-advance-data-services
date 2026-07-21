"""Account self-service: profile edit, password change, data export, deletion."""
from __future__ import annotations

API = "/api/v1"


def _signup(client, email, password="password123", name="Owner"):
    r = client.post(f"{API}/auth/signup", json={"email": email, "password": password, "full_name": name})
    assert r.status_code == 201, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_update_profile(client):
    tok = _signup(client, "profile@example.com")["access_token"]
    r = client.patch(f"{API}/auth/me", json={"full_name": "New Name"}, headers=_auth(tok))
    assert r.status_code == 200, r.text
    assert r.json()["user"]["full_name"] == "New Name"


def test_change_password_flow(client):
    tok = _signup(client, "pw@example.com")["access_token"]

    # Wrong current password is rejected.
    bad = client.post(
        f"{API}/auth/change-password",
        json={"current_password": "wrong", "new_password": "brandnew123"},
        headers=_auth(tok),
    )
    assert bad.status_code == 400

    # Correct current password changes it; the new password then logs in.
    ok = client.post(
        f"{API}/auth/change-password",
        json={"current_password": "password123", "new_password": "brandnew123"},
        headers=_auth(tok),
    )
    assert ok.status_code == 204, ok.text
    assert client.post(
        f"{API}/auth/login", json={"email": "pw@example.com", "password": "brandnew123"}
    ).status_code == 200
    assert client.post(
        f"{API}/auth/login", json={"email": "pw@example.com", "password": "password123"}
    ).status_code == 401


def test_export_includes_businesses_without_secrets(client):
    tok = _signup(client, "export@example.com")["access_token"]
    bid = client.post(f"{API}/businesses", json={"name": "Acme Co"}, headers=_auth(tok)).json()["id"]
    client.post(
        f"{API}/businesses/{bid}/content/generate",
        json={"channel": "instagram", "brief": "Hello world"}, headers=_auth(tok),
    )

    r = client.get(f"{API}/auth/export", headers=_auth(tok))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["account"]["email"] == "export@example.com"
    assert "password_hash" not in data["account"]
    assert len(data["businesses"]) == 1
    biz = data["businesses"][0]
    assert biz["profile"]["name"] == "Acme Co"
    assert len(biz["content"]) >= 1
    # Connected-account tokens must never appear in an export.
    assert all("access_token_enc" not in a for a in biz["connected_accounts"])


def test_delete_account_requires_password_and_cascades(client):
    tok = _signup(client, "del@example.com")["access_token"]
    bid = client.post(f"{API}/businesses", json={"name": "Gone Inc"}, headers=_auth(tok)).json()["id"]

    # Wrong password won't delete.
    assert client.request(
        "DELETE", f"{API}/auth/me", json={"password": "nope"}, headers=_auth(tok)
    ).status_code == 400

    # Correct password deletes the account + its business.
    assert client.request(
        "DELETE", f"{API}/auth/me", json={"password": "password123"}, headers=_auth(tok)
    ).status_code == 204

    # The session is dead and the login no longer works.
    assert client.get(f"{API}/auth/me", headers=_auth(tok)).status_code == 401
    assert client.post(
        f"{API}/auth/login", json={"email": "del@example.com", "password": "password123"}
    ).status_code == 401


def test_delete_account_keeps_businesses_owned_by_others(client):
    # Owner creates a business and invites a member.
    owner = _signup(client, "owner2@example.com")["access_token"]
    bid = client.post(f"{API}/businesses", json={"name": "Shared LLC"}, headers=_auth(owner)).json()["id"]
    _signup(client, "member@example.com")
    client.post(
        f"{API}/businesses/{bid}/members",
        json={"email": "member@example.com", "role": "editor"}, headers=_auth(owner),
    )
    member = client.post(
        f"{API}/auth/login", json={"email": "member@example.com", "password": "password123"}
    ).json()["access_token"]

    # The member deletes their own account — the owner's business survives.
    assert client.request(
        "DELETE", f"{API}/auth/me", json={"password": "password123"}, headers=_auth(member)
    ).status_code == 204
    assert client.get(f"{API}/businesses/{bid}", headers=_auth(owner)).status_code == 200
