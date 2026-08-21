"""Ownership-scoped data access.

This module is the single choke point for multi-tenant safety. Nothing in the
API layer builds a query against a user-owned table directly; everything goes
through these helpers, which always inject a user_id predicate derived from the
authenticated session.

A record belonging to somebody else is reported as NotFound rather than
Forbidden on purpose: a 403 would confirm that the id exists, turning an IDOR
probe into a working enumeration oracle.
"""

from __future__ import annotations

import uuid
from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


def owned_query(model: type[ModelT], user_id: uuid.UUID, *, include_deleted: bool = False) -> Select:
    """Base SELECT for a user-owned table, already scoped to the owner."""
    stmt = select(model).where(model.user_id == user_id)
    if not include_deleted and hasattr(model, "is_deleted"):
        stmt = stmt.where(model.is_deleted.is_(False))
    return stmt


def get_owned(
    db: Session,
    model: type[ModelT],
    entity_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    include_deleted: bool = False,
) -> ModelT:
    """Fetch one row, or raise NotFound when it is missing or not owned."""
    stmt = owned_query(model, user_id, include_deleted=include_deleted).where(model.id == entity_id)
    entity = db.execute(stmt).scalar_one_or_none()
    if entity is None:
        raise NotFound(_not_found_message(model))
    return entity


def get_owned_or_none(
    db: Session,
    model: type[ModelT],
    entity_id: uuid.UUID | None,
    user_id: uuid.UUID,
) -> ModelT | None:
    if entity_id is None:
        return None
    return get_owned(db, model, entity_id, user_id)


def assert_owned(
    db: Session,
    model: type[ModelT],
    entity_id: uuid.UUID | None,
    user_id: uuid.UUID,
) -> None:
    """Validate a client-supplied foreign key before it is written.

    Without this a user could attach their own expense to somebody else's
    category, leaking that the category exists and corrupting both accounts.
    """
    if entity_id is not None:
        get_owned(db, model, entity_id, user_id)


def count_owned(db: Session, model: type[ModelT], user_id: uuid.UUID, *conditions: Any) -> int:
    stmt = select(func.count()).select_from(model).where(model.user_id == user_id)
    if hasattr(model, "is_deleted"):
        stmt = stmt.where(model.is_deleted.is_(False))
    for condition in conditions:
        stmt = stmt.where(condition)
    return int(db.execute(stmt).scalar_one())


def paginate(stmt: Select, page: int, page_size: int) -> Select:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    return stmt.limit(page_size).offset((page - 1) * page_size)


def total_for(db: Session, stmt: Select) -> int:
    """Row count for a filtered query, without loading any rows."""
    subquery = stmt.order_by(None).options().subquery()
    return int(db.execute(select(func.count()).select_from(subquery)).scalar_one())


def _not_found_message(model: type[ModelT]) -> str:
    label = getattr(model, "__tablename__", "record").replace("_", " ").rstrip("s")
    return f"The requested {label} does not exist."
