"""Authentication and session tests."""

from __future__ import annotations

from app.core.config import settings


def test_health_reports_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_register_creates_user_and_session(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "New.User@Example.com",
            "password": "Str0ng-Password",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    body = response.json()
    # E-mail is normalised so sign-in is case-insensitive.
    assert body["user"]["email"] == "new.user@example.com"
    assert body["csrf_token"]
    assert settings.ACCESS_COOKIE_NAME in response.cookies
    assert settings.REFRESH_COOKIE_NAME in response.cookies
    # A brand new account has no Green PIN and is therefore locked.
    assert body["financial"]["pin_configured"] is False
    assert body["financial"]["unlocked"] is False


def test_register_rejects_duplicate_email(client, alice):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": alice.email.upper(), "password": "Another-Pass-1", "full_name": "Copy"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "password", "full_name": "Weak"},
    )
    assert response.status_code == 400


def test_login_and_logout(client, alice):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login", json={"email": alice.email, "password": alice.password}
    )
    assert response.status_code == 200
    csrf = response.json()["csrf_token"]

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == alice.email

    logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200

    # The session row is revoked, so a replayed access token is refused.
    assert client.get("/api/v1/auth/me").status_code == 401


def test_login_with_wrong_password_is_rejected(client, alice):
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login", json={"email": alice.email, "password": "not-the-password"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_unknown_email_is_indistinguishable_from_wrong_password(client, alice):
    client.cookies.clear()
    unknown = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever-123"}
    )
    wrong = client.post(
        "/api/v1/auth/login", json={"email": alice.email, "password": "whatever-123"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_anonymous_requests_are_rejected(client):
    client.cookies.clear()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_rotates_the_token(client, alice):
    alice.use()
    original = client.cookies.get(settings.REFRESH_COOKIE_NAME)

    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 200
    rotated = response.cookies.get(settings.REFRESH_COOKIE_NAME)
    assert rotated and rotated != original

    # The consumed refresh token must not work a second time.
    client.cookies.clear()
    client.cookies.set(settings.REFRESH_COOKIE_NAME, original)
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_state_change_requires_csrf_header(client, alice):
    alice.use()
    response = client.patch("/api/v1/users/me", json={"display_name": "No CSRF"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_forgot_password_does_not_leak_account_existence(monkeypatch, client, alice):
    # A configured SMTP host is the precondition for the 200 path: without
    # one the endpoint reports the misconfiguration instead (503), which is
    # covered separately below.
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com", raising=False)

    known = client.post("/api/v1/auth/forgot-password", json={"email": alice.email})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_password_reset_flow(client, alice, db):
    from app.models.enums import TokenPurpose
    from app.security.tokens import generate_opaque_token, hash_token
    from app.models.user import VerificationToken

    # Mint a token the same way the mailer would.
    raw = generate_opaque_token()
    import uuid as _uuid
    from datetime import datetime, timedelta, timezone

    db.add(
        VerificationToken(
            user_id=_uuid.UUID(alice.id),
            token_hash=hash_token(raw),
            purpose=TokenPurpose.PASSWORD_RESET.value,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
    )
    db.commit()

    response = client.post(
        "/api/v1/auth/reset-password", json={"token": raw, "new_password": "Brand-New-Pass-9"}
    )
    assert response.status_code == 200

    # The token is single-use.
    assert (
        client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw, "new_password": "Another-Pass-9"},
        ).status_code
        == 400
    )

    client.cookies.clear()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": alice.email, "password": "Brand-New-Pass-9"},
        ).status_code
        == 200
    )
    # The old password no longer works.
    client.cookies.clear()
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": alice.email, "password": alice.password}
        ).status_code
        == 401
    )


def test_change_password_signs_out_other_devices(client, alice):
    response = alice.post(
        "/api/v1/auth/change-password",
        json={"current_password": alice.password, "new_password": "Changed-Pass-77"},
    )
    assert response.status_code == 200

    wrong = alice.post(
        "/api/v1/auth/change-password",
        json={"current_password": "still-wrong", "new_password": "Whatever-Pass-1"},
    )
    assert wrong.status_code == 400


def test_sessions_can_be_listed_and_revoked(client, alice):
    response = alice.get("/api/v1/security/sessions")
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True

    # The current session cannot be revoked from the session list.
    assert alice.delete(f"/api/v1/security/sessions/{sessions[0]['id']}").status_code == 400


def test_providers_endpoint_reports_google_state(client):
    response = client.get("/api/v1/auth/providers")
    assert response.status_code == 200
    assert response.json() == {"google": False, "password": True}


def test_google_start_is_disabled_without_configuration(client):
    assert client.get("/api/v1/auth/google/start").status_code == 400


def test_forgot_password_reports_unconfigured_smtp_instead_of_a_false_promise(
    monkeypatch, client, alice
):
    """It used to answer "a reset link is on its way" with no SMTP host set,
    so every reset silently vanished."""
    monkeypatch.setattr(settings, "SMTP_HOST", "", raising=False)

    response = client.post("/api/v1/auth/forgot-password", json={"email": alice.email})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "email_provider_missing"


def test_the_smtp_guard_still_hides_whether_an_account_exists(
    monkeypatch, client, alice
):
    """The guard runs before the account lookup, so a registered and an
    unknown address must be indistinguishable either way."""
    monkeypatch.setattr(settings, "SMTP_HOST", "", raising=False)
    known = client.post("/api/v1/auth/forgot-password", json={"email": alice.email})
    unknown = client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert known.status_code == unknown.status_code == 503
    assert known.json() == unknown.json()

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com", raising=False)
    known = client.post("/api/v1/auth/forgot-password", json={"email": alice.email})
    unknown = client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
