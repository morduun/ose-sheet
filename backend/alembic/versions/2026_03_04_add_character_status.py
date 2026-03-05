"""Add character status column

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('characters', sa.Column('status', sa.String(), server_default='active', nullable=False))
    op.execute("UPDATE characters SET status = 'fallen' WHERE is_alive = 0")


def downgrade():
    op.drop_column('characters', 'status')
