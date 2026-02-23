"""CharacterClass model for OSE class templates."""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CharacterClass(Base):
    """
    Character class templates for OSE.

    Stores class-specific data like hit dice, saving throws, XP progression,
    and special abilities. Can be global defaults (is_default=True) or
    campaign-specific custom classes.
    """

    __tablename__ = "character_classes"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)

    # Basic Info
    name = Column(String, nullable=False, index=True)  # "Fighter", "Cleric"
    description = Column(String, nullable=True)  # Flavor text

    # OSE Class Data (comprehensive JSON structure)
    # Structure (all arrays indexed by level 1-14 or up to max_level):
    # {
    #   "Requirements": {"STR": 9, "CON": 9},  # Ability score minimums
    #   "prime_requisite": ["STR"],            # Prime requisite(s)
    #   "hit_dice": "1d8",                     # Hit die type
    #   "hp_bonus_post_9th": 2,                # Flat HP bonus after level 9
    #   "max_level": 14,                       # Maximum level
    #   "armor": "any",                        # Armor restrictions
    #   "shields": "any",                      # Shield restrictions
    #   "weapons": "any",                      # Weapon restrictions
    #   "languages": ["Common", "Elvish"],     # Known languages
    #   "saving_throws": {                     # Saving throws by level
    #     "death": [8, 8, 6, ...],             # Arrays of length max_level
    #     "wands": [9, 9, 7, ...],
    #     "paralyze": [10, 10, 8, ...],
    #     "breath": [13, 13, 10, ...],
    #     "spells": [12, 12, 10, ...]
    #   },
    #   "thac0": [19, 19, 17, ...],            # THAC0 by level
    #   "xp": [0, 2000, 4000, ...],            # XP thresholds by level
    #   "spells": {                            # Spell slots by level
    #     "1st": [0, 1, 2, ...],               # Arrays of length max_level
    #     "2nd": [0, 0, 0, 1, ...],
    #     ...
    #   },
    #   "turning": {                           # Turn undead table (clerics)
    #     "1hd": ["7", "T", "T", ...],         # "T"=turn, "D"=destroy, "-"=impossible
    #     "2hd": ["9", "7", "T", ...],
    #     ...
    #   },
    #   "thief_skills": {                      # Thief abilities by level
    #     "climb_surface": [87, 88, 89, ...],
    #     "find_traps": [10, 15, 20, ...],
    #     ...
    #   },
    #   "abilities": {                         # Special abilities
    #     "Ability Name": "Description text"
    #   },
    #   "domain": "Domain rules text"          # High-level domain rules
    # }
    class_data = Column(JSON, nullable=False)

    # Default classes available to all campaigns (admin-only)
    is_default = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    campaign = relationship("Campaign", back_populates="character_classes")
    characters = relationship("Character", back_populates="character_class")

    def __repr__(self):
        return f"<CharacterClass(id={self.id}, name='{self.name}', default={self.is_default})>"
