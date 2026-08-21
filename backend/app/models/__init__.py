"""ORM models.

Importing this package registers every table on the shared metadata, which is
what Alembic autogenerate and the test bootstrap rely on.
"""

from app.db.base import Base
from app.models.finance import Budget, Expense, ExpenseCategory, IncomeRecord, IncomeSource
from app.models.investment import (
    InvestmentAccount,
    InvestmentGoal,
    InvestmentHolding,
    InvestmentTransaction,
)
from app.models.ledger import LedgerEntry, LedgerTransaction, Person
from app.models.life import Checklist, ChecklistItem, GoalMilestone, LifeGoal, LifeGoalCategory
from app.models.memories import Album, Photo
from app.models.system import AuditLog, Notification
from app.models.user import (
    AuthAccount,
    PhoneOtp,
    SecuritySetting,
    User,
    UserProfile,
    UserSession,
    VerificationToken,
)

__all__ = [
    "Base",
    "User",
    "UserProfile",
    "AuthAccount",
    "SecuritySetting",
    "UserSession",
    "PhoneOtp",
    "VerificationToken",
    "Person",
    "LedgerEntry",
    "LedgerTransaction",
    "ExpenseCategory",
    "Expense",
    "IncomeSource",
    "IncomeRecord",
    "Budget",
    "InvestmentAccount",
    "InvestmentHolding",
    "InvestmentTransaction",
    "InvestmentGoal",
    "LifeGoalCategory",
    "LifeGoal",
    "GoalMilestone",
    "Checklist",
    "ChecklistItem",
    "Album",
    "Photo",
    "Notification",
    "AuditLog",
]
