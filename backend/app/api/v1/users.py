"""Profile and account management."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import ClientCtx, CurrentAuth, DbSession
from app.core.errors import BadRequest
from app.core.rate_limit import rate_limiter
from app.models.enums import AuditAction
from app.models.user import PhoneOtp, UserProfile
from app.schemas.auth import OtpSentResponse, PhoneOtpRequest, PhoneVerifyRequest, ProfileUpdate, UserOut
from app.schemas.common import MessageResponse
from app.services import audit, auth as auth_service, phone_auth
from app.services import sms as sms_service
from app.storage import storage
from app.storage.images import process_upload

router = APIRouter(prefix="/users", tags=["Profile"])


def _profile(db, user_id) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.flush()
    return profile


def _serialise(db, user) -> UserOut:
    from app.api.v1.auth import _serialise_user

    payload = _serialise_user(db, user)
    profile = _profile(db, user.id)
    if payload.profile is not None and profile.avatar_key:
        payload.profile.avatar_url = storage.public_url(profile.avatar_key)
    return payload


@router.get("/me", response_model=UserOut)
def get_profile(db: DbSession, ctx: CurrentAuth) -> UserOut:
    return _serialise(db, ctx.user)


@router.patch("/me", response_model=UserOut)
def update_profile(payload: ProfileUpdate, db: DbSession, ctx: CurrentAuth) -> UserOut:
    profile = _profile(db, ctx.user_id)
    data = payload.model_dump(exclude_unset=True)

    if "full_name" in data and data["full_name"]:
        ctx.user.full_name = data.pop("full_name").strip()
    else:
        data.pop("full_name", None)

    for field, value in data.items():
        if field == "currency" and value:
            value = value.upper()
        setattr(profile, field, value)

    db.commit()
    return _serialise(db, ctx.user)


@router.post("/me/avatar", response_model=UserOut)
def upload_avatar(
    db: DbSession, ctx: CurrentAuth, file: UploadFile = File(...)
) -> UserOut:
    """Replace the profile picture.

    The bytes are validated as a real image and re-encoded before storage, so a
    file that merely claims to be a PNG cannot be served back to a browser.
    """
    processed = process_upload(file, max_dimension=512)
    profile = _profile(db, ctx.user_id)

    old_key = profile.avatar_key
    profile.avatar_key = storage.save(
        processed.data, prefix=f"avatars/{ctx.user_id}", content_type=processed.mime_type
    )
    db.commit()

    if old_key:
        storage.delete(old_key)
    return _serialise(db, ctx.user)


@router.post("/me/phone/otp", response_model=OtpSentResponse)
def start_phone_link(
    payload: PhoneOtpRequest, db: DbSession, ctx: CurrentAuth, client: ClientCtx
) -> OtpSentResponse:
    """Send a code to verify a new phone number for sign-in.

    Linking - not just sending a code - requires the caller to already be
    signed in, so a phone number cannot be attached to an account its owner
    does not control.
    """
    phone = phone_auth.normalise_phone(payload.phone)
    rate_limiter.check("phone_otp", f"{client.ip or 'unknown'}:{ctx.user_id}")

    code, _ = phone_auth.start_phone_link(db, ctx.user, phone)
    db.commit()
    sms_service.send_otp(phone, code)
    return OtpSentResponse(
        message=f"A verification code has been sent to {phone}.",
        expires_in_minutes=settings.OTP_TTL_MINUTES,
        debug_code=code if (not settings.sms_enabled and not settings.is_production) else None,
    )


@router.post("/me/phone/verify", response_model=UserOut)
def confirm_phone_link(
    payload: PhoneVerifyRequest, db: DbSession, ctx: CurrentAuth
) -> UserOut:
    """Complete phone linking by presenting the code just texted.

    The phone number itself was fixed when the code was requested, so it is
    looked up from whichever "link" code is still pending for this user rather
    than being resupplied by the client.
    """
    pending = db.execute(
        select(PhoneOtp)
        .where(
            PhoneOtp.user_id == ctx.user_id,
            PhoneOtp.purpose == "link",
            PhoneOtp.consumed_at.is_(None),
        )
        .order_by(PhoneOtp.created_at.desc())
    ).scalars().first()
    if pending is None:
        raise BadRequest("Request a verification code first.", code="otp_expired")

    phone_auth.confirm_phone_link(db, ctx.user, pending.phone, payload.code)
    db.commit()
    return _serialise(db, ctx.user)


@router.delete("/me/phone", response_model=UserOut)
def unlink_phone(db: DbSession, ctx: CurrentAuth) -> UserOut:
    phone_auth.unlink_phone(db, ctx.user)
    db.commit()
    return _serialise(db, ctx.user)


@router.delete("/me", response_model=MessageResponse)
def delete_account(
    db: DbSession, ctx: CurrentAuth, client: ClientCtx, confirm: str = ""
) -> MessageResponse:
    """Permanently delete the account and every row that belongs to it.

    Cascade deletes handle the data; storage objects are removed on a
    best-effort basis afterwards.
    """
    if confirm.strip().upper() != "DELETE":
        raise BadRequest(
            "Type DELETE to confirm that you want to permanently remove your account."
        )

    user_id = ctx.user_id
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.DELETE.value,
        entity_type="user",
        entity_id=user_id,
        summary="Account deleted",
        ip_address=client.ip,
    )
    auth_service.revoke_all_sessions(db, user_id)
    db.commit()

    storage.delete_prefix(f"users/{user_id}")
    storage.delete_prefix(f"avatars/{user_id}")

    db.delete(db.get(type(ctx.user), user_id))
    db.commit()
    return MessageResponse(message="Your account and all associated data have been deleted.")
