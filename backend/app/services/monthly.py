"""Monthly expenditure analytics and budget tracking.

These are the numbers behind the expenditure dashboard. All of them are
aggregated in SQL: the endpoint never downloads a year of transactions to add
them up in Python.
"""

from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import String, case, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import InvestmentTxnType, LedgerDirection, LedgerTxnType
from app.models.finance import Budget, Expense, ExpenseCategory, IncomeRecord
from app.models.investment import InvestmentTransaction
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.services.expenses import _money, serialise_expense, month_end, month_start
from app.services.ownership import assert_owned, get_owned, owned_query

ZERO = Decimal("0.00")


def previous_month(period: date) -> date:
    first = month_start(period)
    return (first - timedelta(days=1)).replace(day=1)


def income_for(db: Session, user_id: uuid.UUID, period: date) -> tuple[Decimal, Decimal]:
    row = db.execute(
        select(
            func.coalesce(func.sum(IncomeRecord.net_amount), 0),
            func.coalesce(func.sum(IncomeRecord.gross_amount), 0),
        ).where(
            IncomeRecord.user_id == user_id,
            IncomeRecord.is_deleted.is_(False),
            IncomeRecord.period_month == month_start(period),
        )
    ).one()
    return _money(row[0]), _money(row[1])


def expenses_for(db: Session, user_id: uuid.UUID, period: date) -> tuple[Decimal, int]:
    row = db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0), func.count(Expense.id)).where(
            Expense.user_id == user_id,
            Expense.is_deleted.is_(False),
            Expense.spent_on >= month_start(period),
            Expense.spent_on < month_end(period),
        )
    ).one()
    return _money(row[0]), int(row[1])


def invested_for(db: Session, user_id: uuid.UUID, period: date) -> Decimal:
    """Net money put into investments during the month (buys less sells)."""
    row = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            InvestmentTransaction.txn_type == InvestmentTxnType.BUY.value,
                            InvestmentTransaction.amount + InvestmentTransaction.fees,
                        ),
                        (
                            InvestmentTransaction.txn_type == InvestmentTxnType.SELL.value,
                            -InvestmentTransaction.amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            )
        ).where(
            InvestmentTransaction.user_id == user_id,
            InvestmentTransaction.txn_date >= month_start(period),
            InvestmentTransaction.txn_date < month_end(period),
        )
    ).scalar_one()
    return _money(row)


def ledger_flow_for(db: Session, user_id: uuid.UUID, period: date) -> tuple[Decimal, Decimal]:
    """Money lent out and money received back during the month."""
    rows = db.execute(
        select(
            LedgerEntry.direction,
            LedgerTransaction.txn_type,
            func.coalesce(func.sum(LedgerTransaction.amount), 0).label("amount"),
        )
        .join(LedgerEntry, LedgerEntry.id == LedgerTransaction.entry_id)
        .where(
            LedgerTransaction.user_id == user_id,
            LedgerTransaction.is_voided.is_(False),
            LedgerEntry.is_deleted.is_(False),
            LedgerTransaction.txn_date >= month_start(period),
            LedgerTransaction.txn_date < month_end(period),
        )
        .group_by(LedgerEntry.direction, LedgerTransaction.txn_type)
    ).all()

    given = received = ZERO
    for row in rows:
        amount = _money(row.amount)
        is_principal = row.txn_type in (
            LedgerTxnType.PRINCIPAL.value,
            LedgerTxnType.INTEREST.value,
        )
        if row.direction == LedgerDirection.GIVEN.value and is_principal:
            given += amount
        elif row.direction == LedgerDirection.GIVEN.value and not is_principal:
            received += amount
    return given, received


