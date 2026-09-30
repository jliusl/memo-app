"""initial schema

Written by hand because no database existed when it was created. `alembic revision
--autogenerate` against a migrated database must produce an empty diff; if it does not,
this file and app/models.py have drifted apart.

Revision ID: 0001
Revises:
Create Date: 2025-09-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "memos",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "title IS NOT NULL OR btrim(body) <> ''",
            name=op.f("ck_memos_title_or_body"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_memos_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memos")),
    )
    op.create_index(op.f("ix_memos_owner_id"), "memos", ["owner_id"])
    op.create_index(op.f("ix_memos_pinned_at"), "memos", ["pinned_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_memos_pinned_at"), table_name="memos")
    op.drop_index(op.f("ix_memos_owner_id"), table_name="memos")
    op.drop_table("memos")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
