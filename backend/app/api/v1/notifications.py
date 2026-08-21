"""Notifications endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.deps import CurrentAuth, DbSession
from app.schemas.common import MessageResponse
from app.schemas.notifications import NotificationCreate, NotificationOut
from app.services import notifications as service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    db: DbSession, ctx: CurrentAuth, unread_only: bool = False, limit: int = 50
) -> list[NotificationOut]:
    return [
        NotificationOut.model_validate(n)
        for n in service.list_notifications(db, ctx.user_id, unread_only=unread_only, limit=limit)
    ]


@router.get("/unread-count")
def unread_count(db: DbSession, ctx: CurrentAuth) -> dict:
    return {"count": service.unread_count(db, ctx.user_id)}


@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreate, db: DbSession, ctx: CurrentAuth
) -> NotificationOut:
    """Create a custom reminder."""
    notification = service.create_notification(db, ctx.user_id, payload.model_dump())
    db.commit()
    return NotificationOut.model_validate(notification)


@router.post("/refresh", response_model=MessageResponse)
def refresh_reminders(db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    """Regenerate reminders from current Bahi Khata/budget/goal data."""
    count = service.refresh_reminders(db, ctx.user_id)
    db.commit()
    return MessageResponse(message=f"{count} reminder(s) refreshed.")


@router.post("/read-all", response_model=MessageResponse)
def mark_all_read(db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    count = service.mark_all_read(db, ctx.user_id)
    db.commit()
    return MessageResponse(message=f"{count} notification(s) marked read.")


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> NotificationOut:
    notification = service.mark_read(db, ctx.user_id, notification_id)
    db.commit()
    return NotificationOut.model_validate(notification)


@router.delete("/{notification_id}", response_model=MessageResponse)
def dismiss(notification_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    service.dismiss(db, ctx.user_id, notification_id)
    db.commit()
    return MessageResponse(message="Notification dismissed.")
