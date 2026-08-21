"""Income, salary, expenses, categories and monthly budgets."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, user_fk
from app.db.types import GUID, JSONType, Money
from app.models.enums import CategoryKind, IncomeType, RecurrenceInterval


class ExpenseCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User-owned category tree (one level of sub-categories).

    Defaults are seeded per user rather than shared globally, so anyone can
    rename or delete them without affecting other accounts.
    """

    __tablename__ = "expense_categories"
    __table_args__ = (
        UniqueConstraint("user_id", "name", "parent_id", name="uq_category_user_name_parent"),
        Index("ix_expense_categories_user_kind", "user_id", "kind"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), default=CategoryKind.EXPENSE.value, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("expense_categories.id", ondelete="CASCADE"), index=True
    )
    icon: Mapped[str | None] = mapped_column(String(40))
    color: Mapped[str | None] = mapped_column(String(20))
    #: Seeded defaults; can be archived but are protected from hard deletion
    #: once transactions reference them.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    parent: Mapped["ExpenseCategory | None"] = relationship(remote_side="ExpenseCategory.id")


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expense_amount_positive"),
        Index("ix_expenses_user_date", "user_id", "spent_on"),
        Index("ix_expenses_user_category_date", "user_id", "category_id", "spent_on"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    spent_on: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("expense_categories.id", ondelete="SET NULL"), index=True
    )
    subcategory_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("expense_categories.id", ondelete="SET NULL")
    )
    merchant: Mapped[str | None] = mapped_column(String(160))
    payment_method: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence: Mapped[str] = mapped_column(
        String(20), default=RecurrenceInterval.NONE.value, nullable=False
    )
    tags: Mapped[list | None] = mapped_column(JSONType)
    attachment_key: Mapped[str | None] = mapped_column(String(512))

    category: Mapped[ExpenseCategory | None] = relationship(foreign_keys=[category_id])
    subcategory: Mapped[ExpenseCategory | None] = relationship(foreign_keys=[subcategory_id])


class IncomeSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "income_sources"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_income_source_user_name"),)

    user_id: Mapped[uuid.UUID] = user_fk()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    income_type: Mapped[str] = mapped_column(
        String(20), default=IncomeType.SALARY.value, nullable=False
    )
    employer: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class IncomeRecord(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Salary or other income. Always Green-PIN protected on the way out."""

    __tablename__ = "income_records"
    __table_args__ = (
        CheckConstraint("net_amount >= 0", name="ck_income_net_non_negative"),
        Index("ix_income_user_date", "user_id", "received_on"),
        Index("ix_income_user_period", "user_id", "period_month"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("income_sources.id", ondelete="SET NULL"), index=True
    )
    received_on: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    #: First day of the month the income belongs to - makes monthly rollups a
    #: simple indexed equality check instead of a date_trunc scan.
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    deductions: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)

    source: Mapped[IncomeSource | None] = relationship()


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A per-category cap for one month."""

    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "period_month", "category_id", name="uq_budget_user_month_cat"),
        CheckConstraint("amount >= 0", name="ck_budget_amount_non_negative"),
        Index("ix_budgets_user_period", "user_id", "period_month"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("expense_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300))

    category: Mapped[ExpenseCategory] = relationship()
