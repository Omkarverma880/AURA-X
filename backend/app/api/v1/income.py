"""Income and salary endpoints.

Every response here carries confidential figures, so the whole router sits
behind the Green PIN gate: a locked session gets a 423, never a null-padded
guess at the numbers.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query, status

from app.core.deps import DbSession, UnlockedAuth
from app.schemas.common import MessageResponse, Page
from app.schemas.finance import (
    IncomeCreate,
    IncomeOut,
    IncomeSourceCreate,
    IncomeSourceOut,
    IncomeSourceUpdate,
    IncomeUpdate,
)
from app.services import expenses as service

router = APIRouter(prefix="/income", tags=["Income"])


@router.get("/sources", response_model=list[IncomeSourceOut])
def list_sources(db: DbSession, ctx: UnlockedAuth) -> list[IncomeSourceOut]:
    return [IncomeSourceOut.model_validate(row) for row in service.list_income_sources(db, ctx.user_id)]


@router.post("/sources", response_model=IncomeSourceOut, status_code=status.HTTP_201_CREATED)
def create_source(payload: IncomeSourceCreate, db: DbSession, ctx: UnlockedAuth) -> IncomeSourceOut:
    source = service.create_income_source(db, ctx.user_id, payload.model_dump())
    db.commit()
    return IncomeSourceOut.model_validate(
        {**payload.model_dump(), "id": source.id, "is_active": True, "total_received": 0}
    )


@router.patch("/sources/{source_id}", response_model=IncomeSourceOut)
def update_source(
    source_id: uuid.UUID, payload: IncomeSourceUpdate, db: DbSession, ctx: UnlockedAuth
) -> IncomeSourceOut:
    source = service.update_income_source(
        db, ctx.user_id, source_id, payload.model_dump(exclude_unset=True)
    )
    db.commit()
    rows = {row["id"]: row for row in service.list_income_sources(db, ctx.user_id)}
    return IncomeSourceOut.model_validate(rows.get(source.id))


@router.get("", response_model=Page[IncomeOut])
def list_income(
    db: DbSession,
    ctx: UnlockedAuth,
    period: date | None = None,
    year: int | None = None,
    source_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> Page[IncomeOut]:
    items, total, _ = service.list_income(
        db, ctx.user_id, period=period, year=year, source_id=source_id, page=page, page_size=page_size
    )
    return Page[IncomeOut](
        items=[IncomeOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=IncomeOut, status_code=status.HTTP_201_CREATED)
def create_income(payload: IncomeCreate, db: DbSession, ctx: UnlockedAuth) -> IncomeOut:
    record = service.create_income(db, ctx.user_id, payload.model_dump())
    db.commit()
    return IncomeOut.model_validate(service.get_income(db, ctx.user_id, record.id))


@router.patch("/{record_id}", response_model=IncomeOut)
def update_income(
    record_id: uuid.UUID, payload: IncomeUpdate, db: DbSession, ctx: UnlockedAuth
) -> IncomeOut:
    service.update_income(db, ctx.user_id, record_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return IncomeOut.model_validate(service.get_income(db, ctx.user_id, record_id))


@router.delete("/{record_id}", response_model=MessageResponse)
def delete_income(record_id: uuid.UUID, db: DbSession, ctx: UnlockedAuth) -> MessageResponse:
    service.delete_income(db, ctx.user_id, record_id)
    db.commit()
    return MessageResponse(message="Income record deleted.")
