from pydantic import BaseModel, Field
from datetime import datetime


class SpellBase(BaseModel):
    """Base spell schema with common attributes."""

    name: str
    level: int = Field(..., ge=1, le=6)
    spell_class: str
    description: str
    range: str | None = None
    duration: str | None = None


class SpellCreate(SpellBase):
    """Schema for creating a new spell."""

    pass


class SpellUpdate(BaseModel):
    """Schema for updating a spell."""

    name: str | None = None
    level: int | None = Field(default=None, ge=1, le=6)
    spell_class: str | None = None
    description: str | None = None
    range: str | None = None
    duration: str | None = None


class Spell(SpellBase):
    """Schema for spell responses."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CharacterSpellAssignment(BaseModel):
    """Schema for adding a spell to a character's spellbook."""

    character_id: int
