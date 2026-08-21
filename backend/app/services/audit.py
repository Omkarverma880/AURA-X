"""Audit trail writer."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, redact
from app.models.system import AuditLog

logger = get_logger(__name__)


def record(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    summary: str | None = None,
    meta: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Append an audit entry to the current transaction.

    The caller commits, so the audit row lands atomically with the change it
    describes: a financial write and its trail can never disagree.
    """
    entry = AuditLog(
        user_id=user_id,
        action=str(action),
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        meta=redact(meta) if meta else None,
        ip_address=ip_address,
        user_agent=(user_agent or "")[:400] or None,
    )
    db.add(entry)
    return entry


def list_for_user(db: Session, user_id: uuid.UUID, limit: int = 50) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(desc(AuditLog.created_at))
        .limit(min(limit, 200))
    )
    return list(db.execute(stmt).scalars())
