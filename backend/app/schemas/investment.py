"""Investment portfolio, transaction and goal-planner schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AssetType, GoalStatus, InvestmentTxnType, Priority
from app.schemas.common import Money, ORMModel, OptionalMoney, OptionalPercent, Percent, Units


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    broker: str | None = Field(default=None, max_length=120)
    account_number: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    broker: str | None = Field(default=None, max_length=120)
    account_number: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class AccountOut(ORMModel):
    id: uuid.UUID
    name: str
    broker: str | None = None
    account_number: str | None = None
    notes: str | None = None
    is_active: bool = True
    holding_count: int = 0
    current_value: Money = Decimal("0.00")


class HoldingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    symbol: str | None = Field(default=None, max_length=40)
    asset_type: AssetType = AssetType.STOCK
    account_id: uuid.UUID | None = None
    currency: str = Field(default="INR", min_length=3, max_length=3)
    current_price: OptionalMoney = None
    manual_value: OptionalMoney = None
    maturity_date: date | None = None
    interest_rate: OptionalPercent = None
    notes: str | None = Field(default=None, max_length=2000)
    #: Convenience: open the position with an initial buy in the same call.
    initial_units: Units | None = None
    initial_price: OptionalMoney = None
    initial_amount: OptionalMoney = None
    purchase_date: date | None = None


class HoldingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    symbol: str | None = Field(default=None, max_length=40)
    account_id: uuid.UUID | None = None
    current_price: OptionalMoney = None
    manual_value: OptionalMoney = None
    maturity_date: date | None = None
    interest_rate: OptionalPercent = None
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None


class HoldingOut(ORMModel):
    id: uuid.UUID
    name: str
    symbol: str | None = None
    asset_type: str
    account_id: uuid.UUID | None = None
    account_name: str | None = None
    currency: str = "INR"
    current_price: OptionalMoney = None
    price_updated_at: datetime | None = None
    manual_value: OptionalMoney = None
    maturity_date: date | None = None
    interest_rate: OptionalPercent = None
    notes: str | None = None
    is_active: bool = True
    created_at: datetime

    units_held: Units = Decimal("0")
    avg_price: Money = Decimal("0.00")
    invested_amount: Money = Decimal("0.00")
    current_value: Money = Decimal("0.00")
    unrealised_pnl: Money = Decimal("0.00")
    realised_pnl: Money = Decimal("0.00")
    total_dividends: Money = Decimal("0.00")
    return_percent: Percent = Decimal("0.00")
    xirr_percent: Percent | None = None


class HoldingDetail(HoldingOut):
    transactions: list["InvestmentTxnOut"] = []


class InvestmentTxnCreate(BaseModel):
    txn_type: InvestmentTxnType = InvestmentTxnType.BUY
    txn_date: date = Field(default_factory=date.today)
    units: Units = Decimal("0")
    price_per_unit: OptionalMoney = None
    amount: Money = Field(ge=0)
    fees: Money = Decimal("0.00")
    notes: str | None = Field(default=None, max_length=300)

    @field_validator("txn_date")
    @classmethod
    def _not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("A transaction cannot be dated in the future.")
        return v


class InvestmentTxnOut(ORMModel):
    id: uuid.UUID
    holding_id: uuid.UUID
    txn_type: str
    txn_date: date
    units: Units = Decimal("0")
    price_per_unit: Money = Decimal("0.00")
    amount: Money
    fees: Money = Decimal("0.00")
    notes: str | None = None
    created_at: datetime


class PortfolioSummary(BaseModel):
    """The investment dashboard headline. Confidential - Green PIN gated."""

    total_invested: Money = Decimal("0.00")
    current_value: Money = Decimal("0.00")
    unrealised_pnl: Money = Decimal("0.00")
    realised_pnl: Money = Decimal("0.00")
    total_dividends: Money = Decimal("0.00")
    total_return: Money = Decimal("0.00")
    return_percent: Percent = Decimal("0.00")
    xirr_percent: Percent | None = None
    holding_count: int = 0
    by_asset_type: list[dict] = []
    top_gainers: list[HoldingOut] = []
    top_losers: list[HoldingOut] = []
    monthly_investment: list[dict] = []
    value_history: list[dict] = []


class InvestmentGoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=2000)
    target_amount: Money = Field(gt=0)
    target_date: date | None = None
    current_age: int | None = Field(default=None, ge=0, le=120)
    target_age: int | None = Field(default=None, ge=0, le=120)
    current_corpus: OptionalMoney = None
    use_portfolio_value: bool = True
    expected_return: Percent = Decimal("12.0000")
    monthly_investment: Money = Decimal("0.00")
    step_up_percent: Percent = Decimal("0.0000")
    inflation_rate: Percent = Decimal("0.0000")
    priority: Priority = Priority.MEDIUM

    @field_validator("target_age")
    @classmethod
    def _target_after_current(cls, v, info):
        current = info.data.get("current_age")
        if v is not None and current is not None and v <= current:
            raise ValueError("Target age must be after the current age.")
        return v


class InvestmentGoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=2000)
    target_amount: Money | None = Field(default=None, gt=0)
    target_date: date | None = None
    current_age: int | None = Field(default=None, ge=0, le=120)
    target_age: int | None = Field(default=None, ge=0, le=120)
    current_corpus: OptionalMoney = None
    use_portfolio_value: bool | None = None
    expected_return: Percent | None = None
    monthly_investment: Money | None = None
    step_up_percent: Percent | None = None
    inflation_rate: Percent | None = None
    priority: Priority | None = None
    status: GoalStatus | None = None


class InvestmentGoalOut(ORMModel):
    id: uuid.UUID
    name: str
    category: str | None = None
    description: str | None = None
    target_amount: Money
    target_date: date | None = None
    current_age: int | None = None
    target_age: int | None = None
    current_corpus: OptionalMoney = None
    use_portfolio_value: bool = True
    expected_return: Percent
    monthly_investment: Money
    step_up_percent: Percent
    inflation_rate: Percent
    priority: str = "medium"
    status: str = "in_progress"
    created_at: datetime

    # Projection, computed fresh on every read.
    years_remaining: float = 0
    effective_corpus: Money = Decimal("0.00")
    projected_value: Money = Decimal("0.00")
    required_monthly_sip: Money = Decimal("0.00")
    shortfall: Money = Decimal("0.00")
    surplus: Money = Decimal("0.00")
    on_track: bool = True
    projection_chart: list[dict] = []


HoldingDetail.model_rebuild()
