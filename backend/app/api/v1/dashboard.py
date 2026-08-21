"""The master dashboard endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentAuth, DbSession
from app.schemas.dashboard import DashboardOut
from app.services import dashboard as service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(db: DbSession, ctx: CurrentAuth) -> DashboardOut:
    return DashboardOut.model_validate(service.build_dashboard(db, ctx))
