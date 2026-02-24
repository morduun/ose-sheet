from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# Association table for many-to-many relationship between characters and items
character_items = Table(
    "character_items",
    Base.metadata,
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("quantity", Integer, default=1),
    Column("slot", String, nullable=True),  # null = carried; "armor" | "shield" | "main-hand" | "off-hand"
    Column("identified", Boolean, default=False, server_default="0"),
)

# Association table for campaign shared stash (party loot pool)
campaign_stash = Table(
    "campaign_stash",
    Base.metadata,
    Column("campaign_id", Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("quantity", Integer, default=1),
)


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

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    campaign = relationship("Campaign", back_populates="items")
    characters = relationship(
        "Character",
        secondary=character_items,
        back_populates="items",
    )

    def __repr__(self):
        return f"<Item(id={self.id}, name='{self.name}', type='{self.item_type}', default={self.is_default})>"
