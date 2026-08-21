"""SMS delivery for one-time login codes.

Deliberately provider-agnostic: rather than hard-coding a Twilio or MSG91 SDK,
this posts to a configurable webhook URL that any provider (or a small relay
in front of one) can implement with a {to, message} JSON body. When no
webhook is configured the code is written to the application log instead,
which is exactly how the e-mail service behaves in development.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def send_sms(phone: str, message: str) -> bool:
    if not settings.sms_enabled:
        logger.warning("SMS provider not configured - message not sent. to=%s body=%s", phone, message)
        return False

    try:
        response = httpx.post(
            settings.SMS_WEBHOOK_URL,
            json={"to": phone, "message": message, "sender_id": settings.SMS_SENDER_ID},
            headers={"Authorization": f"Bearer {settings.SMS_API_KEY}"} if settings.SMS_API_KEY else {},
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Sent SMS to=%s", phone)
        return True
    except httpx.HTTPError as exc:
        logger.error("Failed to send SMS to=%s error=%s", phone, exc)
        return False


def send_otp(phone: str, code: str) -> bool:
    return send_sms(
        phone,
        f"{code} is your Aura X verification code. It expires in "
        f"{settings.OTP_TTL_MINUTES} minutes. Do not share this code with anyone.",
    )
