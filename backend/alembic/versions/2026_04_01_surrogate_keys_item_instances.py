"""Add surrogate keys to character_items, campaign_stash, vehicle_cargo.

Replaces composite PKs with autoincrement id columns.
Renames container_item_id -> container_id (self-referential).
Changes characters.coin_container_id FK from items.id -> character_items.id.

Revision ID: 03ed3f729bfd
Revises: 2f91d51435b5
Create Date: 2026-04-01

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "03ed3f729bfd"
down_revision = "2f91d51435b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- character_items ---
    conn = op.get_bind()

    # 1. Create new table with surrogate id
    op.create_table(
        "character_items_new",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("character_id", sa.Integer, sa.ForeignKey("characters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer, default=1),
        sa.Column("slot", sa.String, nullable=True),
        sa.Column("identified", sa.Boolean, default=False, server_default="0"),
        sa.Column("container_id", sa.Integer, nullable=True),  # FK added after data copy
        sa.Column("dropped", sa.Boolean, default=False, server_default="0"),
        sa.Column("stashed", sa.Boolean, default=False, server_default="0"),
        sa.Column("state", sa.JSON, nullable=True),
    )

    # 2. Copy data (container_id stays NULL for now)
    conn.execute(sa.text("""
        INSERT INTO character_items_new
            (character_id, item_id, quantity, slot, identified, dropped, stashed, state)
        SELECT
            character_id, item_id, quantity, slot, identified, dropped, stashed, state
        FROM character_items
    """))

    # 3. Python-level remap: container_item_id -> container_id
    # Under old schema, (character_id, item_id) was unique, so this is unambiguous
    old_rows = conn.execute(sa.text("""
        SELECT character_id, item_id, container_item_id
        FROM character_items
        WHERE container_item_id IS NOT NULL
    """)).fetchall()

    for row in old_rows:
        char_id, item_id, container_item_id = row
        # Find the new id of the container instance
        container_new_id = conn.execute(sa.text("""
            SELECT id FROM character_items_new
            WHERE character_id = :cid AND item_id = :iid
            LIMIT 1
        """), {"cid": char_id, "iid": container_item_id}).scalar()

        if container_new_id is not None:
            # Find the new id of the item that references this container
            conn.execute(sa.text("""
                UPDATE character_items_new
                SET container_id = :ctr_id
                WHERE character_id = :cid AND item_id = :iid
            """), {"ctr_id": container_new_id, "cid": char_id, "iid": item_id})

    # 4. Remap characters.coin_container_id (items.id -> character_items_new.id)
    coin_rows = conn.execute(sa.text("""
        SELECT id, coin_container_id FROM characters
        WHERE coin_container_id IS NOT NULL
    """)).fetchall()

    for char_id, old_coin_ctr_id in coin_rows:
        new_ctr_id = conn.execute(sa.text("""
            SELECT id FROM character_items_new
            WHERE character_id = :cid AND item_id = :iid
            LIMIT 1
        """), {"cid": char_id, "iid": old_coin_ctr_id}).scalar()

        if new_ctr_id is not None:
            conn.execute(sa.text("""
                UPDATE characters SET coin_container_id = :new_id WHERE id = :cid
            """), {"new_id": new_ctr_id, "cid": char_id})
        else:
            # Container not in inventory — clear the reference
            conn.execute(sa.text("""
                UPDATE characters SET coin_container_id = NULL WHERE id = :cid
            """), {"cid": char_id})

    # 5. Drop old table, rename new
    op.drop_table("character_items")
    op.rename_table("character_items_new", "character_items")

    # 6. Add indexes and self-referential FK
    op.create_index("ix_character_items_character_id", "character_items", ["character_id"])
    op.create_index("ix_character_items_container_id", "character_items", ["container_id"])

    # --- campaign_stash ---
    op.create_table(
        "campaign_stash_new",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer, default=1),
        sa.Column("container_id", sa.Integer, nullable=True),
    )

    conn.execute(sa.text("""
        INSERT INTO campaign_stash_new (campaign_id, item_id, quantity)
        SELECT campaign_id, item_id, quantity
        FROM campaign_stash
    """))

    # Remap container_item_id -> container_id for stash
    old_stash_rows = conn.execute(sa.text("""
        SELECT campaign_id, item_id, container_item_id
        FROM campaign_stash
        WHERE container_item_id IS NOT NULL
    """)).fetchall()

    for row in old_stash_rows:
        camp_id, item_id, container_item_id = row
        container_new_id = conn.execute(sa.text("""
            SELECT id FROM campaign_stash_new
            WHERE campaign_id = :cid AND item_id = :iid
            LIMIT 1
        """), {"cid": camp_id, "iid": container_item_id}).scalar()

        if container_new_id is not None:
            conn.execute(sa.text("""
                UPDATE campaign_stash_new
                SET container_id = :ctr_id
                WHERE campaign_id = :cid AND item_id = :iid
            """), {"ctr_id": container_new_id, "cid": camp_id, "iid": item_id})

    op.drop_table("campaign_stash")
    op.rename_table("campaign_stash_new", "campaign_stash")
    op.create_index("ix_campaign_stash_campaign_id", "campaign_stash", ["campaign_id"])

    # --- vehicle_cargo ---
    op.create_table(
        "vehicle_cargo_new",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("campaign_vehicles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer, default=1),
    )

    conn.execute(sa.text("""
        INSERT INTO vehicle_cargo_new (vehicle_id, item_id, quantity)
        SELECT vehicle_id, item_id, quantity
        FROM vehicle_cargo
    """))

    op.drop_table("vehicle_cargo")
    op.rename_table("vehicle_cargo_new", "vehicle_cargo")
    op.create_index("ix_vehicle_cargo_vehicle_id", "vehicle_cargo", ["vehicle_id"])


def downgrade() -> None:
    conn = op.get_bind()

    # --- vehicle_cargo: back to composite PK ---
    op.create_table(
        "vehicle_cargo_old",
        sa.Column("vehicle_id", sa.Integer, sa.ForeignKey("campaign_vehicles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("quantity", sa.Integer, default=1),
    )
    # Merge duplicate (vehicle_id, item_id) rows by summing quantity
    conn.execute(sa.text("""
        INSERT INTO vehicle_cargo_old (vehicle_id, item_id, quantity)
        SELECT vehicle_id, item_id, SUM(quantity)
        FROM vehicle_cargo
        GROUP BY vehicle_id, item_id
    """))
    op.drop_table("vehicle_cargo")
    op.rename_table("vehicle_cargo_old", "vehicle_cargo")

    # --- campaign_stash: back to composite PK ---
    op.create_table(
        "campaign_stash_old",
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("quantity", sa.Integer, default=1),
        sa.Column("container_item_id", sa.Integer, sa.ForeignKey("items.id"), nullable=True),
    )
    conn.execute(sa.text("""
        INSERT INTO campaign_stash_old (campaign_id, item_id, quantity)
        SELECT campaign_id, item_id, SUM(quantity)
        FROM campaign_stash
        GROUP BY campaign_id, item_id
    """))
    op.drop_table("campaign_stash")
    op.rename_table("campaign_stash_old", "campaign_stash")

    # --- character_items: back to composite PK ---
    op.create_table(
        "character_items_old",
        sa.Column("character_id", sa.Integer, sa.ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("quantity", sa.Integer, default=1),
        sa.Column("slot", sa.String, nullable=True),
        sa.Column("identified", sa.Boolean, default=False, server_default="0"),
        sa.Column("container_item_id", sa.Integer, sa.ForeignKey("items.id"), nullable=True),
        sa.Column("dropped", sa.Boolean, default=False, server_default="0"),
        sa.Column("stashed", sa.Boolean, default=False, server_default="0"),
        sa.Column("state", sa.JSON, nullable=True),
    )
    # Take the first row per (character_id, item_id) group
    conn.execute(sa.text("""
        INSERT INTO character_items_old
            (character_id, item_id, quantity, slot, identified, dropped, stashed, state)
        SELECT character_id, item_id, SUM(quantity), slot, identified, dropped, stashed, state
        FROM character_items
        GROUP BY character_id, item_id
    """))

    # Remap container_id back to container_item_id (instance -> item type)
    containers = conn.execute(sa.text("""
        SELECT ci.character_id, ci.item_id, c.item_id AS container_item_id
        FROM character_items ci
        JOIN character_items c ON ci.container_id = c.id
        WHERE ci.container_id IS NOT NULL
    """)).fetchall()
    for row in containers:
        conn.execute(sa.text("""
            UPDATE character_items_old
            SET container_item_id = :ctr_item_id
            WHERE character_id = :cid AND item_id = :iid
        """), {"ctr_item_id": row[2], "cid": row[0], "iid": row[1]})

    # Remap coin_container_id back to items.id
    coin_rows = conn.execute(sa.text("""
        SELECT ch.id, ci.item_id
        FROM characters ch
        JOIN character_items ci ON ch.coin_container_id = ci.id
        WHERE ch.coin_container_id IS NOT NULL
    """)).fetchall()
    for char_id, item_id in coin_rows:
        conn.execute(sa.text("""
            UPDATE characters SET coin_container_id = :iid WHERE id = :cid
        """), {"iid": item_id, "cid": char_id})

    op.drop_table("character_items")
    op.rename_table("character_items_old", "character_items")
