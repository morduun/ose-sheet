"""add_weight_cost_equippable_to_items

Revision ID: 7b3882b43b71
Revises: 67a6b6276b35
Create Date: 2026-02-17 19:17:34.860006

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import json


# revision identifiers, used by Alembic.
revision: str = '7b3882b43b71'
down_revision: Union[str, None] = '67a6b6276b35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns
    op.add_column('items', sa.Column('weight', sa.Float(), nullable=True))
    op.add_column('items', sa.Column('cost_gp', sa.Float(), nullable=True))
    op.add_column('items', sa.Column('equippable', sa.Boolean(), nullable=True))

    # Backfill weight and cost_gp from item_metadata JSON
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, item_metadata, item_type FROM items")).fetchall()
    for row in rows:
        item_id, meta_raw, item_type = row
        if meta_raw:
            meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
            weight = meta.get("weight")
            cost_gp = meta.get("cost_gp")
            # Weapons and armor are equippable
            equippable = item_type in ("weapon", "armor")
            conn.execute(
                sa.text("UPDATE items SET weight = :w, cost_gp = :c, equippable = :e WHERE id = :id"),
                {"w": weight, "c": cost_gp, "e": equippable, "id": item_id},
            )

    # Remap item_type 'equipment' → 'tool'
    conn.execute(sa.text("UPDATE items SET item_type = 'tool' WHERE item_type = 'equipment'"))

    # Set default for equippable on any remaining NULLs
    conn.execute(sa.text("UPDATE items SET equippable = 0 WHERE equippable IS NULL"))


def downgrade() -> None:
    # Remap item_type 'tool' → 'equipment'
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE items SET item_type = 'equipment' WHERE item_type = 'tool'"))

    op.drop_column('items', 'equippable')
    op.drop_column('items', 'cost_gp')
    op.drop_column('items', 'weight')
