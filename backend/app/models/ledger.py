"""Bahi Khata - the lending / borrowing ledger.

Accounting model: a LedgerEntry is an *account* opened against a person, and
every rupee that moves is an immutable LedgerTransaction. Balances are always
derived by summing signed transactions - there is no mutable balance column to
drift out of step with history.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, user_fk
from app.db.types import GUID, Money
from app.models.enums import TXN_SIGN, LedgerDirection, LedgerTxnType


class Person(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A counterparty: someone money was given to or borrowed from."""

    __tablename__ = "ledger_people"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_person_user_name"),
        Index("ix_ledger_people_user_archived", "user_id", "is_archived"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(320))
    relation: Mapped[str | None] = mapped_column(String(60))
    notes: Mapped[str | None] = mapped_column(Text)
    #: Deterministic avatar tint chosen at creation time.
    color: Mapped[str | None] = mapped_column(String(20))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    entries: Mapped[list["LedgerEntry"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class LedgerEntry(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """One lending or borrowing arrangement with a person."""

    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("direction IN ('given','borrowed')", name="ck_ledger_direction"),
        Index("ix_ledger_entries_user_direction", "user_id", "direction"),
        Index("ix_ledger_entries_user_person", "user_id", "person_id"),
        Index("ix_ledger_entries_user_due", "user_id", "due_date"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    person_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("ledger_people.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    purpose: Mapped[str] = mapped_column(String(200), nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    due_date: Mapped[date | None] = mapped_column(Date)
    reminder_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    #: Explicit closure flag for arrangements settled by agreement rather than
    #: by a final payment. Balance-derived settlement needs no flag.
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    person: Mapped[Person] = relationship(back_populates="entries")
    transactions: Mapped[list["LedgerTransaction"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="LedgerTransaction.txn_date",
    )

    # --- Derived money (never persisted) ------------------------------
    def _sum(self, *types: LedgerTxnType) -> Decimal:
        wanted = {t.value for t in types}
        return sum(
            (t.amount for t in self.transactions if not t.is_voided and t.txn_type in wanted),
            Decimal("0.00"),
        )

    @property
    def principal_amount(self) -> Decimal:
        return self._sum(LedgerTxnType.PRINCIPAL)

    @property
    def settled_amount(self) -> Decimal:
        return self._sum(LedgerTxnType.REPAYMENT, LedgerTxnType.WRITE_OFF)

    @property
    def outstanding(self) -> Decimal:
        return sum(
            (Decimal(TXN_SIGN[t.txn_type]) * t.amount for t in self.transactions if not t.is_voided),
            Decimal("0.00"),
        )


class LedgerTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An immutable money movement.

    Rows are never edited in place: a mistake is corrected by voiding the row
    (keeping it visible in history) and recording a replacement.
    """

    __tablename__ = "ledger_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ledger_txn_amount_positive"),
        Index("ix_ledger_txn_user_date", "user_id", "txn_date"),
        Index("ix_ledger_txn_user_entry", "user_id", "entry_id"),
        Index("ix_ledger_txn_user_person_date", "user_id", "person_id", "txn_date"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    entry_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("ledger_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: Denormalised so person-level ledgers avoid a join on the hot path. Kept
    #: consistent by the service layer, never written by clients.
    person_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("ledger_people.id", ondelete="CASCADE"), nullable=False, index=True
    )
    txn_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    txn_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    method: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(300))
    attachment_key: Mapped[str | None] = mapped_column(String(512))

    is_voided: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(String(300))

    entry: Mapped[LedgerEntry] = relationship(back_populates="transactions")
    person: Mapped[Person] = relationship()

    @property
    def signed_amount(self) -> Decimal:
        if self.is_voided:
            return Decimal("0.00")
        return Decimal(TXN_SIGN[self.txn_type]) * self.amount
