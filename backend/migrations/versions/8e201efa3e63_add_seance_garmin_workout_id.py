"""add seance garmin_workout_id

Revision ID: 8e201efa3e63
Revises: 2c6d15192849
Create Date: 2026-07-24 16:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8e201efa3e63"
down_revision: str | Sequence[str] | None = "2c6d15192849"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("seances", sa.Column("garmin_workout_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("seances", "garmin_workout_id")
