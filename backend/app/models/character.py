from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Character(Base):
    """Character model for player characters in OSE."""

    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Retainer fields
    master_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=True, index=True)
    character_type = Column(String, default="pc", nullable=False)  # "pc" or "retainer"
    loyalty = Column(Integer, nullable=True)  # base from master CHA, adjustable

    # Basic Info
    name = Column(String, nullable=False)
    character_class_id = Column(Integer, ForeignKey("character_classes.id", ondelete="RESTRICT"), nullable=True)
    level = Column(Integer, default=1)
    alignment = Column(String, nullable=True)  # e.g., "Lawful", "Neutral", "Chaotic"
    xp = Column(Integer, default=0)

    # Attributes (ability scores)
    strength = Column(Integer, default=10)
    intelligence = Column(Integer, default=10)
    wisdom = Column(Integer, default=10)
    dexterity = Column(Integer, default=10)
    constitution = Column(Integer, default=10)
    charisma = Column(Integer, default=10)

    # Hit Points
    hp_max = Column(Integer, default=1)
    hp_current = Column(Integer, default=1)

    # Armor Class
    ac = Column(Integer, default=9)  # Descending AC (OSE default)

    # Movement Rate (feet per turn)
    movement_rate = Column(Integer, default=120)

    # Saving Throws (stored as JSON for flexibility)
    # Format: {"death_ray_poison": 12, "magic_wands": 13, "paralysis_petrify": 14, "breath_attacks": 15, "spells_rods_staves": 16}
    saving_throws = Column(JSON, nullable=True)

    # Combat Stats (stored as JSON for attack matrices)
    # Format: {"thac0": 19, "attack_bonus": 0}
    combat_stats = Column(JSON, nullable=True)

    # Currency
    copper = Column(Integer, default=0)
    silver = Column(Integer, default=0)
    electrum = Column(Integer, default=0)
    gold = Column(Integer, default=0)
    platinum = Column(Integer, default=0)

    # Character State
    status = Column(String, default="active", nullable=False, server_default="active")  # "active", "independent", "fallen"
    is_alive = Column(Boolean, default=True)

    # Additional Notes
    notes = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    campaign = relationship("Campaign", back_populates="characters")
    player = relationship("User", back_populates="characters")
    character_class = relationship("CharacterClass", back_populates="characters")

    # Self-referential retainer relationships
    master = relationship("Character", remote_side=[id], back_populates="retainers", foreign_keys=[master_id])
    retainers = relationship("Character", back_populates="master", foreign_keys=[master_id], cascade="all, delete-orphan", lazy="noload")
    items = relationship(
        "Item",
        secondary="character_items",
        back_populates="characters",
    )
    spells = relationship(
        "Spell",
        secondary="character_spellbook",
        back_populates="characters",
    )
    memorized_spells = relationship(
        "MemorizedSpell",
        back_populates="character",
        cascade="all, delete-orphan",
    )
    mercenaries = relationship(
        "Mercenary",
        back_populates="character",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    specialists = relationship(
        "Specialist",
        back_populates="character",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    def __repr__(self):
        return f"<Character(id={self.id}, name='{self.name}', class='{self.character_class}', level={self.level})>"
