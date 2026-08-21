"""Local-disk storage for development.

Not suitable for production on Railway, where the container filesystem is
recreated on every deploy. Files are served back through an authenticated proxy
endpoint rather than a static mount, so one user cannot read another photo by
guessing a path.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.base import StorageBackend, generate_key

logger = get_logger(__name__)


class LocalStorage(StorageBackend):
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.STORAGE_LOCAL_DIR).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        """Resolve a key inside the media root, refusing traversal."""
        candidate = (self.root / key).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise ValueError("Invalid object key.")
        return candidate

    def save(self, data: bytes, *, prefix: str, content_type: str) -> str:
        key = generate_key(prefix, content_type)
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except (ValueError, OSError) as exc:
            logger.warning("Could not delete object %s: %s", key, exc)

    def delete_prefix(self, prefix: str) -> None:
        try:
            target = self._path(prefix)
        except ValueError:
            return
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)

    def public_url(self, key: str, *, expires_in: int = 3600) -> str:
        # Routed through the API so the ownership check still applies.
        return f"{settings.API_PREFIX}/media/{key}"

    def read(self, key: str) -> bytes | None:
        try:
            path = self._path(key)
        except ValueError:
            return None
        return path.read_bytes() if path.is_file() else None

    def exists(self, key: str) -> bool:
        try:
            return self._path(key).is_file()
        except ValueError:
            return False
