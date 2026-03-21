"""Add container_item_id and dropped columns to character_items

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'h9i0j1k2l3m4'
down_revision = 'g8h9i0j1k2l3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('character_items') as batch_op:
        batch_op.add_column(sa.Column(
            'container_item_id', sa.Integer(), nullable=True,
        ))
        batch_op.add_column(sa.Column(
            'dropped', sa.Boolean(), server_default='0', nullable=False,
        ))


def downgrade() -> None:
    with op.batch_alter_table('character_items') as batch_op:
        batch_op.drop_column('dropped')
        batch_op.drop_column('container_item_id')
