"""Diagnose OTP delivery configuration.

Run via ``python main.py check-otp [+919876543210]``. With no number it only
reports what is configured and probes each provider's credentials; given a
number it also sends a real code and prints whatever the gateway said back.

The point is to turn "the OTP never arrived" into a specific, fixable line -
a wrong token, an unapproved template, a trial account that will only message
verified numbers - rather than a 503 in production and a guess.

Nothing here prints a secret: tokens are masked to their last four characters.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.services import messaging

OK = "[ ok ]"
BAD = "[fail]"
INFO = "[ -- ]"


def _mask(secret: str) -> str:
    if not secret:
        return "(unset)"
    return f"...{secret[-4:]}" if len(secret) > 4 else "****"


#: This report is exactly the sort of output that gets pasted into a chat or
#: an issue, so provider-supplied strings are redacted before printing.
_scrub = messaging.redact_secrets


def _probe_meta() -> list[str]:
    """Confirm the access token can actually see the phone number ID.

    A token that 400s here is the whole problem; a token that works here but
    fails on send almost always means the authentication template is missing,
    unapproved, or named something other than WHATSAPP_OTP_TEMPLATE.
    """
    lines = [
        f"  phone number ID : {settings.WHATSAPP_PHONE_NUMBER_ID}",
        f"  access token    : {_mask(settings.WHATSAPP_ACCESS_TOKEN)}",
        f"  template        : {settings.WHATSAPP_OTP_TEMPLATE} "
        f"(lang {settings.WHATSAPP_TEMPLATE_LANG}, "
        f"copy-code button: {'yes' if settings.WHATSAPP_OTP_COPY_BUTTON else 'no'})",
    ]
    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}"
        f"/{settings.WHATSAPP_PHONE_NUMBER_ID}"
    )
    try:
        response = httpx.get(
            url,
            params={"fields": "display_phone_number,verified_name,quality_rating"},
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            timeout=messaging.TIMEOUT,
        )
    except httpx.HTTPError as exc:
        lines.append(_scrub(f"  {BAD} could not reach Graph API: {exc}"))
        return lines

    if response.status_code >= 400:
        lines.append(_scrub(f"  {BAD} credentials rejected: {messaging._extract_error(response)}"))
        lines.append(
            "         -> check WHATSAPP_ACCESS_TOKEN has not expired (temporary "
            "tokens last 24h - use a permanent System User token) and that "
            "WHATSAPP_PHONE_NUMBER_ID is the *phone number* ID, not the app or "
            "WhatsApp Business Account ID."
        )
        return lines

    body = response.json()
    lines.append(
        f"  {OK} credentials valid - sending as "
        f"{body.get('display_phone_number', '?')} ({body.get('verified_name', '?')}), "
        f"quality {body.get('quality_rating', 'n/a')}"
    )
    return lines


def _probe_twilio() -> list[str]:
    lines = [
        f"  account SID : {settings.TWILIO_ACCOUNT_SID}",
        f"  auth token  : {_mask(settings.TWILIO_AUTH_TOKEN)}",
    ]
    if settings.TWILIO_WHATSAPP_FROM:
        lines.append(f"  whatsapp from: {settings.TWILIO_WHATSAPP_FROM}")
    if settings.TWILIO_FROM_NUMBER:
        lines.append(f"  sms from     : {settings.TWILIO_FROM_NUMBER}")

    try:
        response = httpx.get(
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{settings.TWILIO_ACCOUNT_SID}.json",
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=messaging.TIMEOUT,
        )
    except httpx.HTTPError as exc:
        lines.append(_scrub(f"  {BAD} could not reach Twilio: {exc}"))
        return lines

    if response.status_code >= 400:
        lines.append(_scrub(f"  {BAD} credentials rejected: {messaging._extract_error(response)}"))
        return lines

    body = response.json()
    lines.append(f"  {OK} credentials valid - account '{body.get('friendly_name')}' "
                 f"({body.get('type')}, status {body.get('status')})")
    if str(body.get("type", "")).lower() == "trial":
        lines.append(
            "         note: trial accounts only deliver to numbers verified in "
            "the Twilio console, and the WhatsApp sandbox only to numbers that "
            "have sent it the 'join ...' message."
        )
    return lines


def report(test_number: str | None = None) -> int:
    """Print the diagnosis. Returns a process exit code."""
    print()
    print(f"Aura X - OTP delivery check   (APP_ENV={settings.APP_ENV})")
    print("=" * 62)

    providers = messaging._providers()

    print(f"\nOTP_CHANNEL = {settings.OTP_CHANNEL}", end="")
    if settings.OTP_CHANNEL == "auto":
        print("  (WhatsApp first, then SMS)")
    else:
        print()

    if not providers:
        print(f"\n{BAD} No provider is configured, so no code can be delivered.")
        if settings.is_production:
            print("     /auth/phone/otp will answer 503 otp_provider_missing.")
        else:
            print("     Development mode: the code is returned in the API response")
            print("     as debug_code instead, so the flow still works locally.")
        print("\n  Set ONE of these groups of variables:")
        print("    WhatsApp (Meta)  : WHATSAPP_PHONE_NUMBER_ID + WHATSAPP_ACCESS_TOKEN")
        print("    WhatsApp (Twilio): TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_WHATSAPP_FROM")
        print("    SMS (Twilio)     : TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_FROM_NUMBER")
        print("    SMS (MSG91)      : MSG91_AUTH_KEY + MSG91_TEMPLATE_ID")
        print("    SMS (webhook)    : SMS_WEBHOOK_URL")
        print()
        return 1

    print(f"\n{OK} {len(providers)} provider(s) configured, tried in this order:\n")
    for position, (channel, name, _) in enumerate(providers, start=1):
        print(f"  {position}. {name}  ({channel})")

    if settings.whatsapp_meta_enabled:
        print("\nwhatsapp_meta")
        for line in _probe_meta():
            print(line)

    if settings.twilio_enabled:
        print("\ntwilio")
        for line in _probe_twilio():
            print(line)

    if settings.msg91_enabled:
        print("\nsms_msg91")
        print(f"  auth key    : {_mask(settings.MSG91_AUTH_KEY)}")
        print(f"  template ID : {settings.MSG91_TEMPLATE_ID}")
        print(f"  {INFO} no credential probe available - use a test send below.")

    if settings.SMS_WEBHOOK_URL:
        print("\nsms_webhook")
        print(f"  url : {settings.SMS_WEBHOOK_URL}")
        print(f"  {INFO} no credential probe available - use a test send below.")

    if not test_number:
        print("\nPass a phone number to send a real test code, e.g.")
        print("  python main.py check-otp +919876543210")
        print()
        return 0

    print(f"\nSending a live test code to {test_number} ...")
    result = messaging.send_otp(test_number, "123456")

    if result.delivered:
        print(f"\n{OK} Delivered via {result.provider} ({result.channel}).")
        print("     Check the handset - the test code is 123456.")
        print()
        return 0

    print(_scrub(f"\n{BAD} Delivery failed: {result.error}"))
    if settings.whatsapp_meta_enabled and "template" in str(result.error).lower():
        print(
            "\n     Template problems are the usual cause. In WhatsApp Manager\n"
            "     -> Message templates, confirm a template named "
            f"'{settings.WHATSAPP_OTP_TEMPLATE}' exists, is category\n"
            "     AUTHENTICATION, is APPROVED, and its language matches "
            f"WHATSAPP_TEMPLATE_LANG ({settings.WHATSAPP_TEMPLATE_LANG}).\n"
            "     If the template has no 'Copy code' button, set "
            "WHATSAPP_OTP_COPY_BUTTON=false."
        )
    print()
    return 1


# --- E-mail -------------------------------------------------------------


def report_email(test_address: str | None = None) -> int:
    """Check SMTP config the same way report() checks OTP delivery.

    Password reset and Green PIN reset both depend on this, and both used to
    fail silently when SMTP was unset - the endpoints now answer 503 instead,
    but only this tells you *why* before a user runs into it.
    """
    import smtplib

    from app.services import email as email_service

    print()
    print(f"Aura X - e-mail delivery check   (APP_ENV={settings.APP_ENV})")
    print("=" * 62)

    if not settings.smtp_enabled:
        print(f"\n{BAD} SMTP_HOST is not set, so no e-mail can be delivered.")
        print("     Password reset and Green PIN reset answer 503")
        print("     (email_provider_missing) rather than silently doing nothing.")
        print("\n  Set: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM")
        print()
        return 1

    print(f"\n  host     : {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    print(f"  user     : {settings.SMTP_USER or '(none)'}")
    print(f"  password : {_mask(settings.SMTP_PASSWORD)}")
    print(f"  from     : {settings.SMTP_FROM}")
    print(f"  starttls : {'yes' if settings.SMTP_TLS else 'no'}")

    # The reset link is built from FRONTEND_URL, so a deployment that never
    # set it mails out working e-mail containing localhost links nobody can
    # open. Cheap to show, and invisible until a user reports a dead link.
    print(f"\n  reset links point at : {settings.FRONTEND_URL}")
    if "localhost" in settings.FRONTEND_URL or "127.0.0.1" in settings.FRONTEND_URL:
        if settings.is_production:
            print(f"  {BAD} FRONTEND_URL is still the local default in production.")
            print("         Every reset link mailed out will be unopenable.")
            print("         Set it to your public app URL.")
        else:
            print(f"  {INFO} fine for local development.")

    if settings.SMTP_PORT == 465:
        print(f"\n  {BAD} Port 465 is implicit TLS, which this mailer does not")
        print("         speak - it uses STARTTLS. Use port 587.")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        print(f"\n{OK} Connected and authenticated.")
    except Exception as exc:
        print(f"\n{BAD} SMTP connection failed: {exc}")
        print("     Common causes: wrong port (use 587 for STARTTLS - 465 is")
        print("     implicit TLS and not supported here), an app-specific")
        print("     password required instead of the account password, or a")
        print("     sender domain that is not verified with the provider yet.")
        print()
        return 1

    if not test_address:
        print("\nPass an address to send a real test e-mail, e.g.")
        print("  python main.py check-email you@example.com")
        print()
        return 0

    print(f"\nSending a test message to {test_address} ...")
    sent = email_service.send_verification(test_address, "test-token-not-valid", "there")
    if sent:
        print(f"\n{OK} Accepted by the server - check the inbox, and spam.")
        print("     The link inside will not work; the token is a placeholder.")
        print()
        return 0

    print(f"\n{BAD} Send failed - the log line above carries the reason.")
    print()
    return 1
