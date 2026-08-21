"""Development/demo seed data.

Creates one demo account with realistic-looking sample data across every
module, so a fresh clone shows a populated app instead of an empty shell.
Uses no real production credentials - the password is printed to the console,
never hard-coded into anything that ships.

Run with:  python -m app.db.seed
"""

from __future__ import annotations

import secrets
import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.logging import configure_logging, get_logger
from app.db.session import SessionLocal, engine
from app.models import Base
from app.models.enums import AlbumType, LedgerTxnType, TrackerType
from app.services import auth as auth_service
from app.services import expenses as expense_service
from app.services import investments as investment_service
from app.services import ledger as ledger_service
from app.services import life as life_service
from app.services import memories as memory_service
from app.services import notifications as notification_service
from app.services.green_pin import set_pin

logger = get_logger(__name__)

DEMO_EMAIL = "demo@aurax.app"
DEMO_NAME = "Demo User"
DEMO_GREEN_PIN = "2468"


def _random_password() -> str:
    return f"Demo-{secrets.token_urlsafe(9)}"


def seed(db: Session, *, reset: bool = False) -> None:
    existing = auth_service.get_user_by_email(db, DEMO_EMAIL)
    if existing is not None:
        if not reset:
            logger.info("Demo user already exists (%s) - skipping seed.", DEMO_EMAIL)
            return
        logger.info("Removing existing demo user before reseeding.")
        db.delete(existing)
        db.commit()

    password = _random_password()
    user = auth_service.create_user(
        db, email=DEMO_EMAIL, full_name=DEMO_NAME, password=password, is_verified=True
    )
    db.flush()
    set_pin(db, user, DEMO_GREEN_PIN)

    _seed_bahi_khata(db, user.id)
    _seed_expenses_and_income(db, user.id)
    _seed_investments(db, user.id)
    _seed_life(db, user.id)
    _seed_memories(db, user.id)

    db.commit()
    notification_service.refresh_reminders(db, user.id)
    db.commit()

    logger.info("Seed complete.")
    print("\nDemo account ready:")
    print(f"  Email:     {DEMO_EMAIL}")
    print(f"  Password:  {password}")
    print(f"  Green PIN: {DEMO_GREEN_PIN}\n")


def _seed_bahi_khata(db: Session, user_id) -> None:
    today = date.today()

    ledger_service.create_entry(
        db, user_id,
        {
            "person_name": "Parbhu", "direction": "given", "purpose": "Tungnath trip",
            "amount": Decimal("12000"), "entry_date": today - timedelta(days=40),
        },
    )
    ledger_service.create_entry(
        db, user_id,
        {
            "person_name": "Parbhu", "direction": "given", "purpose": "Personal loan",
            "amount": Decimal("54592"), "entry_date": today - timedelta(days=20),
            "due_date": today + timedelta(days=10),
        },
    )
    rahul_entry = ledger_service.create_entry(
        db, user_id,
        {
            "person_name": "Rahul", "direction": "borrowed", "purpose": "Emergency",
            "amount": Decimal("20000"), "entry_date": today - timedelta(days=60),
        },
    )
    ledger_service.add_transaction(
        db, user_id, rahul_entry.id,
        {"txn_type": LedgerTxnType.REPAYMENT.value, "amount": Decimal("5000"),
         "txn_date": today - timedelta(days=10)},
    )

    narayan = ledger_service.create_entry(
        db, user_id,
        {
            "person_name": "Narayan Dai", "direction": "given", "purpose": "Kedarnath supplies",
            "amount": Decimal("8000"), "entry_date": today - timedelta(days=90),
        },
    )
    ledger_service.add_transaction(
        db, user_id, narayan.id,
        {"txn_type": LedgerTxnType.REPAYMENT.value, "amount": Decimal("8000"),
         "txn_date": today - timedelta(days=70)},
    )


def _seed_expenses_and_income(db: Session, user_id) -> None:
    today = date.today()
    categories = {c["name"]: c["id"] for c in expense_service.list_categories(db, user_id)}

    source = expense_service.create_income_source(
        db, user_id, {"name": "Primary Job", "income_type": "salary"}
    )
    for months_ago in range(3, -1, -1):
        received = today if months_ago == 0 else _shift_months(today, -months_ago).replace(day=1)
        expense_service.create_income(
            db, user_id,
            {
                "source_id": source.id, "received_on": received,
                "gross_amount": Decimal("150000"), "net_amount": Decimal("125000"),
            },
        )

    samples = [
        ("Food", "Zomato", Decimal("450.50"), "upi"),
        ("Travel", "Ola", Decimal("320"), "upi"),
        ("Bills", "Electricity board", Decimal("2100"), "bank_transfer"),
        ("Shopping", "Amazon", Decimal("1899"), "card"),
        ("Rent", "Landlord", Decimal("25000"), "bank_transfer"),
        ("Entertainment", "Netflix", Decimal("649"), "card"),
        ("Food", "Local market", Decimal("1200"), "cash"),
        ("EMI", "Bike loan", Decimal("4500"), "bank_transfer"),
    ]
    for offset, (category, merchant, amount, method) in enumerate(samples):
        expense_service.create_expense(
            db, user_id,
            {
                "spent_on": today - timedelta(days=offset * 3),
                "amount": amount, "category_id": categories.get(category),
                "merchant": merchant, "payment_method": method,
                "description": f"{merchant} - {category}",
            },
        )

    for name, amount in (("Food", 8000), ("Travel", 6000), ("Shopping", 5000), ("Bills", 4000)):
        if name in categories:
            from app.services import monthly as monthly_service

            monthly_service.upsert_budget(
                db, user_id,
                {"category_id": categories[name], "period_month": today, "amount": Decimal(str(amount))},
            )


