"""Authentication: registration, login, sessions, password lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BadRequest, Conflict, Unauthorized
from app.core.logging import get_logger
from app.models.enums import AuditAction, AuthProvider, TokenPurpose
from app.models.user import (
    AuthAccount,
    SecuritySetting,
    User,
    UserProfile,
    UserSession,
    VerificationToken,
)
from app.security.hashing import (
    dummy_verify,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.security.tokens import (
    create_access_token,
    generate_opaque_token,
    hash_token,
    refresh_expiry,
    verification_expiry,
)
from app.services import audit, defaults

logger = get_logger(__name__)

MIN_PASSWORD_LENGTH = 8


def normalise_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == normalise_email(email))).scalar_one_or_none()


def validate_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise BadRequest(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if password.isdigit() or password.isalpha():
        raise BadRequest("Password must mix letters with numbers or symbols.")


# --- Registration ------------------------------------------------------


def create_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    password: str | None = None,
    provider: AuthProvider = AuthProvider.PASSWORD,
    provider_account_id: str | None = None,
    is_verified: bool = False,
) -> User:
    email = normalise_email(email)
    if get_user_by_email(db, email):
        raise Conflict("An account with this e-mail already exists.")

    if provider == AuthProvider.PASSWORD:
        if not password:
            raise BadRequest("A password is required.")
        validate_password_strength(password)

    user = User(
        email=email,
        full_name=full_name.strip() or email.split("@")[0],
        is_active=True,
        is_verified=is_verified,
    )
    db.add(user)
    db.flush()

    # Assigned here rather than left to the user, so every account has an
    # identifier it can be recovered by from the very first login. Imported
    # locally: account_recovery imports this module for password helpers.
    from app.services.account_recovery import suggest_username

    user.username = suggest_username(db, user.full_name)
    db.flush()

    db.add(
        AuthAccount(
            user_id=user.id,
            provider=provider.value,
            provider_account_id=provider_account_id,
            password_hash=hash_password(password) if password else None,
            password_changed_at=datetime.now(timezone.utc) if password else None,
            email=email,
        )
    )
    db.add(UserProfile(user_id=user.id, display_name=user.full_name))
    db.add(SecuritySetting(user_id=user.id))
    defaults.seed_user_defaults(db, user.id)
    db.flush()
    return user


# --- Login -------------------------------------------------------------


def authenticate(db: Session, email: str, password: str) -> User:
    """Verify credentials.

    The same error is returned for an unknown e-mail and for a wrong password,
    and a dummy hash is verified in the unknown-user branch, so response timing
    does not reveal which accounts exist.
    """
    user = get_user_by_email(db, email)
    if user is None:
        dummy_verify()
        raise Unauthorized("Incorrect e-mail or password.", code="invalid_credentials")

    account = db.execute(
        select(AuthAccount).where(
            AuthAccount.user_id == user.id,
            AuthAccount.provider == AuthProvider.PASSWORD.value,
        )
    ).scalar_one_or_none()

    if account is None or not account.password_hash:
        dummy_verify()
        raise Unauthorized(
            "This account uses Google sign-in. Continue with Google, or set a password "
            "using Forgot password.",
            code="wrong_provider",
        )

    if not verify_password(password, account.password_hash):
        raise Unauthorized("Incorrect e-mail or password.", code="invalid_credentials")

    if not user.is_active:
        raise Unauthorized("This account has been deactivated.", code="account_disabled")

    # Transparently upgrade the stored hash when cost parameters change.
    if password_needs_rehash(account.password_hash):
        account.password_hash = hash_password(password)

    return user


def upsert_google_user(
    db: Session, *, google_sub: str, email: str, full_name: str, picture: str | None = None
) -> User:
    """Find or create the account behind a verified Google identity."""
    email = normalise_email(email)
    account = db.execute(
        select(AuthAccount).where(
            AuthAccount.provider == AuthProvider.GOOGLE.value,
            AuthAccount.provider_account_id == google_sub,
        )
    ).scalar_one_or_none()
    if account is not None:
        return db.get(User, account.user_id)

    user = get_user_by_email(db, email)
    if user is not None:
        # Link Google to the existing password account. Safe because Google has
        # already verified ownership of this address.
        db.add(
            AuthAccount(
                user_id=user.id,
                provider=AuthProvider.GOOGLE.value,
                provider_account_id=google_sub,
                email=email,
            )
        )
        user.is_verified = True
        db.flush()
        return user

    return create_user(
        db,
        email=email,
        full_name=full_name,
        provider=AuthProvider.GOOGLE,
        provider_account_id=google_sub,
        is_verified=True,
    )


# --- Sessions ----------------------------------------------------------


class IssuedSession:
    def __init__(self, session: UserSession, refresh_token: str, access_token: str) -> None:
        self.session = session
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.csrf_token = session.csrf_token


def start_session(
    db: Session, user: User, *, user_agent: str | None = None, ip_address: str | None = None
) -> IssuedSession:
    refresh_token = generate_opaque_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        csrf_token=generate_opaque_token(16),
        user_agent=(user_agent or "")[:400] or None,
        ip_address=ip_address,
        expires_at=refresh_expiry(),
        last_used_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.flush()
    user.last_login_at = datetime.now(timezone.utc)
    access_token = create_access_token(user.id, session.id)
    return IssuedSession(session, refresh_token, access_token)


def get_active_session(db: Session, session_id: uuid.UUID) -> UserSession | None:
    session = db.get(UserSession, session_id)
    if session is None or session.revoked_at is not None:
        return None
    if is_expired(session.expires_at):
        return None
    return session


def rotate_session(db: Session, refresh_token: str) -> IssuedSession:
    """Exchange a refresh token for a fresh pair.

    The old token is replaced in the same transaction (rotation), so a stolen
    refresh token stops working as soon as the real user refreshes.
    """
    session = db.execute(
        select(UserSession).where(UserSession.refresh_token_hash == hash_token(refresh_token))
    ).scalar_one_or_none()

    if session is None or session.revoked_at is not None or is_expired(session.expires_at):
        raise Unauthorized("Session expired. Please login again.")

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise Unauthorized("Session expired. Please login again.")

    new_refresh = generate_opaque_token()
    session.refresh_token_hash = hash_token(new_refresh)
    session.last_used_at = datetime.now(timezone.utc)
    session.expires_at = refresh_expiry()
    db.flush()

    access_token = create_access_token(user.id, session.id)
    return IssuedSession(session, new_refresh, access_token)


def revoke_session(db: Session, session: UserSession) -> None:
    session.revoked_at = datetime.now(timezone.utc)
    session.finance_unlocked_until = None


def revoke_all_sessions(
    db: Session, user_id: uuid.UUID, *, except_id: uuid.UUID | None = None
) -> int:
    stmt = select(UserSession).where(
        UserSession.user_id == user_id, UserSession.revoked_at.is_(None)
    )
    count = 0
    for session in db.execute(stmt).scalars():
        if except_id and session.id == except_id:
            continue
        revoke_session(db, session)
        count += 1
    return count


def list_sessions(db: Session, user_id: uuid.UUID) -> list[UserSession]:
    stmt = (
        select(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .order_by(UserSession.last_used_at.desc())
    )
    return [s for s in db.execute(stmt).scalars() if not is_expired(s.expires_at)]


# --- Password lifecycle ------------------------------------------------


def issue_verification_token(
    db: Session, user_id: uuid.UUID, purpose: TokenPurpose, *, hours: int = 1
) -> str:
    """Create a single-use token and persist only its digest."""
    token = generate_opaque_token()
    db.add(
        VerificationToken(
            user_id=user_id,
            token_hash=hash_token(token),
            purpose=purpose.value,
            expires_at=verification_expiry(hours),
        )
    )
    db.flush()
    return token


def consume_verification_token(db: Session, token: str, purpose: TokenPurpose) -> User:
    row = db.execute(
        select(VerificationToken).where(VerificationToken.token_hash == hash_token(token))
    ).scalar_one_or_none()

    if (
        row is None
        or row.purpose != purpose.value
        or row.used_at is not None
        or is_expired(row.expires_at)
    ):
        raise BadRequest("This link is invalid or has expired. Please request a new one.")

    row.used_at = datetime.now(timezone.utc)
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise BadRequest("This link is invalid or has expired. Please request a new one.")
    return user


def set_password(db: Session, user: User, new_password: str) -> None:
    validate_password_strength(new_password)
    account = db.execute(
        select(AuthAccount).where(
            AuthAccount.user_id == user.id,
            AuthAccount.provider == AuthProvider.PASSWORD.value,
        )
    ).scalar_one_or_none()

    if account is None:
        # A Google-only user setting a password for the first time.
        account = AuthAccount(
            user_id=user.id, provider=AuthProvider.PASSWORD.value, email=user.email
        )
        db.add(account)

    account.password_hash = hash_password(new_password)
    account.password_changed_at = datetime.now(timezone.utc)
    db.flush()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    account = db.execute(
        select(AuthAccount).where(
            AuthAccount.user_id == user.id,
            AuthAccount.provider == AuthProvider.PASSWORD.value,
        )
    ).scalar_one_or_none()

    if account and account.password_hash:
        if not verify_password(current_password, account.password_hash):
            raise BadRequest("Your current password is incorrect.")
    if new_password == current_password:
        raise BadRequest("The new password must be different from the current one.")

    set_password(db, user, new_password)
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.PASSWORD_CHANGED.value,
        entity_type="user",
        entity_id=user.id,
        summary="Password changed",
    )


def cleanup_expired(db: Session) -> None:
    """Best-effort housekeeping of stale sessions and used tokens."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)
    for session in db.execute(select(UserSession).where(UserSession.expires_at < cutoff)).scalars():
        db.delete(session)
    for token in db.execute(
        select(VerificationToken).where(VerificationToken.expires_at < cutoff)
    ).scalars():
        db.delete(token)


def is_expired(moment: datetime | None) -> bool:
    """Compare against now in UTC, tolerating naive values.

    SQLite drops timezone information, so timestamps read back from the test
    database are naive and would otherwise raise on comparison.
    """
    if moment is None:
        return True
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment < datetime.now(timezone.utc)
