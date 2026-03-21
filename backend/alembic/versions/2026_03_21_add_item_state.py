"""Add state JSON column to character_items for per-character item state

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'i0j1k2l3m4n5'
down_revision = 'h9i0j1k2l3m4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('character_items') as batch_op:
        batch_op.add_column(sa.Column('state', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('character_items') as batch_op:
        batch_op.drop_column('state')
