"""Green PIN, sessions and the security area of Settings."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.config import settings
from app.core.deps import ClientCtx, CurrentAuth, DbSession
from app.core.errors import BadRequest, NotFound, ServiceUnavailable
from app.core.rate_limit import rate_limiter
from app.models.enums import TokenPurpose
from app.schemas.auth import (
    FinancialStatus,
    PinRequest,
    ResetPinRequest,
    SecurityPreferences,
    SessionOut,
    SetPinRequest,
)
from app.schemas.common import MessageResponse
from app.services import audit, auth as auth_service, email as email_service, green_pin

router = APIRouter(prefix="/security", tags=["Security"])


@router.get("/financial/status", response_model=FinancialStatus)
def financial_status(db: DbSession, ctx: CurrentAuth) -> FinancialStatus:
    """Whether this session may currently see confidential figures."""
    return FinancialStatus(**green_pin.status(db, ctx.user, ctx.session))


@router.post("/financial/unlock", response_model=FinancialStatus)
def unlock_financial(
    payload: PinRequest, db: DbSession, ctx: CurrentAuth, client: ClientCtx
) -> FinancialStatus:
    """Open the financial window for this session by presenting the Green PIN."""
    rate_limiter.check("pin_verify", f"{client.ip or 'unknown'}:{ctx.user_id}")
    green_pin.unlock(db, ctx.user, ctx.session, payload.pin)
    db.commit()
    return FinancialStatus(**green_pin.status(db, ctx.user, ctx.session))


@router.post("/financial/lock", response_model=FinancialStatus)
def lock_financial(db: DbSession, ctx: CurrentAuth) -> FinancialStatus:
    green_pin.lock(db, ctx.user, ctx.session)
    db.commit()
    return FinancialStatus(**green_pin.status(db, ctx.user, ctx.session))


@router.post("/green-pin", response_model=MessageResponse)
def set_green_pin(payload: SetPinRequest, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    """Create or change the Green PIN.

    Changing requires the current PIN; a forgotten PIN must go through the
    e-mail-verified reset flow, so the frontend can never just post a new one.
    """
    green_pin.set_pin(db, ctx.user, payload.new_pin, current_pin=payload.current_pin)
    db.commit()
    return MessageResponse(message="Green PIN saved.")


@router.post("/green-pin/forgot", response_model=MessageResponse)
def forgot_green_pin(db: DbSession, ctx: CurrentAuth, client: ClientCtx) -> MessageResponse:
    """Mail a single-use PIN reset link to the verified account address."""
    rate_limiter.check("password_reset", f"pin:{ctx.user_id}")
    if not settings.smtp_enabled:
        raise ServiceUnavailable(
            "PIN reset e-mail is not set up on this server yet. "
            "Please contact support.",
            code="email_provider_missing",
        )
    token = auth_service.issue_verification_token(db, ctx.user_id, TokenPurpose.PIN_RESET, hours=1)
    db.commit()
    email_service.send_pin_reset(ctx.user.email, token, ctx.user.full_name)
    return MessageResponse(
        message=f"A reset link has been sent to {_mask_email(ctx.user.email)}."
    )


@router.post("/green-pin/reset", response_model=MessageResponse)
def reset_green_pin(payload: ResetPinRequest, db: DbSession) -> MessageResponse:
    user = auth_service.consume_verification_token(db, payload.token, TokenPurpose.PIN_RESET)
    green_pin.reset_pin_with_token(db, user, payload.new_pin)
    db.commit()
    return MessageResponse(message="Green PIN updated. Financial data has been relocked.")


@router.patch("/preferences", response_model=FinancialStatus)
def update_preferences(
    payload: SecurityPreferences, db: DbSession, ctx: CurrentAuth
) -> FinancialStatus:
    security = green_pin.get_security(db, ctx.user_id)
    if payload.unlock_minutes is not None:
        security.unlock_minutes = payload.unlock_minutes
    if payload.mask_ledger_amounts is not None:
        security.mask_ledger_amounts = payload.mask_ledger_amounts
    db.commit()
    return FinancialStatus(**green_pin.status(db, ctx.user, ctx.session))


# --- Sessions ----------------------------------------------------------


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(db: DbSession, ctx: CurrentAuth) -> list[SessionOut]:
    rows = auth_service.list_sessions(db, ctx.user_id)
    result = []
    for row in rows:
        item = SessionOut.model_validate(row)
        item.is_current = row.id == ctx.session.id
        result.append(item)
    return result


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def revoke_one(session_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    target = next((s for s in auth_service.list_sessions(db, ctx.user_id) if s.id == session_id), None)
    if target is None:
        raise NotFound("That session is no longer active.")
    if target.id == ctx.session.id:
        raise BadRequest("Use sign out to end the session you are currently using.")
    auth_service.revoke_session(db, target)
    db.commit()
    return MessageResponse(message="Session signed out.")


@router.post("/sessions/revoke-all", response_model=MessageResponse)
def revoke_all(db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    count = auth_service.revoke_all_sessions(db, ctx.user_id, except_id=ctx.session.id)
    db.commit()
    return MessageResponse(message=f"Signed out of {count} other device(s).")


@router.get("/audit-log")
def audit_log(db: DbSession, ctx: CurrentAuth, limit: int = 50) -> list[dict]:
    return [
        {
            "id": str(row.id),
            "action": row.action,
            "entity_type": row.entity_type,
            "summary": row.summary,
            "created_at": row.created_at,
            "ip_address": row.ip_address,
        }
        for row in audit.list_for_user(db, ctx.user_id, limit)
    ]


def _mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    visible = name[:2] if len(name) > 2 else name[:1]
    return f"{visible}{'*' * max(len(name) - len(visible), 2)}@{domain}"
