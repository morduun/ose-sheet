"""Add retainer fields to characters table

Revision ID: b3f1a2c4d5e6
Revises: a97ea001cf27
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'b3f1a2c4d5e6'
down_revision = 'a97ea001cf27'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite cannot ALTER to add FK constraints; the self-referential FK
    # (characters.master_id -> characters.id) is enforced by the ORM and
    # CASCADE is handled by SQLAlchemy's relationship cascade setting.
    op.add_column('characters', sa.Column('master_id', sa.Integer(), nullable=True))
    op.add_column('characters', sa.Column('character_type', sa.String(), server_default='pc', nullable=False))
    op.add_column('characters', sa.Column('loyalty', sa.Integer(), nullable=True))
    op.create_index('ix_characters_master_id', 'characters', ['master_id'])
    op.create_index('ix_characters_character_type', 'characters', ['character_type'])


def downgrade():
    op.drop_index('ix_characters_character_type', table_name='characters')
    op.drop_index('ix_characters_master_id', table_name='characters')
    op.drop_column('characters', 'loyalty')
    op.drop_column('characters', 'character_type')
    op.drop_column('characters', 'master_id')
