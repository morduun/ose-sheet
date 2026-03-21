"""Add container_item_id to campaign_stash for container-aware stash

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'j1k2l3m4n5o6'
down_revision = 'i0j1k2l3m4n5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('campaign_stash') as batch_op:
        batch_op.add_column(sa.Column('container_item_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('campaign_stash') as batch_op:
        batch_op.drop_column('container_item_id')
