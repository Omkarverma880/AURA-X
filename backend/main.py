"""Process entry point.

``python main.py server`` boots uvicorn; ``python main.py migrate`` runs
Alembic to head. Kept as a thin CLI over the real app in app.main so the
Docker CMD has one obvious, scriptable place to start from - mirroring how
the sibling Quantflux service is launched.
"""

from __future__ import annotations

import os
import sys

import uvicorn

from app.core.config import settings


def run_server() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=not settings.is_production,
        log_level=settings.LOG_LEVEL.lower(),
    )


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    config = Config("alembic.ini")
    command.upgrade(config, "head")


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "server"
    if action == "server":
        run_server()
    elif action == "migrate":
        run_migrations()
    else:
        print(f"Unknown command: {action}. Use 'server' or 'migrate'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
