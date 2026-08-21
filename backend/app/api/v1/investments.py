"""Investment portfolio and goal-planner endpoints.

Every response here carries portfolio values, so the whole module sits behind
the Green PIN gate the same way income does.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.deps import DbSession, UnlockedAuth
from app.schemas.common import MessageResponse
from app.schemas.investment import (
    AccountCreate,
    AccountOut,
    AccountUpdate,
    HoldingCreate,
    HoldingDetail,
    HoldingOut,
    HoldingUpdate,
    InvestmentGoalCreate,
    InvestmentGoalOut,
    InvestmentGoalUpdate,
    InvestmentTxnCreate,
    InvestmentTxnOut,
    PortfolioSummary,
)
from app.services import investments as service

router = APIRouter(prefix="/investments", tags=["Investments"])
goals_router = APIRouter(prefix="/investment-goals", tags=["Investment Goals"])


# --- Accounts ------------------------------------------------------------


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(db: DbSession, ctx: UnlockedAuth) -> list[AccountOut]:
    return [AccountOut.model_validate(row) for row in service.list_accounts(db, ctx.user_id)]


@router.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: AccountCreate, db: DbSession, ctx: UnlockedAuth) -> AccountOut:
    account = service.create_account(db, ctx.user_id, payload.model_dump())
    db.commit()
    return AccountOut.model_validate(
        {**payload.model_dump(), "id": account.id, "is_active": True, "holding_count": 0, "current_value": 0}
    )


@router.patch("/accounts/{account_id}", response_model=AccountOut)
def update_account(
    account_id: uuid.UUID, payload: AccountUpdate, db: DbSession, ctx: UnlockedAuth
) -> AccountOut:
    service.update_account(db, ctx.user_id, account_id, payload.model_dump(exclude_unset=True))
    db.commit()
    rows = {row["id"]: row for row in service.list_accounts(db, ctx.user_id)}
    return AccountOut.model_validate(rows[account_id])


@router.delete("/accounts/{account_id}", response_model=MessageResponse)
def delete_account(account_id: uuid.UUID, db: DbSession, ctx: UnlockedAuth) -> MessageResponse:
    service.delete_account(db, ctx.user_id, account_id)
    db.commit()
    return MessageResponse(message="Account removed. Its holdings are kept, now unlinked.")


# --- Portfolio summary ---------------------------------------------------
#
# Registered before the /{holding_id} catch-all below: FastAPI matches routes
# within one router in definition order, so this literal path must come first
# or "/investments/summary" would be swallowed as an invalid holding id.


@router.get("/summary", response_model=PortfolioSummary)
def portfolio_summary(db: DbSession, ctx: UnlockedAuth) -> PortfolioSummary:
    return PortfolioSummary.model_validate(service.portfolio_summary(db, ctx.user_id))


# --- Holdings --------------------------------------------------------------


@router.get("", response_model=list[HoldingOut])
def list_holdings(
    db: DbSession,
    ctx: UnlockedAuth,
    asset_type: str | None = None,
    account_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> list[HoldingOut]:
    rows = service.list_holdings(
        db, ctx.user_id, asset_type=asset_type, account_id=account_id, include_inactive=include_inactive
    )
    return [HoldingOut.model_validate(row) for row in rows]


@router.post("", response_model=HoldingDetail, status_code=status.HTTP_201_CREATED)
def create_holding(payload: HoldingCreate, db: DbSession, ctx: UnlockedAuth) -> HoldingDetail:
    holding = service.create_holding(db, ctx.user_id, payload.model_dump())
    db.commit()
    return HoldingDetail.model_validate(service.get_holding_detail(db, ctx.user_id, holding.id))


@router.get("/{holding_id}", response_model=HoldingDetail)
def get_holding(holding_id: uuid.UUID, db: DbSession, ctx: UnlockedAuth) -> HoldingDetail:
    return HoldingDetail.model_validate(service.get_holding_detail(db, ctx.user_id, holding_id))


@router.patch("/{holding_id}", response_model=HoldingDetail)
def update_holding(
    holding_id: uuid.UUID, payload: HoldingUpdate, db: DbSession, ctx: UnlockedAuth
) -> HoldingDetail:
    service.update_holding(db, ctx.user_id, holding_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return HoldingDetail.model_validate(service.get_holding_detail(db, ctx.user_id, holding_id))


@router.delete("/{holding_id}", response_model=MessageResponse)
def delete_holding(holding_id: uuid.UUID, db: DbSession, ctx: UnlockedAuth) -> MessageResponse:
    service.delete_holding(db, ctx.user_id, holding_id)
    db.commit()
    return MessageResponse(message="Holding archived.")


@router.post(
    "/{holding_id}/transactions", response_model=HoldingDetail, status_code=status.HTTP_201_CREATED
)
def add_transaction(
    holding_id: uuid.UUID, payload: InvestmentTxnCreate, db: DbSession, ctx: UnlockedAuth
) -> HoldingDetail:
    service.add_transaction(db, ctx.user_id, holding_id, payload.model_dump())
    db.commit()
    return HoldingDetail.model_validate(service.get_holding_detail(db, ctx.user_id, holding_id))


@router.delete("/transactions/{txn_id}", response_model=MessageResponse)
def delete_transaction(txn_id: uuid.UUID, db: DbSession, ctx: UnlockedAuth) -> MessageResponse:
    service.delete_transaction(db, ctx.user_id, txn_id)
    db.commit()
    return MessageResponse(message="Transaction removed.")


# --- Investment goal planner ---------------------------------------------


@goals_router.get("", response_model=list[InvestmentGoalOut])
def list_goals(db: DbSession, ctx: UnlockedAuth) -> list[InvestmentGoalOut]:
    return [InvestmentGoalOut.model_validate(row) for row in service.list_goals(db, ctx.user_id)]


@goals_router.post("", response_model=InvestmentGoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(payload: InvestmentGoalCreate, db: DbSession, ctx: UnlockedAuth) -> InvestmentGoalOut:
    goal = service.create_goal(db, ctx.user_id, payload.model_dump())
    db.commit()
    return InvestmentGoalOut.model_validate(service.serialise_goal(db, ctx.user_id, goal))


@goals_router.patch("/{goal_id}", response_model=InvestmentGoalOut)
def update_goal(
    goal_id: uuid.UUID, payload: InvestmentGoalUpdate, db: DbSession, ctx: UnlockedAuth
) -> InvestmentGoalOut:
    goal = service.update_goal(db, ctx.user_id, goal_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return InvestmentGoalOut.model_validate(service.serialise_goal(db, ctx.user_id, goal))


@goals_router.delete("/{goal_id}", response_model=MessageResponse)
def delete_goal(goal_id: uuid.UUID, db: DbSession, ctx: UnlockedAuth) -> MessageResponse:
    service.delete_goal(db, ctx.user_id, goal_id)
    db.commit()
    return MessageResponse(message="Investment goal removed.")
