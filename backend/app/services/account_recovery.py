"""Password recovery by identifier, without a delivery channel.

The trust model here is deliberately weaker than the token-by-e-mail flow in
``auth.py``, and that is a product decision rather than an oversight: an
identifier - e-mail, phone or username - names an account but does not prove
control of it, so anyone who knows a user's e-mail address can reset that
user's password. It exists so the app is usable while no SMTP or SMS provider
is configured. Prefer ``forgot-password`` once one is.

What can be defended without a delivery channel is defended:

* the account is never revealed - a wrong identifier and a locked account are
  answered identically, so this cannot be used to enumerate users;
* attempts are rate limited per identifier *and* per caller IP;
* every reset is written to the audit log;
* all existing sessions are revoked, so a reset always evicts whoever else
  was signed in - the legitimate owner included.
"""

from __future__ import annotations

import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import BadRequest
from app.models.enums import AuditAction
from app.models.user import User, UserProfile
from app.services import audit, auth as auth_service

USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,32}$")


def normalise_username(raw: str) -> str:
    candidate = (raw or "").strip().lower()
    if not USERNAME_PATTERN.match(candidate):
        raise BadRequest(
            "Usernames are 3-32 characters, using lower-case letters, numbers "
            "or underscores.",
            code="invalid_username",
        )
    return candidate


def suggest_username(db: Session, full_name: str) -> str:
    """First name, with a numeric suffix if it is already taken."""
    base = re.sub(r"[^a-z0-9]", "", (full_name or "").strip().split(" ")[0].lower())[:24]
    base = base or "user"

    candidate = base
    suffix = 2
    while db.execute(
        select(User.id).where(User.username == candidate)
    ).scalar_one_or_none() is not None:
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def find_by_identifier(db: Session, identifier: str) -> User | None:
    """Resolve an e-mail, phone number or username to one account.

    Phone matching covers both the verified sign-in number on ``User`` and the
    unverified contact number on the profile, since a user recalling "my
    number" does not know which of the two the app stored.
    """
    value = (identifier or "").strip()
    if not value:
        return None

    lowered = value.lower()
    candidates = [User.email == lowered, User.username == lowered]

    # Accept a phone with or without the country code prefix, and ignore the
    # spaces and dashes people type.
    digits = re.sub(r"[^0-9+]", "", value)
    if len(re.sub(r"[^0-9]", "", digits)) >= 8:
        candidates.append(User.phone == digits)
        if not digits.startswith("+"):
            candidates.append(User.phone.like(f"%{digits}"))

    user = db.execute(select(User).where(or_(*candidates))).scalars().first()
    if user is not None:
        return user

    if len(re.sub(r"[^0-9]", "", digits)) >= 8:
        profile_match = db.execute(
            select(UserProfile).where(
                or_(
                    UserProfile.phone == digits,
                    UserProfile.phone.like(f"%{digits}"),
                )
            )
        ).scalars().first()
        if profile_match is not None:
            return db.get(User, profile_match.user_id)

    return None


def recover_password(db: Session, identifier: str, new_password: str) -> User | None:
    """Set a new password for the named account.

    Returns the user on success, or ``None`` when the identifier matches
    nothing or names a deactivated account - the caller answers identically
    either way so that a wrong guess reveals nothing.
    """
    # Validate the password before the lookup: a weak-password complaint must
    # not depend on whether the account exists, or it becomes an oracle.
    auth_service.validate_password_strength(new_password)

    user = find_by_identifier(db, identifier)
    if user is None or not user.is_active:
        return None

    auth_service.set_password(db, user, new_password)
    revoked = auth_service.revoke_all_sessions(db, user.id)
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.UPDATE.value,
        entity_type="user",
        entity_id=user.id,
        summary="Password reset via account recovery",
        meta={"sessions_revoked": revoked},
    )
    return user
