"""Specialist model for tracking hired specialist individuals."""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Specialist(Base):
    """
    Tracks individual specialists hired by a character.

    Each row represents one hired specialist (unlike mercenaries, no quantity/merging).
    """

    __tablename__ = "character_specialists"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    spec_type = Column(String, nullable=False)  # key into SPECIALIST_TYPES
    task = Column(String, nullable=True)  # free-text: what they're currently doing
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    character = relationship("Character", back_populates="specialists")

    def __repr__(self):
        return (
            f"<Specialist(id={self.id}, character_id={self.character_id}, "
            f"type={self.spec_type}, task={self.task!r})>"
        )
