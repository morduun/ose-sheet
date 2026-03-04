from pydantic import BaseModel, Field, computed_field
from datetime import datetime
from app.schemas.character_class import CharacterClass as CharacterClassSchema
from app.schemas.mercenary import MercenaryUnit
from app.services.modifiers import calculate_modifiers


class RetainerSummary(BaseModel):
    """Compact retainer info for embedding in a PC's response."""
    id: int
    name: str
    character_class_name: str | None = None
    level: int = 1
    hp_current: int = 0
    hp_max: int = 1
    ac: int = 9
    loyalty: int | None = None
    is_alive: bool = True
    model_config = {"from_attributes": True}


class CharacterBase(BaseModel):
    """Base character schema with common attributes."""

    name: str
    character_class_id: int = Field(..., description="ID of the character's class")
    level: int = 1
    alignment: str | None = None
    xp: int = 0
    character_type: str = "pc"
    loyalty: int | None = None

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

    # Movement Rate
    movement_rate: int = Field(default=120, ge=0)

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
    player_id: int | None = None  # GM can assign to a player; defaults to current user
    master_id: int | None = None  # Set when hiring a retainer


class CharacterUpdate(BaseModel):
    """Schema for updating a character."""

    name: str | None = None
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
    movement_rate: int | None = Field(default=None, ge=0)

    saving_throws: dict | None = None
    combat_stats: dict | None = None

    copper: int | None = Field(default=None, ge=0)
    silver: int | None = Field(default=None, ge=0)
    electrum: int | None = Field(default=None, ge=0)
    gold: int | None = Field(default=None, ge=0)
    platinum: int | None = Field(default=None, ge=0)

    is_alive: bool | None = None
    notes: str | None = None
    player_id: int | None = None  # GM can reassign character ownership
    loyalty: int | None = Field(default=None, ge=2, le=12)


class Character(CharacterBase):
    """Schema for character responses."""

    id: int
    campaign_id: int
    player_id: int
    master_id: int | None = None
    character_class: CharacterClassSchema  # Full class object via relationship
    retainers: list[RetainerSummary] = []
    mercenaries: list[MercenaryUnit] = []
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def thac0(self) -> int | None:
        """Extract THAC0 from combat_stats for convenient frontend access."""
        if self.combat_stats:
            return self.combat_stats.get("thac0")
        return None

    @computed_field
    @property
    def rear_ac(self) -> int | None:
        """Rear AC from combat_stats (no DEX, no shield)."""
        if self.combat_stats:
            return self.combat_stats.get("rear_ac")
        return None

    @computed_field
    @property
    def shieldless_ac(self) -> int | None:
        """Shieldless AC from combat_stats (no shield bonus)."""
        if self.combat_stats:
            return self.combat_stats.get("shieldless_ac")
        return None

    @computed_field
    @property
    def equipped_weapons(self) -> list[dict] | None:
        """Pre-computed weapon stats from combat_stats."""
        if self.combat_stats:
            return self.combat_stats.get("equipped_weapons")
        return None

    @computed_field
    @property
    def modifiers(self) -> dict:
        """Derived OSE attribute modifiers and prime requisite XP bonus."""
        return calculate_modifiers(self)
