"""OAuth connect flow: start → consent → callback stores an encrypted token."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

API = "/api/v1"


def _owner(client, email="oauth@example.com"):
    tokens = client.post(
        f"{API}/auth/signup", json={"email": email, "password": "password123"}
    ).json()
    h = {"Authorization": f"Bearer {tokens['access_token']}"}
    bid = client.post(f"{API}/businesses", json={"name": "Acme Co"}, headers=h).json()["id"]
    return h, bid


def _state_from(authorize_url: str) -> str:
    return parse_qs(urlparse(authorize_url).query)["state"][0]


def test_start_returns_a_consent_url(client):
    h, bid = _owner(client)
    r = client.post(f"{API}/businesses/{bid}/integrations/oauth/instagram/start", headers=h)
    assert r.status_code == 200, r.text
    url = r.json()["authorize_url"]
    assert "_mock/authorize" in url
    assert "state=" in url and "redirect_uri=" in url


def test_unknown_platform_rejected(client):
    h, bid = _owner(client, email="oauth2@example.com")
    r = client.post(f"{API}/businesses/{bid}/integrations/oauth/myspace/start", headers=h)
    assert r.status_code == 400


def test_full_flow_stores_connected_account(client):
    h, bid = _owner(client, email="oauth3@example.com")
    # 1. start
    url = client.post(
        f"{API}/businesses/{bid}/integrations/oauth/instagram/start", headers=h
    ).json()["authorize_url"]
    state = _state_from(url)

    # 2. consent screen renders
    consent = client.get(
        f"{API}/integrations/oauth/_mock/authorize",
        params={"platform": "instagram", "state": state,
                "redirect_uri": f"{API}/integrations/oauth/instagram/callback"},
    )
    assert consent.status_code == 200
    assert "Authorize" in consent.text

    # 3. callback (platform redirects the browser here with code + state)
    cb = client.get(
        f"{API}/integrations/oauth/instagram/callback",
        params={"code": "mock-auth-code", "state": state},
        follow_redirects=False,
    )
    assert cb.status_code == 302
    assert f"/businesses/{bid}/schedule?connected=instagram" in cb.headers["location"]

    # 4. the account now exists and is connected
    accounts = client.get(f"{API}/businesses/{bid}/integrations/accounts", headers=h).json()
    assert len(accounts) == 1
    assert accounts[0]["platform"] == "instagram"
    assert accounts[0]["status"] == "connected"


def test_denied_consent_redirects_with_error(client):
    h, bid = _owner(client, email="oauth4@example.com")
    url = client.post(
        f"{API}/businesses/{bid}/integrations/oauth/facebook/start", headers=h
    ).json()["authorize_url"]
    state = _state_from(url)

    cb = client.get(
        f"{API}/integrations/oauth/facebook/callback",
        params={"error": "access_denied", "state": state},
        follow_redirects=False,
    )
    assert cb.status_code == 302
    assert "oauth_error=access_denied" in cb.headers["location"]
    # Nothing connected.
    assert client.get(f"{API}/businesses/{bid}/integrations/accounts", headers=h).json() == []


def test_invalid_state_is_rejected(client):
    r = client.get(
        f"{API}/integrations/oauth/instagram/callback",
        params={"code": "x", "state": "not-a-real-token"},
        follow_redirects=False,
    )
    assert r.status_code == 400


def test_start_requires_editor(client):
    owner_h, bid = _owner(client, email="oauthowner@example.com")
    client.post(f"{API}/auth/signup", json={"email": "oauthviewer@example.com", "password": "password123"})
    client.post(
        f"{API}/businesses/{bid}/members",
        json={"email": "oauthviewer@example.com", "role": "viewer"}, headers=owner_h,
    )
    viewer_h = {"Authorization": "Bearer " + client.post(
        f"{API}/auth/login", json={"email": "oauthviewer@example.com", "password": "password123"}
    ).json()["access_token"]}
    r = client.post(f"{API}/businesses/{bid}/integrations/oauth/instagram/start", headers=viewer_h)
    assert r.status_code == 403
