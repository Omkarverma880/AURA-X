"""Aura X API application."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.middleware.gzip import GZipMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger, request_id_ctx
from app.db.session import check_database

configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (env=%s, storage=%s, google=%s)",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.STORAGE_BACKEND,
        "enabled" if settings.google_enabled else "disabled",
    )
    if not check_database():
        # Not fatal: Railway may start the app before the database is ready,
        # and the health endpoint reports the real state either way.
        logger.error("Database is not reachable at startup")
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title="Aura X API",
    description=(
        "Personal money, investments, goals and life management. "
        "Every endpoint is scoped to the authenticated user."
    ),
    version="1.0.0",
    lifespan=lifespan,
    # Interactive docs are a development convenience, not a production surface.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(GZipMiddleware, minimum_size=1024)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
        expose_headers=["X-Request-Id"],
        max_age=600,
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach a request id, time the call and set security headers."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    request_id_ctx.set(request_id)
    started = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    if duration_ms > 1000:
        logger.warning(
            "Slow request %s %s took %.0fms", request.method, request.url.path, duration_ms
        )
    return response


# --- Error handling ----------------------------------------------------


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("%s on %s: %s", exc.code, request.url.path, exc.message)
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn Pydantic errors into field-level messages the UI can render."""
    fields = []
    for error in exc.errors():
        location = [str(part) for part in error["loc"] if part not in ("body", "query", "path")]
        fields.append({"field": ".".join(location) or "request", "message": error["msg"]})
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Please check the details you entered.",
                "details": fields,
            }
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning("Integrity error on %s: %s", request.url.path, exc.orig)
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "conflict",
                "message": "That would conflict with an existing record.",
            }
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error on %s", request.url.path)
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": "database_error",
                "message": "We could not reach the database. Please try again in a moment.",
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last line of defence: log the detail, tell the user nothing sensitive."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Something went wrong on our side. Please try again.",
            }
        },
    )


# --- Health ------------------------------------------------------------


@app.get("/health", tags=["System"])
def health() -> dict:
    """Liveness and readiness probe. Deliberately free of build or config detail."""
    connected = check_database()
    return {
        "status": "ok" if connected else "degraded",
        "database": "connected" if connected else "disconnected",
    }


app.include_router(api_router, prefix=settings.API_PREFIX)


# --- Frontend ----------------------------------------------------------

if settings.SERVE_FRONTEND and FRONTEND_DIST.is_dir():
    # Single-service deployment: FastAPI serves the built SPA, which keeps the
    # API same-origin so the auth cookies need no cross-site relaxation.
    app.mount(
        "/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets"
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        candidate = (FRONTEND_DIST / full_path).resolve()
        if (
            full_path
            and str(candidate).startswith(str(FRONTEND_DIST.resolve()))
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        # Any other path is a client-side route.
        return FileResponse(FRONTEND_DIST / "index.html")
