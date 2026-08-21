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


def test_phone_login_creates_an_account_for_a_new_number(client):
    """Phone auth is phone-first: an unclaimed number signs up, not 401s."""
    otp = client.post("/api/v1/auth/phone/otp", json={"phone": "+911111111111"})
    assert otp.status_code == 200
    code = otp.json()["debug_code"]
    assert code and len(code) == 6

    login = client.post(
        "/api/v1/auth/phone/login",
        json={"phone": "+911111111111", "code": code, "full_name": "Priya Sharma"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["user"]["phone"] == "+911111111111"
    assert body["user"]["phone_verified"] is True
    assert body["user"]["full_name"] == "Priya Sharma"
    # A synthetic placeholder, never a delivery address - just satisfies the
    # NOT NULL/UNIQUE constraint on User.email.
    assert body["user"]["email"].endswith("@phone.aurax.app")


def test_phone_login_signing_in_twice_reuses_the_same_account(client):
    first_code = client.post("/api/v1/auth/phone/otp", json={"phone": "+911111111111"}).json()["debug_code"]
    first = client.post(
        "/api/v1/auth/phone/login", json={"phone": "+911111111111", "code": first_code}
    ).json()

    client.cookies.clear()
    second_code = client.post("/api/v1/auth/phone/otp", json={"phone": "+911111111111"}).json()["debug_code"]
    second = client.post(
        "/api/v1/auth/phone/login", json={"phone": "+911111111111", "code": second_code}
    ).json()

    assert first["user"]["id"] == second["user"]["id"]


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


def test_phone_otp_is_always_sent(client):
    """Unlike password reset, the phone endpoint has nothing to hide: it is
    the sign-up step too, so a code is sent for any valid number."""
    response = client.post("/api/v1/auth/phone/otp", json={"phone": "+911111111111"})
    assert response.status_code == 200
    body = response.json()
    assert body["debug_code"] is not None
    assert len(body["debug_code"]) == 6


def test_a_phone_number_cannot_be_linked_to_two_accounts(alice, bob, client):
    link_and_verify(alice, client, phone="+919876543210")

    sent = bob.post("/api/v1/users/me/phone/otp", json={"phone": "+919876543210"})
    assert sent.status_code == 409
    assert "already linked" in sent.json()["error"]["message"].lower()


def test_unlink_makes_the_number_available_for_a_new_account(alice, client):
    link_and_verify(alice, client)
    response = alice.delete("/api/v1/users/me/phone")
    assert response.status_code == 200
    assert response.json()["phone"] is None

    client.cookies.clear()
    code = client.post("/api/v1/auth/phone/otp", json={"phone": "+919876543210"}).json()["debug_code"]
    login = client.post("/api/v1/auth/phone/login", json={"phone": "+919876543210", "code": code})
    assert login.status_code == 200
    # No longer verified on Alice's account, so this now signs up someone new
    # rather than logging in as her.
    assert login.json()["user"]["id"] != alice.id


def test_resend_before_cooldown_is_rate_limited(alice, client):
    alice.post("/api/v1/users/me/phone/otp", json={"phone": "+919876543210"})
    second = alice.post("/api/v1/users/me/phone/otp", json={"phone": "+919876543210"})
    assert second.status_code == 429


# --- Contact number (no OTP) --------------------------------------------


def test_a_contact_number_can_be_saved_without_any_verification(alice):
    response = alice.patch("/api/v1/users/me", json={"phone": "+919005872572"})
    assert response.status_code == 200
    assert response.json()["profile"]["phone"] == "+919005872572"


def test_a_saved_contact_number_does_not_grant_sign_in(alice, client):
    """The whole point of the split: profile.phone is contact data, while
    User.phone is an identity and stays gated behind OTP. Otherwise anyone
    could type someone else's number and inherit their account."""
    alice.patch("/api/v1/users/me", json={"phone": "+919005872572"})

    me = alice.get("/api/v1/users/me").json()
    assert me["profile"]["phone"] == "+919005872572"
    assert me["phone"] is None          # sign-in identity untouched
    assert me["phone_verified"] is False

    client.cookies.clear()
    code = client.post(
        "/api/v1/auth/phone/otp", json={"phone": "+919005872572"}
    ).json()["debug_code"]
    login = client.post(
        "/api/v1/auth/phone/login", json={"phone": "+919005872572", "code": code}
    )
    # Signs up a brand-new account rather than handing over Alice's.
    assert login.status_code == 200
    assert login.json()["user"]["id"] != alice.id


def test_two_users_may_save_the_same_contact_number(alice, bob):
    """Unlike the verified sign-in identity, contact data is not an identity
    claim - a shared family number must not 409."""
    assert alice.patch("/api/v1/users/me", json={"phone": "+919005872572"}).status_code == 200
    assert bob.patch("/api/v1/users/me", json={"phone": "+919005872572"}).status_code == 200


def test_a_malformed_contact_number_is_rejected(alice):
    response = alice.patch("/api/v1/users/me", json={"phone": "9005872572"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_phone"


def test_a_contact_number_can_be_cleared(alice):
    alice.patch("/api/v1/users/me", json={"phone": "+919005872572"})
    response = alice.patch("/api/v1/users/me", json={"phone": ""})
    assert response.status_code == 200
    assert response.json()["profile"]["phone"] is None
