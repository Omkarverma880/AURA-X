"""add username handle to users

Adds an optional, unique, lower-cased handle and backfills one for every
existing account from the first word of their name, so nobody is left without
a way to identify themselves during password recovery.

Revision ID: c2f7a91b34de
Revises: ba1403950ae7
Create Date: 2026-08-21 16:05:00.000000
"""
from __future__ import annotations

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2f7a91b34de"
down_revision: Union[str, None] = "ba1403950ae7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slug(value: str) -> str:
    """First word of a name, stripped to a-z0-9."""
    first = (value or "").strip().split(" ")[0].lower()
    cleaned = re.sub(r"[^a-z0-9]", "", first)
    return cleaned[:24] or "user"


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=32), nullable=True))

    # Backfill before the unique index exists, resolving collisions with a
    # numeric suffix - "omkar", "omkar2", "omkar3" - in a stable order so a
    # re-run of the migration on a copy produces the same result.
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, full_name FROM users ORDER BY created_at, id")
    ).fetchall()

    taken: set[str] = set()
    for row in rows:
        base = _slug(row.full_name)
        candidate = base
        suffix = 2
        while candidate in taken:
            candidate = f"{base}{suffix}"
            suffix += 1
        taken.add(candidate)
        connection.execute(
            sa.text("UPDATE users SET username = :username WHERE id = :id"),
            {"username": candidate, "id": row.id},
        )

    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
