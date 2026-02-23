"""add_item_secrets_column

Revision ID: 4779e9511b76
Revises: 8094fff4c4e7
Create Date: 2026-02-22 19:51:02.084580

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4779e9511b76'
down_revision: Union[str, None] = '8094fff4c4e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('items', sa.Column('secrets', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('items', 'secrets')
