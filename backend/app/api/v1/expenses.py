"""Expense and category endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentAuth, DbSession
from app.schemas.common import MessageResponse, Page
from app.schemas.finance import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
)
from app.services import expenses as service

router = APIRouter(prefix="/expenses", tags=["Expenses"])
categories_router = APIRouter(prefix="/categories", tags=["Categories"])


# --- Categories ----------------------------------------------------------


@categories_router.get("", response_model=list[CategoryOut])
def list_categories(
    db: DbSession,
    ctx: CurrentAuth,
    kind: str | None = None,
    include_archived: bool = False,
    period: date | None = None,
) -> list[CategoryOut]:
    rows = service.list_categories(
        db, ctx.user_id, kind=kind, include_archived=include_archived, period=period
    )
    return [CategoryOut.model_validate(row) for row in rows]


@categories_router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: DbSession, ctx: CurrentAuth) -> CategoryOut:
    category = service.create_category(db, ctx.user_id, payload.model_dump())
    db.commit()
    return CategoryOut.model_validate(service.serialise_category(category))


@categories_router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: uuid.UUID, payload: CategoryUpdate, db: DbSession, ctx: CurrentAuth
) -> CategoryOut:
    category = service.update_category(
        db, ctx.user_id, category_id, payload.model_dump(exclude_unset=True)
    )
    db.commit()
    return CategoryOut.model_validate(service.serialise_category(category))


@categories_router.delete("/{category_id}", response_model=MessageResponse)
def delete_category(category_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    service.delete_category(db, ctx.user_id, category_id)
    db.commit()
    return MessageResponse(message="Category removed.")


# --- Expenses --------------------------------------------------------------


@router.get("", response_model=Page[ExpenseOut])
def list_expenses(
    db: DbSession,
    ctx: CurrentAuth,
    period: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: uuid.UUID | None = None,
    payment_method: str | None = None,
    search: str | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    recurring_only: bool = False,
    sort: str = "recent",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> Page[ExpenseOut]:
    items, total, _ = service.list_expenses(
        db,
        ctx.user_id,
        period=period,
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        payment_method=payment_method,
        search=search,
        min_amount=min_amount,
        max_amount=max_amount,
        recurring_only=recurring_only,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return Page[ExpenseOut](
        items=[ExpenseOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: DbSession, ctx: CurrentAuth) -> ExpenseOut:
    expense = service.create_expense(db, ctx.user_id, payload.model_dump())
    db.commit()
    return ExpenseOut.model_validate(service.get_expense(db, ctx.user_id, expense.id))


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> ExpenseOut:
    return ExpenseOut.model_validate(service.get_expense(db, ctx.user_id, expense_id))


@router.patch("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: uuid.UUID, payload: ExpenseUpdate, db: DbSession, ctx: CurrentAuth
) -> ExpenseOut:
    service.update_expense(db, ctx.user_id, expense_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return ExpenseOut.model_validate(service.get_expense(db, ctx.user_id, expense_id))


@router.delete("/{expense_id}", response_model=MessageResponse)
def delete_expense(expense_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    service.delete_expense(db, ctx.user_id, expense_id)
    db.commit()
    return MessageResponse(message="Expense deleted.")
