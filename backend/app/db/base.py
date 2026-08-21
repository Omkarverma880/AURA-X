"""Declarative base and the mixins every table is built from."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.types import GUID


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    type_annotation_map = {}


class UUIDPrimaryKeyMixin:
    """UUID primary keys - non-guessable and safe to expose in URLs."""

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4, sort_order=-100
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, sort_order=100
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
        sort_order=101,
    )


class SoftDeleteMixin:
    """Financial history is archived rather than destroyed."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True, sort_order=102
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, sort_order=103
    )

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = utcnow()


class UserOwnedMixin:
    """Every user-owned row carries an indexed FK to its owner.

    Combined with the ownership-scoped repositories this is what makes the
    application multi-tenant: no query ever runs without a user_id filter.
    """

    @property
    def owner_id(self) -> uuid.UUID:
        return self.user_id  # type: ignore[attr-defined]


def user_fk(**kwargs) -> Mapped[uuid.UUID]:
    return mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        sort_order=-90,
        **kwargs,
    )


def short_str(length: int = 255, **kwargs) -> Mapped[str]:
    return mapped_column(String(length), **kwargs)


def owner_index(table: str, *columns: str) -> Index:
    """Composite index starting at user_id - the shape every tenant query uses."""
    return Index(f"ix_{table}_{'_'.join(columns)}", "user_id", *columns)
