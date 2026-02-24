"""add_item_identification

Revision ID: a1b2c3d4e5f6
Revises: 4779e9511b76
Create Date: 2026-02-22 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4779e9511b76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('items', sa.Column('unidentified_name', sa.String(), nullable=True))
    op.add_column('character_items', sa.Column('identified', sa.Boolean(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('character_items', 'identified')
    op.drop_column('items', 'unidentified_name')
