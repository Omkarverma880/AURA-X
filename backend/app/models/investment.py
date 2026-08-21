"""Investment accounts, holdings, transactions and financial goal plans."""

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
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, user_fk
from app.db.types import GUID, Money, Quantity, Rate
from app.models.enums import AssetType, GoalStatus, InvestmentTxnType, Priority


class InvestmentAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A broker, fund house or institution holding assets.

    ``external_provider``/``external_ref`` are the seam for a future Kite or
    bank integration - nothing reads them today.
    """

    __tablename__ = "investment_accounts"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_inv_account_user_name"),)

    user_id: Mapped[uuid.UUID] = user_fk()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    broker: Mapped[str | None] = mapped_column(String(120))
    account_number: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    external_provider: Mapped[str | None] = mapped_column(String(40))
    external_ref: Mapped[str | None] = mapped_column(String(120))

    holdings: Mapped[list["InvestmentHolding"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class InvestmentHolding(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A single asset position.

    Invested amount and units are derived from transactions; only the current
    market price is stored (it cannot be derived and is refreshed manually
    until a market-data feed is connected).
    """

    __tablename__ = "investment_holdings"
    __table_args__ = (
        Index("ix_holdings_user_asset_type", "user_id", "asset_type"),
        Index("ix_holdings_user_active", "user_id", "is_active"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("investment_accounts.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(40))
    asset_type: Mapped[str] = mapped_column(
        String(20), default=AssetType.STOCK.value, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    current_price: Mapped[Decimal | None] = mapped_column(Money)
    price_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: For assets quoted as a lump sum (FD, PPF) rather than per unit.
    manual_value: Mapped[Decimal | None] = mapped_column(Money)
    maturity_date: Mapped[date | None] = mapped_column(Date)
    interest_rate: Mapped[Decimal | None] = mapped_column(Rate)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped[InvestmentAccount | None] = relationship(back_populates="holdings")
    transactions: Mapped[list["InvestmentTransaction"]] = relationship(
        back_populates="holding",
        cascade="all, delete-orphan",
        order_by="InvestmentTransaction.txn_date",
    )


class InvestmentTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "investment_transactions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_inv_txn_amount_non_negative"),
        Index("ix_inv_txn_user_date", "user_id", "txn_date"),
        Index("ix_inv_txn_user_holding", "user_id", "holding_id"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    holding_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("investment_holdings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    txn_type: Mapped[str] = mapped_column(
        String(20), default=InvestmentTxnType.BUY.value, nullable=False
    )
    txn_date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    units: Mapped[Decimal] = mapped_column(Quantity, default=Decimal("0"), nullable=False)
    price_per_unit: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    #: Gross value of the transaction before fees.
    amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    fees: Mapped[Decimal] = mapped_column(Money, default=Decimal("0.00"), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300))

    holding: Mapped[InvestmentHolding] = relationship(back_populates="transactions")


class InvestmentGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A financial target with a projection plan, e.g. "5 crore by age 45"."""

    __tablename__ = "investment_goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_inv_goal_target_positive"),
        Index("ix_inv_goals_user_status", "user_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text)
    target_amount: Mapped[Decimal] = mapped_column(Money, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date)
    current_age: Mapped[int | None] = mapped_column(Integer)
    target_age: Mapped[int | None] = mapped_column(Integer)
    #: Starting corpus. When NULL the live portfolio value is used instead.
    current_corpus: Mapped[Decimal | None] = mapped_column(Money)
    use_portfolio_value: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expected_return: Mapped[Decimal] = mapped_column(Rate, default=Decimal("12.0000"), nullable=False)
    monthly_investment: Mapped[Decimal] = mapped_column(
        Money, default=Decimal("0.00"), nullable=False
    )
    step_up_percent: Mapped[Decimal] = mapped_column(Rate, default=Decimal("0.0000"), nullable=False)
    inflation_rate: Mapped[Decimal] = mapped_column(Rate, default=Decimal("0.0000"), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default=Priority.MEDIUM.value, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=GoalStatus.IN_PROGRESS.value, nullable=False
    )
