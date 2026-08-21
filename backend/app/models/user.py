"""Identity, authentication and per-user security settings."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings as app_settings
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, user_fk
from app.db.types import GUID, JSONType
from app.models.enums import AuthProvider, Theme


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    #: Always stored lower-cased so lookups are case-insensitive on any engine.
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Short handle, always lower-cased. Used to tell accounts apart during
    #: password recovery when someone does not recall which e-mail they signed
    #: up with. An identifier, not a secret - it authenticates nothing.
    username: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    #: Alternate sign-in identifier, E.164 format (e.g. +919876543210). Only
    #: usable for login once verified via OTP - see PhoneOtp.
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped["UserProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    auth_accounts: Mapped[list["AuthAccount"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    security: Mapped["SecuritySetting"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(120))
    avatar_key: Mapped[str | None] = mapped_column(String(512))
    phone: Mapped[str | None] = mapped_column(String(32))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default=app_settings.DEFAULT_CURRENCY)
    timezone: Mapped[str] = mapped_column(String(64), default=app_settings.DEFAULT_TIMEZONE)
    locale: Mapped[str] = mapped_column(String(10), default="en-IN")
    theme: Mapped[str] = mapped_column(String(10), default=Theme.SYSTEM.value)
    #: Mask sensitive figures the moment the app loads.
    privacy_mode_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    #: Order/visibility of dashboard cards - lets the dashboard be personalised
    #: later without a schema change.
    dashboard_layout: Mapped[dict | None] = mapped_column(JSONType)
    bio: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="profile")


class AuthAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One row per sign-in method. A user may hold both a password account and
    a linked Google account against the same identity."""

    __tablename__ = "auth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id", name="uq_auth_provider_account"),
        UniqueConstraint("user_id", "provider", name="uq_auth_user_provider"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default=AuthProvider.PASSWORD.value)
    #: Google's stable subject id; NULL for password accounts.
    provider_account_id: Mapped[str | None] = mapped_column(String(255))
    #: Argon2id hash. Plaintext passwords are never stored anywhere.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email: Mapped[str | None] = mapped_column(String(320))

    user: Mapped[User] = relationship(back_populates="auth_accounts")


class SecuritySetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Green PIN state and financial-privacy preferences."""

    __tablename__ = "security_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    #: Argon2id hash of the 4-digit Green PIN. Never stored in plaintext.
    green_pin_hash: Mapped[str | None] = mapped_column(String(255))
    green_pin_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Brute-force protection: a 4-digit PIN has only 10k combinations, so
    #: throttling is what actually makes it safe.
    failed_pin_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pin_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_pin_lockouts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: How long an unlock lasts before it relocks automatically.
    unlock_minutes: Mapped[int] = mapped_column(
        Integer, default=app_settings.FINANCE_UNLOCK_MINUTES, nullable=False
    )
    #: Whether Bahi Khata amounts are treated as sensitive too.
    mask_ledger_amounts: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="security")

    @property
    def is_pin_set(self) -> bool:
        return bool(self.green_pin_hash)


class UserSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A refresh-token session. Rows are revocable, which is what makes
    "log out everywhere" and the manual financial re-lock possible."""

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = user_fk()
    #: SHA-256 of the opaque refresh token - the raw token only ever exists in
    #: the user's HttpOnly cookie.
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(400))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Green PIN unlock window. Server-side so "Lock now" is instant and the
    #: frontend lock is never the security boundary.
    finance_unlocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class PhoneOtp(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A short-lived one-time code sent by SMS.

    Not tied to a user_id: the "login" purpose is looked up by phone number
    (the account may already exist), while the "link" purpose is issued to an
    authenticated user linking a new number to their account. Only the hash of
    the code is stored.
    """

    __tablename__ = "phone_otp_codes"

    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    #: Set only for "link" - the account requesting the number be added.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VerificationToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Single-use, expiring token for e-mail verification, password reset and
    Green PIN reset. Only the hash is persisted."""

    __tablename__ = "verification_tokens"

    user_id: Mapped[uuid.UUID] = user_fk()
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()
