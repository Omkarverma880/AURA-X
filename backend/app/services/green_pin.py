"""Green PIN - the second factor guarding sensitive financial data.

The Green PIN is deliberately not the login password. It exists for a specific
threat: somebody glancing at the screen while the app is open. Salary, income,
expense totals and portfolio values stay masked until the PIN is entered, and
the unlock is short-lived.

Two properties make a 4-digit secret defensible here:

1. The hash is Argon2id, so a database leak does not yield the PIN cheaply.
2. Online guessing is throttled and then locked out with an escalating
   cooldown, which is what actually stops the 10,000-guess search.

The unlock lives on the server session row, never in a client-held flag, so
"Lock now" is instant and a tampered frontend gains nothing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BadRequest, InvalidGreenPin, RateLimited
from app.models.enums import AuditAction
from app.models.user import SecuritySetting, User, UserSession
from app.security.hashing import hash_pin, verify_pin
from app.services import audit

PIN_LENGTH = 4
MAX_LOCKOUT_SECONDS = 3600

#: Sequences and repeats that offer no protection at all.
_WEAK_PINS = {
    "0000", "1111", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999",
    "1234", "2345", "3456", "4567", "5678", "6789", "0123",
    "4321", "5432", "6543", "7654", "8765", "9876", "3210",
}


def get_security(db: Session, user_id) -> SecuritySetting:
    security = db.execute(
        select(SecuritySetting).where(SecuritySetting.user_id == user_id)
    ).scalar_one_or_none()
    if security is None:
        # Older accounts, or a user created outside the normal flow.
        security = SecuritySetting(user_id=user_id)
        db.add(security)
        db.flush()
    return security


def validate_pin_format(pin: str) -> None:
    if not pin.isdigit() or len(pin) != PIN_LENGTH:
        raise BadRequest(f"The Green PIN must be exactly {PIN_LENGTH} digits.")
    if pin in _WEAK_PINS:
        raise BadRequest("That PIN is too easy to guess. Choose a less predictable one.")


def set_pin(db: Session, user: User, new_pin: str, *, current_pin: str | None = None) -> None:
    """Set or change the Green PIN.

    Changing an existing PIN requires the current one. Resetting a forgotten
    PIN goes through the e-mail-verified flow in reset_pin_with_token instead:
    the frontend can never simply post a new PIN.
    """
    security = get_security(db, user.id)
    changing = security.is_pin_set

    if changing:
        if not current_pin:
            raise BadRequest("Enter your current Green PIN to change it.")
        _assert_not_locked(security)
        if not verify_pin(current_pin, security.green_pin_hash):
            _register_failure(db, security, user)
            raise InvalidGreenPin()

    validate_pin_format(new_pin)
    if changing and current_pin == new_pin:
        raise BadRequest("The new PIN must be different from your current PIN.")

    security.green_pin_hash = hash_pin(new_pin)
    security.green_pin_set_at = datetime.now(timezone.utc)
    security.failed_pin_attempts = 0
    security.pin_locked_until = None

    audit.record(
        db,
        user_id=user.id,
        action=(AuditAction.PIN_CHANGED if changing else AuditAction.PIN_SET).value,
        entity_type="security_setting",
        entity_id=security.id,
        summary="Green PIN changed" if changing else "Green PIN created",
    )


def reset_pin_with_token(db: Session, user: User, new_pin: str) -> None:
    """Set a new PIN after the identity check in the reset-token flow."""
    validate_pin_format(new_pin)
    security = get_security(db, user.id)
    security.green_pin_hash = hash_pin(new_pin)
    security.green_pin_set_at = datetime.now(timezone.utc)
    security.failed_pin_attempts = 0
    security.pin_locked_until = None
    security.total_pin_lockouts = 0

    # Every existing unlock is dropped: a PIN reset invalidates prior access.
    for session in db.execute(
        select(UserSession).where(UserSession.user_id == user.id)
    ).scalars():
        session.finance_unlocked_until = None

    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.PIN_CHANGED.value,
        entity_type="security_setting",
        entity_id=security.id,
        summary="Green PIN reset via verified e-mail",
    )


def unlock(db: Session, user: User, session: UserSession, pin: str) -> datetime:
    """Verify the PIN and open the financial window for this session."""
    security = get_security(db, user.id)
    if not security.is_pin_set:
        raise BadRequest(
            "No Green PIN has been set up yet. Create one in Settings to protect "
            "your financial data.",
            code="pin_not_set",
        )

    _assert_not_locked(security)

    if not verify_pin(pin, security.green_pin_hash):
        remaining = _register_failure(db, security, user)
        if remaining <= 0:
            raise RateLimited(
                "Too many incorrect attempts. Financial data is locked for "
                f"{_cooldown_seconds(security) // 60} minutes.",
                code="pin_locked_out",
                details={"locked_until": _iso(security.pin_locked_until)},
            )
        raise InvalidGreenPin(
            f"Invalid Green PIN. {remaining} attempt(s) remaining.",
            details={"attempts_remaining": remaining},
        )

    security.failed_pin_attempts = 0
    security.pin_locked_until = None
    unlocked_until = datetime.now(timezone.utc) + timedelta(minutes=security.unlock_minutes)
    session.finance_unlocked_until = unlocked_until

    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.PIN_UNLOCK.value,
        entity_type="user_session",
        entity_id=session.id,
        summary="Financial data unlocked",
    )
    return unlocked_until


def lock(db: Session, user: User, session: UserSession) -> None:
    """Relock immediately, e.g. the Lock Financial Data button."""
    session.finance_unlocked_until = None
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.PIN_LOCK.value,
        entity_type="user_session",
        entity_id=session.id,
        summary="Financial data locked",
    )


def is_unlocked(session: UserSession | None) -> bool:
    if session is None or session.finance_unlocked_until is None:
        return False
    return _aware(session.finance_unlocked_until) > datetime.now(timezone.utc)


def seconds_remaining(session: UserSession | None) -> int:
    if not is_unlocked(session):
        return 0
    delta = _aware(session.finance_unlocked_until) - datetime.now(timezone.utc)
    return max(int(delta.total_seconds()), 0)


def status(db: Session, user: User, session: UserSession | None) -> dict:
    security = get_security(db, user.id)
    locked_until = security.pin_locked_until
    return {
        "pin_configured": security.is_pin_set,
        "unlocked": is_unlocked(session),
        "seconds_remaining": seconds_remaining(session),
        "unlock_minutes": security.unlock_minutes,
        "attempts_remaining": max(
            settings.GREEN_PIN_MAX_ATTEMPTS - security.failed_pin_attempts, 0
        ),
        "locked_out": _is_locked_out(security),
        "locked_until": _iso(locked_until) if _is_locked_out(security) else None,
        "mask_ledger_amounts": security.mask_ledger_amounts,
    }


# --- internals ---------------------------------------------------------


def _register_failure(db: Session, security: SecuritySetting, user: User) -> int:
    """Count a bad attempt and start a cooldown once the budget is spent."""
    security.failed_pin_attempts += 1
    remaining = settings.GREEN_PIN_MAX_ATTEMPTS - security.failed_pin_attempts

    if remaining <= 0:
        security.total_pin_lockouts += 1
        security.pin_locked_until = datetime.now(timezone.utc) + timedelta(
            seconds=_cooldown_seconds(security)
        )
        security.failed_pin_attempts = 0

    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.PIN_FAILED.value,
        entity_type="security_setting",
        entity_id=security.id,
        summary="Incorrect Green PIN attempt",
        meta={"attempts_remaining": max(remaining, 0)},
    )
    # Committed even though the request fails: the counter must survive the
    # rejected request, otherwise the lockout could never accumulate.
    db.commit()
    return max(remaining, 0)


def _cooldown_seconds(security: SecuritySetting) -> int:
    """Each repeated lockout doubles the wait, capped at an hour."""
    exponent = max(security.total_pin_lockouts - 1, 0)
    return min(settings.GREEN_PIN_LOCKOUT_SECONDS * (2**exponent), MAX_LOCKOUT_SECONDS)


def _is_locked_out(security: SecuritySetting) -> bool:
    if security.pin_locked_until is None:
        return False
    return _aware(security.pin_locked_until) > datetime.now(timezone.utc)


def _assert_not_locked(security: SecuritySetting) -> None:
    if _is_locked_out(security):
        wait = int((_aware(security.pin_locked_until) - datetime.now(timezone.utc)).total_seconds())
        minutes = max(wait // 60, 1)
        raise RateLimited(
            f"Too many incorrect attempts. Try again in {minutes} minute(s).",
            code="pin_locked_out",
            details={"locked_until": _iso(security.pin_locked_until), "retry_after": wait},
        )


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _iso(moment: datetime | None) -> str | None:
    return _aware(moment).isoformat() if moment else None
