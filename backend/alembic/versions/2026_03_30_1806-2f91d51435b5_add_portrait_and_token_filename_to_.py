"""Add portrait and token filename to characters

Revision ID: 2f91d51435b5
Revises: o6p7q8r9s0t1
Create Date: 2026-03-30 18:06:38.057027

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f91d51435b5'
down_revision: Union[str, None] = 'o6p7q8r9s0t1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('characters', sa.Column('portrait_filename', sa.String(), nullable=True))
    op.add_column('characters', sa.Column('token_filename', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('characters', 'token_filename')
    op.drop_column('characters', 'portrait_filename')
