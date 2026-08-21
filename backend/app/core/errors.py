"""Consistent, human-readable API errors.

Every failure the frontend can encounter is an AppError carrying a stable
machine-readable code plus a message that is safe to show to a user. Stack
traces are never returned to the client.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code: int = 400
    code: str = "bad_request"
    message: str = "Something went wrong."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            body["details"] = self.details
        return {"error": body}


class BadRequest(AppError):
    status_code, code, message = 400, "bad_request", "The request could not be processed."


class Unauthorized(AppError):
    status_code, code, message = 401, "unauthorized", "Session expired. Please login again."


class Forbidden(AppError):
    status_code, code, message = 403, "forbidden", "Insufficient permission."


class NotFound(AppError):
    status_code, code, message = 404, "not_found", "The requested item does not exist."


class Conflict(AppError):
    status_code, code, message = 409, "conflict", "That item already exists."


class ValidationFailed(AppError):
    status_code, code, message = 422, "validation_error", "Please check the details you entered."


class RateLimited(AppError):
    status_code, code, message = 429, "rate_limited", "Too many attempts. Please try again later."


class ServiceUnavailable(AppError):
    """A dependency the request needs - an SMS/WhatsApp gateway, say - is
    unconfigured or refused the call. Reported honestly rather than as a
    success the user then waits on forever."""

    status_code, code, message = (
        503,
        "service_unavailable",
        "That service is temporarily unavailable. Please try again shortly.",
    )


class FinancialLocked(AppError):
    """Raised when a Green-PIN protected resource is read while locked."""

    status_code, code, message = (
        423,
        "financial_locked",
        "Financial data is locked. Enter your Green PIN to unlock.",
    )


class InvalidGreenPin(AppError):
    status_code, code, message = 400, "invalid_green_pin", "Invalid Green PIN."
