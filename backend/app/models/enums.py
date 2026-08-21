"""Domain enumerations.

Stored as short strings rather than native PostgreSQL ENUM types: adding a new
value then needs no ALTER TYPE migration, while validation still happens in the
Pydantic layer.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def values(cls) -> list[str]:
        return [m.value for m in cls]


# --- Auth / security --------------------------------------------------
class AuthProvider(StrEnum):
    PASSWORD = "password"
    GOOGLE = "google"
    PHONE = "phone"


class TokenPurpose(StrEnum):
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"
    PIN_RESET = "pin_reset"


class Theme(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


# --- Bahi Khata -------------------------------------------------------
class LedgerDirection(StrEnum):
    GIVEN = "given"          # money I lent out - an asset / receivable
    BORROWED = "borrowed"    # money I took - a liability / payable


class LedgerTxnType(StrEnum):
    PRINCIPAL = "principal"      # increases the outstanding balance
    REPAYMENT = "repayment"      # decreases it
    INTEREST = "interest"        # increases it
    WRITE_OFF = "write_off"      # decreases it (forgiven / bad debt)


#: Sign applied to each transaction type when deriving an outstanding balance.
TXN_SIGN: dict[str, int] = {
    LedgerTxnType.PRINCIPAL.value: 1,
    LedgerTxnType.INTEREST.value: 1,
    LedgerTxnType.REPAYMENT.value: -1,
    LedgerTxnType.WRITE_OFF.value: -1,
}


class LedgerStatus(StrEnum):
    ACTIVE = "active"
    PARTIAL = "partial"
    SETTLED = "settled"
    OVERDUE = "overdue"


class PaymentMethod(StrEnum):
    CASH = "cash"
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    CHEQUE = "cheque"
    OTHER = "other"


# --- Expenditure ------------------------------------------------------
class CategoryKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class IncomeType(StrEnum):
    SALARY = "salary"
    BONUS = "bonus"
    FREELANCE = "freelance"
    INTEREST = "interest"
    DIVIDEND = "dividend"
    RENTAL = "rental"
    OTHER = "other"


class RecurrenceInterval(StrEnum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


# --- Investments ------------------------------------------------------
class AssetType(StrEnum):
    STOCK = "stock"
    MUTUAL_FUND = "mutual_fund"
    ETF = "etf"
    FIXED_DEPOSIT = "fixed_deposit"
    GOLD = "gold"
    NPS = "nps"
    PPF = "ppf"
    EPF = "epf"
    BOND = "bond"
    REAL_ESTATE = "real_estate"
    CRYPTO = "crypto"
    CASH = "cash"
    OTHER = "other"


class InvestmentTxnType(StrEnum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    FEE = "fee"
    BONUS = "bonus"


class GoalStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    ABANDONED = "abandoned"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --- Life / trackers --------------------------------------------------
class TrackerType(StrEnum):
    GENERIC = "generic"
    TEMPLE = "temple"
    TREK = "trek"
    TRIP = "trip"
    COUNTRY = "country"
    BOOK = "book"
    COURSE = "course"
    FITNESS = "fitness"
    ACHIEVEMENT = "achievement"


class AlbumType(StrEnum):
    TRIP = "trip"
    TREK = "trek"
    FAMILY = "family"
    EVENT = "event"
    GENERAL = "general"


# --- System -----------------------------------------------------------
class NotificationType(StrEnum):
    LEDGER_DUE = "ledger_due"
    BUDGET_EXCEEDED = "budget_exceeded"
    GOAL_DEADLINE = "goal_deadline"
    GOAL_PROGRESS = "goal_progress"
    INVESTMENT_UPDATE = "investment_update"
    CUSTOM = "custom"


class Severity(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    PIN_SET = "pin_set"
    PIN_CHANGED = "pin_changed"
    PIN_UNLOCK = "pin_unlock"
    PIN_FAILED = "pin_failed"
    PIN_LOCK = "pin_lock"
    EXPORT = "export"