def category_breakdown(db: Session, user_id: uuid.UUID, period: date) -> list[dict]:
    """Spend per category for the month."""
    rows = db.execute(
        select(
            Expense.category_id,
            ExpenseCategory.name,
            ExpenseCategory.icon,
            ExpenseCategory.color,
            func.coalesce(func.sum(Expense.amount), 0).label("amount"),
            func.count(Expense.id).label("count"),
        )
        .outerjoin(ExpenseCategory, ExpenseCategory.id == Expense.category_id)
        .where(
            Expense.user_id == user_id,
            Expense.is_deleted.is_(False),
            Expense.spent_on >= month_start(period),
            Expense.spent_on < month_end(period),
        )
        .group_by(Expense.category_id, ExpenseCategory.name, ExpenseCategory.icon, ExpenseCategory.color)
    ).all()

    total = sum((_money(row.amount) for row in rows), ZERO)
    breakdown = [
        {
            "category_id": row.category_id,
            "name": row.name or "Uncategorised",
            "icon": row.icon,
            "color": row.color or "#94a3b8",
            "amount": _money(row.amount),
            "share": round(float(_money(row.amount) / total * 100), 1) if total > ZERO else 0.0,
            "count": int(row.count),
        }
        for row in rows
    ]
    breakdown.sort(key=lambda item: item["amount"], reverse=True)
    return breakdown


def monthly_summary(db: Session, user_id: uuid.UUID, period: date) -> dict:
    period = month_start(period)
    net_income, gross_income = income_for(db, user_id, period)
    spent, expense_count = expenses_for(db, user_id, period)
    invested = invested_for(db, user_id, period)
    given, received = ledger_flow_for(db, user_id, period)

    savings = net_income - spent
    savings_rate = float(savings / net_income * 100) if net_income > ZERO else 0.0

    previous = previous_month(period)
    previous_spent, _ = expenses_for(db, user_id, previous)
    change = (
        float((spent - previous_spent) / previous_spent * 100) if previous_spent > ZERO else 0.0
    )

    days = monthrange(period.year, period.month)[1]
    today = date.today()
    # Part-way through the current month, average over elapsed days only.
    elapsed = today.day if (today.year, today.month) == (period.year, period.month) else days
    daily_average = _money(spent / max(elapsed, 1))

    budgets = budget_overview(db, user_id, period)
    budget_total = sum((item["amount"] for item in budgets), ZERO)
    budget_used = float(spent / budget_total * 100) if budget_total > ZERO else 0.0

    top_stmt = (
        owned_query(Expense, user_id)
        .options(selectinload(Expense.category))
        .where(Expense.spent_on >= period, Expense.spent_on < month_end(period))
        .order_by(Expense.amount.desc())
        .limit(5)
    )
    recurring_stmt = (
        owned_query(Expense, user_id)
        .options(selectinload(Expense.category))
        .where(
            Expense.is_recurring.is_(True),
            Expense.spent_on >= period,
            Expense.spent_on < month_end(period),
        )
        .order_by(Expense.amount.desc())
        .limit(10)
    )

    return {
        "period_month": period,
        "income": net_income,
        "gross_income": gross_income,
        "expenses": spent,
        "savings": savings,
        "savings_rate": round(savings_rate, 1),
        "investments": invested,
        "money_given": given,
        "money_received": received,
        "expense_count": expense_count,
        "daily_average": daily_average,
        "budget_total": budget_total,
        "budget_used": round(budget_used, 1),
        "by_category": category_breakdown(db, user_id, period),
        "top_expenses": [serialise_expense(row) for row in db.execute(top_stmt).scalars()],
        "recurring": [serialise_expense(row) for row in db.execute(recurring_stmt).scalars()],
        "previous_expenses": previous_spent,
        "change_percent": round(change, 1),
    }


def monthly_trend(db: Session, user_id: uuid.UUID, months: int = 12) -> list[dict]:
    """Income, expenses and savings per month, in two grouped queries."""
    month_of = lambda column: func.substr(func.cast(column, String), 1, 7)  # noqa: E731

    expense_rows = db.execute(
        select(
            month_of(Expense.spent_on).label("month"),
            func.coalesce(func.sum(Expense.amount), 0).label("amount"),
        )
        .where(Expense.user_id == user_id, Expense.is_deleted.is_(False))
        .group_by("month")
    ).all()

    income_rows = db.execute(
        select(
            month_of(IncomeRecord.period_month).label("month"),
            func.coalesce(func.sum(IncomeRecord.net_amount), 0).label("amount"),
        )
        .where(IncomeRecord.user_id == user_id, IncomeRecord.is_deleted.is_(False))
        .group_by("month")
    ).all()

    buckets: dict[str, dict] = {}
    for row in expense_rows:
        buckets.setdefault(row.month, {"month": row.month, "income": ZERO, "expenses": ZERO})
        buckets[row.month]["expenses"] = _money(row.amount)
    for row in income_rows:
        buckets.setdefault(row.month, {"month": row.month, "income": ZERO, "expenses": ZERO})
        buckets[row.month]["income"] = _money(row.amount)

    series = []
    for bucket in sorted(buckets.values(), key=lambda item: item["month"])[-months:]:
        savings = bucket["income"] - bucket["expenses"]
        rate = float(savings / bucket["income"] * 100) if bucket["income"] > ZERO else 0.0
        series.append({**bucket, "savings": savings, "savings_rate": round(rate, 1)})
    return series


