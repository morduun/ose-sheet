"""Add vehicle_types reference table and FK on campaign_vehicles

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'l3m4n5o6p7q8'
down_revision = 'k2l3m4n5o6p7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("vehicle_class", sa.String(), nullable=False),
        sa.Column("hp", sa.Integer(), nullable=False),
        sa.Column("ac", sa.Integer(), nullable=False),
        sa.Column("cargo_capacity", sa.Integer(), nullable=False),
        sa.Column("movement_rate", sa.Integer(), nullable=False),
        sa.Column("cost_gp", sa.Integer(), nullable=True),
        sa.Column("crew_min", sa.Integer(), default=0),
        sa.Column("passengers", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vehicle_types_key", "vehicle_types", ["key"])

    with op.batch_alter_table("campaign_vehicles") as batch_op:
        batch_op.add_column(sa.Column("vehicle_type_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("campaign_vehicles") as batch_op:
        batch_op.drop_column("vehicle_type_id")
    op.drop_index("ix_vehicle_types_key", table_name="vehicle_types")
    op.drop_table("vehicle_types")
