from pydantic import BaseModel, Field
from datetime import datetime


class CharacterBase(BaseModel):
    """Base character schema with common attributes."""

    name: str
    character_class: str
    level: int = 1
    alignment: str | None = None
    xp: int = 0

    # Attributes
    strength: int = Field(default=10, ge=3, le=18)
    intelligence: int = Field(default=10, ge=3, le=18)
    wisdom: int = Field(default=10, ge=3, le=18)
    dexterity: int = Field(default=10, ge=3, le=18)
    constitution: int = Field(default=10, ge=3, le=18)
    charisma: int = Field(default=10, ge=3, le=18)

    # Hit Points
    hp_max: int = Field(default=1, ge=1)
    hp_current: int = Field(default=1, ge=0)

    # Armor Class
    ac: int = Field(default=9, ge=0)

    # Saving Throws (optional JSON)
    saving_throws: dict | None = None

    # Combat Stats (optional JSON)
    combat_stats: dict | None = None

    # Currency
    copper: int = Field(default=0, ge=0)
    silver: int = Field(default=0, ge=0)
    electrum: int = Field(default=0, ge=0)
    gold: int = Field(default=0, ge=0)
    platinum: int = Field(default=0, ge=0)

    # State
    is_alive: bool = True

    # Notes
    notes: str | None = None


class CharacterCreate(CharacterBase):
    """Schema for creating a new character."""

    campaign_id: int


class CharacterUpdate(BaseModel):
    """Schema for updating a character."""

    name: str | None = None
    character_class: str | None = None
    level: int | None = Field(default=None, ge=1)
    alignment: str | None = None
    xp: int | None = Field(default=None, ge=0)

    strength: int | None = Field(default=None, ge=3, le=18)
    intelligence: int | None = Field(default=None, ge=3, le=18)
    wisdom: int | None = Field(default=None, ge=3, le=18)
    dexterity: int | None = Field(default=None, ge=3, le=18)
    constitution: int | None = Field(default=None, ge=3, le=18)
    charisma: int | None = Field(default=None, ge=3, le=18)

    hp_max: int | None = Field(default=None, ge=1)
    hp_current: int | None = Field(default=None, ge=0)
    ac: int | None = Field(default=None, ge=0)

    saving_throws: dict | None = None
    combat_stats: dict | None = None

    copper: int | None = Field(default=None, ge=0)
    silver: int | None = Field(default=None, ge=0)
    electrum: int | None = Field(default=None, ge=0)
    gold: int | None = Field(default=None, ge=0)
    platinum: int | None = Field(default=None, ge=0)

    is_alive: bool | None = None
    notes: str | None = None


class Character(CharacterBase):
    """Schema for character responses."""

    id: int
    campaign_id: int
    player_id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
