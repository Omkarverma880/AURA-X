"""One-time-code delivery over WhatsApp and SMS.

Aura X is phone-first, so this is the module that decides *how* a code
reaches a handset. Several providers are supported, all over plain HTTP so
no vendor SDK is needed:

* ``whatsapp_meta``   - Meta WhatsApp Cloud API. Free tier, no DLT paperwork,
  and the default first choice: in India an A2P SMS sender needs TRAI/DLT
  registration before a single message is delivered, whereas a WhatsApp
  authentication template only needs Meta's own approval.
* ``whatsapp_twilio`` - Twilio's WhatsApp channel, including their sandbox,
  which is the quickest way to test WhatsApp delivery end to end.
* ``sms_twilio``      - Twilio programmable SMS.
* ``sms_msg91``       - MSG91's OTP endpoint (India).
* ``sms_webhook``     - the original generic {to, message} relay, kept so
  existing deployments keep working unchanged.

Providers are tried in order of ``Settings.OTP_CHANNEL`` preference and the
first success wins, so configuring WhatsApp *and* SMS gives automatic
fallback when one channel is down or the number has no WhatsApp account.

Nothing here raises: the outcome is returned as a :class:`DeliveryResult` so
callers can decide whether a failure is fatal (production) or merely logged
(development, where the code is surfaced in the API response instead).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TIMEOUT = 10.0

#: (channel, provider name, sender function)
Provider = tuple[str, str, Callable[[str, str], "str | None"]]


@dataclass(frozen=True)
class DeliveryResult:
    """Outcome of trying to put a code in front of the user."""

    delivered: bool
    #: "whatsapp", "sms", or "none" when nothing went out.
    channel: str = "none"
    #: Which provider actually delivered, for logs and support.
    provider: str = ""
    #: Last error seen, when nothing was delivered.
    error: str | None = None

    @property
    def channel_label(self) -> str:
        return {"whatsapp": "on WhatsApp", "sms": "by SMS"}.get(self.channel, "")


def _digits(phone: str) -> str:
    """Meta and MSG91 both want a bare country-code+number, no leading '+'."""
    return phone.lstrip("+")


def _otp_text(code: str) -> str:
    return (
        f"{code} is your Aura X verification code. It expires in "
        f"{settings.OTP_TTL_MINUTES} minutes. Do not share this code with anyone."
    )


# --- Providers ----------------------------------------------------------
# Each returns None on success, or a short error string on failure.


def _send_whatsapp_meta(phone: str, code: str) -> str | None:
    """Send via a Meta-approved authentication template.

    Authentication templates take the code as the single body parameter, and
    - when the template carries the standard "Copy code" button - the same
    value again as the button's parameter. Meta rejects the message outright
    if that button parameter is missing on a template that has one, which is
    the most common reason an otherwise correct account still sends nothing.
    """
    components: list[dict] = [
        {"type": "body", "parameters": [{"type": "text", "text": code}]}
    ]
    if settings.WHATSAPP_OTP_COPY_BUTTON:
        components.append(
            {
                "type": "button",
                "sub_type": "url",
                "index": "0",
                "parameters": [{"type": "text", "text": code}],
            }
        )

    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
        f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    try:
        response = httpx.post(
            url,
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": _digits(phone),
                "type": "template",
                "template": {
                    "name": settings.WHATSAPP_OTP_TEMPLATE,
                    "language": {"code": settings.WHATSAPP_TEMPLATE_LANG},
                    "components": components,
                },
            },
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            return _extract_error(response)
        return None
    except httpx.HTTPError as exc:
        return str(exc)


def _twilio_send(to: str, body: str, from_: str) -> str | None:
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    )
    data = {"To": to, "Body": body}
    if from_:
        data["From"] = from_
    elif settings.TWILIO_MESSAGING_SERVICE_SID:
        data["MessagingServiceSid"] = settings.TWILIO_MESSAGING_SERVICE_SID

    try:
        response = httpx.post(
            url,
            data=data,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            return _extract_error(response)
        return None
    except httpx.HTTPError as exc:
        return str(exc)


def _send_whatsapp_twilio(phone: str, code: str) -> str | None:
    sender = settings.TWILIO_WHATSAPP_FROM
    if not sender.startswith("whatsapp:"):
        sender = f"whatsapp:{sender}"
    return _twilio_send(f"whatsapp:{phone}", _otp_text(code), sender)


def _send_sms_twilio(phone: str, code: str) -> str | None:
    return _twilio_send(phone, _otp_text(code), settings.TWILIO_FROM_NUMBER)


def _send_sms_msg91(phone: str, code: str) -> str | None:
    try:
        response = httpx.post(
            "https://control.msg91.com/api/v5/otp",
            params={
                "template_id": settings.MSG91_TEMPLATE_ID,
                "mobile": _digits(phone),
                "otp": code,
                "sender": settings.MSG91_SENDER_ID,
            },
            json={settings.MSG91_OTP_VAR: code},
            headers={"authkey": settings.MSG91_AUTH_KEY},
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            return _extract_error(response)
        # MSG91 answers 200 with {"type": "error"} on rejection, so the status
        # code alone is not proof of delivery.
        body = _json(response)
        if isinstance(body, dict) and body.get("type") == "error":
            return str(body.get("message") or "MSG91 rejected the request")
        return None
    except httpx.HTTPError as exc:
        return str(exc)


def _send_sms_webhook(phone: str, code: str) -> str | None:
    try:
        response = httpx.post(
            settings.SMS_WEBHOOK_URL,
            json={
                "to": phone,
                "message": _otp_text(code),
                "sender_id": settings.SMS_SENDER_ID,
            },
            headers=(
                {"Authorization": f"Bearer {settings.SMS_API_KEY}"}
                if settings.SMS_API_KEY
                else {}
            ),
            timeout=TIMEOUT,
        )
        if response.status_code >= 400:
            return _extract_error(response)
        return None
    except httpx.HTTPError as exc:
        return str(exc)


# --- Dispatch -----------------------------------------------------------


def _providers() -> list[Provider]:
    """Every configured provider, in the order they should be attempted."""
    whatsapp: list[Provider] = []
    if settings.whatsapp_meta_enabled:
        whatsapp.append(("whatsapp", "whatsapp_meta", _send_whatsapp_meta))
    if settings.whatsapp_twilio_enabled:
        whatsapp.append(("whatsapp", "whatsapp_twilio", _send_whatsapp_twilio))

    sms: list[Provider] = []
    if settings.twilio_sms_enabled:
        sms.append(("sms", "sms_twilio", _send_sms_twilio))
    if settings.msg91_enabled:
        sms.append(("sms", "sms_msg91", _send_sms_msg91))
    if settings.SMS_WEBHOOK_URL:
        sms.append(("sms", "sms_webhook", _send_sms_webhook))

    if settings.OTP_CHANNEL == "whatsapp":
        return whatsapp
    if settings.OTP_CHANNEL == "sms":
        return sms
    return whatsapp + sms


def send_otp(phone: str, code: str) -> DeliveryResult:
    """Deliver ``code`` to ``phone``, trying each configured provider in turn."""
    providers = _providers()

    if not providers:
        logger.warning(
            "No OTP provider configured - code not sent. to=%s "
            "(set WHATSAPP_* or TWILIO_* / MSG91_* / SMS_WEBHOOK_URL)",
            phone,
        )
        return DeliveryResult(False, error="no_provider")

    last_error: str | None = None
    for channel, name, send in providers:
        error = send(phone, code)
        if error is None:
            logger.info("Sent OTP to=%s channel=%s provider=%s", phone, channel, name)
            return DeliveryResult(True, channel=channel, provider=name)
        last_error = error
        logger.error(
            "OTP delivery failed to=%s provider=%s error=%s", phone, name, error
        )

    return DeliveryResult(False, error=last_error)


def _json(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return None


def redact_secrets(text: str) -> str:
    """Strip any configured credential that a provider quoted back at us.

    Meta echoes the offending token verbatim when it is malformed, and these
    strings end up in the application log and in operator-facing reports, so
    no secret is allowed to survive into one.
    """
    for secret in (
        settings.WHATSAPP_ACCESS_TOKEN,
        settings.TWILIO_AUTH_TOKEN,
        settings.MSG91_AUTH_KEY,
        settings.SMS_API_KEY,
    ):
        if secret and len(secret) > 4:
            text = text.replace(secret, f"...{secret[-4:]}")
    return text


def _extract_error(response: httpx.Response) -> str:
    """Pull the human-readable reason out of a provider's error body."""
    body = _json(response)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            detail = error.get("error_user_msg") or error.get("message")
            if detail:
                return redact_secrets(str(detail))
        for key in ("message", "detail", "error_message"):
            if body.get(key):
                return redact_secrets(str(body[key]))
    text = (response.text or "").strip()
    if text:
        return redact_secrets(f"HTTP {response.status_code}: {text[:200]}")
    return f"HTTP {response.status_code}"
