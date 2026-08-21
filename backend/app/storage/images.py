"""Upload validation and image processing.

An uploaded file is untrusted input. Nothing here believes the filename or the
declared Content-Type: the bytes are decoded by Pillow, verified to be a real
image of an allowed format, stripped of metadata by re-encoding, and only then
stored.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from fastapi import UploadFile
from PIL import Image, ImageOps

from app.core.config import settings
from app.core.errors import BadRequest

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 50_000_000  # guards against decompression-bomb images
THUMBNAIL_SIZE = (600, 600)


@dataclass
class ProcessedImage:
    data: bytes
    mime_type: str
    width: int
    height: int
    size_bytes: int


def _read_within_limit(file: UploadFile) -> bytes:
    """Read the upload, refusing anything over the configured size cap.

    Read in chunks so an oversized file is rejected without ever being fully
    buffered in memory.
    """
    limit = settings.max_upload_bytes
    buffer = bytearray()
    while True:
        chunk = file.file.read(64 * 1024)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > limit:
            raise BadRequest(
                f"That file is larger than the {settings.MAX_UPLOAD_MB} MB limit.",
                code="file_too_large",
            )
    if not buffer:
        raise BadRequest("The uploaded file is empty.")
    return bytes(buffer)


def process_upload(
    file: UploadFile, *, max_dimension: int = 2560, quality: int = 85
) -> ProcessedImage:
    """Validate and normalise an uploaded image."""
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME:
        raise BadRequest(
            "Only JPEG, PNG and WebP images can be uploaded.", code="unsupported_media_type"
        )

    raw = _read_within_limit(file)

    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()  # structural check; consumes the file object
        image = Image.open(io.BytesIO(raw))
    except Exception:
        raise BadRequest(
            "That file is not a readable image.", code="invalid_image"
        ) from None

    if image.format not in ALLOWED_PIL_FORMATS:
        raise BadRequest("Only JPEG, PNG and WebP images can be uploaded.", code="invalid_image")

    if image.width * image.height > MAX_PIXELS:
        raise BadRequest("That image is too large to process.", code="invalid_image")

    # Honour the EXIF orientation flag, then drop the rest of the EXIF block -
    # which is where GPS coordinates and device identifiers live.
    image = ImageOps.exif_transpose(image)
    image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        output_format, mime = "PNG", "image/png"
        save_kwargs: dict = {"optimize": True}
    else:
        image = image.convert("RGB")
        output_format, mime = "JPEG", "image/jpeg"
        save_kwargs = {"quality": quality, "optimize": True, "progressive": True}

    buffer = io.BytesIO()
    image.save(buffer, format=output_format, **save_kwargs)
    data = buffer.getvalue()

    return ProcessedImage(
        data=data,
        mime_type=mime,
        width=image.width,
        height=image.height,
        size_bytes=len(data),
    )


def make_thumbnail(data: bytes, quality: int = 78) -> ProcessedImage:
    """Small preview used by grid views so galleries stay fast."""
    image = Image.open(io.BytesIO(data))
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
    output = buffer.getvalue()
    return ProcessedImage(
        data=output,
        mime_type="image/jpeg",
        width=image.width,
        height=image.height,
        size_bytes=len(output),
    )
