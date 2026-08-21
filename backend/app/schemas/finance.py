"""Expenditure, income and budget schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CategoryKind, IncomeType, PaymentMethod, RecurrenceInterval
from app.schemas.common import Money, ORMModel, OptionalMoney, PositiveMoney


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: CategoryKind = CategoryKind.EXPENSE
    parent_id: uuid.UUID | None = None
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=20)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    is_archived: bool | None = None
    sort_order: int | None = None


class CategoryOut(ORMModel):
    id: uuid.UUID
    name: str
    kind: str
    parent_id: uuid.UUID | None = None
    icon: str | None = None
    color: str | None = None
    is_default: bool = False
    is_archived: bool = False
    sort_order: int = 0
    children: list["CategoryOut"] = []
    #: Spend in the requested window, when the caller asked for usage.
    spent: OptionalMoney = None
    transaction_count: int | None = None


class ExpenseCreate(BaseModel):
    spent_on: date = Field(default_factory=date.today)
    amount: PositiveMoney
    category_id: uuid.UUID | None = None
    subcategory_id: uuid.UUID | None = None
    merchant: str | None = Field(default=None, max_length=160)
    payment_method: PaymentMethod | None = None
    description: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=2000)
    is_recurring: bool = False
    recurrence: RecurrenceInterval = RecurrenceInterval.NONE
    tags: list[str] | None = None

    @field_validator("spent_on")
    @classmethod
    def _not_far_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("An expense cannot be dated in the future.")
        return v


class ExpenseUpdate(BaseModel):
    spent_on: date | None = None
    amount: PositiveMoney | None = None
    category_id: uuid.UUID | None = None
    subcategory_id: uuid.UUID | None = None
    merchant: str | None = Field(default=None, max_length=160)
    payment_method: PaymentMethod | None = None
    description: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=2000)
    is_recurring: bool | None = None
    recurrence: RecurrenceInterval | None = None
    tags: list[str] | None = None


class ExpenseOut(ORMModel):
    id: uuid.UUID
    spent_on: date
    amount: Money
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None
    subcategory_id: uuid.UUID | None = None
    subcategory_name: str | None = None
    merchant: str | None = None
    payment_method: str | None = None
    description: str | None = None
    notes: str | None = None
    is_recurring: bool = False
    recurrence: str = "none"
    tags: list[str] | None = None
    created_at: datetime


class IncomeSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    income_type: IncomeType = IncomeType.SALARY
    employer: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=2000)


class IncomeSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    income_type: IncomeType | None = None
    employer: str | None = Field(default=None, max_length=160)
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)


class IncomeSourceOut(ORMModel):
    id: uuid.UUID
    name: str
    income_type: str
    employer: str | None = None
    is_active: bool = True
    notes: str | None = None
    total_received: Money = Decimal("0.00")


class IncomeCreate(BaseModel):
    source_id: uuid.UUID | None = None
    received_on: date = Field(default_factory=date.today)
    gross_amount: PositiveMoney
    net_amount: PositiveMoney
    deductions: Money = Decimal("0.00")
    description: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("net_amount")
    @classmethod
    def _net_not_above_gross(cls, v, info):
        gross = info.data.get("gross_amount")
        if gross is not None and v > gross:
            raise ValueError("Net pay cannot be higher than gross pay.")
        return v


class IncomeUpdate(BaseModel):
    source_id: uuid.UUID | None = None
    received_on: date | None = None
    gross_amount: PositiveMoney | None = None
    net_amount: PositiveMoney | None = None
    deductions: Money | None = None
    description: str | None = Field(default=None, max_length=300)
    notes: str | None = Field(default=None, max_length=2000)


class IncomeOut(ORMModel):
    id: uuid.UUID
    source_id: uuid.UUID | None = None
    source_name: str | None = None
    income_type: str | None = None
    received_on: date
    period_month: date
    gross_amount: Money
    net_amount: Money
    deductions: Money = Decimal("0.00")
    description: str | None = None
    notes: str | None = None
    created_at: datetime


class BudgetUpsert(BaseModel):
    category_id: uuid.UUID
    period_month: date
    amount: Money = Field(ge=0)
    notes: str | None = Field(default=None, max_length=300)


class BudgetOut(ORMModel):
    id: uuid.UUID | None = None
    category_id: uuid.UUID
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None
    period_month: date
    amount: Money = Decimal("0.00")
    spent: Money = Decimal("0.00")
    remaining: Money = Decimal("0.00")
    utilisation: float = 0
    status: str = "on_track"
    notes: str | None = None


class CategorySpend(BaseModel):
    category_id: uuid.UUID | None = None
    name: str
    icon: str | None = None
    color: str | None = None
    amount: Money = Decimal("0.00")
    share: float = 0
    count: int = 0


class MonthlySummary(BaseModel):
    """The monthly expenditure dashboard.

    Every figure is confidential, so the whole payload is only served to a
    session that has passed the Green PIN gate.
    """

    period_month: date
    income: Money = Decimal("0.00")
    gross_income: Money = Decimal("0.00")
    expenses: Money = Decimal("0.00")
    savings: Money = Decimal("0.00")
    savings_rate: float = 0
    investments: Money = Decimal("0.00")
    money_given: Money = Decimal("0.00")
    money_received: Money = Decimal("0.00")
    expense_count: int = 0
    daily_average: Money = Decimal("0.00")
    budget_total: Money = Decimal("0.00")
    budget_used: float = 0
    by_category: list[CategorySpend] = []
    top_expenses: list[ExpenseOut] = []
    recurring: list[ExpenseOut] = []
    previous_expenses: Money = Decimal("0.00")
    change_percent: float = 0


class TrendPoint(BaseModel):
    month: str
    income: Money = Decimal("0.00")
    expenses: Money = Decimal("0.00")
    savings: Money = Decimal("0.00")
    savings_rate: float = 0
