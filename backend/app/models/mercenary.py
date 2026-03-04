"""Mercenary model for tracking hired mercenary units."""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Mercenary(Base):
    """
    Tracks mercenary units hired by a character.

    Each row represents a group of mercenaries of a single type and race.
    """

    __tablename__ = "character_mercenaries"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    merc_type = Column(String, nullable=False)  # key into MERCENARY_TYPES
    race = Column(String, nullable=False)  # "human", "dwarf", "elf", "orc", "goblin"
    quantity = Column(Integer, nullable=False, default=1)
    wartime = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    character = relationship("Character", back_populates="mercenaries")

    def __repr__(self):
        return (
            f"<Mercenary(id={self.id}, character_id={self.character_id}, "
            f"type={self.merc_type}, race={self.race}, qty={self.quantity})>"
        )
