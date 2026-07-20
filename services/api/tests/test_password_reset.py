"""Forgot-password flow: request a code, reset with it, and the new password works."""
from __future__ import annotations

import re

from app.email import mock as email_mock

API = "/api/v1"


def _signup(client, email, password="password123"):
    r = client.post(f"{API}/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 201, r.text


def _last_code(email: str) -> str:
    """Pull the 6-digit code out of the most recent mock email to `email`."""
    msg = next(m for m in reversed(email_mock.sent) if m.to == email)
    return re.search(r"\b(\d{6})\b", msg.text).group(1)


def test_forgot_then_reset_password(client):
    _signup(client, "reset@example.com", password="oldpassword1")

    r = client.post(f"{API}/auth/forgot-password", json={"email": "reset@example.com"})
    assert r.status_code == 200, r.text
    code = _last_code("reset@example.com")

    # Reset to a new password.
    r = client.post(f"{API}/auth/reset-password", json={
        "email": "reset@example.com", "code": code, "new_password": "brandnew123",
    })
    assert r.status_code == 204, r.text

    # New password works; old one no longer does.
    assert client.post(f"{API}/auth/login",
                       json={"email": "reset@example.com", "password": "brandnew123"}).status_code == 200
    assert client.post(f"{API}/auth/login",
                       json={"email": "reset@example.com", "password": "oldpassword1"}).status_code == 401


def test_forgot_password_hides_unknown_email(client):
    before = len(email_mock.sent)
    # Never reveals whether the address is registered: generic 200, no email sent,
    # no dev_code.
    r = client.post(f"{API}/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert r.json()["dev_code"] is None
    assert len(email_mock.sent) == before  # nothing emailed for a non-user


def test_reset_rejects_wrong_code(client):
    _signup(client, "wrongcode@example.com")
    client.post(f"{API}/auth/forgot-password", json={"email": "wrongcode@example.com"})
    r = client.post(f"{API}/auth/reset-password", json={
        "email": "wrongcode@example.com", "code": "000000", "new_password": "whatever123",
    })
    assert r.status_code == 400, r.text


def test_code_is_single_use(client):
    _signup(client, "onetime@example.com")
    client.post(f"{API}/auth/forgot-password", json={"email": "onetime@example.com"})
    code = _last_code("onetime@example.com")
    first = client.post(f"{API}/auth/reset-password", json={
        "email": "onetime@example.com", "code": code, "new_password": "firstpass123",
    })
    assert first.status_code == 204
    # Re-using the same code fails.
    second = client.post(f"{API}/auth/reset-password", json={
        "email": "onetime@example.com", "code": code, "new_password": "secondpass123",
    })
    assert second.status_code == 400
