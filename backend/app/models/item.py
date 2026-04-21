from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CharacterItem(Base):
    """Instance of an item in a character's inventory."""

    __tablename__ = "character_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1)
    slot = Column(String, nullable=True)  # null = carried; "armor" | "shield" | "main-hand" | "off-hand" | "ammo" | "worn"
    identified = Column(Boolean, default=False, server_default="0")
    container_id = Column(Integer, ForeignKey("character_items.id", ondelete="SET NULL"), nullable=True, index=True)
    dropped = Column(Boolean, default=False, server_default="0")
    stashed = Column(Boolean, default=False, server_default="0")
    state = Column(JSON, nullable=True)  # Per-character item state (e.g. fill, contents)

    # Relationships
    character = relationship("Character", back_populates="inventory", foreign_keys=[character_id])
    item = relationship("Item")
    container = relationship("CharacterItem", remote_side=[id], foreign_keys=[container_id])
    contents = relationship("CharacterItem", foreign_keys=[container_id], overlaps="container")


class StashItem(Base):
    """Instance of an item in a campaign's party stash."""

    __tablename__ = "campaign_stash"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1)
    container_id = Column(Integer, ForeignKey("campaign_stash.id", ondelete="SET NULL"), nullable=True)
    state = Column(JSON, nullable=True)  # Per-instance state (gp_value, material, description for treasure)

    # Relationships
    campaign = relationship("Campaign", back_populates="stash_items")
    item = relationship("Item")
    container = relationship("StashItem", remote_side=[id], foreign_keys=[container_id])
    contents = relationship("StashItem", foreign_keys=[container_id], overlaps="container")


class Item(Base):
    """Item model for equipment, weapons, armor, and other items."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)

    # Basic Info
    name = Column(String, nullable=False, index=True)
    unidentified_name = Column(String, nullable=True)  # Mundane name shown when not identified
    item_type = Column(String, nullable=False)  # weapon, armor, ammo, consumable, tool, treasure

    # Promoted fields (previously in item_metadata)
    weight = Column(Float, nullable=True)        # in coins (1 coin ≈ 0.1 lb per OSE)
    cost_gp = Column(Float, nullable=True)       # cost in gold pieces
    equippable = Column(Boolean, default=False)   # can be worn/wielded

    # Descriptions
    description_player = Column(String, nullable=True)  # What players can see
    description_gm = Column(String, nullable=True)  # What only the GM can see

    # Revealable secrets — list of {text: str, revealed: bool}
    secrets = Column(JSON, nullable=True, default=None)

    # Item-specific metadata (stored as JSON for flexibility)
    # For weapons: {"weapon_type": "sword", "damage_dice": "1d8", "damage_bonus": 0, "hit_bonus": 0, "range": null}
    # For armor: {"armor_type": "chainmail", "ac": 5}
    # For treasure: {"gp_value": 100, "materials": "gold and ruby"}
    item_metadata = Column(JSON, nullable=True)

    # Default items are available to all campaigns
    is_default = Column(Boolean, default=False, index=True)

    # GM-only items are hidden from player "Add Item" — only assignable by GM
    gm_only = Column(Boolean, default=False, server_default="0")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    campaign = relationship("Campaign", back_populates="items")

    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}', type='{self.item_type}', default={self.is_default})>"