def _shift_months(base: date, delta_months: int) -> date:
    month_index = base.month - 1 + delta_months
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(base.day, 28))


def _seed_investments(db: Session, user_id) -> None:
    today = date.today()

    nifty = investment_service.create_holding(
        db, user_id,
        {
            "name": "Nifty 50 Index Fund", "asset_type": "mutual_fund",
            "initial_units": Decimal("500"), "initial_amount": Decimal("50000"),
            "purchase_date": today - timedelta(days=400),
        },
    )
    investment_service.update_holding(db, user_id, nifty.id, {"current_price": Decimal("125")})

    gold = investment_service.create_holding(
        db, user_id,
        {
            "name": "Sovereign Gold Bond", "asset_type": "gold",
            "initial_units": Decimal("20"), "initial_amount": Decimal("120000"),
            "purchase_date": today - timedelta(days=200),
        },
    )
    investment_service.update_holding(db, user_id, gold.id, {"current_price": Decimal("6500")})

    investment_service.create_holding(
        db, user_id,
        {
            "name": "Fixed Deposit - HDFC", "asset_type": "fixed_deposit",
            "manual_value": Decimal("205000"),
            "initial_units": Decimal("1"), "initial_amount": Decimal("200000"),
            "purchase_date": today - timedelta(days=180),
            "interest_rate": Decimal("7.1"),
        },
    )

    investment_service.create_goal(
        db, user_id,
        {
            "name": "Financial Freedom", "category": "Retirement",
            "target_amount": Decimal("50000000"), "current_age": 30, "target_age": 45,
            "expected_return": Decimal("12"), "monthly_investment": Decimal("25000"),
            "step_up_percent": Decimal("10"), "use_portfolio_value": True,
        },
    )


def _seed_life(db: Session, user_id) -> None:
    jyotirlinga_names = [
        "Somnath", "Mallikarjuna", "Mahakaleshwar", "Omkareshwar", "Kedarnath",
        "Bhimashankar", "Kashi Vishwanath", "Trimbakeshwar", "Vaidyanath",
        "Nageshwar", "Rameshwar", "Grishneshwar",
    ]
    checklist = life_service.create_checklist(
        db, user_id,
        {
            "title": "12 Jyotirlingas", "tracker_type": TrackerType.TEMPLE.value,
            "icon": "flame", "color": "#f97316", "items": jyotirlinga_names,
        },
    )
    db.flush()
    detail = life_service.get_checklist_detail(db, user_id, checklist.id)
    for item in detail["items"][:5]:
        life_service.update_item(db, user_id, item["id"], {"is_completed": True, "rating": 5})

    treks = life_service.create_checklist(
        db, user_id,
        {
            "title": "Himalayan Treks", "tracker_type": TrackerType.TREK.value,
            "icon": "mountain", "color": "#16a34a", "target_count": 20,
            "items": ["Tungnath", "Kedarkantha", "Roopkund", "Valley of Flowers", "Har Ki Dun"],
        },
    )
    db.flush()
    detail = life_service.get_checklist_detail(db, user_id, treks.id)
    for item in detail["items"][:3]:
        life_service.update_item(
            db, user_id, item["id"],
            {"is_completed": True, "rating": 4, "details": {"difficulty": "moderate"}},
        )

    goal = life_service.create_goal(
        db, user_id,
        {
            "title": "Complete all 12 Jyotirlingas", "priority": "high",
            "target_date": date.today() + timedelta(days=365),
        },
    )
    db.flush()
    for title in ["Visit all 4 Char Dham temples first", "Plan South India temple circuit"]:
        life_service.add_milestone(db, user_id, goal.id, {"title": title})


def _seed_memories(db: Session, user_id) -> None:
    today = date.today()
    memory_service.create_album(
        db, user_id,
        {
            "title": "Uttarakhand 4 Dham - 2026", "album_type": AlbumType.TRIP.value,
            "location": "Uttarakhand, India",
            "start_date": today - timedelta(days=45), "end_date": today - timedelta(days=38),
            "notes": "Kedarnath, Badrinath, Gangotri, Yamunotri in one trip.",
        },
    )
    memory_service.create_album(
        db, user_id,
        {
            "title": "Family Moments", "album_type": AlbumType.FAMILY.value,
            "notes": "General family memories, updated over time.",
        },
    )


def main() -> None:
    configure_logging()
    reset = "--reset" in sys.argv

    Base.metadata.create_all(engine)  # convenience for a fresh local dev DB
    db = SessionLocal()
    try:
        seed(db, reset=reset)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
