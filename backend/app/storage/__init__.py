"""Storage backend selection."""

from __future__ import annotations

from app.core.config import settings
from app.storage.base import StorageBackend


def _build_backend() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        from app.storage.s3 import S3Storage

        return S3Storage()

    from app.storage.local import LocalStorage

    return LocalStorage()


#: Process-wide storage backend. Import this, never a concrete class, so that
#: swapping providers is a configuration change rather than a code change.
storage: StorageBackend = _build_backend()

__all__ = ["storage", "StorageBackend"]
