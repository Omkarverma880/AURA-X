"""Trips, albums and photo memories schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import AlbumType
from app.schemas.common import ORMModel


class AlbumCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    album_type: AlbumType = AlbumType.GENERAL
    location: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    tags: list[str] | None = None
    notes: str | None = Field(default=None, max_length=2000)


class AlbumUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    tags: list[str] | None = None
    is_favourite: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)
    cover_photo_id: uuid.UUID | None = None


class PhotoOut(ORMModel):
    id: uuid.UUID
    album_id: uuid.UUID
    url: str | None = None
    thumbnail_url: str | None = None
    original_filename: str | None = None
    mime_type: str
    width: int | None = None
    height: int | None = None
    caption: str | None = None
    taken_at: datetime | None = None
    position: int = 0
    created_at: datetime


class PhotoUpdate(BaseModel):
    caption: str | None = Field(default=None, max_length=300)
    position: int | None = None


class AlbumOut(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    album_type: str
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    cover_photo_id: uuid.UUID | None = None
    cover_photo_url: str | None = None
    tags: list[str] | None = None
    is_favourite: bool = False
    notes: str | None = None
    created_at: datetime
    photo_count: int = 0


class AlbumDetail(AlbumOut):
    photos: list[PhotoOut] = []
