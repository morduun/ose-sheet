"""Add character_animals table

Revision ID: o6p7q8r9s0t1
Revises: n5o6p7q8r9s0
Create Date: 2026-03-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'o6p7q8r9s0t1'
down_revision = 'n5o6p7q8r9s0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_animals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("character_id", sa.Integer(), sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("animal_type", sa.String(), nullable=False),
        sa.Column("hp_max", sa.Integer(), nullable=False),
        sa.Column("hp_current", sa.Integer(), nullable=False),
        sa.Column("ac", sa.Integer(), nullable=False),
        sa.Column("morale", sa.Integer(), nullable=False),
        sa.Column("hit_dice", sa.Float(), nullable=False),
        sa.Column("base_movement", sa.Integer(), nullable=False),
        sa.Column("encumbered_movement", sa.Integer(), nullable=True),
        sa.Column("base_load", sa.Integer(), nullable=True),
        sa.Column("max_load", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(), default="purchased"),
        sa.Column("attacks", sa.JSON(), nullable=True),
        sa.Column("abilities", sa.JSON(), nullable=True),
        sa.Column("equipment", sa.JSON(), nullable=True),
        sa.Column("inventory", sa.JSON(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_character_animals_character_id", "character_animals", ["character_id"])


def downgrade() -> None:
    op.drop_index("ix_character_animals_character_id", table_name="character_animals")
    op.drop_table("character_animals")
