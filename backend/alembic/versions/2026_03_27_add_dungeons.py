"""Add dungeons and dungeon_rooms tables

Revision ID: n5o6p7q8r9s0
Revises: m4n5o6p7q8r9
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'n5o6p7q8r9s0'
down_revision = 'm4n5o6p7q8r9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dungeons",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dungeons_campaign_id", "dungeons", ["campaign_id"])

    op.create_table(
        "dungeon_rooms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dungeon_id", sa.Integer(), sa.ForeignKey("dungeons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("state", sa.String(), server_default="unvisited"),
        sa.Column("treasure_type_key", sa.String(), nullable=True),
        sa.Column("monsters", sa.JSON(), nullable=True),
        sa.Column("items", sa.JSON(), nullable=True),
        sa.Column("traps", sa.JSON(), nullable=True),
        sa.Column("exits", sa.JSON(), nullable=True),
    )
    op.create_index("ix_dungeon_rooms_dungeon_id", "dungeon_rooms", ["dungeon_id"])


def downgrade() -> None:
    op.drop_index("ix_dungeon_rooms_dungeon_id", table_name="dungeon_rooms")
    op.drop_table("dungeon_rooms")
    op.drop_index("ix_dungeons_campaign_id", table_name="dungeons")
    op.drop_table("dungeons")
