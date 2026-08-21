"""Process entry point.

``python main.py server`` boots uvicorn; ``python main.py migrate`` runs
Alembic to head; ``python main.py check-otp [number]`` diagnoses WhatsApp/SMS
delivery. Kept as a thin CLI over the real app in app.main so the Docker CMD
has one obvious, scriptable place to start from - mirroring how the sibling
Quantflux service is launched.
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


def run_otp_check() -> int:
    """Report on OTP delivery config, optionally sending a live test code.

    Deliberately part of this CLI rather than a loose script: it ships inside
    the container, so it can be run in Railway's shell against the exact
    environment the API sees instead of a local guess at it.
    """
    from app.services import otp_doctor

    return otp_doctor.report(sys.argv[2] if len(sys.argv) > 2 else None)


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "server"
    if action == "server":
        run_server()
    elif action == "migrate":
        run_migrations()
    elif action in ("check-otp", "check_otp"):
        sys.exit(run_otp_check())
    elif action in ("check-email", "check_email"):
        from app.services import otp_doctor

        sys.exit(otp_doctor.report_email(sys.argv[2] if len(sys.argv) > 2 else None))
    else:
        print(
            f"Unknown command: {action}. "
            "Use 'server', 'migrate', 'check-otp [phone]' "
            "or 'check-email [address]'."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