# --- Budgets -----------------------------------------------------------


def budget_overview(db: Session, user_id: uuid.UUID, period: date) -> list[dict]:
    """Budget against actual spend for one month."""
    period = month_start(period)
    budgets = list(
        db.execute(
            owned_query(Budget, user_id)
            .options(selectinload(Budget.category))
            .where(Budget.period_month == period)
        ).scalars()
    )

    spend_rows = db.execute(
        select(Expense.category_id, func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.user_id == user_id,
            Expense.is_deleted.is_(False),
            Expense.spent_on >= period,
            Expense.spent_on < month_end(period),
        )
        .group_by(Expense.category_id)
    ).all()
    spent_by_category = {row[0]: _money(row[1]) for row in spend_rows}

    overview = []
    for budget in budgets:
        spent = spent_by_category.get(budget.category_id, ZERO)
        remaining = budget.amount - spent
        utilisation = float(spent / budget.amount * 100) if budget.amount > ZERO else 0.0
        if utilisation >= 100:
            status = "exceeded"
        elif utilisation >= 80:
            status = "warning"
        else:
            status = "on_track"

        overview.append(
            {
                "id": budget.id,
                "category_id": budget.category_id,
                "category_name": budget.category.name if budget.category else None,
                "category_icon": budget.category.icon if budget.category else None,
                "category_color": budget.category.color if budget.category else None,
                "period_month": budget.period_month,
                "amount": budget.amount,
                "spent": spent,
                "remaining": remaining,
                "utilisation": round(utilisation, 1),
                "status": status,
                "notes": budget.notes,
            }
        )
    overview.sort(key=lambda item: item["utilisation"], reverse=True)
    return overview


def upsert_budget(db: Session, user_id: uuid.UUID, data: dict) -> Budget:
    """Create or replace the budget for one category and month."""
    assert_owned(db, ExpenseCategory, data["category_id"], user_id)
    period = month_start(data["period_month"])

    budget = db.execute(
        owned_query(Budget, user_id).where(
            Budget.category_id == data["category_id"], Budget.period_month == period
        )
    ).scalar_one_or_none()

    if budget is None:
        budget = Budget(
            user_id=user_id,
            category_id=data["category_id"],
            period_month=period,
            amount=data["amount"],
            notes=data.get("notes"),
        )
        db.add(budget)
    else:
        budget.amount = data["amount"]
        budget.notes = data.get("notes", budget.notes)
    db.flush()
    return budget


def delete_budget(db: Session, user_id: uuid.UUID, budget_id: uuid.UUID) -> None:
    db.delete(get_owned(db, Budget, budget_id, user_id))


def copy_budgets(db: Session, user_id: uuid.UUID, source: date, target: date) -> int:
    """Carry a month of budgets forward, so a routine is set up once."""
    source, target = month_start(source), month_start(target)
    existing = {
        row.category_id
        for row in db.execute(
            owned_query(Budget, user_id).where(Budget.period_month == target)
        ).scalars()
    }
    copied = 0
    for budget in db.execute(
        owned_query(Budget, user_id).where(Budget.period_month == source)
    ).scalars():
        if budget.category_id in existing:
            continue
        db.add(
            Budget(
                user_id=user_id,
                category_id=budget.category_id,
                period_month=target,
                amount=budget.amount,
                notes=budget.notes,
            )
        )
        copied += 1
    return copied
