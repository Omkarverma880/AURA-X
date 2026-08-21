"""Notifications.

Kept deliberately simple for v1: in-app rows only, generated on demand from
data that already exists (overdue Bahi Khata entries, exceeded budgets,
approaching goal deadlines) rather than a background scheduler. The row shape
already supports a due_at/entity_id/action_url, so e-mail or push delivery can
be added later by draining unread rows without a schema change.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import NotificationType, Severity
from app.models.ledger import LedgerEntry
from app.models.life import LifeGoal
from app.models.system import Notification
from app.services import monthly as monthly_service
from app.services.ownership import get_owned, owned_query


def list_notifications(
    db: Session, user_id: uuid.UUID, *, unread_only: bool = False, limit: int = 50
) -> list[Notification]:
    stmt = owned_query(Notification, user_id).order_by(Notification.created_at.desc()).limit(limit)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.where(Notification.is_dismissed.is_(False))
    return list(db.execute(stmt).scalars())


def unread_count(db: Session, user_id: uuid.UUID) -> int:
    return int(
        db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
                Notification.is_dismissed.is_(False),
            )
        ).scalar_one()
    )


def create_notification(db: Session, user_id: uuid.UUID, data: dict) -> Notification:
    notification = Notification(user_id=user_id, **data)
    db.add(notification)
    db.flush()
    return notification


def mark_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    notification = get_owned(db, Notification, notification_id, user_id)
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    return notification


def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
    rows = list(
        db.execute(
            owned_query(Notification, user_id).where(Notification.is_read.is_(False))
        ).scalars()
    )
    for row in rows:
        row.is_read = True
        row.read_at = datetime.now(timezone.utc)
    return len(rows)


def dismiss(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
    notification = get_owned(db, Notification, notification_id, user_id)
    notification.is_dismissed = True


def refresh_reminders(db: Session, user_id: uuid.UUID) -> int:
    """Generate/refresh reminder notifications from current data.

    Idempotent: an existing unread reminder for the same entity is updated
    rather than duplicated, so calling this on every dashboard load is safe.
    """
    created_or_updated = 0
    today = date.today()

    # Bahi Khata: entries overdue or due within a week.
    soon = today + timedelta(days=7)
    for entry in db.execute(
        select(LedgerEntry).where(
            LedgerEntry.user_id == user_id,
            LedgerEntry.is_deleted.is_(False),
            LedgerEntry.is_closed.is_(False),
            LedgerEntry.due_date.is_not(None),
            LedgerEntry.due_date <= soon,
        )
    ).scalars():
        overdue = entry.due_date < today
        verb = "Collect from" if entry.direction == "given" else "Pay"
        person = entry.person.name if entry.person else "someone"
        title = f"{verb} {person}" + (" - overdue" if overdue else " - due soon")
        _upsert(
            db, user_id,
            notification_type=NotificationType.LEDGER_DUE.value,
            severity=Severity.DANGER.value if overdue else Severity.WARNING.value,
            title=title,
            body=entry.purpose,
            entity_type="ledger_entry",
            entity_id=entry.id,
            due_at=datetime.combine(entry.due_date, datetime.min.time(), tzinfo=timezone.utc),
        )
        created_or_updated += 1

    # Budgets exceeded this month.
    for row in monthly_service.budget_overview(db, user_id, today):
        if row["status"] == "exceeded":
            _upsert(
                db, user_id,
                notification_type=NotificationType.BUDGET_EXCEEDED.value,
                severity=Severity.DANGER.value,
                title=f"{row['category_name']} budget exceeded",
                body=f"Spent {row['spent']} of {row['amount']}",
                entity_type="budget",
                entity_id=row["id"],
            )
            created_or_updated += 1

    # Life goals with an approaching deadline.
    for goal in db.execute(
        select(LifeGoal).where(
            LifeGoal.user_id == user_id,
            LifeGoal.is_deleted.is_(False),
            LifeGoal.status.notin_(["completed", "abandoned"]),
            LifeGoal.target_date.is_not(None),
            LifeGoal.target_date <= soon,
        )
    ).scalars():
        _upsert(
            db, user_id,
            notification_type=NotificationType.GOAL_DEADLINE.value,
            severity=Severity.WARNING.value,
            title=f"{goal.title} - deadline approaching",
            body=None,
            entity_type="life_goal",
            entity_id=goal.id,
            due_at=datetime.combine(goal.target_date, datetime.min.time(), tzinfo=timezone.utc),
        )
        created_or_updated += 1

    return created_or_updated


def _upsert(db: Session, user_id: uuid.UUID, *, entity_type: str, entity_id, **fields) -> None:
    existing = db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.entity_type == entity_type,
            Notification.entity_id == entity_id,
            Notification.is_dismissed.is_(False),
        )
    ).scalar_one_or_none()

    if existing is not None:
        for key, value in fields.items():
            setattr(existing, key, value)
        existing.is_read = False
        return

    db.add(Notification(user_id=user_id, entity_type=entity_type, entity_id=entity_id, **fields))
