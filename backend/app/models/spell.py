from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# Association table for many-to-many relationship between characters and spells
character_spellbook = Table(
    "character_spellbook",
    Base.metadata,
    Column("character_id", Integer, ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True),
    Column("spell_id", Integer, ForeignKey("spells.id", ondelete="CASCADE"), primary_key=True),
)


class Spell(Base):
    """Spell model for OSE spellcasting."""

    __tablename__ = "spells"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    level = Column(Integer, nullable=False)       # 1–6
    spell_class = Column(String, nullable=False)  # "magic-user", "cleric", "druid", "illusionist"
    description = Column(String, nullable=False)  # Compact reference format: key mechanics
    range = Column(String, nullable=True)         # e.g., "60′", "Touch", "Caster"
    duration = Column(String, nullable=True)      # e.g., "1 turn", "Permanent", "Concentration"
    aoe = Column(String, nullable=True)           # Area of effect, e.g., "20′ radius", "60′×5′ line"
    save = Column(String, nullable=True)          # Saving throw, e.g., "Negates", "½ damage"
    reversed = Column(String, nullable=True)      # Description of reversed form; null if not reversible

    # Default spells are available to all campaigns
    is_default = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    characters = relationship(
        "Character",
        secondary=character_spellbook,
        back_populates="spells",
    )

    def __repr__(self):
        return f"<Spell(id={self.id}, name='{self.name}', level={self.level}, class='{self.spell_class}')>"
