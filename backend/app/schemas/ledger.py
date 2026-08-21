"""Bahi Khata schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import LedgerDirection, LedgerTxnType, PaymentMethod
from app.schemas.common import Money, ORMModel, PositiveMoney


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=320)
    relation: str | None = Field(default=None, max_length=60)
    notes: str | None = Field(default=None, max_length=2000)


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=320)
    relation: str | None = Field(default=None, max_length=60)
    notes: str | None = Field(default=None, max_length=2000)
    is_archived: bool | None = None


class PersonOut(ORMModel):
    id: uuid.UUID
    name: str
    phone: str | None = None
    email: str | None = None
    relation: str | None = None
    notes: str | None = None
    color: str | None = None
    is_archived: bool
    created_at: datetime

    # Derived totals, always computed from transactions.
    total_given: Money = Decimal("0.00")
    total_received: Money = Decimal("0.00")
    total_borrowed: Money = Decimal("0.00")
    total_repaid: Money = Decimal("0.00")
    outstanding_receivable: Money = Decimal("0.00")
    outstanding_payable: Money = Decimal("0.00")
    net_balance: Money = Decimal("0.00")
    entry_count: int = 0
    active_count: int = 0
    last_activity: date | None = None


class TransactionCreate(BaseModel):
    txn_type: LedgerTxnType = LedgerTxnType.REPAYMENT
    amount: PositiveMoney
    txn_date: date = Field(default_factory=date.today)
    method: PaymentMethod | None = None
    description: str | None = Field(default=None, max_length=300)

    @field_validator("txn_date")
    @classmethod
    def _not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("A transaction cannot be dated in the future.")
        return v


class TransactionOut(ORMModel):
    id: uuid.UUID
    entry_id: uuid.UUID
    person_id: uuid.UUID
    txn_type: str
    amount: Money
    signed_amount: Money = Decimal("0.00")
    txn_date: date
    method: str | None = None
    description: str | None = None
    is_voided: bool = False
    void_reason: str | None = None
    created_at: datetime
    #: Running outstanding balance after this row, for the ledger view.
    balance_after: Money | None = None
    person_name: str | None = None
    purpose: str | None = None


class VoidRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class EntryCreate(BaseModel):
    person_id: uuid.UUID | None = None
    #: Convenience for the quick-add flow: name a person who may not exist yet.
    person_name: str | None = Field(default=None, max_length=120)
    direction: LedgerDirection
    purpose: str = Field(min_length=1, max_length=200)
    amount: PositiveMoney
    entry_date: date = Field(default_factory=date.today)
    due_date: date | None = None
    reminder_on: date | None = None
    method: PaymentMethod | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("entry_date")
    @classmethod
    def _not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("An entry cannot be dated in the future.")
        return v


class EntryUpdate(BaseModel):
    purpose: str | None = Field(default=None, min_length=1, max_length=200)
    due_date: date | None = None
    reminder_on: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    is_closed: bool | None = None


class EntryOut(ORMModel):
    id: uuid.UUID
    person_id: uuid.UUID
    person_name: str | None = None
    direction: str
    purpose: str
    entry_date: date
    due_date: date | None = None
    reminder_on: date | None = None
    notes: str | None = None
    currency: str = "INR"
    is_closed: bool
    created_at: datetime

    principal_amount: Money = Decimal("0.00")
    settled_amount: Money = Decimal("0.00")
    outstanding: Money = Decimal("0.00")
    progress_percent: float = 0
    status: str = "active"
    is_overdue: bool = False
    days_overdue: int = 0
    transaction_count: int = 0


class EntryDetail(EntryOut):
    transactions: list[TransactionOut] = []


class PersonDetail(PersonOut):
    entries: list[EntryOut] = []
    ledger: list[TransactionOut] = []


class LedgerSummary(BaseModel):
    """Headline Bahi Khata numbers, all derived from transactions."""

    total_given: Money = Decimal("0.00")
    total_received: Money = Decimal("0.00")
    outstanding_receivable: Money = Decimal("0.00")
    total_borrowed: Money = Decimal("0.00")
    total_repaid: Money = Decimal("0.00")
    outstanding_payable: Money = Decimal("0.00")
    net_position: Money = Decimal("0.00")
    settlement_rate: float = 0
    people_count: int = 0
    active_entries: int = 0
    settled_entries: int = 0
    overdue_entries: int = 0
    overdue_amount: Money = Decimal("0.00")
    largest_outstanding: dict | None = None
    oldest_outstanding: dict | None = None


class LedgerAnalytics(BaseModel):
    summary: LedgerSummary
    monthly_trend: list[dict] = []
    outstanding_by_person: list[dict] = []
    status_breakdown: list[dict] = []
    direction_split: list[dict] = []
