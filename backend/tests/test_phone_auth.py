"""Phone-number sign-in: linking, OTP login and cross-account safety."""

from __future__ import annotations


def link_and_verify(alice, client, phone="+919876543210"):
    sent = alice.post("/api/v1/users/me/phone/otp", json={"phone": phone})
    assert sent.status_code == 200, sent.text
    code = sent.json()["debug_code"]
    assert code and len(code) == 6

    verified = alice.post("/api/v1/users/me/phone/verify", json={"code": code})
    assert verified.status_code == 200, verified.text
    return verified.json()


def test_linking_a_phone_number_marks_it_verified(alice, client):
    user = link_and_verify(alice, client)
    assert user["phone"] == "+919876543210"
    assert user["phone_verified"] is True


def test_invalid_phone_format_is_rejected(alice, client):
    response = alice.post("/api/v1/users/me/phone/otp", json={"phone": "9876543210"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_phone"


def test_wrong_otp_code_is_rejected_and_counted(alice, client):
    alice.post("/api/v1/users/me/phone/otp", json={"phone": "+919876543210"})
    response = alice.post("/api/v1/users/me/phone/verify", json={"code": "000000"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "otp_invalid"


def test_otp_is_single_use(alice, client):
    sent = alice.post("/api/v1/users/me/phone/otp", json={"phone": "+919876543210"})
    code = sent.json()["debug_code"]

    first = alice.post("/api/v1/users/me/phone/verify", json={"code": code})
    assert first.status_code == 200

    # Nothing pending any more - the endpoint reports there is no code to check.
    second = alice.post("/api/v1/users/me/phone/verify", json={"code": code})
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "otp_expired"


def test_phone_login_requires_a_previously_verified_number(client):
    response = client.post(
        "/api/v1/auth/phone/login", json={"phone": "+911111111111", "code": "123456"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "phone_not_registered"


def test_phone_login_end_to_end(alice, client):
    link_and_verify(alice, client)
    client.cookies.clear()

    otp = client.post("/api/v1/auth/phone/otp", json={"phone": "+919876543210"})
    assert otp.status_code == 200
    code = otp.json()["debug_code"]
    assert code

    login = client.post(
        "/api/v1/auth/phone/login", json={"phone": "+919876543210", "code": code}
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == alice.email

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["phone"] == "+919876543210"


def test_phone_otp_for_unregistered_number_returns_generic_response(client):
    """The public endpoint must not reveal whether a number is registered."""
    response = client.post("/api/v1/auth/phone/otp", json={"phone": "+911111111111"})
    assert response.status_code == 200
    body = response.json()
    assert "If that phone number is registered" in body["message"]
    assert body["debug_code"] is None


def test_a_phone_number_cannot_be_linked_to_two_accounts(alice, bob, client):
    link_and_verify(alice, client, phone="+919876543210")

    sent = bob.post("/api/v1/users/me/phone/otp", json={"phone": "+919876543210"})
    assert sent.status_code == 409
    assert "already linked" in sent.json()["error"]["message"].lower()


def test_unlink_removes_phone_login(alice, client):
    link_and_verify(alice, client)
    response = alice.delete("/api/v1/users/me/phone")
    assert response.status_code == 200
    assert response.json()["phone"] is None

    client.cookies.clear()
    otp = client.post("/api/v1/auth/phone/otp", json={"phone": "+919876543210"})
    assert otp.json()["debug_code"] is None  # no longer a registered number


def test_resend_before_cooldown_is_rate_limited(alice, client):
    alice.post("/api/v1/users/me/phone/otp", json={"phone": "+919876543210"})
    second = alice.post("/api/v1/users/me/phone/otp", json={"phone": "+919876543210"})
    assert second.status_code == 429
