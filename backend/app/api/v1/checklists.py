"""Custom checklists / trackers: Jyotirlingas, treks, countries, books, and
anything else a user invents. One structure serves every tracker type."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.deps import CurrentAuth, DbSession
from app.schemas.common import MessageResponse
from app.schemas.life import (
    ChecklistCreate,
    ChecklistDetail,
    ChecklistItemCreate,
    ChecklistItemOut,
    ChecklistItemUpdate,
    ChecklistOut,
    ChecklistUpdate,
)
from app.services import life as service

router = APIRouter(prefix="/checklists", tags=["Checklists"])


@router.get("", response_model=list[ChecklistOut])
def list_checklists(
    db: DbSession, ctx: CurrentAuth, tracker_type: str | None = None, include_archived: bool = False
) -> list[ChecklistOut]:
    rows = service.list_checklists(
        db, ctx.user_id, tracker_type=tracker_type, include_archived=include_archived
    )
    return [ChecklistOut.model_validate(row) for row in rows]


@router.post("", response_model=ChecklistDetail, status_code=status.HTTP_201_CREATED)
def create_checklist(payload: ChecklistCreate, db: DbSession, ctx: CurrentAuth) -> ChecklistDetail:
    checklist = service.create_checklist(db, ctx.user_id, payload.model_dump())
    db.commit()
    return ChecklistDetail.model_validate(service.get_checklist_detail(db, ctx.user_id, checklist.id))


@router.get("/{checklist_id}", response_model=ChecklistDetail)
def get_checklist(checklist_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> ChecklistDetail:
    return ChecklistDetail.model_validate(service.get_checklist_detail(db, ctx.user_id, checklist_id))


@router.patch("/{checklist_id}", response_model=ChecklistDetail)
def update_checklist(
    checklist_id: uuid.UUID, payload: ChecklistUpdate, db: DbSession, ctx: CurrentAuth
) -> ChecklistDetail:
    service.update_checklist(db, ctx.user_id, checklist_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return ChecklistDetail.model_validate(service.get_checklist_detail(db, ctx.user_id, checklist_id))


@router.delete("/{checklist_id}", response_model=MessageResponse)
def delete_checklist(checklist_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    service.delete_checklist(db, ctx.user_id, checklist_id)
    db.commit()
    return MessageResponse(message="Tracker deleted.")


@router.post(
    "/{checklist_id}/items", response_model=ChecklistDetail, status_code=status.HTTP_201_CREATED
)
def add_item(
    checklist_id: uuid.UUID, payload: ChecklistItemCreate, db: DbSession, ctx: CurrentAuth
) -> ChecklistDetail:
    service.add_item(db, ctx.user_id, checklist_id, payload.model_dump())
    db.commit()
    return ChecklistDetail.model_validate(service.get_checklist_detail(db, ctx.user_id, checklist_id))


@router.patch("/items/{item_id}", response_model=ChecklistItemOut)
def update_item(
    item_id: uuid.UUID, payload: ChecklistItemUpdate, db: DbSession, ctx: CurrentAuth
) -> ChecklistItemOut:
    item = service.update_item(db, ctx.user_id, item_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return ChecklistItemOut.model_validate(service.serialise_item(item))


@router.delete("/items/{item_id}", response_model=MessageResponse)
def delete_item(item_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    service.delete_item(db, ctx.user_id, item_id)
    db.commit()
    return MessageResponse(message="Item removed.")
