"""Add character_mercenaries table

Revision ID: c4d5e6f7a8b9
Revises: b3f1a2c4d5e6
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'c4d5e6f7a8b9'
down_revision = 'b3f1a2c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'character_mercenaries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id', ondelete='CASCADE'), nullable=False),
        sa.Column('merc_type', sa.String(), nullable=False),
        sa.Column('race', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('wartime', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_character_mercenaries_character_id', 'character_mercenaries', ['character_id'])


def downgrade():
    op.drop_index('ix_character_mercenaries_character_id', table_name='character_mercenaries')
    op.drop_table('character_mercenaries')
