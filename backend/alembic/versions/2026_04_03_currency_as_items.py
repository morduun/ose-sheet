"""Convert currency from character/campaign fields to item instances.

Characters: copper/silver/electrum/gold/platinum/coin_container_id -> CharacterItem with currency state
Campaigns: stash_cp/sp/ep/gp/pp -> StashItem with currency state

Revision ID: 0eaeab19cc12
Revises: bee4dd7dc23f
Create Date: 2026-04-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0eaeab19cc12"
down_revision = "bee4dd7dc23f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Find the default Coins item
    coins_id = conn.execute(sa.text(
        "SELECT id FROM items WHERE name = 'Coins' AND item_type = 'currency' AND is_default = 1 LIMIT 1"
    )).scalar()
    if coins_id is None:
        raise RuntimeError("Default 'Coins' item not found — seed it first")

    # --- Convert character coins to CharacterItem instances ---
    char_rows = conn.execute(sa.text("""
        SELECT id, copper, silver, electrum, gold, platinum, coin_container_id
        FROM characters
        WHERE (copper > 0 OR silver > 0 OR electrum > 0 OR gold > 0 OR platinum > 0)
    """)).fetchall()

    for row in char_rows:
        char_id, cp, sp, ep, gp, pp, container_id = row
        state = {}
        if cp: state["cp"] = cp
        if sp: state["sp"] = sp
        if ep: state["ep"] = ep
        if gp: state["gp"] = gp
        if pp: state["pp"] = pp

        if not state:
            continue

        import json
        state_json = json.dumps(state)

        # If coins were in a container, find that container's instance_id
        # coin_container_id already points to character_items.id after surrogate key migration
        target_container = container_id  # already an instance ID or None

        conn.execute(sa.text("""
            INSERT INTO character_items (character_id, item_id, quantity, container_id, state)
            VALUES (:cid, :iid, 1, :ctr, :state)
        """), {"cid": char_id, "iid": coins_id, "ctr": target_container, "state": state_json})

    # --- Convert campaign treasury to StashItem instances ---
    camp_rows = conn.execute(sa.text("""
        SELECT id, stash_cp, stash_sp, stash_ep, stash_gp, stash_pp
        FROM campaigns
        WHERE (stash_cp > 0 OR stash_sp > 0 OR stash_ep > 0 OR stash_gp > 0 OR stash_pp > 0)
    """)).fetchall()

    for row in camp_rows:
        camp_id, cp, sp, ep, gp, pp = row
        state = {}
        if cp: state["cp"] = cp
        if sp: state["sp"] = sp
        if ep: state["ep"] = ep
        if gp: state["gp"] = gp
        if pp: state["pp"] = pp

        if not state:
            continue

        import json
        state_json = json.dumps(state)

        conn.execute(sa.text("""
            INSERT INTO campaign_stash (campaign_id, item_id, quantity, state)
            VALUES (:cid, :iid, 1, :state)
        """), {"cid": camp_id, "iid": coins_id, "state": state_json})

    # --- Drop old columns ---
    # SQLite can't drop columns in older versions, so rebuild tables
    # IMPORTANT: Use CREATE TABLE with full schema, not CREATE TABLE AS SELECT
    # (the latter strips PKs, constraints, and autoincrement)

    # Characters: rebuild without coin columns
    conn.execute(sa.text("""
        CREATE TABLE characters_new (
            id INTEGER NOT NULL PRIMARY KEY,
            campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
            player_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            master_id INTEGER REFERENCES characters(id) ON DELETE CASCADE,
            character_type VARCHAR NOT NULL DEFAULT 'pc',
            loyalty INTEGER,
            name VARCHAR NOT NULL,
            character_class_id INTEGER REFERENCES character_classes(id) ON DELETE RESTRICT,
            level INTEGER DEFAULT 1,
            alignment VARCHAR,
            xp INTEGER DEFAULT 0,
            strength INTEGER DEFAULT 10, intelligence INTEGER DEFAULT 10,
            wisdom INTEGER DEFAULT 10, dexterity INTEGER DEFAULT 10,
            constitution INTEGER DEFAULT 10, charisma INTEGER DEFAULT 10,
            hp_max INTEGER DEFAULT 1, hp_current INTEGER DEFAULT 1,
            ac INTEGER DEFAULT 9, movement_rate INTEGER DEFAULT 120,
            saving_throws JSON, combat_stats JSON,
            status VARCHAR NOT NULL DEFAULT 'active',
            is_alive BOOLEAN DEFAULT 1,
            portrait_filename VARCHAR, token_filename VARCHAR,
            notes VARCHAR,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
            updated_at DATETIME
        )
    """))
    conn.execute(sa.text("""
        INSERT INTO characters_new
        SELECT id, campaign_id, player_id, master_id, character_type, loyalty,
               name, character_class_id, level, alignment, xp,
               strength, intelligence, wisdom, dexterity, constitution, charisma,
               hp_max, hp_current, ac, movement_rate,
               saving_throws, combat_stats,
               status, is_alive, portrait_filename, token_filename,
               notes, created_at, updated_at
        FROM characters
    """))
    conn.execute(sa.text("DROP TABLE characters"))
    conn.execute(sa.text("ALTER TABLE characters_new RENAME TO characters"))
    conn.execute(sa.text("CREATE INDEX ix_characters_master_id ON characters (master_id)"))

    # Campaigns: rebuild without stash coin columns
    conn.execute(sa.text("""
        CREATE TABLE campaigns_new (
            id INTEGER NOT NULL PRIMARY KEY,
            name VARCHAR NOT NULL,
            description VARCHAR,
            gm_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            invite_code VARCHAR NOT NULL UNIQUE,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
            updated_at DATETIME
        )
    """))
    conn.execute(sa.text("""
        INSERT INTO campaigns_new
        SELECT id, name, description, gm_id, invite_code, created_at, updated_at
        FROM campaigns
    """))
    conn.execute(sa.text("DROP TABLE campaigns"))
    conn.execute(sa.text("ALTER TABLE campaigns_new RENAME TO campaigns"))


def downgrade() -> None:
    conn = op.get_bind()

    # Campaigns: add stash columns back
    op.add_column("campaigns", sa.Column("stash_cp", sa.Integer, default=0, server_default="0"))
    op.add_column("campaigns", sa.Column("stash_sp", sa.Integer, default=0, server_default="0"))
    op.add_column("campaigns", sa.Column("stash_ep", sa.Integer, default=0, server_default="0"))
    op.add_column("campaigns", sa.Column("stash_gp", sa.Integer, default=0, server_default="0"))
    op.add_column("campaigns", sa.Column("stash_pp", sa.Integer, default=0, server_default="0"))

    # Characters: add coin columns back
    op.add_column("characters", sa.Column("copper", sa.Integer, default=0))
    op.add_column("characters", sa.Column("silver", sa.Integer, default=0))
    op.add_column("characters", sa.Column("electrum", sa.Integer, default=0))
    op.add_column("characters", sa.Column("gold", sa.Integer, default=0))
    op.add_column("characters", sa.Column("platinum", sa.Integer, default=0))
    op.add_column("characters", sa.Column("coin_container_id", sa.Integer, nullable=True))

    # Restore data from currency instances
    from app.models.item import Item
    coins_id = conn.execute(sa.text(
        "SELECT id FROM items WHERE name = 'Coins' AND item_type = 'currency' AND is_default = 1 LIMIT 1"
    )).scalar()

    if coins_id:
        # Restore character coins
        import json
        ci_rows = conn.execute(sa.text("""
            SELECT character_id, container_id, state FROM character_items
            WHERE item_id = :iid
        """), {"iid": coins_id}).fetchall()

        for row in ci_rows:
            char_id, container_id, state_raw = row
            state = json.loads(state_raw) if state_raw else {}
            conn.execute(sa.text("""
                UPDATE characters SET
                    copper = COALESCE(copper, 0) + :cp,
                    silver = COALESCE(silver, 0) + :sp,
                    electrum = COALESCE(electrum, 0) + :ep,
                    gold = COALESCE(gold, 0) + :gp,
                    platinum = COALESCE(platinum, 0) + :pp,
                    coin_container_id = :ctr
                WHERE id = :cid
            """), {
                "cp": state.get("cp", 0), "sp": state.get("sp", 0),
                "ep": state.get("ep", 0), "gp": state.get("gp", 0),
                "pp": state.get("pp", 0), "ctr": container_id, "cid": char_id,
            })

        # Restore campaign treasury
        si_rows = conn.execute(sa.text("""
            SELECT campaign_id, state FROM campaign_stash
            WHERE item_id = :iid
        """), {"iid": coins_id}).fetchall()

        for row in si_rows:
            camp_id, state_raw = row
            state = json.loads(state_raw) if state_raw else {}
            conn.execute(sa.text("""
                UPDATE campaigns SET
                    stash_cp = COALESCE(stash_cp, 0) + :cp,
                    stash_sp = COALESCE(stash_sp, 0) + :sp,
                    stash_ep = COALESCE(stash_ep, 0) + :ep,
                    stash_gp = COALESCE(stash_gp, 0) + :gp,
                    stash_pp = COALESCE(stash_pp, 0) + :pp
                WHERE id = :cid
            """), {
                "cp": state.get("cp", 0), "sp": state.get("sp", 0),
                "ep": state.get("ep", 0), "gp": state.get("gp", 0),
                "pp": state.get("pp", 0), "cid": camp_id,
            })

        # Delete currency instances
        conn.execute(sa.text("DELETE FROM character_items WHERE item_id = :iid"), {"iid": coins_id})
        conn.execute(sa.text("DELETE FROM campaign_stash WHERE item_id = :iid"), {"iid": coins_id})
