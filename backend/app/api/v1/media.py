"""Authenticated media proxy for the local storage backend.

Production uses presigned URLs straight from the bucket. In development the
bytes are served here instead, and the ownership check still applies: every key
embeds the owner id, and a request for somebody else object is refused.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.core.deps import CurrentAuth
from app.core.errors import NotFound
from app.storage import storage

router = APIRouter(prefix="/media", tags=["Media"])

CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}


@router.get("/{key:path}")
def get_object(key: str, ctx: CurrentAuth) -> Response:
    owner_segment = str(ctx.user_id)
    if owner_segment not in key.split("/"):
        # Reported as missing rather than forbidden so the endpoint cannot be
        # used to confirm that another object exists.
        raise NotFound("That file does not exist.")

    data = storage.read(key)
    if data is None:
        raise NotFound("That file does not exist.")

    extension = key.rsplit(".", 1)[-1].lower()
    return Response(
        content=data,
        media_type=CONTENT_TYPES.get(extension, "application/octet-stream"),
        headers={
            "Cache-Control": "private, max-age=3600",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )
