"""Password recovery by identifier, with no delivery channel.

This flow trades security for availability by design - an identifier names an
account but does not prove control of it. These tests pin down the parts that
*are* defended, so the trade-off stays where it was put and does not quietly
widen.
"""

from __future__ import annotations

import pytest

from app.core.rate_limit import rate_limiter

NEW_PASSWORD = "Recovered123!"


@pytest.fixture(autouse=True)
def _reset_limits():
    """The recovery limiter is deliberately tight; keep tests independent."""
    rate_limiter.reset("account_recovery", "unknown")
    yield


def recover(client, identifier, password=NEW_PASSWORD):
    return client.post(
        "/api/v1/auth/recover-password",
        json={"identifier": identifier, "new_password": password},
    )


def test_recovery_by_email_lets_the_user_sign_in_again(client, alice):
    assert recover(client, alice.email).status_code == 200

    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login", json={"email": alice.email, "password": NEW_PASSWORD}
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == alice.id


def test_recovery_by_username_works(client, alice):
    username = client.get("/api/v1/auth/me").json()["user"]["username"]
    assert username

    client.cookies.clear()
    assert recover(client, username).status_code == 200

    login = client.post(
        "/api/v1/auth/login", json={"email": alice.email, "password": NEW_PASSWORD}
    )
    assert login.status_code == 200


def test_recovery_by_contact_phone_works(alice, client):
    alice.patch("/api/v1/users/me", json={"phone": "+919005872572"})
    client.cookies.clear()

    assert recover(client, "+919005872572").status_code == 200
    login = client.post(
        "/api/v1/auth/login", json={"email": alice.email, "password": NEW_PASSWORD}
    )
    assert login.status_code == 200


def test_recovery_accepts_a_phone_without_the_country_code(alice, client):
    alice.patch("/api/v1/users/me", json={"phone": "+919005872572"})
    client.cookies.clear()

    assert recover(client, "9005872572").status_code == 200
    assert client.post(
        "/api/v1/auth/login", json={"email": alice.email, "password": NEW_PASSWORD}
    ).status_code == 200


def test_an_unknown_identifier_is_indistinguishable_from_a_known_one(client, alice):
    """The flow is weak enough already; it must not also enumerate accounts."""
    known = recover(client, alice.email)
    unknown = recover(client, "ghost@example.com")

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_a_weak_password_is_rejected_before_the_account_is_looked_up(client):
    """Otherwise the strength check becomes an existence oracle: 'weak
    password' for real accounts, 'ok' for everything else."""
    for identifier in ("ghost@example.com", "alice@example.com"):
        response = recover(client, identifier, password="short")
        assert response.status_code == 422


def test_recovery_revokes_every_existing_session(client, alice):
    """A reset must evict whoever was already signed in - otherwise a stolen
    account stays stolen after the owner recovers it."""
    assert client.get("/api/v1/auth/me").status_code == 200

    recover(client, alice.email)

    # The cookie in hand belonged to a session that recovery just revoked.
    assert client.get("/api/v1/auth/me").status_code == 401


def test_recovery_is_rate_limited_per_identifier(client, alice, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True, raising=False)
    rate_limiter.reset("account_recovery", "unknown")
    rate_limiter.reset("account_recovery", f"id:{alice.email}")

    codes = [recover(client, alice.email).status_code for _ in range(7)]
    assert 429 in codes, codes


def test_a_deactivated_account_cannot_be_recovered(client, alice, db):
    import uuid

    from app.models.user import User

    user = db.get(User, uuid.UUID(alice.id))
    user.is_active = False
    db.commit()

    assert recover(client, alice.email).status_code == 200  # says nothing

    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login", json={"email": alice.email, "password": NEW_PASSWORD}
    )
    assert login.status_code == 401


# --- Usernames ----------------------------------------------------------


def test_every_new_account_gets_a_username_from_its_first_name(client, alice):
    assert client.get("/api/v1/auth/me").json()["user"]["username"] == "alice"


def test_a_second_account_with_the_same_first_name_gets_a_suffix(client, alice, bob, db):
    from app.services import account_recovery

    assert account_recovery.suggest_username(db, "Alice Cooper") == "alice2"


def test_a_user_can_choose_their_own_username(alice):
    response = alice.patch("/api/v1/users/me", json={"username": "omkar"})
    assert response.status_code == 200
    assert response.json()["username"] == "omkar"


def test_a_username_already_taken_is_refused(alice, bob, client):
    alice.patch("/api/v1/users/me", json={"username": "omkar"})
    response = bob.patch("/api/v1/users/me", json={"username": "omkar"})
    assert response.status_code == 409


def test_a_malformed_username_is_refused(alice):
    for bad in ("ab", "Omkar Verma", "omkar!", "x" * 40):
        response = alice.patch("/api/v1/users/me", json={"username": bad})
        assert response.status_code in (400, 422), bad
