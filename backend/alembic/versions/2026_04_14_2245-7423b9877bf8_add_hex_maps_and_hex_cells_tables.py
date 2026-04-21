"""Add hex_maps and hex_cells tables

Revision ID: 7423b9877bf8
Revises: 4b578e812d3b
Create Date: 2026-04-14 22:45:50.331205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7423b9877bf8'
down_revision: Union[str, None] = '4b578e812d3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hex_maps",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("width", sa.Integer, nullable=False),
        sa.Column("height", sa.Integer, nullable=False),
        sa.Column("hex_size_miles", sa.Integer, nullable=False, server_default="6"),
        sa.Column("party_col", sa.Integer, nullable=True),
        sa.Column("party_row", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hex_maps_id", "hex_maps", ["id"])

    op.create_table(
        "hex_cells",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("hex_map_id", sa.Integer, sa.ForeignKey("hex_maps.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("col", sa.Integer, nullable=False),
        sa.Column("row", sa.Integer, nullable=False),
        sa.Column("terrain_type", sa.String, nullable=False),
        sa.Column("name", sa.String, nullable=True),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("pois", sa.JSON, nullable=True),
        sa.Column("visited", sa.Boolean, nullable=False, server_default="0"),
    )
    op.create_index("ix_hex_cells_id", "hex_cells", ["id"])


def downgrade() -> None:
    op.drop_table("hex_cells")
    op.drop_table("hex_maps")
