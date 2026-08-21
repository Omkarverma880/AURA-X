"""Life goals, milestones and custom checklist/tracker schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import GoalStatus, Priority, TrackerType
from app.schemas.common import Money, ORMModel, OptionalMoney


class LifeCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=20)


class LifeCategoryOut(ORMModel):
    id: uuid.UUID
    name: str
    icon: str | None = None
    color: str | None = None
    sort_order: int = 0


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    is_completed: bool | None = None


class MilestoneOut(ORMModel):
    id: uuid.UUID
    goal_id: uuid.UUID
    title: str
    description: str | None = None
    due_date: date | None = None
    is_completed: bool = False
    completed_on: date | None = None
    position: int = 0


class LifeGoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    target_date: date | None = None
    started_on: date | None = None
    target_amount: OptionalMoney = None
    current_amount: OptionalMoney = None
    priority: Priority = Priority.MEDIUM
    notes: str | None = Field(default=None, max_length=2000)


class LifeGoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    target_date: date | None = None
    started_on: date | None = None
    target_amount: OptionalMoney = None
    current_amount: OptionalMoney = None
    priority: Priority | None = None
    status: GoalStatus | None = None
    manual_progress: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=2000)


class LifeGoalOut(ORMModel):
    id: uuid.UUID
    title: str
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    description: str | None = None
    target_date: date | None = None
    started_on: date | None = None
    completed_on: date | None = None
    target_amount: OptionalMoney = None
    current_amount: OptionalMoney = None
    status: str = "in_progress"
    priority: str = "medium"
    notes: str | None = None
    created_at: datetime

    progress_percent: float = 0
    milestone_total: int = 0
    milestone_done: int = 0
    is_overdue: bool = False


class LifeGoalDetail(LifeGoalOut):
    milestones: list[MilestoneOut] = []


# --- Checklists / custom trackers ---------------------------------------


class ChecklistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    tracker_type: TrackerType = TrackerType.GENERIC
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    target_count: int | None = Field(default=None, ge=1)
    goal_id: uuid.UUID | None = None
    #: Convenience: seed items in the same call, e.g. the 12 Jyotirlingas.
    items: list[str] | None = None


class ChecklistUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    icon: str | None = Field(default=None, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    target_count: int | None = Field(default=None, ge=1)
    is_archived: bool | None = None


class ChecklistOut(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    tracker_type: str
    icon: str | None = None
    color: str | None = None
    target_count: int | None = None
    is_archived: bool = False
    goal_id: uuid.UUID | None = None
    created_at: datetime

    item_count: int = 0
    completed_count: int = 0
    progress_percent: float = 0


class ChecklistItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    details: dict | None = None


class ChecklistItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    is_completed: bool | None = None
    completed_on: date | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = Field(default=None, max_length=2000)
    details: dict | None = None
    album_id: uuid.UUID | None = None
    position: int | None = None


class ChecklistItemOut(ORMModel):
    id: uuid.UUID
    checklist_id: uuid.UUID
    name: str
    description: str | None = None
    location: str | None = None
    position: int = 0
    is_completed: bool = False
    completed_on: date | None = None
    rating: int | None = None
    notes: str | None = None
    details: dict | None = None
    album_id: uuid.UUID | None = None


class ChecklistDetail(ChecklistOut):
    items: list[ChecklistItemOut] = []


class LifeAnalytics(BaseModel):
    goals_completed: int = 0
    goals_in_progress: int = 0
    goals_overdue: int = 0
    trackers: list[dict] = []
    trips_completed: int = 0
    memory_count: int = 0
