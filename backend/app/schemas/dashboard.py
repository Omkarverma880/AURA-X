"""Master dashboard and cross-module analytics schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import Money, OptionalMoney
from app.schemas.finance import MonthlySummary
from app.schemas.investment import PortfolioSummary
from app.schemas.ledger import LedgerSummary
from app.schemas.life import LifeAnalytics


class GreetingBlock(BaseModel):
    name: str
    greeting: str
    date: str
    privacy_mode: bool = False


class FinancialSnapshot(BaseModel):
    """Bahi Khata figures are never confidential; income/expense figures are
    null (not zero) while the Green PIN is locked, so the frontend can render
    a masked placeholder instead of a misleading ₹0."""

    money_given: Money
    to_receive: Money
    money_borrowed: Money
    to_pay: Money
    net_position: Money

    monthly_income: OptionalMoney = None
    monthly_expenses: OptionalMoney = None
    net_savings: OptionalMoney = None
    savings_rate: float | None = None
    financial_locked: bool = False


class ModuleCard(BaseModel):
    module: str
    headline: str
    subtext: str
    trend: str | None = None  # "up" | "down" | "flat"
    locked: bool = False


class DashboardOut(BaseModel):
    greeting: GreetingBlock
    snapshot: FinancialSnapshot
    cards: list[ModuleCard] = []
    upcoming_reminders: list[dict] = []
    recent_activity: list[dict] = []
    unread_notifications: int = 0


class AnalyticsOverview(BaseModel):
    financial: MonthlySummary | None = None
    bahi_khata: LedgerSummary
    investments: PortfolioSummary | None = None
    life: LifeAnalytics
    financial_locked: bool = False
