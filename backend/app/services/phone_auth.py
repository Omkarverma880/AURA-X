"""Phone-number sign-in.

Mirrors the trust model of the Green PIN and password reset flows: a code is
never trusted on its own claim, the raw value only ever exists in the SMS
itself, and only its hash is persisted. Verification is rate limited and
attempt-capped so a 6-digit code stays safe against online guessing.

Two purposes share the same table:

* "login"  - proves control of a number. Verifying it signs the caller into
  the account already holding that number, or - like Google sign-in -
  transparently creates one on first use. This is the standard phone-first
  pattern (WhatsApp, most Indian/Nepali fintech apps): entering a number
  always gets a code, and the app itself decides sign-in vs sign-up.
* "link"   - an already-authenticated user attaching a new number to their
  account from Settings. That flow still refuses a number already verified
  on someone else's account, since it is changing an existing identity
  rather than creating one.
"""

from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BadRequest, Conflict, RateLimited, Unauthorized
from app.models.enums import AuditAction, AuthProvider
from app.models.user import PhoneOtp, User
from app.security.tokens import hash_token
from app.services import audit
from app.services.auth import create_user, start_session  # re-exported for callers

PHONE_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def normalise_phone(raw: str) -> str:
    """Validate and normalise to E.164 (+countrycode followed by digits)."""
    candidate = raw.strip().replace(" ", "").replace("-", "")
    if not candidate.startswith("+"):
        raise BadRequest(
            "Enter your phone number with the country code, e.g. +91XXXXXXXXXX.",
            code="invalid_phone",
        )
    if not PHONE_PATTERN.match(candidate):
        raise BadRequest("That does not look like a valid phone number.", code="invalid_phone")
    return candidate


def _generate_code() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(settings.OTP_LENGTH))


def _hash_code(phone: str, code: str) -> str:
    # Salted with the phone number so identical codes for different numbers
    # never collide in storage.
    return hash_token(f"{phone}:{code}")


def request_otp(
    db: Session, phone: str, purpose: str, *, user_id: uuid.UUID | None = None
) -> tuple[str, PhoneOtp]:
    """Issue a fresh code, superseding any still-pending one for this phone."""
    recent = db.execute(
        select(PhoneOtp)
        .where(PhoneOtp.phone == phone, PhoneOtp.purpose == purpose, PhoneOtp.consumed_at.is_(None))
        .order_by(PhoneOtp.created_at.desc())
    ).scalars().first()

    if recent is not None:
        age = (datetime.now(timezone.utc) - _aware(recent.created_at)).total_seconds()
        if age < settings.OTP_RESEND_SECONDS:
            raise RateLimited(
                f"Please wait {int(settings.OTP_RESEND_SECONDS - age)} seconds before requesting "
                "another code.",
                details={"retry_after": int(settings.OTP_RESEND_SECONDS - age)},
            )
        recent.consumed_at = datetime.now(timezone.utc)

    code = _generate_code()
    otp = PhoneOtp(
        phone=phone,
        code_hash=_hash_code(phone, code),
        purpose=purpose,
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_TTL_MINUTES),
    )
    db.add(otp)
    db.flush()
    return code, otp


def _consume(db: Session, phone: str, code: str, purpose: str) -> PhoneOtp:
    otp = db.execute(
        select(PhoneOtp)
        .where(PhoneOtp.phone == phone, PhoneOtp.purpose == purpose, PhoneOtp.consumed_at.is_(None))
        .order_by(PhoneOtp.created_at.desc())
    ).scalars().first()

    if otp is None or _expired(otp.expires_at):
        raise BadRequest("That code has expired. Request a new one.", code="otp_expired")

    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise RateLimited("Too many incorrect attempts. Request a new code.", code="otp_locked")

    if not secrets.compare_digest(otp.code_hash, _hash_code(phone, code)):
        otp.attempts += 1
        db.commit()
        remaining = max(settings.OTP_MAX_ATTEMPTS - otp.attempts, 0)
        raise BadRequest(
            f"Incorrect code. {remaining} attempt(s) remaining.",
            code="otp_invalid",
            details={"attempts_remaining": remaining},
        )

    otp.consumed_at = datetime.now(timezone.utc)
    return otp


#: Accounts created straight from a phone number get a synthetic address
#: under a domain the app controls, purely to satisfy User.email's NOT NULL
#: UNIQUE constraint. It is never used for delivery, and the user can attach
#: a real e-mail from Settings whenever they choose to.
#:
#: Deliberately not one of the IANA special-use TLDs (.local/.internal/
#: .invalid/...) - Pydantic's EmailStr rejects those outright regardless of
#: syntax, so a normal-looking subdomain is what actually validates.
_PHONE_EMAIL_DOMAIN = "phone.aurax.app"


def verify_login_otp(db: Session, phone: str, code: str, *, full_name: str | None = None) -> tuple[User, bool]:
    """Verify a login/sign-up code.

    Returns ``(user, created)``. A number already verified on an account
    signs that account in; a number nobody has claimed yet creates a new
    account on the spot - the same trust model as Google sign-in, where
    proving control of the identifier *is* the signup step.
    """
    otp_phone_digits = phone.lstrip("+")
    _consume(db, phone, code, "login")

    user = db.execute(
        select(User).where(User.phone == phone, User.phone_verified.is_(True))
    ).scalar_one_or_none()

    if user is not None:
        if not user.is_active:
            raise Unauthorized("This account has been deactivated.", code="account_disabled")
        return user, False

    user = create_user(
        db,
        email=f"phone-{otp_phone_digits}@{_PHONE_EMAIL_DOMAIN}",
        full_name=(full_name or "").strip() or "New User",
        password=None,
        provider=AuthProvider.PHONE,
        provider_account_id=phone,
        is_verified=False,
    )
    user.phone = phone
    user.phone_verified = True
    db.flush()
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.CREATE.value,
        entity_type="user",
        entity_id=user.id,
        summary="Account created via phone sign-in",
    )
    return user, True


def start_phone_link(db: Session, user: User, phone: str) -> tuple[str, PhoneOtp]:
    existing = db.execute(
        select(User).where(
            User.phone == phone, User.phone_verified.is_(True), User.id != user.id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise Conflict("That phone number is already linked to another account.")
    return request_otp(db, phone, "link", user_id=user.id)


def confirm_phone_link(db: Session, user: User, phone: str, code: str) -> User:
    otp = _consume(db, phone, code, "link")
    if otp.user_id != user.id:
        raise BadRequest("This code was not issued for your account.", code="otp_invalid")

    clash = db.execute(
        select(User).where(
            User.phone == phone, User.phone_verified.is_(True), User.id != user.id
        )
    ).scalar_one_or_none()
    if clash is not None:
        raise Conflict("That phone number is already linked to another account.")

    user.phone = phone
    user.phone_verified = True
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.UPDATE.value,
        entity_type="user",
        entity_id=user.id,
        summary="Linked phone number for sign-in",
    )
    return user


def unlink_phone(db: Session, user: User) -> None:
    user.phone = None
    user.phone_verified = False
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.UPDATE.value,
        entity_type="user",
        entity_id=user.id,
        summary="Unlinked phone number",
    )


def _expired(moment: datetime) -> bool:
    return _aware(moment) < datetime.now(timezone.utc)


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
