"""initial satellite table

Revision ID: 001_initial
Revises:
Create Date: 2026-07-16 06:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "satellites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("tle_line1", sa.String(), nullable=False),
        sa.Column("tle_line2", sa.String(), nullable=False),
        sa.Column("epoch", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_satellites_name"), "satellites", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_satellites_name"), table_name="satellites")
    op.drop_table("satellites")
