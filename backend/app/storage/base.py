"""Object storage abstraction.

Photos must not live on the application container: Railway rebuilds the
filesystem on every deploy, so anything written there disappears. The backend
therefore talks to this interface, and the concrete backend is chosen by
configuration - local disk for development, any S3-compatible bucket for
production.
"""

from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timezone

EXTENSION_BY_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


def generate_key(prefix: str, content_type: str) -> str:
    """Build an unguessable object key.

    The uploaded filename is never reused: it is attacker-controlled and could
    contain path separators or a misleading double extension.
    """
    extension = EXTENSION_BY_MIME.get(content_type, "bin")
    stamp = datetime.now(timezone.utc).strftime("%Y/%m")
    return f"{prefix.strip('/')}/{stamp}/{secrets.token_urlsafe(18)}.{extension}"


class StorageBackend(ABC):
    """Minimal surface every storage provider must implement."""

    @abstractmethod
    def save(self, data: bytes, *, prefix: str, content_type: str) -> str:
        """Persist bytes and return the object key."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove one object. Missing objects are not an error."""

    @abstractmethod
    def delete_prefix(self, prefix: str) -> None:
        """Remove every object under a prefix."""

    @abstractmethod
    def public_url(self, key: str, *, expires_in: int = 3600) -> str:
        """A URL the browser can load.

        Implementations return a time-limited signed URL wherever the bucket is
        private, so raw storage credentials never reach the frontend.
        """

    @abstractmethod
    def read(self, key: str) -> bytes | None:
        """Fetch the bytes back, used by the local proxy endpoint."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Whether the object is present."""
