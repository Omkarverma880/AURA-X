"""Life goals, milestones and the custom checklist / tracker system."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, user_fk
from app.db.types import GUID, JSONType, Money
from app.models.enums import GoalStatus, Priority, TrackerType


class LifeGoalCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "life_goal_categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_life_cat_user_name"),)

    user_id: Mapped[uuid.UUID] = user_fk()
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(40))
    color: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class LifeGoal(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """An ambition. Progress is milestone-derived, amount-derived or manual -
    whichever the goal actually has data for."""

    __tablename__ = "life_goals"
    __table_args__ = (
        Index("ix_life_goals_user_status", "user_id", "status"),
        Index("ix_life_goals_user_target", "user_id", "target_date"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("life_goal_categories.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_date: Mapped[date | None] = mapped_column(Date)
    started_on: Mapped[date | None] = mapped_column(Date)
    completed_on: Mapped[date | None] = mapped_column(Date)
    target_amount: Mapped[Decimal | None] = mapped_column(Money)
    current_amount: Mapped[Decimal | None] = mapped_column(Money)
    status: Mapped[str] = mapped_column(
        String(20), default=GoalStatus.IN_PROGRESS.value, nullable=False
    )
    priority: Mapped[str] = mapped_column(String(10), default=Priority.MEDIUM.value, nullable=False)
    #: Manual override used only when the goal has no milestones and no amounts.
    manual_progress: Mapped[int | None] = mapped_column(Integer)
    cover_photo_id: Mapped[uuid.UUID | None] = mapped_column(GUID)
    notes: Mapped[str | None] = mapped_column(Text)

    category: Mapped[LifeGoalCategory | None] = relationship()
    milestones: Mapped[list["GoalMilestone"]] = relationship(
        back_populates="goal",
        cascade="all, delete-orphan",
        order_by="GoalMilestone.position",
    )


class GoalMilestone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "goal_milestones"
    __table_args__ = (Index("ix_milestones_user_goal", "user_id", "goal_id"),)

    user_id: Mapped[uuid.UUID] = user_fk()
    goal_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("life_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_on: Mapped[date | None] = mapped_column(Date)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    goal: Mapped[LifeGoal] = relationship(back_populates="milestones")


class Checklist(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A custom tracker: 12 Jyotirlingas, 20 treks, countries visited, books.

    The tracker type only drives presentation (which extra fields to show); the
    structure is identical for every kind, so users can invent their own.
    """

    __tablename__ = "checklists"
    __table_args__ = (Index("ix_checklists_user_type", "user_id", "tracker_type"),)

    user_id: Mapped[uuid.UUID] = user_fk()
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tracker_type: Mapped[str] = mapped_column(
        String(20), default=TrackerType.GENERIC.value, nullable=False
    )
    icon: Mapped[str | None] = mapped_column(String(40))
    color: Mapped[str | None] = mapped_column(String(20))
    #: Optional denominator when the list samples a bigger ambition, e.g. 7 of
    #: a planned 20 treks recorded so far.
    target_count: Mapped[int | None] = mapped_column(Integer)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("life_goals.id", ondelete="SET NULL")
    )

    items: Mapped[list["ChecklistItem"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="ChecklistItem.position",
    )


class ChecklistItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "checklist_items"
    __table_args__ = (
        Index("ix_checklist_items_user_list", "user_id", "checklist_id"),
        Index("ix_checklist_items_user_done", "user_id", "is_completed"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("checklists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_on: Mapped[date | None] = mapped_column(Date)
    rating: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    #: Tracker-specific fields (trek difficulty, distance, elevation, book
    #: author, course provider). Free-form so a new tracker type needs no
    #: migration.
    details: Mapped[dict | None] = mapped_column(JSONType)
    album_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("albums.id", ondelete="SET NULL")
    )

    checklist: Mapped[Checklist] = relationship(back_populates="items")
