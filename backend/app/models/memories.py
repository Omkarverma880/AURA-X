"""Trips, albums and photo memories.

Only metadata lives in PostgreSQL; the bytes live in object storage behind the
storage abstraction, because the Railway container filesystem is ephemeral.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, user_fk
from app.db.types import GUID, JSONType
from app.models.enums import AlbumType


class Album(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A trip or a themed collection of memories."""

    __tablename__ = "albums"
    __table_args__ = (
        Index("ix_albums_user_date", "user_id", "start_date"),
        Index("ix_albums_user_type", "user_id", "album_type"),
    )

    user_id: Mapped[uuid.UUID] = user_fk()
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    album_type: Mapped[str] = mapped_column(
        String(20), default=AlbumType.GENERAL.value, nullable=False
    )
    location: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    cover_photo_id: Mapped[uuid.UUID | None] = mapped_column(GUID)
    tags: Mapped[list | None] = mapped_column(JSONType)
    is_favourite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    photos: Mapped[list["Photo"]] = relationship(
        back_populates="album",
        cascade="all, delete-orphan",
        order_by="Photo.position",
    )


class Photo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memory_photos"
    __table_args__ = (Index("ix_photos_user_album", "user_id", "album_id"),)

    user_id: Mapped[uuid.UUID] = user_fk()
    album_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("albums.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: Opaque, randomly generated object key. Never derived from the uploaded
    #: filename, so a hostile filename cannot escape its prefix.
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(60), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(String(300))
    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    album: Mapped[Album] = relationship(back_populates="photos")
