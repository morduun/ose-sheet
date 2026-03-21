"""Add allowed_emails table and seed from existing users

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-03-20
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'g8h9i0j1k2l3'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allowed_emails",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("added_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_allowed_emails_email", "allowed_emails", ["email"], unique=True)

    # Seed: every existing user is pre-approved
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO allowed_emails (email, added_by_id) "
            "SELECT email, id FROM users"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_allowed_emails_email", table_name="allowed_emails")
    op.drop_table("allowed_emails")
