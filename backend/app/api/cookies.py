"""Auth cookie handling.

Access and refresh tokens live in HttpOnly cookies so that no JavaScript on the
page - including anything injected through an XSS hole - can read them. The
CSRF token is deliberately readable, because the frontend has to echo it back
in a header.
"""

from __future__ import annotations

from fastapi import Response

from app.core.config import settings


def _base_kwargs() -> dict:
    kwargs: dict = {
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
    }
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    return kwargs


def set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str, csrf_token: str
) -> None:
    response.set_cookie(
        settings.ACCESS_COOKIE_NAME,
        access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_TTL_MINUTES * 60,
        **_base_kwargs(),
    )
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 24 * 3600,
        **_base_kwargs(),
    )
    # Readable by the frontend on purpose: it is echoed in the X-CSRF-Token
    # header, which is exactly what a cross-site attacker cannot do.
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf_token,
        httponly=False,
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 24 * 3600,
        **_base_kwargs(),
    )


def clear_auth_cookies(response: Response) -> None:
    kwargs = _base_kwargs()
    kwargs.pop("secure", None)
    kwargs.pop("samesite", None)
    for name in (
        settings.ACCESS_COOKIE_NAME,
        settings.REFRESH_COOKIE_NAME,
        settings.CSRF_COOKIE_NAME,
    ):
        response.delete_cookie(name, **kwargs)
