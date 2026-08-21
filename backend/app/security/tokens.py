"""Token creation and verification.

Two kinds of token are in play:

* a short-lived signed JWT access token, kept in an HttpOnly cookie;
* opaque high-entropy tokens (refresh, e-mail verification, password reset)
  of which only a SHA-256 digest is ever persisted, so a database leak does
  not hand over usable credentials.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    expires_minutes: int | None = None,
) -> str:
    expires_minutes = expires_minutes or settings.ACCESS_TOKEN_TTL_MINUTES
    issued = _now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "typ": "access",
        "iat": int(issued.timestamp()),
        "exp": int((issued + timedelta(minutes=expires_minutes)).timestamp()),
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Return the claims, or None when the token is invalid or expired."""
    try:
        claims = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    if claims.get("typ") != "access":
        return None
    return claims


def generate_opaque_token(nbytes: int = 32) -> str:
    """A URL-safe secret with at least 256 bits of entropy."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """SHA-256 digest used for database lookups.

    A plain digest is correct here (unlike for passwords) because the token is
    already high-entropy random, so there is nothing to brute-force.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)


def refresh_expiry() -> datetime:
    return _now() + timedelta(days=settings.REFRESH_TOKEN_TTL_DAYS)


def verification_expiry(hours: int = 1) -> datetime:
    return _now() + timedelta(hours=hours)
