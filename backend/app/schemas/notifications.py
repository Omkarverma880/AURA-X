"""Notification schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class NotificationCreate(BaseModel):
    notification_type: str = Field(default="custom", max_length=30)
    severity: str = Field(default="info", max_length=10)
    title: str = Field(min_length=1, max_length=200)
    body: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    action_url: str | None = Field(default=None, max_length=300)


class NotificationOut(ORMModel):
    id: uuid.UUID
    notification_type: str
    severity: str
    title: str
    body: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    action_url: str | None = None
    due_at: datetime | None = None
    is_read: bool = False
    is_dismissed: bool = False
    created_at: datetime
