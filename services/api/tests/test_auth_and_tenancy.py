"""End-to-end Phase 1 checks: auth, tenancy, RBAC, and plan feature-gating."""
from __future__ import annotations

API = "/api/v1"


def _signup(client, email, password="password123", name="Owner"):
    r = client.post(f"{API}/auth/signup", json={"email": email, "password": password, "full_name": name})
    assert r.status_code == 201, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_login_me(client):
    tokens = _signup(client, "owner@example.com")
    assert tokens["access_token"] and tokens["refresh_token"]

    r = client.post(f"{API}/auth/login", json={"email": "owner@example.com", "password": "password123"})
    assert r.status_code == 200

    r = client.get(f"{API}/auth/me", headers=_auth(tokens["access_token"]))
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "owner@example.com"


def test_duplicate_signup_conflicts(client):
    _signup(client, "dup@example.com")
    r = client.post(f"{API}/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    assert r.status_code == 409


def test_wrong_password_rejected(client):
    _signup(client, "u@example.com")
    r = client.post(f"{API}/auth/login", json={"email": "u@example.com", "password": "nope"})
    assert r.status_code == 401


def test_refresh_token_issues_new_access(client):
    tokens = _signup(client, "r@example.com")
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    # An access token must not be usable as a refresh token.
    bad = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401


def test_create_and_list_business(client):
    tokens = _signup(client, "biz@example.com")
    h = _auth(tokens["access_token"])
    r = client.post(f"{API}/businesses", json={"name": "Acme Co", "industry": "Retail"}, headers=h)
    assert r.status_code == 201, r.text
    business = r.json()
    assert business["plan_id"] is not None  # defaulted to Starter

    r = client.get(f"{API}/businesses", headers=h)
    assert r.status_code == 200
    assert [b["id"] for b in r.json()] == [business["id"]]


def test_tenant_isolation(client):
    owner = _auth(_signup(client, "o1@example.com")["access_token"])
    other = _auth(_signup(client, "o2@example.com")["access_token"])
    biz = client.post(f"{API}/businesses", json={"name": "Private LLC"}, headers=owner).json()

    # Non-member gets 404 (existence not leaked), member gets 200.
    assert client.get(f"{API}/businesses/{biz['id']}", headers=other).status_code == 404
    assert client.get(f"{API}/businesses/{biz['id']}", headers=owner).status_code == 200


def test_rbac_and_plan_limit_on_invite(client):
    owner = _auth(_signup(client, "owner2@example.com")["access_token"])
    biz = client.post(f"{API}/businesses", json={"name": "TeamCo"}, headers=owner).json()
    bid = biz["id"]

    # Members must already exist as users to be invited.
    _signup(client, "member1@example.com")
    _signup(client, "member2@example.com")

    # Starter plan allows max_users=2; owner already occupies one seat.
    r1 = client.post(f"{API}/businesses/{bid}/members",
                     json={"email": "member1@example.com", "role": "editor"}, headers=owner)
    assert r1.status_code == 201, r1.text

    # Second invite would exceed the Starter limit -> 402 Payment Required.
    r2 = client.post(f"{API}/businesses/{bid}/members",
                     json={"email": "member2@example.com", "role": "viewer"}, headers=owner)
    assert r2.status_code == 402, r2.text

    # A viewer/editor cannot invite (needs admin+). Log in as the editor we added.
    editor = _auth(client.post(f"{API}/auth/login",
                   json={"email": "member1@example.com", "password": "password123"}).json()["access_token"])
    r3 = client.post(f"{API}/businesses/{bid}/members",
                     json={"email": "member2@example.com", "role": "viewer"}, headers=editor)
    assert r3.status_code == 403, r3.text
