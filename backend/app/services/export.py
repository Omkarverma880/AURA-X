"""Self-service data export.

Only the calling user's own rows are ever touched (everything routes through
owned_query), and only plain, already-serialised values go into the file - no
ORM objects, so there is no risk of a relationship silently pulling in
something unexpected.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services import expenses as expense_service
from app.services import investments as investment_service
from app.services import ledger as ledger_service
from app.services import life as life_service
from app.services import memories as memory_service


def _default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(value)


def collect_user_data(db: Session, user_id: uuid.UUID) -> dict:
    """Assemble everything the user owns into one exportable structure."""
    people = ledger_service.list_people(db, user_id, include_archived=True)
    entries, _ = ledger_service.list_entries(db, user_id, page=1, page_size=10_000)
    expenses, _, _ = expense_service.list_expenses(db, user_id, page=1, page_size=10_000)
    income, _, _ = expense_service.list_income(db, user_id, page=1, page_size=10_000)
    investments = investment_service.list_holdings(db, user_id, include_inactive=True)
    investment_goals = investment_service.list_goals(db, user_id)
    life_goals = life_service.list_goals(db, user_id)
    checklists = life_service.list_checklists(db, user_id, include_archived=True)
    albums = memory_service.list_albums(db, user_id)

    return {
        "exported_at": datetime.utcnow().isoformat(),
        "bahi_khata": {"people": people, "entries": entries},
        "expenses": expenses,
        "income": income,
        "investments": {"holdings": investments, "goals": investment_goals},
        "life_goals": life_goals,
        "checklists": checklists,
        "albums": albums,
    }


def to_json(data: dict) -> str:
    return json.dumps(data, default=_default, indent=2)


def to_csv_zip_parts(data: dict) -> dict[str, str]:
    """Flatten each top-level list into its own CSV text, keyed by filename.

    Kept as one CSV per section rather than a single sheet: the modules have
    unrelated columns, and mashing them together would produce a file no
    spreadsheet tool could usefully open.
    """
    parts: dict[str, str] = {}

    def write(name: str, rows: list[dict]) -> None:
        if not rows:
            return
        buffer = io.StringIO()
        fieldnames = sorted({key for row in rows for key in row.keys()})
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _default(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in row.items()})
        parts[f"{name}.csv"] = buffer.getvalue()

    write("bahi_khata_people", data["bahi_khata"]["people"])
    write("bahi_khata_entries", data["bahi_khata"]["entries"])
    write("expenses", data["expenses"])
    write("income", data["income"])
    write("investment_holdings", data["investments"]["holdings"])
    write("investment_goals", data["investments"]["goals"])
    write("life_goals", data["life_goals"])
    write("checklists", data["checklists"])
    write("albums", data["albums"])
    return parts
