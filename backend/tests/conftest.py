"""Test fixtures.

The suite runs against SQLite so it needs no server, while the application code
under test is the same code that runs on PostgreSQL: the portable column types
in app.db.types render natively on both.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import suppress
from collections.abc import Generator
from pathlib import Path

import pytest

# Configure the environment before any application module is imported, since
# settings are read once at import time.
_TMP_DB = Path(tempfile.gettempdir()) / "bahikhata_test.sqlite3"
_TMP_DB.unlink(missing_ok=True)
os.environ.update(
    {
        "APP_ENV": "test",
        "DEBUG": "false",
        "DATABASE_URL": f"sqlite+pysqlite:///{_TMP_DB.as_posix()}",
        "SECRET_KEY": "test-secret-key-not-used-anywhere-else-0123456789",
        "RATE_LIMIT_ENABLED": "false",
        "COOKIE_SECURE": "false",
        "STORAGE_BACKEND": "local",
        "STORAGE_LOCAL_DIR": str(Path(tempfile.gettempdir()) / "bahikhata_media"),
        "SMTP_HOST": "",
        "CORS_ORIGINS": "http://localhost:5173",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.rate_limit import rate_limiter  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Generator[None, None, None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    # Windows keeps the file locked until every pooled connection is closed.
    engine.dispose()
    with suppress(OSError):
        _TMP_DB.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def _clean_tables() -> Generator[None, None, None]:
    """Start every test from an empty database."""
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    rate_limiter.clear()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


class ApiUser:
    """A registered user with a signed-in client.

    Wraps the TestClient so every mutating call carries the CSRF header the
    real frontend sends.
    """

    def __init__(self, client: TestClient, email: str, password: str, name: str) -> None:
        self.client = client
        self.email = email
        self.password = password
        self.name = name
        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": name},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        self.id = body["user"]["id"]
        self.csrf = body["csrf_token"]
        self.cookies = dict(client.cookies)

    def _headers(self, extra: dict | None = None) -> dict:
        headers = {"X-CSRF-Token": self.csrf}
        headers.update(extra or {})
        return headers

    def use(self) -> None:
        """Make this user the active identity on the shared client."""
        self.client.cookies.clear()
        for key, value in self.cookies.items():
            self.client.cookies.set(key, value)

    def get(self, url: str, **kwargs):
        self.use()
        return self.client.get(url, headers=self._headers(kwargs.pop("headers", None)), **kwargs)

    def post(self, url: str, **kwargs):
        self.use()
        return self.client.post(url, headers=self._headers(kwargs.pop("headers", None)), **kwargs)

    def patch(self, url: str, **kwargs):
        self.use()
        return self.client.patch(url, headers=self._headers(kwargs.pop("headers", None)), **kwargs)

    def put(self, url: str, **kwargs):
        self.use()
        return self.client.put(url, headers=self._headers(kwargs.pop("headers", None)), **kwargs)

    def delete(self, url: str, **kwargs):
        self.use()
        return self.client.delete(url, headers=self._headers(kwargs.pop("headers", None)), **kwargs)

    def set_pin(self, pin: str = "8317") -> None:
        response = self.post("/api/v1/security/green-pin", json={"new_pin": pin})
        assert response.status_code == 200, response.text

    def unlock(self, pin: str = "8317") -> None:
        response = self.post("/api/v1/security/financial/unlock", json={"pin": pin})
        assert response.status_code == 200, response.text


@pytest.fixture
def alice(client: TestClient) -> ApiUser:
    return ApiUser(client, "alice@example.com", "Alice-Pass-123", "Alice Sharma")


@pytest.fixture
def bob(client: TestClient) -> ApiUser:
    return ApiUser(client, "bob@example.com", "Bob-Pass-123", "Bob Verma")
