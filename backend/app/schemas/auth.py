"""Authentication, profile and security schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = True


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10, max_length=256)


class ProfileOut(ORMModel):
    display_name: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    locale: str = "en-IN"
    theme: str = "system"
    privacy_mode_default: bool = True
    dashboard_layout: dict | None = None
    bio: str | None = None


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    username: str | None = Field(default=None, max_length=32)
    full_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    date_of_birth: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=10)
    theme: str | None = None
    privacy_mode_default: bool | None = None
    dashboard_layout: dict | None = None
    bio: str | None = Field(default=None, max_length=500)

    @field_validator("theme")
    @classmethod
    def _valid_theme(cls, v: str | None) -> str | None:
        if v is not None and v not in {"light", "dark", "system"}:
            raise ValueError("Theme must be light, dark or system.")
        return v


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None = None
    profile: ProfileOut | None = None
    has_password: bool = False
    google_linked: bool = False
    phone: str | None = None
    phone_verified: bool = False
    username: str | None = None


class PhoneOtpRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class PhoneLoginRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    code: str = Field(min_length=4, max_length=8)
    #: Only used the first time this number signs in, to name the new
    #: account it creates. Ignored for a number that already has one.
    full_name: str | None = Field(default=None, max_length=120)


class PhoneVerifyRequest(BaseModel):
    code: str = Field(min_length=4, max_length=8)


class RecoverPasswordRequest(BaseModel):
    """Reset by identifier, with no token and no delivery channel.

    ``identifier`` is an e-mail address, phone number or username - whichever
    the user remembers.
    """

    identifier: str = Field(min_length=3, max_length=320)
    new_password: str = Field(min_length=8, max_length=128)


class OtpSentResponse(BaseModel):
    message: str
    expires_in_minutes: int
    #: Channel the code actually went out on - "whatsapp", "sms", or "none"
    #: when no provider is configured and the code is returned inline below.
    channel: str = "none"
    #: Populated only in development when no SMS provider is configured, so
    #: the flow can be exercised end-to-end without sending a real text.
    debug_code: str | None = None


class SessionOut(ORMModel):
    id: uuid.UUID
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime
    is_current: bool = False


class AuthResponse(BaseModel):
    """Returned after login/register. Tokens travel in HttpOnly cookies, never
    in this body; only the CSRF token is client-readable by design."""

    user: UserOut
    csrf_token: str
    financial: "FinancialStatus"


# --- Green PIN ---------------------------------------------------------


class PinRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=4)

    @field_validator("pin")
    @classmethod
    def _digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("The Green PIN must be 4 digits.")
        return v


class SetPinRequest(BaseModel):
    new_pin: str = Field(min_length=4, max_length=4)
    current_pin: str | None = Field(default=None, min_length=4, max_length=4)

    @field_validator("new_pin", "current_pin")
    @classmethod
    def _digits(cls, v: str | None) -> str | None:
        if v is not None and not v.isdigit():
            raise ValueError("The Green PIN must be 4 digits.")
        return v


class ResetPinRequest(BaseModel):
    token: str = Field(min_length=10, max_length=256)
    new_pin: str = Field(min_length=4, max_length=4)

    @field_validator("new_pin")
    @classmethod
    def _digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("The Green PIN must be 4 digits.")
        return v


class FinancialStatus(BaseModel):
    """Whether this session may currently see confidential figures."""

    pin_configured: bool
    unlocked: bool
    seconds_remaining: int
    unlock_minutes: int
    attempts_remaining: int
    locked_out: bool
    locked_until: str | None = None
    mask_ledger_amounts: bool = False


class SecurityPreferences(BaseModel):
    unlock_minutes: int | None = Field(default=None, ge=1, le=60)
    mask_ledger_amounts: bool | None = None


AuthResponse.model_rebuild()
