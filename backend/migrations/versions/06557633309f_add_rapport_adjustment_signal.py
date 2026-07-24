"""add rapport adjustment signal columns

Revision ID: 06557633309f
Revises: f24ae4a9a0c1
Create Date: 2026-07-24 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "06557633309f"
down_revision: str | Sequence[str] | None = "f24ae4a9a0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rapports",
        sa.Column("completed_as_planned", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "rapports",
        sa.Column("perceived_effort", sa.String(), nullable=False, server_default="as_expected"),
    )
    op.add_column(
        "rapports",
        sa.Column("flag", sa.String(), nullable=False, server_default="none"),
    )
    op.alter_column("rapports", "completed_as_planned", server_default=None)
    op.alter_column("rapports", "perceived_effort", server_default=None)
    op.alter_column("rapports", "flag", server_default=None)


def downgrade() -> None:
    op.drop_column("rapports", "flag")
    op.drop_column("rapports", "perceived_effort")
    op.drop_column("rapports", "completed_as_planned")
