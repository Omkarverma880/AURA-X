"""Application configuration, loaded from the environment.

Secrets are never hard-coded: everything comes from environment variables
(or a local .env file that is git-ignored).
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Core ---------------------------------------------------------
    APP_NAME: str = "Aura X"
    APP_ENV: Literal["development", "test", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(64))
    API_PREFIX: str = "/api/v1"

    # --- Database -----------------------------------------------------
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/aurax"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # --- URLs / CORS --------------------------------------------------
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173"
    SERVE_FRONTEND: bool = False

    # --- Auth ---------------------------------------------------------
    ACCESS_TOKEN_TTL_MINUTES: int = 30
    REFRESH_TOKEN_TTL_DAYS: int = 30
    COOKIE_SECURE: bool = False
    COOKIE_DOMAIN: str = ""
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    ACCESS_COOKIE_NAME: str = "bk_access"
    REFRESH_COOKIE_NAME: str = "bk_refresh"
    CSRF_COOKIE_NAME: str = "bk_csrf"

    # --- Green PIN ----------------------------------------------------
    FINANCE_UNLOCK_MINUTES: int = 5
    GREEN_PIN_MAX_ATTEMPTS: int = 5
    GREEN_PIN_LOCKOUT_SECONDS: int = 300

    # --- Google OAuth -------------------------------------------------
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # --- Phone / OTP sign-in -------------------------------------------
    OTP_LENGTH: int = 6
    OTP_TTL_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_SECONDS: int = 45
    #: Which channel to deliver codes over. "auto" tries WhatsApp first and
    #: falls back to SMS, which is what most Indian apps do now that A2P SMS
    #: needs DLT registration while WhatsApp does not.
    OTP_CHANNEL: Literal["auto", "whatsapp", "sms"] = "auto"

    # WhatsApp — Meta Cloud API (graph.facebook.com). Free to start, no DLT
    # registration, but OTP text must go out as an approved *authentication*
    # template rather than free-form text.
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_OTP_TEMPLATE: str = "otp_login"
    WHATSAPP_TEMPLATE_LANG: str = "en_US"
    #: Meta's authentication templates normally carry a "Copy code" button,
    #: which must be filled in with the same code as the body. Set false only
    #: if your approved template has no button.
    WHATSAPP_OTP_COPY_BUTTON: bool = True
    WHATSAPP_API_VERSION: str = "v21.0"

    # WhatsApp / SMS — Twilio. One account covers both channels; WhatsApp
    # additionally needs a sender (the sandbox number works for testing).
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    TWILIO_MESSAGING_SERVICE_SID: str = ""
    TWILIO_WHATSAPP_FROM: str = ""

    # SMS — MSG91 (India). Uses their OTP endpoint, so the code is passed as a
    # template variable rather than as raw body text.
    MSG91_AUTH_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""
    MSG91_SENDER_ID: str = "AURAXX"
    MSG91_OTP_VAR: str = "otp"

    #: Generic webhook-style SMS gateway (any provider fronted by a small
    #: relay that accepts {to, message}). Left blank in development, where
    #: the code is logged instead of sent.
    SMS_WEBHOOK_URL: str = ""
    SMS_API_KEY: str = ""
    SMS_SENDER_ID: str = "AuraX"

    # --- SMTP ---------------------------------------------------------
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "Aura X <no-reply@aurax.app>"
    SMTP_TLS: bool = True

    # --- Storage ------------------------------------------------------
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_ENDPOINT: str = ""
    STORAGE_REGION: str = "auto"
    STORAGE_BUCKET: str = "aurax-media"
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""
    STORAGE_PUBLIC_BASE_URL: str = ""
    STORAGE_LOCAL_DIR: str = "media"
    MAX_UPLOAD_MB: int = 10

    # --- Misc ---------------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    DEFAULT_CURRENCY: str = "INR"
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalise_db_url(cls, v: str) -> str:
        """Railway and Heroku hand out postgres:// URLs; SQLAlchemy 2 wants an
        explicit driver, so normalise everything onto psycopg3."""
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+psycopg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        raw = [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",")]
        return [o for o in raw if o]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def google_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.SMTP_HOST)

    @property
    def twilio_enabled(self) -> bool:
        return bool(self.TWILIO_ACCOUNT_SID and self.TWILIO_AUTH_TOKEN)

    @property
    def whatsapp_meta_enabled(self) -> bool:
        return bool(self.WHATSAPP_PHONE_NUMBER_ID and self.WHATSAPP_ACCESS_TOKEN)

    @property
    def whatsapp_twilio_enabled(self) -> bool:
        return bool(self.twilio_enabled and self.TWILIO_WHATSAPP_FROM)

    @property
    def whatsapp_enabled(self) -> bool:
        return self.whatsapp_meta_enabled or self.whatsapp_twilio_enabled

    @property
    def twilio_sms_enabled(self) -> bool:
        return bool(
            self.twilio_enabled
            and (self.TWILIO_FROM_NUMBER or self.TWILIO_MESSAGING_SERVICE_SID)
        )

    @property
    def msg91_enabled(self) -> bool:
        return bool(self.MSG91_AUTH_KEY and self.MSG91_TEMPLATE_ID)

    @property
    def sms_enabled(self) -> bool:
        return bool(self.SMS_WEBHOOK_URL or self.twilio_sms_enabled or self.msg91_enabled)

    @property
    def otp_delivery_enabled(self) -> bool:
        """True when *some* provider can actually deliver a code.

        The OTP endpoints check this rather than ``sms_enabled`` so that a
        WhatsApp-only deployment is not mistaken for an unconfigured one.
        """
        return self.sms_enabled or self.whatsapp_enabled

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
