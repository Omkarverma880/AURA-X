"""FastAPI dependencies: authentication, CSRF and the financial unlock gate.

Every authenticated route derives its user from the signed access cookie. A
user_id supplied in a path, query string or request body is never trusted as an
identity - it is only ever used as a lookup key that is then filtered by the
authenticated owner.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import Forbidden, Unauthorized
from app.db.session import get_db
from app.models.user import User, UserSession
from app.security.tokens import constant_time_equals, decode_access_token
from app.services import auth as auth_service
from app.services import green_pin

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

DbSession = Annotated[Session, Depends(get_db)]


@dataclass
class ClientInfo:
    ip: str | None
    user_agent: str | None


def get_client_info(request: Request) -> ClientInfo:
    """Best-effort client identity for auditing and rate limiting.

    X-Forwarded-For is only meaningful behind a trusted proxy (Railway sets it);
    the left-most entry is used and never echoed back to any user.
    """
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else None
    )
    return ClientInfo(ip=ip, user_agent=request.headers.get("user-agent"))


ClientCtx = Annotated[ClientInfo, Depends(get_client_info)]


def _extract_access_token(request: Request) -> str | None:
    token = request.cookies.get(settings.ACCESS_COOKIE_NAME)
    if token:
        return token
    header = request.headers.get("authorization") or ""
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


@dataclass
class AuthContext:
    """The authenticated principal for the current request."""

    user: User
    session: UserSession
    via_cookie: bool

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id

    @property
    def finance_unlocked(self) -> bool:
        return green_pin.is_unlocked(self.session)


def get_auth_context(request: Request, db: DbSession) -> AuthContext:
    token = _extract_access_token(request)
    if not token:
        raise Unauthorized("You need to sign in to continue.")

    claims = decode_access_token(token)
    if claims is None:
        raise Unauthorized("Session expired. Please login again.")

    try:
        user_id = uuid.UUID(claims["sub"])
        session_id = uuid.UUID(claims["sid"])
    except (KeyError, ValueError):
        raise Unauthorized("Session expired. Please login again.") from None

    # The session row is authoritative: revoking it logs the user out
    # immediately, even while the signed access token is still within its TTL.
    session = auth_service.get_active_session(db, session_id)
    if session is None or session.user_id != user_id:
        raise Unauthorized("Session expired. Please login again.")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("Session expired. Please login again.")

    via_cookie = bool(request.cookies.get(settings.ACCESS_COOKIE_NAME))
    ctx = AuthContext(user=user, session=session, via_cookie=via_cookie)

    _verify_csrf(request, ctx)
    return ctx


def _verify_csrf(request: Request, ctx: AuthContext) -> None:
    """Double-submit CSRF check for cookie-authenticated state changes.

    Cookies are SameSite=Lax already, which blocks the classic cross-site form
    post; this is the belt-and-braces layer. Bearer-token callers are exempt
    because a browser never attaches that header automatically.
    """
    if request.method in SAFE_METHODS or not ctx.via_cookie:
        return
    header_token = request.headers.get("x-csrf-token", "")
    if not header_token or not constant_time_equals(header_token, ctx.session.csrf_token):
        raise Forbidden(
            "Your session could not be verified. Please refresh the page and try again.",
            code="csrf_failed",
        )


CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]


def get_current_user(ctx: CurrentAuth) -> User:
    return ctx.user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_finance_unlock(ctx: CurrentAuth, db: DbSession) -> AuthContext:
    """Gate for endpoints that return or mutate confidential money data.

    This is the real security boundary. The frontend mask is presentation only;
    a locked session simply never receives the numbers.

    Users who have not set up a Green PIN have opted out of this protection, so
    the gate stays open for them - otherwise the app would be unusable until a
    PIN exists, and a half-blocked app teaches people to work around it.
    """
    if not green_pin.get_security(db, ctx.user_id).is_pin_set:
        return ctx
    if not ctx.finance_unlocked:
        from app.core.errors import FinancialLocked

        raise FinancialLocked()
    return ctx


def finance_visible(ctx: AuthContext, db: Session) -> bool:
    """Whether confidential figures may be included in a mixed response.

    Used by aggregate endpoints (dashboard, analytics) that stay useful while
    locked by returning nulls for the protected fields instead of failing.
    """
    if not green_pin.get_security(db, ctx.user_id).is_pin_set:
        return True
    return ctx.finance_unlocked


UnlockedAuth = Annotated[AuthContext, Depends(require_finance_unlock)]
