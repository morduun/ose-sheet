"""Schemas for spell memorization tracking."""

from pydantic import BaseModel

from app.schemas.spell import Spell as SpellSchema


class MemorizedSpellEntry(BaseModel):
    """A single memorized spell slot with cast state."""

    id: int
    spell: SpellSchema
    spell_level: int
    cast: bool

    model_config = {"from_attributes": True}


class SpellSlotInfo(BaseModel):
    """Slot usage summary for one spell level."""

    total: int  # Max slots from class template
    used: int   # Number of cast=True entries at this level


class CharacterSpellsResponse(BaseModel):
    """Combined spell state for a character."""

    spellbook: list[SpellSchema]           # All spells the character knows
    memorized: list[MemorizedSpellEntry]   # Today's memorization list
    slots: dict[str, SpellSlotInfo]        # Slot counts keyed by ordinal ("1st", "2nd", etc.)


class MemorizeRequest(BaseModel):
    """Request body for memorizing a spell."""

    spell_id: int
