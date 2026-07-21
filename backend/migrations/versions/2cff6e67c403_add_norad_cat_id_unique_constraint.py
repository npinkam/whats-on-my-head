"""add norad_cat_id unique constraint

Revision ID: 2cff6e67c403
Revises: 001_initial
Create Date: 2026-07-21 00:10:16.280199

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2cff6e67c403"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("satellites", sa.Column("norad_cat_id", sa.Integer(), nullable=False))
    op.drop_constraint("satellites_name_key", "satellites", type_="unique")
    op.drop_index(op.f("ix_satellites_name"), table_name="satellites")
    op.create_index(op.f("ix_satellites_norad_cat_id"), "satellites", ["norad_cat_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_satellites_norad_cat_id"), table_name="satellites")
    op.create_index(op.f("ix_satellites_name"), "satellites", ["name"], unique=True)
    op.create_unique_constraint("satellites_name_key", "satellites", ["name"])
    op.drop_column("satellites", "norad_cat_id")
