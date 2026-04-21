"""Add secondary_skill to characters.

Revision ID: 9345907eee25
Revises: 0eaeab19cc12
Create Date: 2026-04-06

"""
from alembic import op
import sqlalchemy as sa

revision = "9345907eee25"
down_revision = "0eaeab19cc12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("secondary_skill", sa.String, nullable=True))


def downgrade() -> None:
    op.drop_column("characters", "secondary_skill")
