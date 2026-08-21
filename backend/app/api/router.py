"""Versioned API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    budgets,
    checklists,
    dashboard,
    expenses,
    export,
    goals,
    income,
    investments,
    ledger,
    media,
    memories,
    notifications,
    search,
    security,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(security.router)
api_router.include_router(dashboard.router)
api_router.include_router(ledger.router)
api_router.include_router(expenses.categories_router)
# summary_router declares literal paths under /expenses (monthly-summary,
# trend) and must be registered before expenses.router's /expenses/{id}
# catch-all, or FastAPI matches the catch-all first and 422s on the literal.
api_router.include_router(budgets.summary_router)
api_router.include_router(expenses.router)
api_router.include_router(income.router)
api_router.include_router(budgets.router)
api_router.include_router(investments.router)
api_router.include_router(investments.goals_router)
api_router.include_router(goals.router)
api_router.include_router(checklists.router)
api_router.include_router(memories.router)
api_router.include_router(analytics.router)
api_router.include_router(notifications.router)
api_router.include_router(search.router)
api_router.include_router(export.router)
api_router.include_router(media.router)
