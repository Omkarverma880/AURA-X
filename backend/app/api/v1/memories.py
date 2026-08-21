"""Trips, albums and photo memories endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, UploadFile, status

from app.core.deps import CurrentAuth, DbSession
from app.core.rate_limit import rate_limiter
from app.schemas.common import MessageResponse
from app.schemas.memories import (
    AlbumCreate,
    AlbumDetail,
    AlbumOut,
    AlbumUpdate,
    PhotoOut,
    PhotoUpdate,
)
from app.services import memories as service
from app.storage import storage

router = APIRouter(prefix="/memories", tags=["Memories"])


@router.get("/albums", response_model=list[AlbumOut])
def list_albums(
    db: DbSession, ctx: CurrentAuth, album_type: str | None = None, search: str | None = None
) -> list[AlbumOut]:
    rows = service.list_albums(db, ctx.user_id, album_type=album_type, search=search)
    return [AlbumOut.model_validate(row) for row in rows]


@router.post("/albums", response_model=AlbumDetail, status_code=status.HTTP_201_CREATED)
def create_album(payload: AlbumCreate, db: DbSession, ctx: CurrentAuth) -> AlbumDetail:
    album = service.create_album(db, ctx.user_id, payload.model_dump())
    db.commit()
    return AlbumDetail.model_validate(service.get_album_detail(db, ctx.user_id, album.id))


@router.get("/albums/{album_id}", response_model=AlbumDetail)
def get_album(album_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> AlbumDetail:
    return AlbumDetail.model_validate(service.get_album_detail(db, ctx.user_id, album_id))


@router.patch("/albums/{album_id}", response_model=AlbumDetail)
def update_album(
    album_id: uuid.UUID, payload: AlbumUpdate, db: DbSession, ctx: CurrentAuth
) -> AlbumDetail:
    service.update_album(db, ctx.user_id, album_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return AlbumDetail.model_validate(service.get_album_detail(db, ctx.user_id, album_id))


@router.delete("/albums/{album_id}", response_model=MessageResponse)
def delete_album(album_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    keys = service.delete_album(db, ctx.user_id, album_id)
    db.commit()
    for key in keys:
        storage.delete(key)
    return MessageResponse(message="Album deleted.")


@router.post(
    "/albums/{album_id}/photos", response_model=PhotoOut, status_code=status.HTTP_201_CREATED
)
def upload_photo(
    album_id: uuid.UUID,
    db: DbSession,
    ctx: CurrentAuth,
    file: UploadFile = File(...),
    caption: str | None = Form(default=None),
) -> PhotoOut:
    rate_limiter.check("upload", str(ctx.user_id))
    photo = service.upload_photo(db, ctx.user_id, album_id, file, caption)
    db.commit()
    return PhotoOut.model_validate(service.serialise_photo(photo))


@router.patch("/photos/{photo_id}", response_model=PhotoOut)
def update_photo(
    photo_id: uuid.UUID, payload: PhotoUpdate, db: DbSession, ctx: CurrentAuth
) -> PhotoOut:
    photo = service.update_photo(db, ctx.user_id, photo_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return PhotoOut.model_validate(service.serialise_photo(photo))


@router.delete("/photos/{photo_id}", response_model=MessageResponse)
def delete_photo(photo_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    keys = service.delete_photo(db, ctx.user_id, photo_id)
    db.commit()
    for key in keys:
        storage.delete(key)
    return MessageResponse(message="Photo deleted.")
