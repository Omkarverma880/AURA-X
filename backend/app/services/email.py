"""Transactional e-mail.

When SMTP is not configured the message is written to the application log
instead of being sent. That keeps local development frictionless, and the log
line is the only place a reset link ever appears in plaintext.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from urllib.parse import quote

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _send(to: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
    if not settings.smtp_enabled:
        logger.warning(
            "SMTP not configured - e-mail not sent. to=%s subject=%s body=%s",
            to,
            subject,
            text_body.replace("\n", " | "),
        )
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        logger.info("Sent e-mail to=%s subject=%s", to, subject)
        return True
    except Exception as exc:
        # Never surface SMTP failures to the caller: a password-reset request
        # must respond identically whether or not delivery succeeded.
        logger.error("Failed to send e-mail to=%s subject=%s error=%s", to, subject, exc)
        return False


def _wrap(title: str, intro: str, button_label: str, link: str, footer: str) -> str:
    return f"""
<div style="font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
            background:#f6f6fb;padding:32px">
  <div style="max-width:520px;margin:0 auto;background:#fff;border-radius:16px;
              padding:32px;box-shadow:0 1px 3px rgba(16,24,40,.08)">
    <div style="font-size:13px;letter-spacing:.14em;text-transform:uppercase;
                color:#a8791f;font-weight:700">Aura X</div>
    <h1 style="font-size:22px;color:#101828;margin:12px 0 8px">{title}</h1>
    <p style="color:#475467;font-size:15px;line-height:1.6">{intro}</p>
    <p style="margin:28px 0">
      <a href="{link}" style="background:#a8791f;color:#fff;text-decoration:none;
         padding:12px 22px;border-radius:10px;font-weight:600;display:inline-block">
        {button_label}</a>
    </p>
    <p style="color:#98a2b3;font-size:13px;line-height:1.6">{footer}</p>
  </div>
</div>
"""


def send_password_reset(to: str, token: str, name: str) -> bool:
    link = f"{settings.FRONTEND_URL}/reset-password?token={quote(token)}"
    return _send(
        to,
        "Reset your Aura X password",
        f"Hi {name},\n\nReset your password using this link (valid for 1 hour):\n{link}\n\n"
        "If you did not request this, you can safely ignore this e-mail.",
        _wrap(
            "Reset your password",
            f"Hi {name}, we received a request to reset your Aura X password.",
            "Reset password",
            link,
            "This link expires in 1 hour and can be used only once. "
            "If you did not request it, no action is needed.",
        ),
    )


def send_verification(to: str, token: str, name: str) -> bool:
    link = f"{settings.FRONTEND_URL}/verify-email?token={quote(token)}"
    return _send(
        to,
        "Verify your Aura X e-mail",
        f"Hi {name},\n\nConfirm your e-mail address:\n{link}\n\nThis link is valid for 24 hours.",
        _wrap(
            "Confirm your e-mail",
            f"Hi {name}, welcome to Aura X. Confirm your address to secure your account.",
            "Verify e-mail",
            link,
            "This link expires in 24 hours.",
        ),
    )


def send_pin_reset(to: str, token: str, name: str) -> bool:
    link = f"{settings.FRONTEND_URL}/reset-green-pin?token={quote(token)}"
    return _send(
        to,
        "Reset your Aura X Green PIN",
        f"Hi {name},\n\nReset your Green PIN using this link (valid for 30 minutes):\n{link}\n\n"
        "If you did not request this, secure your account by changing your password.",
        _wrap(
            "Reset your Green PIN",
            f"Hi {name}, use the button below to set a new Green PIN for your financial data.",
            "Reset Green PIN",
            link,
            "This link expires in 30 minutes and can be used only once. If you did not "
            "request it, change your password immediately.",
        ),
    )
