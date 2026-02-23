"""add_campaign_stash_table

Revision ID: 8094fff4c4e7
Revises: 9fb7e437a9ef
Create Date: 2026-02-21 23:24:34.724134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8094fff4c4e7'
down_revision: Union[str, None] = '9fb7e437a9ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('campaign_stash',
    sa.Column('campaign_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('campaign_id', 'item_id')
    )


def downgrade() -> None:
    op.drop_table('campaign_stash')
