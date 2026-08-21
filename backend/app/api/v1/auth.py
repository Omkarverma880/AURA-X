"""Authentication endpoints."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.cookies import clear_auth_cookies, set_auth_cookies
from app.core.config import settings
from app.core.deps import ClientCtx, CurrentAuth, DbSession
from app.core.errors import BadRequest, ServiceUnavailable, Unauthorized
from app.core.logging import get_logger
from app.core.rate_limit import rate_limiter
from app.models.enums import AuditAction, AuthProvider, TokenPurpose
from app.models.user import AuthAccount, User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    OtpSentResponse,
    PhoneLoginRequest,
    PhoneOtpRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserOut,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse
from app.services import audit, auth as auth_service, email as email_service, green_pin
from app.services import phone_auth
from app.services import messaging as sms_service

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
OAUTH_STATE_COOKIE = "bk_oauth_state"


def _serialise_user(db, user: User) -> UserOut:
    accounts = db.execute(
        select(AuthAccount).where(AuthAccount.user_id == user.id)
    ).scalars().all()
    payload = UserOut.model_validate(user)
    payload.has_password = any(a.password_hash for a in accounts)
    payload.google_linked = any(a.provider == AuthProvider.GOOGLE.value for a in accounts)
    return payload


def otp_response(
    db,
    result: "sms_service.DeliveryResult",
    code: str,
    otp,
    *,
    destination: str = "",
) -> "OtpSentResponse":
    """Turn a delivery attempt into a response - or an honest error.

    Previously the endpoints reported "a code has been sent" regardless of
    what the gateway did, so a deployment with no provider configured left
    users waiting on a message that was never going to arrive. Now a failure
    is surfaced, and the pending code is retired first so the resend cooldown
    does not then block the user from trying again.
    """
    if not result.delivered:
        if not settings.is_production:
            # Development: no provider needed, the code comes back inline and
            # the pending OTP stays live so it can actually be verified.
            return OtpSentResponse(
                message="No messaging provider is configured, so the code is shown here.",
                expires_in_minutes=settings.OTP_TTL_MINUTES,
                channel="none",
                debug_code=code,
            )

        # Nothing reached the user, so retire the pending code - otherwise the
        # resend cooldown would block them from trying again for a code they
        # never received.
        otp.consumed_at = datetime.now(timezone.utc)
        db.commit()

        if result.error == "no_provider":
            raise ServiceUnavailable(
                "Verification codes are not set up on this server yet. "
                "Please sign in with your e-mail and password instead.",
                code="otp_provider_missing",
            )
        raise ServiceUnavailable(
            "We could not send your verification code just now. Please try again "
            "in a moment.",
            code="otp_send_failed",
        )

    where = f" to {destination}" if destination else ""
    label = f" {result.channel_label}" if result.channel_label else ""
    return OtpSentResponse(
        message=f"A verification code has been sent{where}{label}.",
        expires_in_minutes=settings.OTP_TTL_MINUTES,
        channel=result.channel,
        debug_code=None,
    )


def _auth_response(db, response: Response, issued, user: User) -> AuthResponse:
    set_auth_cookies(
        response,
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        csrf_token=issued.csrf_token,
    )
    return AuthResponse(
        user=_serialise_user(db, user),
        csrf_token=issued.csrf_token,
        financial=green_pin.status(db, user, issued.session),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, response: Response, db: DbSession, client: ClientCtx
) -> AuthResponse:
    """Create an account and sign the new user straight in."""
    rate_limiter.check("register", client.ip or "unknown")

    user = auth_service.create_user(
        db,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
    )
    issued = auth_service.start_session(
        db, user, user_agent=client.user_agent, ip_address=client.ip
    )
    token = auth_service.issue_verification_token(
        db, user.id, TokenPurpose.EMAIL_VERIFY, hours=24
    )
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.CREATE.value,
        entity_type="user",
        entity_id=user.id,
        summary="Account created",
        ip_address=client.ip,
        user_agent=client.user_agent,
    )
    db.commit()

    email_service.send_verification(user.email, token, user.full_name)
    return _auth_response(db, response, issued, user)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest, response: Response, db: DbSession, client: ClientCtx
) -> AuthResponse:
    identifier = f"{client.ip or 'unknown'}:{payload.email.lower()}"
    rate_limiter.check("login", identifier)

    try:
        user = auth_service.authenticate(db, payload.email, payload.password)
    except Unauthorized:
        audit.record(
            db,
            user_id=None,
            action=AuditAction.LOGIN_FAILED.value,
            entity_type="user",
            summary="Failed login attempt",
            meta={"email": auth_service.normalise_email(payload.email)},
            ip_address=client.ip,
            user_agent=client.user_agent,
        )
        db.commit()
        raise

    rate_limiter.reset("login", identifier)
    issued = auth_service.start_session(
        db, user, user_agent=client.user_agent, ip_address=client.ip
    )
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.LOGIN.value,
        entity_type="user",
        entity_id=user.id,
        summary="Signed in",
        ip_address=client.ip,
        user_agent=client.user_agent,
    )
    db.commit()
    return _auth_response(db, response, issued, user)


@router.post("/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, db: DbSession) -> AuthResponse:
    """Rotate the refresh token and mint a new access token."""
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not token:
        raise Unauthorized("Session expired. Please login again.")

    issued = auth_service.rotate_session(db, token)
    user = db.get(User, issued.session.user_id)
    db.commit()
    return _auth_response(db, response, issued, user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response, db: DbSession, ctx: CurrentAuth, client: ClientCtx
) -> MessageResponse:
    auth_service.revoke_session(db, ctx.session)
    audit.record(
        db,
        user_id=ctx.user_id,
        action=AuditAction.LOGOUT.value,
        entity_type="user_session",
        entity_id=ctx.session.id,
        summary="Signed out",
        ip_address=client.ip,
    )
    db.commit()
    clear_auth_cookies(response)
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=AuthResponse)
def me(db: DbSession, ctx: CurrentAuth) -> AuthResponse:
    return AuthResponse(
        user=_serialise_user(db, ctx.user),
        csrf_token=ctx.session.csrf_token,
        financial=green_pin.status(db, ctx.user, ctx.session),
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest, db: DbSession, client: ClientCtx
) -> MessageResponse:
    """Send a reset link.

    The response is identical whether or not the address is registered, so this
    endpoint cannot be used to enumerate accounts.
    """
    rate_limiter.check("password_reset", client.ip or "unknown")
    generic = MessageResponse(
        message="If an account exists for that e-mail, a reset link is on its way."
    )

    user = auth_service.get_user_by_email(db, payload.email)
    if user is None or not user.is_active:
        return generic

    token = auth_service.issue_verification_token(
        db, user.id, TokenPurpose.PASSWORD_RESET, hours=1
    )
    db.commit()
    email_service.send_password_reset(user.email, token, user.full_name)
    return generic


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest, db: DbSession, client: ClientCtx
) -> MessageResponse:
    user = auth_service.consume_verification_token(
        db, payload.token, TokenPurpose.PASSWORD_RESET
    )
    auth_service.set_password(db, user, payload.new_password)

    # A password reset ends every other session: if the account was taken over,
    # this is what evicts the attacker.
    auth_service.revoke_all_sessions(db, user.id)
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.PASSWORD_RESET.value,
        entity_type="user",
        entity_id=user.id,
        summary="Password reset via e-mail link",
        ip_address=client.ip,
    )
    db.commit()
    return MessageResponse(message="Password updated. You can sign in with your new password.")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest, db: DbSession, ctx: CurrentAuth
) -> MessageResponse:
    auth_service.change_password(db, ctx.user, payload.current_password, payload.new_password)
    auth_service.revoke_all_sessions(db, ctx.user_id, except_id=ctx.session.id)
    db.commit()
    return MessageResponse(message="Password updated. Other devices have been signed out.")


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: DbSession) -> MessageResponse:
    user = auth_service.consume_verification_token(
        db, payload.token, TokenPurpose.EMAIL_VERIFY
    )
    user.is_verified = True
    db.commit()
    return MessageResponse(message="E-mail verified.")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    if ctx.user.is_verified:
        return MessageResponse(message="Your e-mail is already verified.")
    token = auth_service.issue_verification_token(
        db, ctx.user_id, TokenPurpose.EMAIL_VERIFY, hours=24
    )
    db.commit()
    email_service.send_verification(ctx.user.email, token, ctx.user.full_name)
    return MessageResponse(message="Verification e-mail sent.")


# --- Phone number sign-in -----------------------------------------------


@router.post("/phone/otp", response_model=OtpSentResponse)
def request_phone_login_otp(
    payload: PhoneOtpRequest, db: DbSession, client: ClientCtx
) -> OtpSentResponse:
    """Send a sign-in code to any valid phone number.

    Phone auth is phone-first, the same model Google sign-in already uses for
    e-mail: proving control of the number is itself enough to sign in *or*
    create an account, so - unlike the password-reset flow - there is nothing
    to hide about whether a number is already registered, and a code is
    always sent.
    """
    phone = phone_auth.normalise_phone(payload.phone)
    rate_limiter.check("phone_otp", f"{client.ip or 'unknown'}:{phone}")

    code, otp = phone_auth.request_otp(db, phone, "login")
    db.commit()
    result = sms_service.send_otp(phone, code)
    return otp_response(db, result, code, otp)


@router.post("/phone/login", response_model=AuthResponse)
def phone_login(
    payload: PhoneLoginRequest, response: Response, db: DbSession, client: ClientCtx
) -> AuthResponse:
    phone = phone_auth.normalise_phone(payload.phone)
    identifier = f"{client.ip or 'unknown'}:{phone}"
    rate_limiter.check("login", identifier)

    user, created = phone_auth.verify_login_otp(db, phone, payload.code, full_name=payload.full_name)
    rate_limiter.reset("login", identifier)

    issued = auth_service.start_session(
        db, user, user_agent=client.user_agent, ip_address=client.ip
    )
    audit.record(
        db,
        user_id=user.id,
        action=(AuditAction.CREATE if created else AuditAction.LOGIN).value,
        entity_type="user",
        entity_id=user.id,
        summary="Signed up with phone number" if created else "Signed in with phone number",
        ip_address=client.ip,
        user_agent=client.user_agent,
    )
    db.commit()
    return _auth_response(db, response, issued, user)


# --- Google OAuth ------------------------------------------------------


@router.get("/providers")
def providers() -> dict:
    """Tell the frontend which sign-in buttons to render."""
    return {"google": settings.google_enabled, "password": True}


@router.get("/google/start")
def google_start(response: Response) -> dict:
    """Begin the Google authorisation-code flow."""
    if not settings.google_enabled:
        raise BadRequest("Google sign-in is not configured on this server.")

    state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    # The state cookie is what proves the callback belongs to this browser.
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        httponly=True,
        max_age=600,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"authorization_url": url}


@router.get("/google/callback")
def google_callback(
    request: Request,
    db: DbSession,
    client: ClientCtx,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Exchange the authorisation code and start a session."""
    failure = RedirectResponse(f"{settings.FRONTEND_URL}/login?error=google_failed", status_code=302)

    if error or not code:
        return failure
    if not settings.google_enabled:
        return failure

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not expected_state or not state or not secrets.compare_digest(state, expected_state):
        logger.warning("Google callback rejected: state mismatch")
        return failure

    try:
        with httpx.Client(timeout=15) as http:
            token_response = http.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")

            userinfo = http.get(
                GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            userinfo.raise_for_status()
            info = userinfo.json()
    except httpx.HTTPError as exc:
        logger.error("Google token exchange failed: %s", exc)
        return failure

    if not info.get("email") or not info.get("email_verified", True):
        return failure

    user = auth_service.upsert_google_user(
        db,
        google_sub=info["sub"],
        email=info["email"],
        full_name=info.get("name") or info["email"].split("@")[0],
        picture=info.get("picture"),
    )
    issued = auth_service.start_session(
        db, user, user_agent=client.user_agent, ip_address=client.ip
    )
    audit.record(
        db,
        user_id=user.id,
        action=AuditAction.LOGIN.value,
        entity_type="user",
        entity_id=user.id,
        summary="Signed in with Google",
        ip_address=client.ip,
    )
    db.commit()

    redirect = RedirectResponse(f"{settings.FRONTEND_URL}/dashboard", status_code=302)
    set_auth_cookies(
        redirect,
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        csrf_token=issued.csrf_token,
    )
    redirect.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    return redirect
