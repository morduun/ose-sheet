from pydantic import BaseModel, Field
from datetime import datetime


class SpellBase(BaseModel):
    """Base spell schema with common attributes."""

    name: str
    level: int = Field(..., ge=1, le=6)
    spell_class: str       # "magic-user", "cleric", "druid", "illusionist"
    description: str       # Compact reference format: key mechanics
    range: str | None = None
    duration: str | None = None
    aoe: str | None = None       # Area of effect
    save: str | None = None      # Saving throw (e.g., "Negates", "½ damage")
    reversed: str | None = None  # Description of reversed form; null = not reversible
    is_default: bool = True


class SpellCreate(SpellBase):
    """Schema for creating a new spell."""

    pass


class SpellBatchCreate(BaseModel):
    """Schema for batch-creating spells."""

    spells: list[SpellCreate]


class SpellUpdate(BaseModel):
    """Schema for updating a spell."""

    name: str | None = None
    level: int | None = Field(default=None, ge=1, le=6)
    spell_class: str | None = None
    description: str | None = None
    range: str | None = None
    duration: str | None = None
    aoe: str | None = None
    save: str | None = None
    reversed: str | None = None


class Spell(SpellBase):
    """Schema for spell responses."""

    id: int
    is_default: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CharacterSpellAssignment(BaseModel):
    """Schema for adding a spell to a character's spellbook."""

    character_id: int
