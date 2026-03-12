"""initial_schema

Revision ID: 0000000000000
Revises:
Create Date: 2026-01-01 00:00:00.000000

NOTE: This migration only creates the bare minimum columns that existed before
any subsequent migration. Columns added by later migrations are intentionally
omitted here and added by their respective migration files:

  - users.is_admin                          → 5f8536ac7a58
  - spells.is_default, spells.campaign_id   → 5f8536ac7a58
  - spells.reversible                       → 495d5a9b4f85
  - spells.aoe, spells.save, spells.reversed → a6753e249563
  - characters.movement_rate               → 67a6b6276b35
  - characters.master_id, character_type, loyalty → b3f1a2c4d5e6
  - characters.status                      → d5e6f7a8b9c0
  - items.campaign_id, is_default          → later migration
  - items.weight, cost_gp, equippable      → 7b3882b43b71
  - items.unidentified_name                → later migration
  - items.secrets                          → later migration
  - character_items.slot                   → 9fb7e437a9ef
  - character_items.identified             → 4779e9511b76
  - monsters.campaign_id, is_default       → later migration
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0000000000000'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users — is_admin added by 5f8536ac7a58
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('google_id', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_google_id', 'users', ['google_id'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # campaigns
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('gm_id', sa.Integer(), nullable=False),
        sa.Column('invite_code', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['gm_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_campaigns_id', 'campaigns', ['id'], unique=False)
    op.create_index('ix_campaigns_invite_code', 'campaigns', ['invite_code'], unique=True)

    # campaign_players association
    op.create_table(
        'campaign_players',
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('campaign_id', 'user_id'),
    )

    # character_classes
    op.create_table(
        'character_classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('class_data', sa.JSON(), nullable=False),
        sa.Column('is_default', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_character_classes_id', 'character_classes', ['id'], unique=False)
    op.create_index('ix_character_classes_name', 'character_classes', ['name'], unique=False)
    op.create_index('ix_character_classes_is_default', 'character_classes', ['is_default'], unique=False)

    # spells — is_default + campaign_id added by 5f8536ac7a58
    #           reversible added by 495d5a9b4f85
    #           aoe, save, reversed added by a6753e249563
    op.create_table(
        'spells',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('spell_class', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('range', sa.String(), nullable=True),
        sa.Column('duration', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_spells_id', 'spells', ['id'], unique=False)
    op.create_index('ix_spells_name', 'spells', ['name'], unique=False)

    # items — campaign_id, unidentified_name, secrets, weight, cost_gp,
    #          equippable, is_default all added by later migrations
    op.create_table(
        'items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('item_type', sa.String(), nullable=False),
        sa.Column('description_player', sa.String(), nullable=True),
        sa.Column('description_gm', sa.String(), nullable=True),
        sa.Column('item_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_items_id', 'items', ['id'], unique=False)
    op.create_index('ix_items_name', 'items', ['name'], unique=False)


    # characters — movement_rate added by 67a6b6276b35
    #              master_id, character_type, loyalty added by b3f1a2c4d5e6
    #              status added by d5e6f7a8b9c0
    op.create_table(
        'characters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('character_class_id', sa.Integer(), nullable=True),
        sa.Column('level', sa.Integer(), default=1),
        sa.Column('alignment', sa.String(), nullable=True),
        sa.Column('xp', sa.Integer(), default=0),
        sa.Column('strength', sa.Integer(), default=10),
        sa.Column('intelligence', sa.Integer(), default=10),
        sa.Column('wisdom', sa.Integer(), default=10),
        sa.Column('dexterity', sa.Integer(), default=10),
        sa.Column('constitution', sa.Integer(), default=10),
        sa.Column('charisma', sa.Integer(), default=10),
        sa.Column('hp_max', sa.Integer(), default=1),
        sa.Column('hp_current', sa.Integer(), default=1),
        sa.Column('ac', sa.Integer(), default=9),
        sa.Column('saving_throws', sa.JSON(), nullable=True),
        sa.Column('combat_stats', sa.JSON(), nullable=True),
        sa.Column('copper', sa.Integer(), default=0),
        sa.Column('silver', sa.Integer(), default=0),
        sa.Column('electrum', sa.Integer(), default=0),
        sa.Column('gold', sa.Integer(), default=0),
        sa.Column('platinum', sa.Integer(), default=0),
        sa.Column('is_alive', sa.Boolean(), default=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['player_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['character_class_id'], ['character_classes.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_characters_id', 'characters', ['id'], unique=False)

    # character_items — slot added by 9fb7e437a9ef, identified added by 4779e9511b76
    op.create_table(
        'character_items',
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), default=1),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('character_id', 'item_id'),
    )

    # character_spellbook association
    op.create_table(
        'character_spellbook',
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('spell_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['spell_id'], ['spells.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('character_id', 'spell_id'),
    )

    # character_memorized_spells
    op.create_table(
        'character_memorized_spells',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('spell_id', sa.Integer(), nullable=False),
        sa.Column('spell_level', sa.Integer(), nullable=False),
        sa.Column('cast', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['spell_id'], ['spells.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_character_memorized_spells_id', 'character_memorized_spells', ['id'], unique=False)
    op.create_index('ix_character_memorized_spells_character_id', 'character_memorized_spells', ['character_id'], unique=False)





def downgrade() -> None:
    op.drop_table('monsters')
    op.drop_table('character_specialists')
    op.drop_table('character_mercenaries')
    op.drop_table('character_memorized_spells')
    op.drop_table('character_spellbook')
    op.drop_table('character_items')
    op.drop_table('characters')
    op.drop_table('campaign_stash')
    op.drop_table('items')
    op.drop_table('spells')
    op.drop_table('character_classes')
    op.drop_table('campaign_players')
    op.drop_table('campaigns')
    op.drop_table('users')