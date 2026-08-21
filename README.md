# Aura X

**Your Money. Your Wealth. Your Goals. Your Life.**

A multi-tenant personal finance and life-management platform: lending/borrowing
(Bahi Khata), expenses & salary, investments with XIRR and a goal planner,
life goals, custom trackers (temples, treks, books, ...), and photo memories —
all behind a Green PIN that keeps confidential figures hidden until you choose
to reveal them. A public landing page (`/`) introduces the product with a
3D animated hero (`frontend/src/pages/Landing.tsx`, react-three-fiber) before
handing off to sign-in/sign-up.

Built with FastAPI + PostgreSQL on the backend and React + TypeScript + Vite +
Tailwind on the frontend.

---

## Contents

- [Architecture](#architecture)
- [Local setup](#local-setup)
- [PostgreSQL & pgAdmin](#postgresql--pgadmin)
- [Database migrations](#database-migrations)
- [Seed / demo data](#seed--demo-data)
- [Authentication setup](#authentication-setup)
- [Green PIN](#green-pin)
- [Object storage (photos)](#object-storage-photos)
- [Testing](#testing)
- [Railway deployment](#railway-deployment)
- [Security notes](#security-notes)
- [Project structure](#project-structure)

---

## Architecture

```
┌─────────────────────────┐        ┌──────────────────────────┐
│   React SPA (Vite)      │  same  │   FastAPI (uvicorn)       │
│   TanStack Query        │ origin │   SQLAlchemy 2.x          │
│   Tailwind v4            │──────▶│   Alembic migrations      │
│   react-hook-form + zod │  /api  │   Argon2id / JWT sessions │
└─────────────────────────┘        └────────────┬─────────────┘
                                                  │
                                     ┌────────────▼─────────────┐
                                     │  PostgreSQL (production)  │
                                     │  or SQLite (tests only)   │
                                     └────────────────────────────┘
```

In production the backend serves the built frontend directly
(`SERVE_FRONTEND=true`) so the browser only ever talks to one origin — that's
what lets auth cookies stay `SameSite=Lax` without any cross-site relaxation.
In local development, Vite's dev server proxies `/api` to the backend instead
(see `frontend/vite.config.ts`), so the same cookie behaviour holds there too.

Every user-owned table carries a `user_id` foreign key, and every query in
`app/services/*.py` goes through `app/services/ownership.py`, which injects
that filter centrally — there is no code path in the app that queries a
user-owned table without it. A row belonging to another user comes back as
`404`, never `403`, so an ID-guessing probe can't even confirm the row exists.

Money is `NUMERIC(18,2)` end to end — never a float — and Bahi Khata /
investment balances are always *derived* by summing immutable transactions,
not stored as a mutable balance column that could drift out of sync.

---

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 22+
- PostgreSQL 15+ (or Docker, to run one locally)

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements-dev.txt

cp ../.env.example .env
# edit .env: at minimum set DATABASE_URL and SECRET_KEY

alembic upgrade head
python -m app.db.seed          # optional: creates a demo account

python main.py server          # http://localhost:8000
# Swagger UI (dev only): http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:8000` (see
`vite.config.ts`), so open `http://localhost:5173` and everything just works
against your local backend.

### Running the whole thing with SQLite (no Postgres install)

Not recommended beyond a quick spin, but works for a first look:

```bash
# backend/.env
DATABASE_URL=sqlite+pysqlite:///./dev.sqlite3
```

`alembic upgrade head` and the seed script both work unchanged — the schema
is described with portable SQLAlchemy types (`app/db/types.py`) that render
correctly on both engines. SQLite is genuinely fine for this; the one thing
to know is that the engine hands each request thread its own connection
rather than sharing one, specifically so concurrent browser requests don't
corrupt a shared SQLite connection (see `app/db/session.py`).

---

## PostgreSQL & pgAdmin

1. Create a database and user:

   ```sql
   CREATE DATABASE aurax;
   CREATE USER aurax WITH PASSWORD 'change-me';
   GRANT ALL PRIVILEGES ON DATABASE aurax TO aurax;
   ```

2. Set `DATABASE_URL` in `backend/.env`:

   ```
   DATABASE_URL=postgresql+psycopg://aurax:change-me@localhost:5432/aurax
   ```

3. In pgAdmin, register a new server pointing at the same host/port/database.
   Once `alembic upgrade head` has run, every table described in
   [Project structure](#project-structure) is visible under
   `aurax → Schemas → public → Tables`.

---

## Database migrations

Alembic is wired to read `DATABASE_URL` from application settings
(`alembic/env.py`), so there's one source of truth for dev, tests, and
Railway alike — nothing to keep in sync in `alembic.ini`.

```bash
cd backend
alembic upgrade head                          # apply all migrations
alembic downgrade -1                          # roll back one
alembic revision --autogenerate -m "message"  # generate a new migration after changing a model
alembic current                               # what's applied right now
```

After autogenerating, **read the generated file** before committing it —
autogenerate is a good first draft, not a guarantee, particularly around
renames (which it sees as a drop + add) and data migrations (which it never
writes for you).

---

## Seed / demo data

```bash
cd backend
python -m app.db.seed            # creates demo@aurax.app if it doesn't exist
python -m app.db.seed --reset    # deletes and recreates it
```

The script prints the generated password and the Green PIN (`2468`) to the
console — nothing is hard-coded, and nothing resembling a real credential
ships in the repository. The seeded account gets:

- 3 Bahi Khata people (Parbhu, Rahul, Narayan Dai) with a mix of active,
  partially settled and fully settled entries
- 4 months of income + a week of sample expenses across categories, plus
  budgets for the current month
- 3 investment holdings (a mutual fund, a gold bond, a fixed deposit) and one
  investment goal
- A "12 Jyotirlingas" and a "Himalayan Treks" tracker, a life goal with
  milestones, and two memory albums

## Authentication setup

Three sign-in methods ship, and all three can be enabled at once:

### Email + password (always on)

No configuration needed. Passwords are hashed with Argon2id
(`app/security/hashing.py`); registration sends a verification e-mail (or, if
SMTP isn't configured, logs the link instead — see below).

### Google sign-in

1. Create an OAuth 2.0 Client ID at
   [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials).
2. Authorised redirect URI: `{your backend URL}/api/v1/auth/google/callback`
   (e.g. `http://localhost:8000/api/v1/auth/google/callback` locally).
3. Set in `.env`:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
   ```
4. The frontend automatically shows the Google button once
   `GET /api/v1/auth/providers` reports it enabled — nothing else to wire up.

### Phone number (OTP) sign-in

A user links a verified phone number from **Settings → Account**, then can
sign in with it afterwards (an unlinked number can't be used to sign in or to
create an account — that's deliberate, to stop throwaway-SIM signups from
skipping e-mail verification entirely).

SMS delivery is provider-agnostic: point `SMS_WEBHOOK_URL` at any gateway (or
a small relay in front of one) that accepts a `{to, message}` JSON POST. With
no webhook configured, the OTP is logged server-side **and** returned in the
API response as `debug_code` — but only when `APP_ENV != production`, so this
never leaks in a real deployment.

### Password reset / Green PIN reset (e-mail)

Set `SMTP_HOST` (+ `SMTP_USER`/`SMTP_PASSWORD` if required) to send real
e-mail. Without it, reset/verification links are written to the backend log
instead — convenient for local development, never used in production.

---

## Green PIN

The Green PIN is a **second, separate secret** from the login password — a
4-digit code that unlocks confidential figures (salary, expenses, investment
values) for 5 minutes at a time, so glancing at someone's screen doesn't hand
over their salary.

- Set up from **Settings → Security**. Hashed with Argon2id
  (`app/services/green_pin.py`), never stored or logged in plaintext.
- 5 wrong attempts locks it out with an exponentially increasing cooldown
  (5 min → 10 min → 20 min → ... capped at 1 hour).
- A forgotten PIN is reset only through a single-use e-mail link
  (`Settings → Security → Forgot your PIN?`) — the frontend can never simply
  post a replacement PIN.
- **The server is the real gate.** Endpoints serving confidential data
  (`app/api/v1/income.py`, `investments.py`, `budgets.py`, `export.py`) depend
  on `UnlockedAuth` and return `423 Locked` outright while locked; the
  dashboard/analytics endpoints instead null out the sensitive fields. The
  frontend's masked `••••••` display (`CurrencyDisplay`) is presentation
  only — a modified frontend gains nothing, because the numbers were never
  sent.
- A user who never sets up a Green PIN is not gated — protection is opt-in,
  not a lock the app starts in and traps them behind.

---

## Object storage (photos)

Railway's container filesystem is rebuilt on every deploy, so photo bytes
never live on local disk in production.

- **Local development** (default): `STORAGE_BACKEND=local` writes to
  `backend/media/` and serves files back through an authenticated proxy
  (`GET /api/v1/media/{key}`) rather than a static mount, so the same
  ownership check applies to a photo as to any other resource.
- **Production**: set `STORAGE_BACKEND=s3` plus `STORAGE_ENDPOINT`,
  `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`. Works with AWS
  S3 or any S3-compatible provider (Cloudflare R2, Backblaze B2, MinIO, ...).
  Uploads are validated and re-encoded server-side before storage
  (`app/storage/images.py`) — the raw uploaded bytes are never trusted or
  stored as-is, and EXIF metadata (including GPS) is stripped.

---

## Testing

```bash
cd backend
pytest                  # 102 tests: auth, ledger, expenses, investments,
                         # life/checklists/memories, dashboard/analytics,
                         # phone auth
pytest -q --no-header   # quieter output
```

The suite runs on a temp-file SQLite database (`tests/conftest.py`) rather
than Postgres, using the same portable column types the app ships with — the
code under test is identical to what runs in production. Every module
includes an explicit **cross-user isolation test**: a second user attempting
to read, edit or delete another user's row must get `404`, never their data.

Frontend:

```bash
cd frontend
npm run typecheck       # tsc -b --noEmit
npm run build            # full production build
```

---

## Railway deployment

1. Push this repo to GitHub and create a new Railway project from it.
2. Add a **PostgreSQL** plugin to the project — Railway injects `DATABASE_URL`
   automatically; `app/core/config.py` normalises the `postgres://` scheme
   Railway hands out into the `postgresql+psycopg://` driver SQLAlchemy 2
   needs, so no manual edit is required.
3. Railway detects `railway.toml` at the repo root and builds the Dockerfile
   there — one service serves both the API and the built frontend.
4. Set the remaining environment variables from `.env.example` on the
   service (`SECRET_KEY`, `COOKIE_SECURE=true`, `CORS_ORIGINS` if you split
   frontend/backend into separate services, Google/SMTP/SMS credentials if
   you want those features live, `STORAGE_*` for photo uploads).
5. On deploy, the container runs `python main.py migrate` before
   `python main.py server` (see the Dockerfile `CMD`) — migrations always
   apply before the new code starts serving traffic, and a failed migration
   fails the deploy instead of booting against a stale schema.
6. Railway's health check hits `/health` (configured in `railway.toml`),
   which reports `{"status": "ok", "database": "connected"}` without leaking
   any internal detail.

Set `COOKIE_SECURE=true` and `APP_ENV=production` in production — this also
turns off `/docs`/`/redoc`/`/openapi.json` and disables the phone-OTP
`debug_code` field.

---

## Security notes

- **Passwords & PINs**: Argon2id, tuned parameters in `app/security/hashing.py`.
  A wrong login and an unknown e-mail return the identical error with a dummy
  hash verified either way, so response timing can't be used to enumerate
  accounts (`app/services/auth.py::authenticate`).
- **Sessions**: opaque refresh tokens, only their SHA-256 hash persisted,
  rotated on every refresh. Revoking a session (or "sign out everywhere")
  takes effect immediately even though the short-lived access JWT is still
  technically unexpired, because the session row backing it is checked on
  every request.
- **CSRF**: double-submit token, checked on every state-changing
  cookie-authenticated request (`app/core/deps.py`).
- **Rate limiting**: login, registration, password reset, Green PIN and OTP
  endpoints are throttled (`app/core/rate_limit.py`).
- **File uploads**: validated by decoding actual image bytes (not filename or
  declared Content-Type), capped in size, re-encoded server-side, EXIF
  stripped, stored under a random key that never derives from user input.
- **Audit trail**: every security-relevant and financial action is recorded
  (`app/services/audit.py`) — logins, password/PIN changes, ledger entries,
  repayments — with payloads redacted of anything sensitive before storage.
- **No secrets in the repo.** `.env` is git-ignored; `.env.example` documents
  every variable with no real values.

---

## Project structure

```
backend/
  app/
    api/v1/          # one router module per feature area
    core/             # config, error types, auth deps, rate limiting
    db/               # engine/session, portable column types
    models/           # SQLAlchemy models (27 tables)
    schemas/          # Pydantic request/response schemas
    services/         # business logic - the layer with the real rules
    security/         # hashing, JWT/token helpers
    storage/          # local-disk / S3 backends + upload validation
  alembic/versions/    # migrations
  tests/               # pytest suite, one file per feature area

frontend/
  src/
    api / hooks/       # TanStack Query hooks, one file per module
    components/
      ui/              # design-system primitives (Button, Card, Dialog, ...)
      shared/           # CurrencyDisplay, GreenPinModal, StatCard, ...
      layout/           # Sidebar, BottomNav, Header, AppShell
    contexts/           # Auth, Financial (Green PIN), Theme, Toast
    pages/               # one folder per module, route-lazy-loaded
```
