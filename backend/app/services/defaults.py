"""Per-user starter data created at registration.

Categories are seeded per user rather than shared globally so that renaming or
deleting one can never affect another account.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.enums import CategoryKind, IncomeType
from app.models.finance import ExpenseCategory, IncomeSource
from app.models.life import LifeGoalCategory

# name, icon, color
DEFAULT_EXPENSE_CATEGORIES: list[tuple[str, str, str]] = [
    ("Food", "utensils", "#f97316"),
    ("Travel", "plane", "#0ea5e9"),
    ("Shopping", "shopping-bag", "#ec4899"),
    ("Bills", "receipt", "#eab308"),
    ("Rent", "home", "#8b5cf6"),
    ("Utilities", "zap", "#14b8a6"),
    ("Healthcare", "heart-pulse", "#ef4444"),
    ("Education", "graduation-cap", "#3b82f6"),
    ("Family", "users", "#a855f7"),
    ("Entertainment", "clapperboard", "#f43f5e"),
    ("Investments", "trending-up", "#22c55e"),
    ("EMI", "landmark", "#64748b"),
    ("Personal", "user", "#06b6d4"),
    ("Other", "circle-ellipsis", "#94a3b8"),
]

DEFAULT_INCOME_CATEGORIES: list[tuple[str, str, str]] = [
    ("Salary", "wallet", "#22c55e"),
    ("Bonus", "gift", "#84cc16"),
    ("Freelance", "briefcase", "#10b981"),
    ("Interest", "percent", "#0d9488"),
    ("Other Income", "circle-plus", "#4ade80"),
]

DEFAULT_LIFE_CATEGORIES: list[tuple[str, str, str]] = [
    ("Travel", "map", "#0ea5e9"),
    ("Spiritual", "flame", "#f97316"),
    ("Adventure", "mountain", "#16a34a"),
    ("Financial", "coins", "#8b5cf6"),
    ("Career", "briefcase", "#3b82f6"),
    ("Health", "heart-pulse", "#ef4444"),
    ("Learning", "book-open", "#eab308"),
    ("Personal", "sparkles", "#ec4899"),
]


def seed_user_defaults(db: Session, user_id: uuid.UUID) -> None:
    """Create the starter categories for a brand new account."""
    for order, (name, icon, color) in enumerate(DEFAULT_EXPENSE_CATEGORIES):
        db.add(
            ExpenseCategory(
                user_id=user_id,
                name=name,
                kind=CategoryKind.EXPENSE.value,
                icon=icon,
                color=color,
                is_default=True,
                sort_order=order,
            )
        )

    for order, (name, icon, color) in enumerate(DEFAULT_INCOME_CATEGORIES):
        db.add(
            ExpenseCategory(
                user_id=user_id,
                name=name,
                kind=CategoryKind.INCOME.value,
                icon=icon,
                color=color,
                is_default=True,
                sort_order=order,
            )
        )

    for order, (name, icon, color) in enumerate(DEFAULT_LIFE_CATEGORIES):
        db.add(
            LifeGoalCategory(user_id=user_id, name=name, icon=icon, color=color, sort_order=order)
        )

    db.add(
        IncomeSource(
            user_id=user_id,
            name="Primary Salary",
            income_type=IncomeType.SALARY.value,
            is_active=True,
        )
    )
