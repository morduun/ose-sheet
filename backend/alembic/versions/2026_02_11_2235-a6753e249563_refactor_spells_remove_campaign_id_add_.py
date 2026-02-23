"""refactor_spells_remove_campaign_id_add_aoe_save_reversed

Revision ID: a6753e249563
Revises: 495d5a9b4f85
Create Date: 2026-02-11 22:35:37.837681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6753e249563'
down_revision: Union[str, None] = '495d5a9b4f85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # aoe/save/reversed were added to the spells table in a prior partial run.
    # Only need to drop the two obsolete columns.
    with op.batch_alter_table('spells', recreate='always') as batch_op:
        batch_op.drop_column('reversible')
        batch_op.drop_column('campaign_id')


def downgrade() -> None:
    with op.batch_alter_table('spells', recreate='always') as batch_op:
        batch_op.drop_column('reversed')
        batch_op.drop_column('save')
        batch_op.drop_column('aoe')

    op.add_column('spells', sa.Column('campaign_id', sa.INTEGER(), nullable=True))
    op.add_column('spells', sa.Column('reversible', sa.BOOLEAN(), nullable=True))
