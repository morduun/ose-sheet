"""Add character_specialists table

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'character_specialists',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id', ondelete='CASCADE'), nullable=False),
        sa.Column('spec_type', sa.String(), nullable=False),
        sa.Column('task', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_character_specialists_character_id', 'character_specialists', ['character_id'])


def downgrade():
    op.drop_index('ix_character_specialists_character_id', table_name='character_specialists')
    op.drop_table('character_specialists')
