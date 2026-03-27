"""Pydantic schemas for animal companions."""

from pydantic import BaseModel


class AnimalTypeInfo(BaseModel):
    """Reference data for an animal type."""
    key: str
    name: str
    cost_gp: int
    ac: int
    hit_dice: float
    hp: int
    morale: int
    base_movement: int
    encumbered_movement: int | None = None
    base_load: int | None = None
    max_load: int | None = None
    attacks: list[dict] = []
    abilities: dict = {}


class AnimalCreate(BaseModel):
    """Request to add an animal. Use animal_type for templates, or set to 'custom' and provide stats."""
    animal_type: str = "custom"
    name: str | None = None
    source: str = "purchased"
    # Custom stats (used when animal_type not in template list)
    hp: int | None = None
    ac: int | None = None
    morale: int | None = None
    hit_dice: float | None = None
    base_movement: int | None = None
    encumbered_movement: int | None = None
    base_load: int | None = None
    max_load: int | None = None
    attacks: list[dict] | None = None
    abilities: dict | None = None


class AnimalUpdate(BaseModel):
    """Request to update an animal."""
    name: str | None = None
    animal_type: str | None = None
    hp_current: int | None = None
    equipment: dict | None = None
    inventory: list[dict] | None = None
    notes: str | None = None
    source: str | None = None


class AnimalResponse(BaseModel):
    """An animal companion with computed stats."""
    id: int
    character_id: int
    name: str
    animal_type: str
    hp_max: int
    hp_current: int
    ac: int
    effective_ac: int
    morale: int
    hit_dice: float
    base_movement: int
    encumbered_movement: int | None = None
    effective_movement: int
    base_load: int | None = None
    max_load: int | None = None
    current_load: int = 0
    container_capacity: int = 0
    load_tier: str = "none"
    source: str = "purchased"
    attacks: list[dict] = []
    abilities: dict = {}
    equipment: dict = {}
    inventory: list[dict] = []
    notes: str | None = None

    model_config = {"from_attributes": True}
