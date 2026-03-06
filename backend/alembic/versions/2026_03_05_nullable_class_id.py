"""Make character_class_id nullable for monster retainers

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'f7a8b9c0d1e2'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite doesn't support ALTER COLUMN, so use batch mode
    with op.batch_alter_table("characters") as batch_op:
        batch_op.alter_column(
            "character_class_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("characters") as batch_op:
        batch_op.alter_column(
            "character_class_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
