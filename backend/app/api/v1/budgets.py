"""Monthly budgets and the expenditure dashboard.

Budgets themselves are just caps and are not confidential; the summary
endpoint that shows spend against income is, and sits behind the Green PIN.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query

from app.core.deps import DbSession, UnlockedAuth
from app.schemas.common import MessageResponse
from app.schemas.finance import BudgetOut, BudgetUpsert, MonthlySummary, TrendPoint
from app.services import monthly as service

router = APIRouter(prefix="/budgets", tags=["Budgets"])
summary_router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("", response_model=list[BudgetOut])
def list_budgets(db: DbSession, ctx: UnlockedAuth, period: date = Query(...)) -> list[BudgetOut]:
    return [BudgetOut.model_validate(row) for row in service.budget_overview(db, ctx.user_id, period)]


@router.put("", response_model=BudgetOut)
def upsert_budget(payload: BudgetUpsert, db: DbSession, ctx: UnlockedAuth) -> BudgetOut:
    service.upsert_budget(db, ctx.user_id, payload.model_dump())
    db.commit()
    rows = service.budget_overview(db, ctx.user_id, payload.period_month)
    match = next(r for r in rows if r["category_id"] == payload.category_id)
    return BudgetOut.model_validate(match)


@router.delete("/{budget_id}", response_model=MessageResponse)
def delete_budget(budget_id: uuid.UUID, db: DbSession, ctx: UnlockedAuth) -> MessageResponse:
    service.delete_budget(db, ctx.user_id, budget_id)
    db.commit()
    return MessageResponse(message="Budget removed.")


@router.post("/copy", response_model=MessageResponse)
def copy_budgets(
    db: DbSession, ctx: UnlockedAuth, source: date = Query(...), target: date = Query(...)
) -> MessageResponse:
    """Carry last month's budgets forward, so setup only happens once."""
    count = service.copy_budgets(db, ctx.user_id, source, target)
    db.commit()
    return MessageResponse(message=f"Copied {count} budget(s).")


# --- Monthly expenditure dashboard --------------------------------------


@summary_router.get("/monthly-summary", response_model=MonthlySummary)
def monthly_summary(db: DbSession, ctx: UnlockedAuth, period: date = Query(...)) -> MonthlySummary:
    return MonthlySummary.model_validate(service.monthly_summary(db, ctx.user_id, period))


@summary_router.get("/trend", response_model=list[TrendPoint])
def expense_trend(db: DbSession, ctx: UnlockedAuth, months: int = 12) -> list[TrendPoint]:
    return [TrendPoint.model_validate(row) for row in service.monthly_trend(db, ctx.user_id, months)]
