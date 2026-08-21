"""Life goals, milestones and the custom checklist/tracker system.

A goal's progress is never stored - it is derived from whichever signal the
goal actually has: milestones first (most specific), then a target amount,
then a manual percentage the user set by hand. This mirrors the ledger and
investment modules, where a displayed number always traces back to rows that
were actually recorded rather than to a field that can drift out of sync.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import AuditAction, GoalStatus
from app.models.life import Checklist, ChecklistItem, GoalMilestone, LifeGoal, LifeGoalCategory
from app.models.memories import Album
from app.services import audit
from app.services.ownership import assert_owned, get_owned, owned_query


# --- Life goals ----------------------------------------------------------


def _goal_progress(goal: LifeGoal, milestones: list[GoalMilestone]) -> tuple[float, int, int]:
    total = len(milestones)
    done = sum(1 for m in milestones if m.is_completed)

    if total > 0:
        return round(done / total * 100, 1), total, done
    if goal.target_amount and goal.target_amount > 0:
        current = goal.current_amount or 0
        return round(min(float(current / goal.target_amount * 100), 100.0), 1), 0, 0
    if goal.manual_progress is not None:
        return float(goal.manual_progress), 0, 0
    if goal.status == GoalStatus.COMPLETED.value:
        return 100.0, 0, 0
    return 0.0, 0, 0


def serialise_goal(goal: LifeGoal, milestones: list[GoalMilestone] | None = None) -> dict:
    rows = milestones if milestones is not None else list(goal.milestones)
    progress, total, done = _goal_progress(goal, rows)
    overdue = bool(
        goal.target_date
        and goal.target_date < date.today()
        and goal.status not in (GoalStatus.COMPLETED.value, GoalStatus.ABANDONED.value)
    )
    return {
        "id": goal.id,
        "title": goal.title,
        "category_id": goal.category_id,
        "category_name": goal.category.name if goal.category else None,
        "description": goal.description,
        "target_date": goal.target_date,
        "started_on": goal.started_on,
        "completed_on": goal.completed_on,
        "target_amount": goal.target_amount,
        "current_amount": goal.current_amount,
        "status": goal.status,
        "priority": goal.priority,
        "notes": goal.notes,
        "created_at": goal.created_at,
        "progress_percent": progress,
        "milestone_total": total,
        "milestone_done": done,
        "is_overdue": overdue,
    }


def list_goals(
    db: Session, user_id: uuid.UUID, *, status: str | None = None, category_id: uuid.UUID | None = None
) -> list[dict]:
    stmt = owned_query(LifeGoal, user_id).options(
        selectinload(LifeGoal.milestones), selectinload(LifeGoal.category)
    )
    if status:
        stmt = stmt.where(LifeGoal.status == status)
    if category_id:
        stmt = stmt.where(LifeGoal.category_id == category_id)
    rows = [serialise_goal(g) for g in db.execute(stmt).scalars()]
    rows.sort(key=lambda r: (r["status"] == "completed", r["target_date"] or date.max))
    return rows


def create_goal(db: Session, user_id: uuid.UUID, data: dict) -> LifeGoal:
    assert_owned(db, LifeGoalCategory, data.get("category_id"), user_id)
    goal = LifeGoal(
        user_id=user_id,
        title=data["title"].strip(),
        category_id=data.get("category_id"),
        description=data.get("description"),
        target_date=data.get("target_date"),
        started_on=data.get("started_on") or date.today(),
        target_amount=data.get("target_amount"),
        current_amount=data.get("current_amount"),
        priority=data.get("priority") or "medium",
        notes=data.get("notes"),
    )
    db.add(goal)
    db.flush()
    audit.record(
        db, user_id=user_id, action=AuditAction.CREATE.value, entity_type="life_goal",
        entity_id=goal.id, summary=f"Added life goal: {goal.title}",
    )
    return goal


def update_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID, data: dict) -> LifeGoal:
    goal = get_owned(db, LifeGoal, goal_id, user_id)
    assert_owned(db, LifeGoalCategory, data.get("category_id"), user_id)

    for field in (
        "title", "category_id", "description", "target_date", "started_on",
        "target_amount", "current_amount", "priority", "status", "manual_progress", "notes",
    ):
        if field in data and data[field] is not None:
            setattr(goal, field, data[field])

    if data.get("status") == GoalStatus.COMPLETED.value and goal.completed_on is None:
        goal.completed_on = date.today()
    elif data.get("status") not in (None, GoalStatus.COMPLETED.value):
        goal.completed_on = None
    return goal


def delete_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    goal = get_owned(db, LifeGoal, goal_id, user_id)
    goal.soft_delete()


def get_goal_detail(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> dict:
    goal = get_owned(db, LifeGoal, goal_id, user_id)
    milestones = sorted(goal.milestones, key=lambda m: m.position)
    payload = serialise_goal(goal, milestones)
    payload["milestones"] = [serialise_milestone(m) for m in milestones]
    return payload


def serialise_milestone(milestone: GoalMilestone) -> dict:
    return {
        "id": milestone.id,
        "goal_id": milestone.goal_id,
        "title": milestone.title,
        "description": milestone.description,
        "due_date": milestone.due_date,
        "is_completed": milestone.is_completed,
        "completed_on": milestone.completed_on,
        "position": milestone.position,
    }


def add_milestone(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID, data: dict) -> GoalMilestone:
    goal = get_owned(db, LifeGoal, goal_id, user_id)
    position = db.execute(
        select(func.coalesce(func.max(GoalMilestone.position), -1)).where(
            GoalMilestone.goal_id == goal_id
        )
    ).scalar_one()
    milestone = GoalMilestone(
        user_id=user_id,
        goal_id=goal.id,
        title=data["title"].strip(),
        description=data.get("description"),
        due_date=data.get("due_date"),
        position=position + 1,
    )
    db.add(milestone)
    db.flush()
    return milestone


def update_milestone(
    db: Session, user_id: uuid.UUID, milestone_id: uuid.UUID, data: dict
) -> GoalMilestone:
    milestone = get_owned(db, GoalMilestone, milestone_id, user_id)
    for field in ("title", "description", "due_date"):
        if field in data and data[field] is not None:
            setattr(milestone, field, data[field])
    if "is_completed" in data and data["is_completed"] is not None:
        milestone.is_completed = data["is_completed"]
        milestone.completed_on = date.today() if data["is_completed"] else None
    return milestone


def delete_milestone(db: Session, user_id: uuid.UUID, milestone_id: uuid.UUID) -> None:
    db.delete(get_owned(db, GoalMilestone, milestone_id, user_id))


# --- Checklists / custom trackers ----------------------------------------


def serialise_checklist(checklist: Checklist, items: list[ChecklistItem] | None = None) -> dict:
    rows = items if items is not None else list(checklist.items)
    total = len(rows)
    done = sum(1 for i in rows if i.is_completed)
    denominator = checklist.target_count or total
    progress = round(done / denominator * 100, 1) if denominator else 0.0
    return {
        "id": checklist.id,
        "title": checklist.title,
        "description": checklist.description,
        "tracker_type": checklist.tracker_type,
        "icon": checklist.icon,
        "color": checklist.color,
        "target_count": checklist.target_count,
        "is_archived": checklist.is_archived,
        "goal_id": checklist.goal_id,
        "created_at": checklist.created_at,
        "item_count": total,
        "completed_count": done,
        "progress_percent": min(progress, 100.0),
    }


def serialise_item(item: ChecklistItem) -> dict:
    return {
        "id": item.id,
        "checklist_id": item.checklist_id,
        "name": item.name,
        "description": item.description,
        "location": item.location,
        "position": item.position,
        "is_completed": item.is_completed,
        "completed_on": item.completed_on,
        "rating": item.rating,
        "notes": item.notes,
        "details": item.details,
        "album_id": item.album_id,
    }


def list_checklists(
    db: Session, user_id: uuid.UUID, *, tracker_type: str | None = None, include_archived: bool = False
) -> list[dict]:
    stmt = owned_query(Checklist, user_id).options(selectinload(Checklist.items))
    if tracker_type:
        stmt = stmt.where(Checklist.tracker_type == tracker_type)
    if not include_archived:
        stmt = stmt.where(Checklist.is_archived.is_(False))
    return [serialise_checklist(c) for c in db.execute(stmt).scalars()]


def create_checklist(db: Session, user_id: uuid.UUID, data: dict) -> Checklist:
    checklist = Checklist(
        user_id=user_id,
        title=data["title"].strip(),
        description=data.get("description"),
        tracker_type=data.get("tracker_type") or "generic",
        icon=data.get("icon"),
        color=data.get("color"),
        target_count=data.get("target_count"),
        goal_id=data.get("goal_id"),
    )
    db.add(checklist)
    db.flush()

    for position, name in enumerate(data.get("items") or []):
        name = name.strip()
        if name:
            db.add(
                ChecklistItem(
                    user_id=user_id, checklist_id=checklist.id, name=name, position=position
                )
            )
    db.flush()

    audit.record(
        db, user_id=user_id, action=AuditAction.CREATE.value, entity_type="checklist",
        entity_id=checklist.id, summary=f"Created tracker: {checklist.title}",
    )
    return checklist


def update_checklist(db: Session, user_id: uuid.UUID, checklist_id: uuid.UUID, data: dict) -> Checklist:
    checklist = get_owned(db, Checklist, checklist_id, user_id)
    for field in ("title", "description", "icon", "color", "target_count", "is_archived"):
        if field in data and data[field] is not None:
            setattr(checklist, field, data[field])
    return checklist


def delete_checklist(db: Session, user_id: uuid.UUID, checklist_id: uuid.UUID) -> None:
    checklist = get_owned(db, Checklist, checklist_id, user_id)
    checklist.soft_delete()


def get_checklist_detail(db: Session, user_id: uuid.UUID, checklist_id: uuid.UUID) -> dict:
    checklist = get_owned(db, Checklist, checklist_id, user_id)
    items = sorted(checklist.items, key=lambda i: i.position)
    payload = serialise_checklist(checklist, items)
    payload["items"] = [serialise_item(i) for i in items]
    return payload


def add_item(db: Session, user_id: uuid.UUID, checklist_id: uuid.UUID, data: dict) -> ChecklistItem:
    checklist = get_owned(db, Checklist, checklist_id, user_id)
    position = db.execute(
        select(func.coalesce(func.max(ChecklistItem.position), -1)).where(
            ChecklistItem.checklist_id == checklist_id
        )
    ).scalar_one()
    item = ChecklistItem(
        user_id=user_id,
        checklist_id=checklist.id,
        name=data["name"].strip(),
        description=data.get("description"),
        location=data.get("location"),
        details=data.get("details"),
        position=position + 1,
    )
    db.add(item)
    db.flush()
    return item


def update_item(db: Session, user_id: uuid.UUID, item_id: uuid.UUID, data: dict) -> ChecklistItem:
    item = get_owned(db, ChecklistItem, item_id, user_id)
    assert_owned(db, Album, data.get("album_id"), user_id)

    for field in ("name", "description", "location", "rating", "notes", "details", "album_id", "position"):
        if field in data and data[field] is not None:
            setattr(item, field, data[field])

    if "is_completed" in data and data["is_completed"] is not None:
        item.is_completed = data["is_completed"]
        item.completed_on = data.get("completed_on") or (date.today() if data["is_completed"] else None)
    return item


def delete_item(db: Session, user_id: uuid.UUID, item_id: uuid.UUID) -> None:
    db.delete(get_owned(db, ChecklistItem, item_id, user_id))


# --- Analytics -------------------------------------------------------------


def life_analytics(db: Session, user_id: uuid.UUID) -> dict:
    goals = list_goals(db, user_id)
    completed = sum(1 for g in goals if g["status"] == "completed")
    in_progress = sum(1 for g in goals if g["status"] == "in_progress")
    overdue = sum(1 for g in goals if g["is_overdue"])

    trackers = list_checklists(db, user_id)
    tracker_summary = [
        {
            "id": str(t["id"]),
            "title": t["title"],
            "tracker_type": t["tracker_type"],
            "completed": t["completed_count"],
            "total": t["item_count"],
            "progress_percent": t["progress_percent"],
        }
        for t in trackers
    ]

    trips_completed = db.execute(
        select(func.count()).select_from(Album).where(
            Album.user_id == user_id, Album.is_deleted.is_(False), Album.album_type == "trip"
        )
    ).scalar_one()
    memory_count = db.execute(
        select(func.count()).select_from(Album).where(
            Album.user_id == user_id, Album.is_deleted.is_(False)
        )
    ).scalar_one()

    return {
        "goals_completed": completed,
        "goals_in_progress": in_progress,
        "goals_overdue": overdue,
        "trackers": tracker_summary,
        "trips_completed": int(trips_completed),
        "memory_count": int(memory_count),
    }
