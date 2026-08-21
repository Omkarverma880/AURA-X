"""Expenditure: categories, expenses, income and monthly analytics."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BadRequest, Conflict
from app.models.enums import AuditAction, CategoryKind
from app.models.finance import Budget, Expense, ExpenseCategory, IncomeRecord, IncomeSource
from app.services import audit
from app.services.ownership import assert_owned, get_owned, owned_query

ZERO = Decimal("0.00")


def month_start(value: date) -> date:
    """First day of the month a date falls in - the monthly rollup key."""
    return value.replace(day=1)


def month_end(value: date) -> date:
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1, day=1)
    return value.replace(month=value.month + 1, day=1)


def month_expr(column):
    return func.substr(func.cast(column, String), 1, 7)


def _money(value) -> Decimal:
    if value is None:
        return ZERO
    return Decimal(str(value)).quantize(Decimal("0.01"))


# --- Categories --------------------------------------------------------


def list_categories(
    db: Session,
    user_id: uuid.UUID,
    *,
    kind: str | None = None,
    include_archived: bool = False,
    period: date | None = None,
) -> list[dict]:
    """Return the category tree, optionally annotated with spend for a month."""
    stmt = owned_query(ExpenseCategory, user_id).order_by(
        ExpenseCategory.sort_order, ExpenseCategory.name
    )
    if kind:
        stmt = stmt.where(ExpenseCategory.kind == kind)
    if not include_archived:
        stmt = stmt.where(ExpenseCategory.is_archived.is_(False))

    categories = list(db.execute(stmt).scalars())
    spend: dict[uuid.UUID, tuple[Decimal, int]] = {}
    if period is not None:
        rows = db.execute(
            select(
                Expense.category_id,
                func.sum(Expense.amount).label("total"),
                func.count(Expense.id).label("count"),
            )
            .where(
                Expense.user_id == user_id,
                Expense.is_deleted.is_(False),
                Expense.spent_on >= month_start(period),
                Expense.spent_on < month_end(period),
            )
            .group_by(Expense.category_id)
        ).all()
        spend = {row.category_id: (_money(row.total), int(row.count)) for row in rows}

    by_id: dict[uuid.UUID, dict] = {}
    for category in categories:
        amount, count = spend.get(category.id, (ZERO, 0))
        by_id[category.id] = {
            "id": category.id,
            "name": category.name,
            "kind": category.kind,
            "parent_id": category.parent_id,
            "icon": category.icon,
            "color": category.color,
            "is_default": category.is_default,
            "is_archived": category.is_archived,
            "sort_order": category.sort_order,
            "children": [],
            "spent": amount if period is not None else None,
            "transaction_count": count if period is not None else None,
        }

    roots = []
    for payload in by_id.values():
        parent = by_id.get(payload["parent_id"]) if payload["parent_id"] else None
        if parent is not None:
            parent["children"].append(payload)
        else:
            roots.append(payload)
    return roots


def serialise_category(category: ExpenseCategory) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "kind": category.kind,
        "parent_id": category.parent_id,
        "icon": category.icon,
        "color": category.color,
        "is_default": category.is_default,
        "is_archived": category.is_archived,
        "sort_order": category.sort_order,
        "children": [],
        "spent": None,
        "transaction_count": None,
    }


def create_category(db: Session, user_id: uuid.UUID, data: dict) -> ExpenseCategory:
    name = data["name"].strip()
    parent_id = data.get("parent_id")
    assert_owned(db, ExpenseCategory, parent_id, user_id)

    clash = db.execute(
        owned_query(ExpenseCategory, user_id).where(
            func.lower(ExpenseCategory.name) == name.lower(),
            ExpenseCategory.parent_id == parent_id,
        )
    ).scalar_one_or_none()
    if clash is not None:
        raise Conflict(f"A category named {name} already exists.")

    category = ExpenseCategory(
        user_id=user_id,
        name=name,
        kind=data.get("kind") or CategoryKind.EXPENSE.value,
        parent_id=parent_id,
        icon=data.get("icon"),
        color=data.get("color"),
    )
    db.add(category)
    db.flush()
    return category


def update_category(
    db: Session, user_id: uuid.UUID, category_id: uuid.UUID, data: dict
) -> ExpenseCategory:
    category = get_owned(db, ExpenseCategory, category_id, user_id)
    for field in ("name", "icon", "color", "is_archived", "sort_order"):
        if field in data and data[field] is not None:
            setattr(category, field, data[field].strip() if field == "name" else data[field])
    return category


def delete_category(db: Session, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
    """Archive a category that is in use; delete it outright when it is not.

    Hard-deleting a used category would orphan the history behind it, so the
    safe path is chosen automatically rather than asked about.
    """
    category = get_owned(db, ExpenseCategory, category_id, user_id)
    in_use = db.execute(
        select(func.count())
        .select_from(Expense)
        .where(
            Expense.user_id == user_id,
            or_(Expense.category_id == category_id, Expense.subcategory_id == category_id),
        )
    ).scalar_one()

    if in_use:
        category.is_archived = True
    else:
        db.delete(category)


# --- Expenses ----------------------------------------------------------


def serialise_expense(expense: Expense) -> dict:
    return {
        "id": expense.id,
        "spent_on": expense.spent_on,
        "amount": expense.amount,
        "category_id": expense.category_id,
        "category_name": expense.category.name if expense.category else None,
        "category_icon": expense.category.icon if expense.category else None,
        "category_color": expense.category.color if expense.category else None,
        "subcategory_id": expense.subcategory_id,
        "subcategory_name": expense.subcategory.name if expense.subcategory else None,
        "merchant": expense.merchant,
        "payment_method": expense.payment_method,
        "description": expense.description,
        "notes": expense.notes,
        "is_recurring": expense.is_recurring,
        "recurrence": expense.recurrence,
        "tags": expense.tags,
        "created_at": expense.created_at,
    }


def list_expenses(
    db: Session,
    user_id: uuid.UUID,
    *,
    period: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: uuid.UUID | None = None,
    payment_method: str | None = None,
    search: str | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    recurring_only: bool = False,
    sort: str = "recent",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[dict], int, Decimal]:
    """Filtered, paginated expense list plus the total for the filter."""
    stmt = owned_query(Expense, user_id).options(
        selectinload(Expense.category), selectinload(Expense.subcategory)
    )
    conditions = []

    if period is not None:
        conditions += [Expense.spent_on >= month_start(period), Expense.spent_on < month_end(period)]
    if date_from is not None:
        conditions.append(Expense.spent_on >= date_from)
    if date_to is not None:
        conditions.append(Expense.spent_on <= date_to)
    if category_id is not None:
        conditions.append(
            or_(Expense.category_id == category_id, Expense.subcategory_id == category_id)
        )
    if payment_method:
        conditions.append(Expense.payment_method == payment_method)
    if min_amount is not None:
        conditions.append(Expense.amount >= min_amount)
    if max_amount is not None:
        conditions.append(Expense.amount <= max_amount)
    if recurring_only:
        conditions.append(Expense.is_recurring.is_(True))
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Expense.description.ilike(pattern),
                Expense.merchant.ilike(pattern),
                Expense.notes.ilike(pattern),
            )
        )

    for condition in conditions:
        stmt = stmt.where(condition)

    # Count and total come from the database, never from loading every row.
    aggregate = select(func.count(Expense.id), func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.user_id == user_id, Expense.is_deleted.is_(False)
    )
    for condition in conditions:
        aggregate = aggregate.where(condition)
    total_count, total_amount = db.execute(aggregate).one()

    order = {
        "recent": (Expense.spent_on.desc(), Expense.created_at.desc()),
        "oldest": (Expense.spent_on.asc(), Expense.created_at.asc()),
        "highest": (Expense.amount.desc(),),
        "lowest": (Expense.amount.asc(),),
    }.get(sort, (Expense.spent_on.desc(), Expense.created_at.desc()))
    stmt = stmt.order_by(*order).limit(page_size).offset(max(page - 1, 0) * page_size)

    rows = [serialise_expense(expense) for expense in db.execute(stmt).scalars()]
    return rows, int(total_count), _money(total_amount)


def create_expense(db: Session, user_id: uuid.UUID, data: dict) -> Expense:
    # Client-supplied foreign keys are verified against the caller before use,
    # so an expense can never point at somebody else category.
    assert_owned(db, ExpenseCategory, data.get("category_id"), user_id)
    assert_owned(db, ExpenseCategory, data.get("subcategory_id"), user_id)

    expense = Expense(
        user_id=user_id,
        spent_on=data.get("spent_on") or date.today(),
        amount=data["amount"],
        category_id=data.get("category_id"),
        subcategory_id=data.get("subcategory_id"),
        merchant=data.get("merchant"),
        payment_method=data.get("payment_method"),
        description=data.get("description"),
        notes=data.get("notes"),
        is_recurring=data.get("is_recurring", False),
        recurrence=data.get("recurrence") or "none",
        tags=data.get("tags"),
    )
    db.add(expense)
    db.flush()
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.CREATE.value,
        entity_type="expense",
        entity_id=expense.id,
        summary=f"Added expense of {expense.amount}",
    )
    return expense


def update_expense(db: Session, user_id: uuid.UUID, expense_id: uuid.UUID, data: dict) -> Expense:
    expense = get_owned(db, Expense, expense_id, user_id)
    assert_owned(db, ExpenseCategory, data.get("category_id"), user_id)
    assert_owned(db, ExpenseCategory, data.get("subcategory_id"), user_id)

    for field, value in data.items():
        setattr(expense, field, value)

    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.UPDATE.value,
        entity_type="expense",
        entity_id=expense.id,
        summary=f"Updated expense of {expense.amount}",
    )
    return expense


def delete_expense(db: Session, user_id: uuid.UUID, expense_id: uuid.UUID) -> None:
    expense = get_owned(db, Expense, expense_id, user_id)
    expense.soft_delete()
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.DELETE.value,
        entity_type="expense",
        entity_id=expense.id,
        summary=f"Deleted expense of {expense.amount}",
    )


def get_expense(db: Session, user_id: uuid.UUID, expense_id: uuid.UUID) -> dict:
    return serialise_expense(get_owned(db, Expense, expense_id, user_id))


# --- Income ------------------------------------------------------------


def list_income_sources(db: Session, user_id: uuid.UUID) -> list[dict]:
    totals = dict(
        db.execute(
            select(IncomeRecord.source_id, func.coalesce(func.sum(IncomeRecord.net_amount), 0))
            .where(IncomeRecord.user_id == user_id, IncomeRecord.is_deleted.is_(False))
            .group_by(IncomeRecord.source_id)
        ).all()
    )
    sources = db.execute(owned_query(IncomeSource, user_id).order_by(IncomeSource.name)).scalars()
    return [
        {
            "id": source.id,
            "name": source.name,
            "income_type": source.income_type,
            "employer": source.employer,
            "is_active": source.is_active,
            "notes": source.notes,
            "total_received": _money(totals.get(source.id)),
        }
        for source in sources
    ]


def create_income_source(db: Session, user_id: uuid.UUID, data: dict) -> IncomeSource:
    name = data["name"].strip()
    clash = db.execute(
        owned_query(IncomeSource, user_id).where(func.lower(IncomeSource.name) == name.lower())
    ).scalar_one_or_none()
    if clash is not None:
        raise Conflict(f"An income source named {name} already exists.")
    source = IncomeSource(
        user_id=user_id,
        name=name,
        income_type=data.get("income_type") or "salary",
        employer=data.get("employer"),
        notes=data.get("notes"),
    )
    db.add(source)
    db.flush()
    return source


def update_income_source(
    db: Session, user_id: uuid.UUID, source_id: uuid.UUID, data: dict
) -> IncomeSource:
    source = get_owned(db, IncomeSource, source_id, user_id)
    for field, value in data.items():
        if value is not None:
            setattr(source, field, value)
    return source


def _serialise_income(record: IncomeRecord) -> dict:
    return {
        "id": record.id,
        "source_id": record.source_id,
        "source_name": record.source.name if record.source else None,
        "income_type": record.source.income_type if record.source else None,
        "received_on": record.received_on,
        "period_month": record.period_month,
        "gross_amount": record.gross_amount,
        "net_amount": record.net_amount,
        "deductions": record.deductions,
        "description": record.description,
        "notes": record.notes,
        "created_at": record.created_at,
    }


def list_income(
    db: Session,
    user_id: uuid.UUID,
    *,
    period: date | None = None,
    year: int | None = None,
    source_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[dict], int, Decimal]:
    stmt = owned_query(IncomeRecord, user_id).options(selectinload(IncomeRecord.source))
    conditions = []
    if period is not None:
        conditions.append(IncomeRecord.period_month == month_start(period))
    if year is not None:
        conditions += [
            IncomeRecord.received_on >= date(year, 1, 1),
            IncomeRecord.received_on <= date(year, 12, 31),
        ]
    if source_id is not None:
        conditions.append(IncomeRecord.source_id == source_id)
    for condition in conditions:
        stmt = stmt.where(condition)

    aggregate = select(
        func.count(IncomeRecord.id), func.coalesce(func.sum(IncomeRecord.net_amount), 0)
    ).where(IncomeRecord.user_id == user_id, IncomeRecord.is_deleted.is_(False))
    for condition in conditions:
        aggregate = aggregate.where(condition)
    count, total = db.execute(aggregate).one()

    stmt = (
        stmt.order_by(IncomeRecord.received_on.desc())
        .limit(page_size)
        .offset(max(page - 1, 0) * page_size)
    )
    return (
        [_serialise_income(row) for row in db.execute(stmt).scalars()],
        int(count),
        _money(total),
    )


def create_income(db: Session, user_id: uuid.UUID, data: dict) -> IncomeRecord:
    assert_owned(db, IncomeSource, data.get("source_id"), user_id)
    received_on = data.get("received_on") or date.today()

    record = IncomeRecord(
        user_id=user_id,
        source_id=data.get("source_id"),
        received_on=received_on,
        period_month=month_start(received_on),
        gross_amount=data["gross_amount"],
        net_amount=data["net_amount"],
        deductions=data.get("deductions") or (data["gross_amount"] - data["net_amount"]),
        description=data.get("description"),
        notes=data.get("notes"),
    )
    db.add(record)
    db.flush()
    # The amount is deliberately absent from the audit summary: the trail must
    # not become a way to read salary while the app is locked.
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.CREATE.value,
        entity_type="income_record",
        entity_id=record.id,
        summary="Recorded income",
    )
    return record


def update_income(db: Session, user_id: uuid.UUID, record_id: uuid.UUID, data: dict) -> IncomeRecord:
    record = get_owned(db, IncomeRecord, record_id, user_id)
    assert_owned(db, IncomeSource, data.get("source_id"), user_id)

    for field, value in data.items():
        setattr(record, field, value)
    if "received_on" in data and data["received_on"]:
        record.period_month = month_start(record.received_on)
    if record.net_amount > record.gross_amount:
        raise BadRequest("Net pay cannot be higher than gross pay.")

    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.UPDATE.value,
        entity_type="income_record",
        entity_id=record.id,
        summary="Updated income record",
    )
    return record


def get_income(db: Session, user_id: uuid.UUID, record_id: uuid.UUID) -> dict:
    record = get_owned(db, IncomeRecord, record_id, user_id)
    return _serialise_income(record)


def delete_income(db: Session, user_id: uuid.UUID, record_id: uuid.UUID) -> None:
    record = get_owned(db, IncomeRecord, record_id, user_id)
    record.soft_delete()
    audit.record(
        db,
        user_id=user_id,
        action=AuditAction.DELETE.value,
        entity_type="income_record",
        entity_id=record.id,
        summary="Deleted income record",
    )
