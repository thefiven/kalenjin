"""create objectifs, plans, seances tables

Revision ID: 2c6d15192849
Revises: 06557633309f
Create Date: 2026-07-24 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2c6d15192849"
down_revision: str | Sequence[str] | None = "06557633309f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "objectifs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sport", sa.String(), nullable=False),
        sa.Column("target_distance_meters", sa.Float(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("target_time_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("objectif_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["objectif_id"], ["objectifs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plans_objectif_id"), "plans", ["objectif_id"], unique=False)
    op.create_table(
        "seances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("detail", sa.String(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("seance_type", sa.String(), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("theme", sa.String(), nullable=True),
        sa.Column("week_volume_meters", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("garmin_activity_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_seances_plan_id"), "seances", ["plan_id"], unique=False)
    op.create_index(op.f("ix_seances_week_start"), "seances", ["week_start"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_seances_week_start"), table_name="seances")
    op.drop_index(op.f("ix_seances_plan_id"), table_name="seances")
    op.drop_table("seances")
    op.drop_index(op.f("ix_plans_objectif_id"), table_name="plans")
    op.drop_table("plans")
    op.drop_table("objectifs")
