from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, JSON, Table
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
)


class Item(Base):
    """Item model for equipment, weapons, armor, and other items."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)

    # Basic Info
    name = Column(String, nullable=False, index=True)
    item_type = Column(String, nullable=False)  # e.g., "weapon", "armor", "equipment", "treasure"

    # Descriptions
    description_player = Column(String, nullable=True)  # What players can see
    description_gm = Column(String, nullable=True)  # What only the GM can see

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
