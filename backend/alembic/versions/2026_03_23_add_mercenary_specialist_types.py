"""Add mercenary_types and specialist_types reference tables

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

revision = 'm4n5o6p7q8r9'
down_revision = 'l3m4n5o6p7q8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mercenary_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("ac", sa.Integer(), nullable=False),
        sa.Column("morale", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("race_costs", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_mercenary_types_key", "mercenary_types", ["key"])

    op.create_table(
        "specialist_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("wage", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_specialist_types_key", "specialist_types", ["key"])


def downgrade() -> None:
    op.drop_index("ix_specialist_types_key", table_name="specialist_types")
    op.drop_table("specialist_types")
    op.drop_index("ix_mercenary_types_key", table_name="mercenary_types")
    op.drop_table("mercenary_types")
