"""MemorizedSpell model for tracking prepared spells."""

from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MemorizedSpell(Base):
    """
    Tracks spells a character has memorized for the day.

    Each row represents one spell slot — the same spell can appear multiple
    times if memorized in multiple slots (e.g., two Sleep slots).

    Cast spells have cast=True. A rest resets all cast flags to False.
    """

    __tablename__ = "character_memorized_spells"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    spell_id = Column(
        Integer,
        ForeignKey("spells.id", ondelete="CASCADE"),
        nullable=False,
    )
    spell_level = Column(Integer, nullable=False)  # Denormalized for fast slot counting
    cast = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    character = relationship("Character", back_populates="memorized_spells")
    spell = relationship("Spell")

    def __repr__(self):
        return (
            f"<MemorizedSpell(id={self.id}, character_id={self.character_id}, "
            f"spell_id={self.spell_id}, cast={self.cast})>"
        )
