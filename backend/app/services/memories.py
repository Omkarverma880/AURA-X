"""Trips, albums and photo memories.

Only metadata is ever touched here; the actual bytes go through the storage
abstraction (local disk in dev, S3-compatible in production) and validated
image processing in app.storage.images before a Photo row is even created.
"""

from __future__ import annotations

import uuid

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BadRequest
from app.models.enums import AuditAction
from app.models.memories import Album, Photo
from app.services import audit
from app.services.ownership import get_owned, owned_query
from app.storage import storage
from app.storage.images import make_thumbnail, process_upload


def _photo_url(key: str | None) -> str | None:
    return storage.public_url(key) if key else None


def serialise_photo(photo: Photo) -> dict:
    return {
        "id": photo.id,
        "album_id": photo.album_id,
        "url": _photo_url(photo.object_key),
        "thumbnail_url": _photo_url(photo.thumbnail_key),
        "original_filename": photo.original_filename,
        "mime_type": photo.mime_type,
        "width": photo.width,
        "height": photo.height,
        "caption": photo.caption,
        "taken_at": photo.taken_at,
        "position": photo.position,
        "created_at": photo.created_at,
    }


def serialise_album(album: Album, photos: list[Photo] | None = None) -> dict:
    rows = photos if photos is not None else list(album.photos)
    cover = next((p for p in rows if p.id == album.cover_photo_id), rows[0] if rows else None)
    return {
        "id": album.id,
        "title": album.title,
        "description": album.description,
        "album_type": album.album_type,
        "location": album.location,
        "start_date": album.start_date,
        "end_date": album.end_date,
        "cover_photo_id": album.cover_photo_id,
        "cover_photo_url": _photo_url(cover.object_key) if cover else None,
        "tags": album.tags,
        "is_favourite": album.is_favourite,
        "notes": album.notes,
        "created_at": album.created_at,
        "photo_count": len(rows),
    }


# --- Albums --------------------------------------------------------------


def list_albums(
    db: Session, user_id: uuid.UUID, *, album_type: str | None = None, search: str | None = None
) -> list[dict]:
    stmt = owned_query(Album, user_id).options(selectinload(Album.photos))
    if album_type:
        stmt = stmt.where(Album.album_type == album_type)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(Album.title.ilike(pattern) | Album.location.ilike(pattern))
    rows = [serialise_album(a) for a in db.execute(stmt).scalars()]
    rows.sort(key=lambda a: a["start_date"] or a["created_at"].date(), reverse=True)
    return rows


def create_album(db: Session, user_id: uuid.UUID, data: dict) -> Album:
    album = Album(
        user_id=user_id,
        title=data["title"].strip(),
        description=data.get("description"),
        album_type=data.get("album_type") or "general",
        location=data.get("location"),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        tags=data.get("tags"),
        notes=data.get("notes"),
    )
    db.add(album)
    db.flush()
    audit.record(
        db, user_id=user_id, action=AuditAction.CREATE.value, entity_type="album",
        entity_id=album.id, summary=f"Created album: {album.title}",
    )
    return album


def update_album(db: Session, user_id: uuid.UUID, album_id: uuid.UUID, data: dict) -> Album:
    album = get_owned(db, Album, album_id, user_id)
    if data.get("cover_photo_id"):
        photo = get_owned(db, Photo, data["cover_photo_id"], user_id)
        if photo.album_id != album.id:
            raise BadRequest("That photo does not belong to this album.")

    for field in (
        "title", "description", "location", "start_date", "end_date",
        "tags", "is_favourite", "notes", "cover_photo_id",
    ):
        if field in data and data[field] is not None:
            setattr(album, field, data[field])
    return album


def delete_album(db: Session, user_id: uuid.UUID, album_id: uuid.UUID) -> None:
    """Delete an album, its photo rows and their stored bytes.

    Storage cleanup runs after the commit succeeds (best-effort, outside the
    transaction) so a slow or failing object-store call never blocks the
    database delete.
    """
    album = get_owned(db, Album, album_id, user_id)
    keys = [p.object_key for p in album.photos] + [
        p.thumbnail_key for p in album.photos if p.thumbnail_key
    ]
    album.soft_delete()
    return keys


def get_album_detail(db: Session, user_id: uuid.UUID, album_id: uuid.UUID) -> dict:
    album = get_owned(db, Album, album_id, user_id)
    photos = sorted(album.photos, key=lambda p: p.position)
    payload = serialise_album(album, photos)
    payload["photos"] = [serialise_photo(p) for p in photos]
    return payload


# --- Photos ----------------------------------------------------------------


def upload_photo(
    db: Session, user_id: uuid.UUID, album_id: uuid.UUID, file: UploadFile, caption: str | None = None
) -> Photo:
    album = get_owned(db, Album, album_id, user_id)

    processed = process_upload(file, max_dimension=2560)
    key = storage.save(
        processed.data, prefix=f"users/{user_id}/albums/{album_id}", content_type=processed.mime_type
    )

    thumb = make_thumbnail(processed.data)
    thumb_key = storage.save(
        thumb.data, prefix=f"users/{user_id}/albums/{album_id}/thumbs", content_type=thumb.mime_type
    )

    position = db.execute(
        select(func.coalesce(func.max(Photo.position), -1)).where(Photo.album_id == album_id)
    ).scalar_one()

    photo = Photo(
        user_id=user_id,
        album_id=album.id,
        object_key=key,
        thumbnail_key=thumb_key,
        original_filename=(file.filename or "")[:255] or None,
        mime_type=processed.mime_type,
        size_bytes=processed.size_bytes,
        width=processed.width,
        height=processed.height,
        caption=caption,
        position=position + 1,
    )
    db.add(photo)
    db.flush()

    if album.cover_photo_id is None:
        album.cover_photo_id = photo.id

    return photo


def update_photo(db: Session, user_id: uuid.UUID, photo_id: uuid.UUID, data: dict) -> Photo:
    photo = get_owned(db, Photo, photo_id, user_id)
    for field in ("caption", "position"):
        if field in data and data[field] is not None:
            setattr(photo, field, data[field])
    return photo


def delete_photo(db: Session, user_id: uuid.UUID, photo_id: uuid.UUID) -> list[str]:
    photo = get_owned(db, Photo, photo_id, user_id)
    keys = [k for k in (photo.object_key, photo.thumbnail_key) if k]

    album = db.get(Album, photo.album_id)
    if album and album.cover_photo_id == photo.id:
        album.cover_photo_id = None

    db.delete(photo)
    return keys
