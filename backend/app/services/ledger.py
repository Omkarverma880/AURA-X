"""Bahi Khata business logic.

Every rupee figure in this module is derived by summing signed transactions.
There is no stored balance to repair, so a voided or back-dated transaction
immediately produces a consistent answer everywhere it is displayed.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Select, String, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BadRequest, Conflict, NotFound
from app.models.enums import (
    AuditAction,
    LedgerDirection,
    LedgerStatus,
    LedgerTxnType,
)
from app.models.ledger import LedgerEntry, LedgerTransaction, Person
from app.services import audit
from app.services.ownership import get_owned, owned_query

ZERO = Decimal("0.00")

#: Avatar tints assigned round-robin so the people list stays readable.
PERSON_COLORS = [
    "#6d28d9", "#0ea5e9", "#f97316", "#16a34a", "#e11d48",
    "#0891b2", "#7c3aed", "#ca8a04", "#db2777", "#059669",
]


def signed_amount_expr():
    """SQL expression for a transaction signed by its effect on the balance."""
    return case(
        (
            LedgerTransaction.txn_type.in_(
                [LedgerTxnType.PRINCIPAL.value, LedgerTxnType.INTEREST.value]
            ),
            LedgerTransaction.amount,
        ),
        else_=-LedgerTransaction.amount,
    )


def month_expr(column):
    """Portable YYYY-MM bucket.

    Casting a DATE to text yields an ISO string on both PostgreSQL and SQLite,
    so the first seven characters are the month on either engine.
    """
    return func.substr(func.cast(column, String), 1, 7)


def _typed_sum(*types: LedgerTxnType):
    wanted = [t.value for t in types]
    return func.coalesce(
        func.sum(
            case((LedgerTransaction.txn_type.in_(wanted), LedgerTransaction.amount), else_=0)
        ),
        0,
    )


def _money(value) -> Decimal:
    """Normalise a SQL aggregate to an exact 2dp Decimal.

    SQLite hands back floats for SUM; PostgreSQL returns Decimal. Quantising
    here keeps both engines exact to the paisa.
    """
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))


# --- People ------------------------------------------------------------


def _person_totals_subquery(user_id: uuid.UUID):
    """Per-person aggregates in one grouped pass, avoiding an N+1 fan-out."""
    given = LedgerDirection.GIVEN.value
    borrowed = LedgerDirection.BORROWED.value
    principal_types = [LedgerTxnType.PRINCIPAL.value, LedgerTxnType.INTEREST.value]

    def directional(direction: str, of_principal: bool):
        if of_principal:
            condition = (LedgerEntry.direction == direction) & (
                LedgerTransaction.txn_type.in_(principal_types)
            )
        else:
            condition = (LedgerEntry.direction == direction) & (
                LedgerTransaction.txn_type.notin_(principal_types)
            )
        return func.coalesce(
            func.sum(case((condition, LedgerTransaction.amount), else_=0)), 0
        )

    return (
        select(
            LedgerTransaction.person_id.label("person_id"),
            directional(given, True).label("total_given"),
            directional(given, False).label("total_received"),
            directional(borrowed, True).label("total_borrowed"),
            directional(borrowed, False).label("total_repaid"),
            func.max(LedgerTransaction.txn_date).label("last_activity"),
        )
        .join(LedgerEntry, LedgerEntry.id == LedgerTransaction.entry_id)
        .where(
            LedgerTransaction.user_id == user_id,
            LedgerTransaction.is_voided.is_(False),
            LedgerEntry.is_deleted.is_(False),
        )
        .group_by(LedgerTransaction.person_id)
        .subquery()
    )


def list_people(
    db: Session,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
    include_archived: bool = False,
    only_outstanding: bool = False,
) -> list[dict]:
    totals = _person_totals_subquery(user_id)
    entry_counts = (
        select(
            LedgerEntry.person_id.label("person_id"),
            func.count(LedgerEntry.id).label("entry_count"),
        )
        .where(LedgerEntry.user_id == user_id, LedgerEntry.is_deleted.is_(False))
        .group_by(LedgerEntry.person_id)
        .subquery()
    )

    stmt = (
        select(Person, totals, entry_counts.c.entry_count)
        .outerjoin(totals, totals.c.person_id == Person.id)
        .outerjoin(entry_counts, entry_counts.c.person_id == Person.id)
        .where(Person.user_id == user_id, Person.is_deleted.is_(False))
    )
    if not include_archived:
        stmt = stmt.where(Person.is_archived.is_(False))
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(Person.name.ilike(pattern), Person.phone.ilike(pattern), Person.notes.ilike(pattern))
        )

    # Active-entry counts for every person in one pass. Computing this per
    # person inside the loop would be a classic N+1.
    active_by_person = _active_counts_by_person(db, user_id)

    results = []
    for row in db.execute(stmt).all():
        person = row[0]
        given = _money(row.total_given)
        received = _money(row.total_received)
        borrowed = _money(row.total_borrowed)
        repaid = _money(row.total_repaid)
        receivable = given - received
        payable = borrowed - repaid

        if only_outstanding and receivable <= ZERO and payable <= ZERO:
            continue

        results.append(
            {
                **person_base(person),
                "total_given": given,
                "total_received": received,
                "total_borrowed": borrowed,
                "total_repaid": repaid,
                "outstanding_receivable": max(receivable, ZERO),
                "outstanding_payable": max(payable, ZERO),
                "net_balance": receivable - payable,
                "entry_count": int(row.entry_count or 0),
                "active_count": active_by_person.get(person.id, 0),
                "last_activity": row.last_activity,
            }
        )

    results.sort(key=lambda p: (p["outstanding_receivable"] + p["outstanding_payable"]), reverse=True)
    return results


def person_base(person: Person) -> dict:
    return {
        "id": person.id,
        "name": person.name,
        "phone": person.phone,
        "email": person.email,
        "relation": person.relation,
        "notes": person.notes,
        "color": person.color,
        "is_archived": person.is_archived,
        "created_at": person.created_at,
    }


def _active_counts_by_person(db: Session, user_id: uuid.UUID) -> dict[uuid.UUID, int]:
    """How many entries still carry a balance, keyed by person."""
    balances = _entry_balances(db, user_id)
    owners = db.execute(
        select(LedgerEntry.id, LedgerEntry.person_id).where(
            LedgerEntry.user_id == user_id, LedgerEntry.is_deleted.is_(False)
        )
    ).all()

    counts: dict[uuid.UUID, int] = {}
    for entry_id, person_id in owners:
        balance = balances.get(entry_id)
        if balance and balance["outstanding"] > ZERO:
            counts[person_id] = counts.get(person_id, 0) + 1
    return counts


def create_person(db: Session, user_id: uuid.UUID, data: dict) -> Person:
    name = data["name"].strip()
    existing = db.execute(
        owned_query(Person, user_id).where(func.lower(Person.name) == name.lower())
    ).scalar_one_or_none()
    if existing is not None:
        raise Conflict(f"{name} is already in your Bahi Khata.")

    count = db.execute(
        select(func.count()).select_from(Person).where(Person.user_id == user_id)
    ).scalar_one()

    person = Person(
        user_id=user_id,
        name=name,
        phone=data.get("phone"),
        email=data.get("email"),
        relation=data.get("relation"),
        notes=data.get("notes"),
        color=PERSON_COLORS[int(count) % len(PERSON_COLORS)],
    )
    db.add(person)
    db.flush()
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.CREATE.value,
        entity_type="person",
        entity_id=person.id,
        summary=f"Added {person.name} to Bahi Khata",
    )
    return person


def get_or_create_person(db: Session, user_id: uuid.UUID, name: str) -> Person:
    existing = db.execute(
        owned_query(Person, user_id).where(func.lower(Person.name) == name.strip().lower())
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    return create_person(db, user_id, {"name": name})


def update_person(db: Session, user_id: uuid.UUID, person_id: uuid.UUID, data: dict) -> Person:
    person = get_owned(db, Person, person_id, user_id)
    if "name" in data and data["name"]:
        new_name = data["name"].strip()
        clash = db.execute(
            owned_query(Person, user_id).where(
                func.lower(Person.name) == new_name.lower(), Person.id != person_id
            )
        ).scalar_one_or_none()
        if clash is not None:
            raise Conflict(f"Another person is already named {new_name}.")
        person.name = new_name

    for field in ("phone", "email", "relation", "notes", "is_archived"):
        if field in data and data[field] is not None:
            setattr(person, field, data[field])

    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.UPDATE.value,
        entity_type="person",
        entity_id=person.id,
        summary=f"Updated {person.name}",
    )
    return person


def delete_person(db: Session, user_id: uuid.UUID, person_id: uuid.UUID) -> None:
    """Archive a person, refusing while money is still owed either way."""
    person = get_owned(db, Person, person_id, user_id)
    balances = _entry_balances(db, user_id, person_id=person_id)
    if any(value["outstanding"] > ZERO for value in balances.values()):
        raise BadRequest(
            f"{person.name} still has an outstanding balance. Settle or write it off first."
        )
    person.soft_delete()
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.DELETE.value,
        entity_type="person",
        entity_id=person.id,
        summary=f"Removed {person.name}",
    )


# --- Entries -----------------------------------------------------------


def _entry_balances(
    db: Session,
    user_id: uuid.UUID,
    *,
    person_id: uuid.UUID | None = None,
    entry_ids: list[uuid.UUID] | None = None,
) -> dict[uuid.UUID, dict]:
    """Aggregate principal, settled and outstanding per entry in one query."""
    stmt = (
        select(
            LedgerTransaction.entry_id,
            _typed_sum(LedgerTxnType.PRINCIPAL, LedgerTxnType.INTEREST).label("principal"),
            _typed_sum(LedgerTxnType.REPAYMENT, LedgerTxnType.WRITE_OFF).label("settled"),
            func.count(LedgerTransaction.id).label("txn_count"),
        )
        .where(
            LedgerTransaction.user_id == user_id,
            LedgerTransaction.is_voided.is_(False),
        )
        .group_by(LedgerTransaction.entry_id)
    )
    if person_id is not None:
        stmt = stmt.where(LedgerTransaction.person_id == person_id)
    if entry_ids is not None:
        if not entry_ids:
            return {}
        stmt = stmt.where(LedgerTransaction.entry_id.in_(entry_ids))

    balances: dict[uuid.UUID, dict] = {}
    for row in db.execute(stmt).all():
        principal = _money(row.principal)
        settled = _money(row.settled)
        balances[row.entry_id] = {
            "principal": principal,
            "settled": settled,
            "outstanding": principal - settled,
            "txn_count": int(row.txn_count),
        }
    return balances


def entry_status(entry: LedgerEntry, balance: dict, today: date | None = None) -> tuple[str, bool, int]:
    """Derive status, overdue flag and days overdue for one entry."""
    today = today or date.today()
    outstanding = balance["outstanding"]
    principal = balance["principal"]

    if entry.is_closed or outstanding <= ZERO:
        return LedgerStatus.SETTLED.value, False, 0

    overdue = bool(entry.due_date and entry.due_date < today)
    days_overdue = (today - entry.due_date).days if overdue and entry.due_date else 0

    if overdue:
        return LedgerStatus.OVERDUE.value, True, days_overdue
    if balance["settled"] > ZERO and outstanding < principal:
        return LedgerStatus.PARTIAL.value, False, 0
    return LedgerStatus.ACTIVE.value, False, 0


def serialise_entry(entry: LedgerEntry, balance: dict | None, person_name: str | None = None) -> dict:
    balance = balance or {
        "principal": ZERO, "settled": ZERO, "outstanding": ZERO, "txn_count": 0
    }
    status, is_overdue, days_overdue = entry_status(entry, balance)
    principal = balance["principal"]
    progress = float(balance["settled"] / principal * 100) if principal > ZERO else 0.0

    return {
        "id": entry.id,
        "person_id": entry.person_id,
        "person_name": person_name or (entry.person.name if entry.person else None),
        "direction": entry.direction,
        "purpose": entry.purpose,
        "entry_date": entry.entry_date,
        "due_date": entry.due_date,
        "reminder_on": entry.reminder_on,
        "notes": entry.notes,
        "currency": entry.currency,
        "is_closed": entry.is_closed,
        "created_at": entry.created_at,
        "principal_amount": principal,
        "settled_amount": balance["settled"],
        "outstanding": max(balance["outstanding"], ZERO),
        "progress_percent": round(min(progress, 100.0), 1),
        "status": status,
        "is_overdue": is_overdue,
        "days_overdue": days_overdue,
        "transaction_count": balance["txn_count"],
    }


def list_entries(
    db: Session,
    user_id: uuid.UUID,
    *,
    direction: str | None = None,
    status: str | None = None,
    person_id: uuid.UUID | None = None,
    search: str | None = None,
    sort: str = "recent",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[dict], int]:
    stmt: Select = (
        owned_query(LedgerEntry, user_id)
        .options(selectinload(LedgerEntry.person))
        .join(Person, Person.id == LedgerEntry.person_id)
    )
    if direction:
        stmt = stmt.where(LedgerEntry.direction == direction)
    if person_id:
        stmt = stmt.where(LedgerEntry.person_id == person_id)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(or_(LedgerEntry.purpose.ilike(pattern), Person.name.ilike(pattern)))

    rows = list(db.execute(stmt).scalars().unique())
    balances = _entry_balances(db, user_id, entry_ids=[row.id for row in rows])
    items = [serialise_entry(row, balances.get(row.id)) for row in rows]

    if status:
        items = [item for item in items if item["status"] == status]

    sorters = {
        "recent": lambda i: (i["entry_date"], i["created_at"]),
        "oldest": lambda i: (i["entry_date"], i["created_at"]),
        "amount": lambda i: i["principal_amount"],
        "outstanding": lambda i: i["outstanding"],
        "due": lambda i: (i["due_date"] or date.max),
        "person": lambda i: (i["person_name"] or "").lower(),
    }
    key = sorters.get(sort, sorters["recent"])
    reverse = sort in {"recent", "amount", "outstanding"}
    items.sort(key=key, reverse=reverse)

    total = len(items)
    start = max(page - 1, 0) * page_size
    return items[start : start + page_size], total


def create_entry(db: Session, user_id: uuid.UUID, data: dict) -> LedgerEntry:
    """Open a lending or borrowing account and post its opening principal.

    Both rows are written in one transaction: an entry without its principal
    would report a zero balance and silently understate what is owed.
    """
    person_id = data.get("person_id")
    if person_id:
        person = get_owned(db, Person, person_id, user_id)
    elif data.get("person_name"):
        person = get_or_create_person(db, user_id, data["person_name"])
    else:
        raise BadRequest("Choose who this entry is for.")

    entry = LedgerEntry(
        user_id=user_id,
        person_id=person.id,
        direction=data["direction"],
        purpose=data["purpose"].strip(),
        entry_date=data.get("entry_date") or date.today(),
        due_date=data.get("due_date"),
        reminder_on=data.get("reminder_on"),
        notes=data.get("notes"),
    )
    db.add(entry)
    db.flush()

    db.add(
        LedgerTransaction(
            user_id=user_id,
            entry_id=entry.id,
            person_id=person.id,
            txn_type=LedgerTxnType.PRINCIPAL.value,
            amount=data["amount"],
            txn_date=entry.entry_date,
            method=data.get("method"),
            description=entry.purpose,
        )
    )
    db.flush()

    verb = "Gave" if entry.direction == LedgerDirection.GIVEN.value else "Borrowed"
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.CREATE.value,
        entity_type="ledger_entry",
        entity_id=entry.id,
        summary=f"{verb} {data['amount']} - {person.name} ({entry.purpose})",
        meta={"direction": entry.direction, "amount": str(data["amount"])},
    )
    return entry


def update_entry(db: Session, user_id: uuid.UUID, entry_id: uuid.UUID, data: dict) -> LedgerEntry:
    """Update descriptive fields only.

    Amounts are intentionally not editable here: money is corrected by voiding
    a transaction and posting a replacement, which keeps the history honest.
    """
    entry = get_owned(db, LedgerEntry, entry_id, user_id)
    for field in ("purpose", "due_date", "reminder_on", "notes", "is_closed"):
        if field in data and data[field] is not None:
            setattr(entry, field, data[field])
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.UPDATE.value,
        entity_type="ledger_entry",
        entity_id=entry.id,
        summary=f"Updated entry {entry.purpose}",
    )
    return entry


def delete_entry(db: Session, user_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    entry = get_owned(db, LedgerEntry, entry_id, user_id)
    entry.soft_delete()
    for txn in entry.transactions:
        txn.is_voided = True
        txn.voided_at = datetime.now(timezone.utc)
        txn.void_reason = "Entry deleted"
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.DELETE.value,
        entity_type="ledger_entry",
        entity_id=entry.id,
        summary=f"Deleted entry {entry.purpose}",
    )


def get_entry_detail(db: Session, user_id: uuid.UUID, entry_id: uuid.UUID) -> dict:
    entry = get_owned(db, LedgerEntry, entry_id, user_id)
    balances = _entry_balances(db, user_id, entry_ids=[entry.id])
    payload = serialise_entry(entry, balances.get(entry.id))

    running = ZERO
    transactions = []
    for txn in sorted(entry.transactions, key=lambda t: (t.txn_date, t.created_at)):
        if not txn.is_voided:
            running += txn.signed_amount
        transactions.append(serialise_txn(txn, running, entry))
    payload["transactions"] = list(reversed(transactions))
    return payload


def serialise_txn(
    txn: LedgerTransaction, balance_after: Decimal | None, entry: LedgerEntry | None = None
) -> dict:
    return {
        "id": txn.id,
        "entry_id": txn.entry_id,
        "person_id": txn.person_id,
        "txn_type": txn.txn_type,
        "amount": txn.amount,
        "signed_amount": txn.signed_amount,
        "txn_date": txn.txn_date,
        "method": txn.method,
        "description": txn.description,
        "is_voided": txn.is_voided,
        "void_reason": txn.void_reason,
        "created_at": txn.created_at,
        "balance_after": balance_after,
        "purpose": entry.purpose if entry else None,
    }


# --- Transactions ------------------------------------------------------


def add_transaction(
    db: Session, user_id: uuid.UUID, entry_id: uuid.UUID, data: dict
) -> LedgerTransaction:
    """Record a repayment or any other movement against an entry."""
    entry = get_owned(db, LedgerEntry, entry_id, user_id)
    balances = _entry_balances(db, user_id, entry_ids=[entry.id])
    balance = balances.get(
        entry.id, {"principal": ZERO, "settled": ZERO, "outstanding": ZERO, "txn_count": 0}
    )

    txn_type = data.get("txn_type") or LedgerTxnType.REPAYMENT.value
    amount = Decimal(str(data["amount"]))

    # Guard against over-settlement, which would produce a negative balance
    # and a misleading "they owe me less than nothing" figure.
    if txn_type in (LedgerTxnType.REPAYMENT.value, LedgerTxnType.WRITE_OFF.value):
        if balance["outstanding"] <= ZERO:
            raise BadRequest("This entry is already fully settled.")
        if amount > balance["outstanding"]:
            raise BadRequest(
                f"That is more than the outstanding balance of {balance['outstanding']}.",
                details={"outstanding": float(balance["outstanding"])},
            )

    txn = LedgerTransaction(
        user_id=user_id,
        entry_id=entry.id,
        person_id=entry.person_id,
        txn_type=txn_type,
        amount=amount,
        txn_date=data.get("txn_date") or date.today(),
        method=data.get("method"),
        description=data.get("description"),
    )
    db.add(txn)
    db.flush()

    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.CREATE.value,
        entity_type="ledger_transaction",
        entity_id=txn.id,
        summary=f"Recorded {txn_type} of {amount} on {entry.purpose}",
        meta={"entry_id": str(entry.id), "amount": str(amount), "type": txn_type},
    )
    return txn


def void_transaction(
    db: Session, user_id: uuid.UUID, txn_id: uuid.UUID, reason: str
) -> LedgerTransaction:
    """Reverse a transaction without erasing it.

    The row stays visible in the ledger marked as voided, so the correction is
    part of the record rather than a hole in it.
    """
    txn = get_owned(db, LedgerTransaction, txn_id, user_id)
    if txn.is_voided:
        raise BadRequest("That transaction has already been voided.")

    if txn.txn_type == LedgerTxnType.PRINCIPAL.value:
        balances = _entry_balances(db, user_id, entry_ids=[txn.entry_id])
        balance = balances.get(txn.entry_id)
        if balance and (balance["principal"] - txn.amount) < balance["settled"]:
            raise BadRequest(
                "Voiding this would leave more repaid than was ever lent. "
                "Void the repayments first."
            )

    txn.is_voided = True
    txn.voided_at = datetime.now(timezone.utc)
    txn.void_reason = reason
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.UPDATE.value,
        entity_type="ledger_transaction",
        entity_id=txn.id,
        summary=f"Voided {txn.txn_type} of {txn.amount}",
        meta={"reason": reason},
    )
    return txn


def settle_entry(db: Session, user_id: uuid.UUID, entry_id: uuid.UUID, data: dict) -> LedgerEntry:
    """Close an entry by settling whatever is still outstanding."""
    entry = get_owned(db, LedgerEntry, entry_id, user_id)
    balances = _entry_balances(db, user_id, entry_ids=[entry.id])
    outstanding = balances.get(entry.id, {}).get("outstanding", ZERO)

    if outstanding > ZERO:
        add_transaction(
            db,
            user_id,
            entry_id,
            {
                "txn_type": data.get("txn_type") or LedgerTxnType.REPAYMENT.value,
                "amount": outstanding,
                "txn_date": data.get("txn_date") or date.today(),
                "method": data.get("method"),
                "description": data.get("description") or "Full settlement",
            },
        )
    entry.is_closed = True
    return entry


# --- Person detail -----------------------------------------------------


def get_person_detail(db: Session, user_id: uuid.UUID, person_id: uuid.UUID) -> dict:
    person = get_owned(db, Person, person_id, user_id)

    entries = list(
        db.execute(
            owned_query(LedgerEntry, user_id)
            .where(LedgerEntry.person_id == person_id)
            .order_by(LedgerEntry.entry_date.desc())
        ).scalars()
    )
    balances = _entry_balances(db, user_id, person_id=person_id)
    entry_payloads = [serialise_entry(entry, balances.get(entry.id), person.name) for entry in entries]

    entry_by_id = {entry.id: entry for entry in entries}
    txns = list(
        db.execute(
            select(LedgerTransaction)
            .where(
                LedgerTransaction.user_id == user_id,
                LedgerTransaction.person_id == person_id,
                LedgerTransaction.entry_id.in_(list(entry_by_id.keys())) if entry_by_id else False,
            )
            .order_by(LedgerTransaction.txn_date, LedgerTransaction.created_at)
        ).scalars()
    )

    running = ZERO
    ledger_rows = []
    for txn in txns:
        if not txn.is_voided:
            running += txn.signed_amount
        row = serialise_txn(txn, running, entry_by_id.get(txn.entry_id))
        row["person_name"] = person.name
        ledger_rows.append(row)

    given = sum((p["principal_amount"] for p in entry_payloads if p["direction"] == "given"), ZERO)
    received = sum((p["settled_amount"] for p in entry_payloads if p["direction"] == "given"), ZERO)
    borrowed = sum(
        (p["principal_amount"] for p in entry_payloads if p["direction"] == "borrowed"), ZERO
    )
    repaid = sum((p["settled_amount"] for p in entry_payloads if p["direction"] == "borrowed"), ZERO)

    return {
        **person_base(person),
        "total_given": given,
        "total_received": received,
        "total_borrowed": borrowed,
        "total_repaid": repaid,
        "outstanding_receivable": max(given - received, ZERO),
        "outstanding_payable": max(borrowed - repaid, ZERO),
        "net_balance": (given - received) - (borrowed - repaid),
        "entry_count": len(entry_payloads),
        "active_count": sum(1 for p in entry_payloads if p["outstanding"] > ZERO),
        "last_activity": max((t.txn_date for t in txns), default=None),
        "entries": entry_payloads,
        "ledger": list(reversed(ledger_rows)),
    }


# --- Summary and analytics ---------------------------------------------


def get_summary(db: Session, user_id: uuid.UUID) -> dict:
    """Headline Bahi Khata figures for the dashboard, in a few grouped queries."""
    rows = db.execute(
        select(
            LedgerEntry.direction,
            _typed_sum(LedgerTxnType.PRINCIPAL, LedgerTxnType.INTEREST).label("principal"),
            _typed_sum(LedgerTxnType.REPAYMENT, LedgerTxnType.WRITE_OFF).label("settled"),
        )
        .join(LedgerEntry, LedgerEntry.id == LedgerTransaction.entry_id)
        .where(
            LedgerTransaction.user_id == user_id,
            LedgerTransaction.is_voided.is_(False),
            LedgerEntry.is_deleted.is_(False),
        )
        .group_by(LedgerEntry.direction)
    ).all()

    totals = {
        LedgerDirection.GIVEN.value: (ZERO, ZERO),
        LedgerDirection.BORROWED.value: (ZERO, ZERO),
    }
    for row in rows:
        totals[row.direction] = (_money(row.principal), _money(row.settled))

    given, received = totals[LedgerDirection.GIVEN.value]
    borrowed, repaid = totals[LedgerDirection.BORROWED.value]

    entries = list(db.execute(owned_query(LedgerEntry, user_id)).scalars())
    balances = _entry_balances(db, user_id)
    today = date.today()

    active = settled_count = overdue = 0
    overdue_amount = ZERO
    outstanding_entries: list[tuple[LedgerEntry, Decimal]] = []

    for entry in entries:
        balance = balances.get(
            entry.id, {"principal": ZERO, "settled": ZERO, "outstanding": ZERO, "txn_count": 0}
        )
        status, is_overdue, _ = entry_status(entry, balance, today)
        if status == LedgerStatus.SETTLED.value:
            settled_count += 1
            continue
        active += 1
        outstanding_entries.append((entry, balance["outstanding"]))
        if is_overdue:
            overdue += 1
            overdue_amount += balance["outstanding"]

    total_principal = given + borrowed
    total_settled = received + repaid
    settlement_rate = float(total_settled / total_principal * 100) if total_principal > ZERO else 0.0

    largest = max(outstanding_entries, key=lambda pair: pair[1], default=None)
    oldest = min(outstanding_entries, key=lambda pair: pair[0].entry_date, default=None)

    people_count = db.execute(
        select(func.count())
        .select_from(Person)
        .where(
            Person.user_id == user_id,
            Person.is_deleted.is_(False),
            Person.is_archived.is_(False),
        )
    ).scalar_one()

    return {
        "total_given": given,
        "total_received": received,
        "outstanding_receivable": max(given - received, ZERO),
        "total_borrowed": borrowed,
        "total_repaid": repaid,
        "outstanding_payable": max(borrowed - repaid, ZERO),
        "net_position": (given - received) - (borrowed - repaid),
        "settlement_rate": round(settlement_rate, 1),
        "people_count": int(people_count),
        "active_entries": active,
        "settled_entries": settled_count,
        "overdue_entries": overdue,
        "overdue_amount": overdue_amount,
        "largest_outstanding": _entry_ref(largest),
        "oldest_outstanding": _entry_ref(oldest),
    }


def _entry_ref(pair: tuple[LedgerEntry, Decimal] | None) -> dict | None:
    if not pair:
        return None
    entry, amount = pair
    return {
        "entry_id": str(entry.id),
        "person_id": str(entry.person_id),
        "person_name": entry.person.name if entry.person else None,
        "purpose": entry.purpose,
        "amount": float(amount),
        "entry_date": entry.entry_date.isoformat(),
        "direction": entry.direction,
    }


def get_analytics(db: Session, user_id: uuid.UUID, months: int = 12) -> dict:
    summary = get_summary(db, user_id)

    trend_rows = db.execute(
        select(
            month_expr(LedgerTransaction.txn_date).label("month"),
            LedgerEntry.direction,
            LedgerTransaction.txn_type,
            func.sum(LedgerTransaction.amount).label("amount"),
        )
        .join(LedgerEntry, LedgerEntry.id == LedgerTransaction.entry_id)
        .where(
            LedgerTransaction.user_id == user_id,
            LedgerTransaction.is_voided.is_(False),
            LedgerEntry.is_deleted.is_(False),
        )
        .group_by("month", LedgerEntry.direction, LedgerTransaction.txn_type)
    ).all()

    buckets: dict[str, dict] = {}
    for row in trend_rows:
        bucket = buckets.setdefault(
            row.month, {"month": row.month, "given": 0.0, "received": 0.0, "borrowed": 0.0, "repaid": 0.0}
        )
        is_principal = row.txn_type in (LedgerTxnType.PRINCIPAL.value, LedgerTxnType.INTEREST.value)
        if row.direction == LedgerDirection.GIVEN.value:
            key = "given" if is_principal else "received"
        else:
            key = "borrowed" if is_principal else "repaid"
        bucket[key] += float(_money(row.amount))

    monthly = sorted(buckets.values(), key=lambda b: b["month"])[-months:]

    people = list_people(db, user_id, only_outstanding=True)
    outstanding_by_person = [
        {
            "person_id": str(person["id"]),
            "name": person["name"],
            "receivable": float(person["outstanding_receivable"]),
            "payable": float(person["outstanding_payable"]),
            "total": float(person["outstanding_receivable"] + person["outstanding_payable"]),
        }
        for person in people[:10]
    ]

    entries, _ = list_entries(db, user_id, page=1, page_size=1000)
    status_counts: dict[str, int] = {}
    for entry in entries:
        status_counts[entry["status"]] = status_counts.get(entry["status"], 0) + 1

    return {
        "summary": summary,
        "monthly_trend": monthly,
        "outstanding_by_person": outstanding_by_person,
        "status_breakdown": [
            {"status": key, "count": value} for key, value in sorted(status_counts.items())
        ],
        "direction_split": [
            {"direction": "given", "amount": float(summary["outstanding_receivable"])},
            {"direction": "borrowed", "amount": float(summary["outstanding_payable"])},
        ],
    }
