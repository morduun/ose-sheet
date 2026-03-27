from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Dungeon(Base):
    """A dungeon belonging to a campaign, containing rooms."""

    __tablename__ = "dungeons"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign = relationship("Campaign", back_populates="dungeons")
    rooms = relationship("DungeonRoom", back_populates="dungeon", cascade="all, delete-orphan",
                         order_by="DungeonRoom.room_number")


class DungeonRoom(Base):
    """A numbered room within a dungeon."""

    __tablename__ = "dungeon_rooms"

    id = Column(Integer, primary_key=True, index=True)
    dungeon_id = Column(
        Integer,
        ForeignKey("dungeons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_number = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    notes = Column(String, nullable=True)  # GM play notes
    state = Column(String, default="unvisited", server_default="unvisited")  # unvisited, visited, cleared

    # Treasure type key for generic hoard rolling (optional)
    treasure_type_key = Column(String, nullable=True)

    # Room contents stored as JSON for simplicity
    # monsters: [{monster_id, quantity}]
    monsters = Column(JSON, nullable=True, default=list)
    # items: [{item_id, quantity, hidden, search_chance}]
    items = Column(JSON, nullable=True, default=list)
    # traps: [{name, trigger, damage_dice, save_type, save_target, description}]
    traps = Column(JSON, nullable=True, default=list)
    # exits: [{direction, description, locked, key_hint}]
    exits = Column(JSON, nullable=True, default=list)
    # currency: {cp, sp, ep, gp, pp}
    currency = Column(JSON, nullable=True)

    # Relationships
    dungeon = relationship("Dungeon", back_populates="rooms")
