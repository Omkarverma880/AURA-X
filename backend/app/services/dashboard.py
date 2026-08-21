"""The master dashboard: one aggregate call, real numbers, nothing hardcoded.

Every figure here is computed by the same service functions the dedicated
module pages use - there is no separate "dashboard truth" that could drift
from the real one. The only dashboard-specific logic is which of those
figures to show while financial data is locked.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, finance_visible
from app.models.ledger import LedgerEntry
from app.models.life import LifeGoal
from app.services import expenses as expense_service
from app.services import investments as investment_service
from app.services import ledger as ledger_service
from app.services import life as life_service
from app.services import monthly as monthly_service
from app.services import notifications as notification_service


def _greeting(hour: int) -> str:
    if hour < 5:
        return "Still up"
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    if hour < 21:
        return "Good evening"
    return "Good night"


def build_dashboard(db: Session, ctx: AuthContext) -> dict:
    now = datetime.now(timezone.utc)
    unlocked = finance_visible(ctx, db)

    ledger_summary = ledger_service.get_summary(db, ctx.user_id)

    monthly = None
    if unlocked:
        monthly = monthly_service.monthly_summary(db, ctx.user_id, date.today())

    snapshot = {
        "money_given": ledger_summary["outstanding_receivable"],
        "to_receive": ledger_summary["outstanding_receivable"],
        "money_borrowed": ledger_summary["total_borrowed"],
        "to_pay": ledger_summary["outstanding_payable"],
        "net_position": ledger_summary["net_position"],
        "monthly_income": monthly["income"] if monthly else None,
        "monthly_expenses": monthly["expenses"] if monthly else None,
        "net_savings": monthly["savings"] if monthly else None,
        "savings_rate": monthly["savings_rate"] if monthly else None,
        "financial_locked": not unlocked,
    }

    cards = _build_cards(db, ctx.user_id, ledger_summary, monthly, unlocked)
    reminders = _upcoming_reminders(db, ctx.user_id)
    activity = _recent_activity(db, ctx.user_id)
    unread = notification_service.unread_count(db, ctx.user_id)

    return {
        "greeting": {
            "name": ctx.user.full_name.split(" ")[0],
            "greeting": _greeting(now.hour),
            "date": date.today().isoformat(),
            "privacy_mode": not unlocked,
        },
        "snapshot": snapshot,
        "cards": cards,
        "upcoming_reminders": reminders,
        "recent_activity": activity,
        "unread_notifications": unread,
    }


def _build_cards(
    db: Session, user_id: uuid.UUID, ledger_summary: dict, monthly: dict | None, unlocked: bool
) -> list[dict]:
    cards = []

    due = ledger_summary["outstanding_receivable"] + ledger_summary["outstanding_payable"]
    cards.append(
        {
            "module": "bahi_khata",
            "headline": f"₹{ledger_summary['outstanding_receivable']:,.0f} to receive",
            "subtext": f"₹{ledger_summary['outstanding_payable']:,.0f} to pay · "
            f"{ledger_summary['active_entries']} active",
            "trend": "up" if ledger_summary["outstanding_receivable"] > ledger_summary["outstanding_payable"] else "down",
            "locked": False,
        }
    )

    if unlocked and monthly is not None:
        cards.append(
            {
                "module": "expenses",
                "headline": f"₹{monthly['expenses']:,.0f} spent this month",
                "subtext": f"Savings rate {monthly['savings_rate']:.0f}%",
                "trend": "down" if monthly["change_percent"] > 0 else "up",
                "locked": False,
            }
        )
    else:
        cards.append(
            {"module": "expenses", "headline": "••••••", "subtext": "Unlock to view", "locked": True}
        )

    if unlocked:
        portfolio = investment_service.portfolio_summary(db, user_id)
        cards.append(
            {
                "module": "investments",
                "headline": f"₹{portfolio['current_value']:,.0f}",
                "subtext": f"{portfolio['return_percent']:+.1f}% overall return",
                "trend": "up" if portfolio["return_percent"] >= 0 else "down",
                "locked": False,
            }
        )
    else:
        cards.append(
            {"module": "investments", "headline": "••••••", "subtext": "Unlock to view", "locked": True}
        )

    goals = life_service.list_goals(db, user_id)
    completed = sum(1 for g in goals if g["status"] == "completed")
    cards.append(
        {
            "module": "goals",
            "headline": f"{completed}/{len(goals)} goals completed",
            "subtext": f"{sum(1 for g in goals if g['is_overdue'])} overdue" if goals else "Nothing tracked yet",
            "trend": "flat",
            "locked": False,
        }
    )

    life_stats = life_service.life_analytics(db, user_id)
    cards.append(
        {
            "module": "life",
            "headline": f"{life_stats['trips_completed']} trips · {life_stats['memory_count']} albums",
            "subtext": f"{len(life_stats['trackers'])} custom trackers",
            "trend": "flat",
            "locked": False,
        }
    )
    return cards


def _upcoming_reminders(db: Session, user_id: uuid.UUID, limit: int = 5) -> list[dict]:
    today = date.today()
    stmt = (
        select(LedgerEntry)
        .where(
            LedgerEntry.user_id == user_id,
            LedgerEntry.is_deleted.is_(False),
            LedgerEntry.is_closed.is_(False),
            LedgerEntry.due_date.is_not(None),
            LedgerEntry.due_date >= today,
        )
        .order_by(LedgerEntry.due_date)
        .limit(limit)
    )
    reminders = [
        {
            "type": "ledger_due",
            "title": f"{'Collect from' if e.direction == 'given' else 'Pay'} {e.person.name if e.person else ''}",
            "detail": e.purpose,
            "due_date": e.due_date.isoformat(),
            "entity_id": str(e.id),
        }
        for e in db.execute(stmt).scalars()
    ]

    goal_stmt = (
        select(LifeGoal)
        .where(
            LifeGoal.user_id == user_id,
            LifeGoal.is_deleted.is_(False),
            LifeGoal.status.notin_(["completed", "abandoned"]),
            LifeGoal.target_date.is_not(None),
            LifeGoal.target_date >= today,
        )
        .order_by(LifeGoal.target_date)
        .limit(limit)
    )
    for goal in db.execute(goal_stmt).scalars():
        reminders.append(
            {
                "type": "goal_deadline",
                "title": goal.title,
                "detail": "Target date approaching",
                "due_date": goal.target_date.isoformat(),
                "entity_id": str(goal.id),
            }
        )

    reminders.sort(key=lambda r: r["due_date"])
    return reminders[:limit]


def _recent_activity(db: Session, user_id: uuid.UUID, limit: int = 8) -> list[dict]:
    from app.models.system import AuditLog

    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(desc(AuditLog.created_at))
        .limit(limit)
    )
    return [
        {
            "action": row.action,
            "summary": row.summary,
            "entity_type": row.entity_type,
            "created_at": row.created_at.isoformat(),
        }
        for row in db.execute(stmt).scalars()
    ]


def build_analytics(db: Session, ctx: AuthContext) -> dict:
    unlocked = finance_visible(ctx, db)
    return {
        "financial": monthly_service.monthly_summary(db, ctx.user_id, date.today()) if unlocked else None,
        "bahi_khata": ledger_service.get_summary(db, ctx.user_id),
        "investments": investment_service.portfolio_summary(db, ctx.user_id) if unlocked else None,
        "life": life_service.life_analytics(db, ctx.user_id),
        "financial_locked": not unlocked,
    }
