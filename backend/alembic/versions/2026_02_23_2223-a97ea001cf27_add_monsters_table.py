"""Add monsters table

Revision ID: a97ea001cf27
Revises: a1b2c3d4e5f6
Create Date: 2026-02-23 22:23:08.348024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a97ea001cf27'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'monsters',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('campaign_id', sa.Integer(), sa.ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('ac', sa.Integer(), nullable=True),
        sa.Column('hit_dice', sa.String(), nullable=True),
        sa.Column('hp', sa.Integer(), nullable=True),
        sa.Column('thac0', sa.Integer(), nullable=True),
        sa.Column('movement_rate', sa.String(), nullable=True),
        sa.Column('morale', sa.Integer(), nullable=True),
        sa.Column('alignment', sa.String(), nullable=True),
        sa.Column('xp', sa.Integer(), nullable=True),
        sa.Column('monster_metadata', sa.JSON(), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='0', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_monsters_id', 'monsters', ['id'])
    op.create_index('ix_monsters_name', 'monsters', ['name'])
    op.create_index('ix_monsters_is_default', 'monsters', ['is_default'])


def downgrade() -> None:
    op.drop_index('ix_monsters_is_default', table_name='monsters')
    op.drop_index('ix_monsters_name', table_name='monsters')
    op.drop_index('ix_monsters_id', table_name='monsters')
    op.drop_table('monsters')
