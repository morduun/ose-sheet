from pydantic import BaseModel
from datetime import datetime


class ItemBase(BaseModel):
    """Base item schema with common attributes."""

    name: str
    item_type: str
    description_player: str | None = None
    description_gm: str | None = None
    item_metadata: dict | None = None


class ItemCreate(ItemBase):
    """Schema for creating a new item."""

    campaign_id: int | None = None  # None for default items
    is_default: bool = False


class ItemUpdate(BaseModel):
    """Schema for updating an item."""

    name: str | None = None
    item_type: str | None = None
    description_player: str | None = None
    description_gm: str | None = None
    item_metadata: dict | None = None


class Item(ItemBase):
    """Schema for item responses."""

    id: int
    campaign_id: int | None = None
    is_default: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ItemPublic(BaseModel):
    """Public item information (player-visible only)."""

    id: int
    name: str
    item_type: str
    description_player: str | None = None
    item_metadata: dict | None = None

    model_config = {"from_attributes": True}


class CharacterItemAssignment(BaseModel):
    """Schema for assigning an item to a character."""

    character_id: int
    quantity: int = 1
