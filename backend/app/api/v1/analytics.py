"""Cross-module analytics: the tabbed Analytics screen.

Financial and investment figures are omitted (not masked with fake zeros)
while the session is locked - financial_locked tells the frontend which tabs
to show behind the PIN prompt.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentAuth, DbSession
from app.schemas.dashboard import AnalyticsOverview
from app.schemas.ledger import LedgerAnalytics
from app.services import dashboard as dashboard_service
from app.services import ledger as ledger_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("", response_model=AnalyticsOverview)
def analytics_overview(db: DbSession, ctx: CurrentAuth) -> AnalyticsOverview:
    return AnalyticsOverview.model_validate(dashboard_service.build_analytics(db, ctx))


@router.get("/bahi-khata", response_model=LedgerAnalytics)
def bahi_khata_analytics(db: DbSession, ctx: CurrentAuth, months: int = 12) -> LedgerAnalytics:
    return LedgerAnalytics.model_validate(ledger_service.get_analytics(db, ctx.user_id, months))
