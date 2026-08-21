"""OTP delivery: provider selection, channel fallback, and honest failures.

The bug these cover: with no gateway configured the endpoints used to answer
"a verification code has been sent" and return 200, so a production
deployment left users waiting forever on a message nothing had tried to
send.
"""

from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.services import messaging


class FakeResponse:
    """Just enough of httpx.Response for the provider functions."""

    def __init__(self, status_code: int = 200, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"messages": [{"id": "wamid.1"}]}
        self.text = str(self._payload)

    def json(self):
        return self._payload


@pytest.fixture
def calls(monkeypatch):
    """Capture every outbound HTTP call the messaging layer makes."""
    recorded: list[dict] = []

    def fake_post(url, **kwargs):
        recorded.append({"url": url, **kwargs})
        return FakeResponse()

    monkeypatch.setattr(messaging.httpx, "post", fake_post)
    return recorded


@pytest.fixture
def meta_whatsapp(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "123456", raising=False)
    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "token-abc", raising=False)
    monkeypatch.setattr(settings, "OTP_CHANNEL", "auto", raising=False)


@pytest.fixture
def twilio_sms(monkeypatch):
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "ACxxx", raising=False)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "secret", raising=False)
    monkeypatch.setattr(settings, "TWILIO_FROM_NUMBER", "+15550001111", raising=False)


# --- Provider selection -------------------------------------------------


def test_no_provider_configured_reports_failure_rather_than_silence():
    result = messaging.send_otp("+919876543210", "123456")
    assert result.delivered is False
    assert result.error == "no_provider"
    assert result.channel == "none"


def test_whatsapp_is_preferred_over_sms_on_auto(calls, meta_whatsapp, twilio_sms):
    result = messaging.send_otp("+919876543210", "123456")

    assert result.delivered is True
    assert result.channel == "whatsapp"
    assert result.provider == "whatsapp_meta"
    assert len(calls) == 1
    assert "graph.facebook.com" in calls[0]["url"]


def test_channel_sms_skips_whatsapp_entirely(monkeypatch, calls, meta_whatsapp, twilio_sms):
    monkeypatch.setattr(settings, "OTP_CHANNEL", "sms", raising=False)

    result = messaging.send_otp("+919876543210", "123456")

    assert result.channel == "sms"
    assert result.provider == "sms_twilio"
    assert "api.twilio.com" in calls[0]["url"]


def test_delivery_falls_back_to_sms_when_whatsapp_rejects(
    monkeypatch, meta_whatsapp, twilio_sms
):
    seen: list[str] = []

    def fake_post(url, **kwargs):
        seen.append(url)
        if "graph.facebook.com" in url:
            return FakeResponse(400, {"error": {"message": "Template not found"}})
        return FakeResponse()

    monkeypatch.setattr(messaging.httpx, "post", fake_post)

    result = messaging.send_otp("+919876543210", "123456")

    assert result.delivered is True
    assert result.channel == "sms"
    assert len(seen) == 2


def test_every_provider_failing_surfaces_the_last_error(monkeypatch, meta_whatsapp):
    def fake_post(url, **kwargs):
        raise httpx.ConnectError("network unreachable")

    monkeypatch.setattr(messaging.httpx, "post", fake_post)

    result = messaging.send_otp("+919876543210", "123456")
    assert result.delivered is False
    assert "network unreachable" in result.error


# --- Payload shape ------------------------------------------------------


def test_meta_payload_carries_the_code_in_body_and_copy_button(calls, meta_whatsapp):
    messaging.send_otp("+919876543210", "654321")

    template = calls[0]["json"]["template"]
    assert calls[0]["json"]["to"] == "919876543210"  # no leading '+'
    assert template["name"] == settings.WHATSAPP_OTP_TEMPLATE

    body, button = template["components"]
    assert body["parameters"][0]["text"] == "654321"
    # Meta rejects an authentication template whose copy-code button is left
    # unfilled, so the same code has to appear twice.
    assert button["type"] == "button"
    assert button["parameters"][0]["text"] == "654321"


def test_meta_payload_omits_the_button_when_the_template_has_none(
    monkeypatch, calls, meta_whatsapp
):
    monkeypatch.setattr(settings, "WHATSAPP_OTP_COPY_BUTTON", False, raising=False)

    messaging.send_otp("+919876543210", "654321")

    components = calls[0]["json"]["template"]["components"]
    assert len(components) == 1
    assert components[0]["type"] == "body"


def test_twilio_whatsapp_prefixes_both_ends_of_the_conversation(monkeypatch, calls):
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "ACxxx", raising=False)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "secret", raising=False)
    monkeypatch.setattr(settings, "TWILIO_WHATSAPP_FROM", "+14155238886", raising=False)

    result = messaging.send_otp("+919876543210", "654321")

    assert result.provider == "whatsapp_twilio"
    assert calls[0]["data"]["To"] == "whatsapp:+919876543210"
    assert calls[0]["data"]["From"] == "whatsapp:+14155238886"


def test_msg91_error_body_is_treated_as_a_failure_despite_http_200(monkeypatch):
    monkeypatch.setattr(settings, "MSG91_AUTH_KEY", "key", raising=False)
    monkeypatch.setattr(settings, "MSG91_TEMPLATE_ID", "tmpl", raising=False)
    monkeypatch.setattr(
        messaging.httpx,
        "post",
        lambda url, **kw: FakeResponse(200, {"type": "error", "message": "Invalid template"}),
    )

    result = messaging.send_otp("+919876543210", "654321")
    assert result.delivered is False
    assert result.error == "Invalid template"


# --- Endpoint behaviour -------------------------------------------------


def test_production_without_a_provider_returns_503_not_a_false_success(
    monkeypatch, client
):
    monkeypatch.setattr(settings, "APP_ENV", "production", raising=False)

    response = client.post("/api/v1/auth/phone/otp", json={"phone": "+919876543210"})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "otp_provider_missing"


def test_production_delivery_failure_does_not_block_an_immediate_retry(
    monkeypatch, client, meta_whatsapp
):
    """A code the user never received must not hold the resend cooldown."""
    monkeypatch.setattr(settings, "APP_ENV", "production", raising=False)
    monkeypatch.setattr(
        messaging.httpx,
        "post",
        lambda url, **kw: FakeResponse(400, {"error": {"message": "Template paused"}}),
    )

    first = client.post("/api/v1/auth/phone/otp", json={"phone": "+919876543210"})
    assert first.status_code == 503
    assert first.json()["error"]["code"] == "otp_send_failed"

    # Would be a 429 "please wait 45 seconds" if the dead code were still pending.
    second = client.post("/api/v1/auth/phone/otp", json={"phone": "+919876543210"})
    assert second.status_code == 503


def test_successful_send_tells_the_client_which_channel_to_check(
    monkeypatch, client, meta_whatsapp
):
    monkeypatch.setattr(settings, "APP_ENV", "production", raising=False)
    monkeypatch.setattr(messaging.httpx, "post", lambda url, **kw: FakeResponse())

    response = client.post("/api/v1/auth/phone/otp", json={"phone": "+919876543210"})

    assert response.status_code == 200
    body = response.json()
    assert body["channel"] == "whatsapp"
    assert "WhatsApp" in body["message"]
    # The real code never leaves the server once a provider is carrying it.
    assert body["debug_code"] is None
