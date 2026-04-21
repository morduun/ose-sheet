"""Repair characters and campaigns tables after CREATE TABLE AS SELECT lost PKs.

The currency migration used CREATE TABLE AS SELECT which strips constraints.
This rebuilds both tables with proper PRIMARY KEY, NOT NULL, and DEFAULT clauses.

Revision ID: 4b578e812d3b
Revises: 9345907eee25
Create Date: 2026-04-06

"""
from alembic import op
import sqlalchemy as sa

revision = "4b578e812d3b"
down_revision = "9345907eee25"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # --- Rebuild characters table with proper schema ---
    conn.execute(sa.text("""
        CREATE TABLE characters_rebuilt (
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
            strength INTEGER DEFAULT 10,
            intelligence INTEGER DEFAULT 10,
            wisdom INTEGER DEFAULT 10,
            dexterity INTEGER DEFAULT 10,
            constitution INTEGER DEFAULT 10,
            charisma INTEGER DEFAULT 10,
            hp_max INTEGER DEFAULT 1,
            hp_current INTEGER DEFAULT 1,
            ac INTEGER DEFAULT 9,
            movement_rate INTEGER DEFAULT 120,
            saving_throws JSON,
            combat_stats JSON,
            status VARCHAR NOT NULL DEFAULT 'active',
            is_alive BOOLEAN DEFAULT 1,
            portrait_filename VARCHAR,
            token_filename VARCHAR,
            secondary_skill VARCHAR,
            notes VARCHAR,
            created_at DATETIME DEFAULT (CURRENT_TIMESTAMP),
            updated_at DATETIME
        )
    """))

    conn.execute(sa.text("""
        INSERT INTO characters_rebuilt
        SELECT id, campaign_id, player_id, master_id, character_type, loyalty,
               name, character_class_id, level, alignment, xp,
               strength, intelligence, wisdom, dexterity, constitution, charisma,
               hp_max, hp_current, ac, movement_rate,
               saving_throws, combat_stats,
               status, is_alive, portrait_filename, token_filename,
               secondary_skill, notes, created_at, updated_at
        FROM characters
    """))

    conn.execute(sa.text("DROP TABLE characters"))
    conn.execute(sa.text("ALTER TABLE characters_rebuilt RENAME TO characters"))
    conn.execute(sa.text("CREATE INDEX ix_characters_master_id ON characters (master_id)"))

    # --- Rebuild campaigns table with proper schema ---
    conn.execute(sa.text("""
        CREATE TABLE campaigns_rebuilt (
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
        INSERT INTO campaigns_rebuilt
        SELECT id, name, description, gm_id, invite_code, created_at, updated_at
        FROM campaigns
    """))

    conn.execute(sa.text("DROP TABLE campaigns"))
    conn.execute(sa.text("ALTER TABLE campaigns_rebuilt RENAME TO campaigns"))


def downgrade() -> None:
    pass  # No downgrade needed — this is a repair
