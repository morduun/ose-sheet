"""Add campaign_vehicles and vehicle_cargo tables

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'k2l3m4n5o6p7'
down_revision = 'j1k2l3m4n5o6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign_vehicles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("vehicle_type", sa.String(), nullable=False),
        sa.Column("base_type", sa.String(), nullable=False),
        sa.Column("hp_max", sa.Integer(), nullable=False),
        sa.Column("hp_current", sa.Integer(), nullable=False),
        sa.Column("ac", sa.Integer(), nullable=False),
        sa.Column("cargo_capacity", sa.Integer(), nullable=False),
        sa.Column("movement_rate", sa.Integer(), nullable=False),
        sa.Column("cost_gp", sa.Integer(), nullable=True),
        sa.Column("vehicle_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_campaign_vehicles_campaign_id", "campaign_vehicles", ["campaign_id"])

    op.create_table(
        "vehicle_cargo",
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("campaign_vehicles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("quantity", sa.Integer(), default=1),
    )


def downgrade() -> None:
    op.drop_table("vehicle_cargo")
    op.drop_index("ix_campaign_vehicles_campaign_id", table_name="campaign_vehicles")
    op.drop_table("campaign_vehicles")
