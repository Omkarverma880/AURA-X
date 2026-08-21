# syntax=docker/dockerfile:1
#
# Single-service image: FastAPI serves both the API and the built React SPA.
# Keeping frontend and backend same-origin means the auth cookies need no
# cross-site relaxation (SameSite=Lax just works), which is why Railway gets
# one service instead of two here.

# ── Stage 1: build the frontend ─────────────────────────────────────────
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: backend runtime ─────────────────────────────────────────────
FROM python:3.12-slim AS backend

# psycopg[binary] ships its own libpq, so no postgres client headers are
# needed at runtime - only the minimal build toolchain some wheels fall back
# to when no prebuilt wheel matches this platform.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVE_FRONTEND=true \
    APP_ENV=production

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:${PORT:-8000}/health || exit 1

# Run migrations, then start the server. A failed migration must fail the
# deploy rather than boot an app pointed at a stale schema.
CMD ["sh", "-c", "python main.py migrate && python main.py server"]
