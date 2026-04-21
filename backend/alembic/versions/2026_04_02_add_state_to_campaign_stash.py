"""Add state column to campaign_stash for per-instance treasure metadata.

Revision ID: bee4dd7dc23f
Revises: 03ed3f729bfd
Create Date: 2026-04-02

"""
from alembic import op
import sqlalchemy as sa

revision = "bee4dd7dc23f"
down_revision = "03ed3f729bfd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaign_stash", sa.Column("state", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("campaign_stash", "state")
