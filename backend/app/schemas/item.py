from pydantic import BaseModel, Field
from datetime import datetime


class SecretEntry(BaseModel):
    """A single revealable secret on an item."""
    text: str
    revealed: bool = False


class SecretToggleRequest(BaseModel):
    """Request to toggle a secret's revealed state."""
    revealed: bool


class ItemBase(BaseModel):
    """Base item schema with common attributes."""

    name: str
    unidentified_name: str | None = None
    item_type: str
    weight: float | None = None
    cost_gp: float | None = None
    equippable: bool = False
    description_player: str | None = None
    description_gm: str | None = None
    secrets: list[SecretEntry] | None = None
    item_metadata: dict | None = None


class ItemCreate(ItemBase):
    """Schema for creating a new item."""

    campaign_id: int | None = None  # None for default items
    is_default: bool = False
    gm_only: bool = False


class ItemUpdate(BaseModel):
    """Schema for updating an item."""

    name: str | None = None
    unidentified_name: str | None = None
    item_type: str | None = None
    weight: float | None = None
    cost_gp: float | None = None
    equippable: bool | None = None
    gm_only: bool | None = None
    description_player: str | None = None
    description_gm: str | None = None
    secrets: list[SecretEntry] | None = None
    item_metadata: dict | None = None


class Item(ItemBase):
    """Schema for item responses."""

    id: int
    campaign_id: int | None = None
    is_default: bool
    gm_only: bool = False
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ItemPublic(BaseModel):
    """Public item information (player-visible only)."""

    id: int
    name: str
    unidentified_name: str | None = None
    item_type: str
    weight: float | None = None
    cost_gp: float | None = None
    equippable: bool = False
    description_player: str | None = None
    revealed_secrets: list[str] | None = None
    item_metadata: dict | None = None
    is_default: bool = False
    gm_only: bool = False

    model_config = {"from_attributes": True}


class CharacterItemAssignment(BaseModel):
    """Schema for assigning an item to a character."""

    character_id: int
    quantity: int = 1


class CharacterInventoryEntry(BaseModel):
    """An item in a character's inventory with its quantity."""

    item: ItemPublic
    quantity: int
    slot: str | None = None  # null = carried; "armor" | "shield" | "main-hand" | "off-hand"
    identified: bool = False
    container_item_id: int | None = None  # items.id of the container holding this item
    dropped: bool = False  # True if this container has been dropped
    stashed: bool = False  # True if stored at home base (not carried)
    state: dict | None = None  # Per-character item state (fill, contents, etc.)


class CharacterInventoryEntryGM(BaseModel):
    """An item in a character's inventory (GM view with secrets control)."""
    item: Item  # Full Item schema (includes secrets, description_gm)
    quantity: int
    slot: str | None = None
    identified: bool = False
    container_item_id: int | None = None
    dropped: bool = False
    stashed: bool = False
    state: dict | None = None


class StashEntry(BaseModel):
    """An item in the campaign party stash."""

    item: ItemPublic
    quantity: int


class StashAddRequest(BaseModel):
    """Request to add an item to the party stash."""

    item_id: int
    quantity: int = 1


class StashTakeRequest(BaseModel):
    """Request to take an item from the stash to a character."""

    character_id: int
    quantity: int = 1


class StashReturnRequest(BaseModel):
    """Request to return an item from a character to the stash."""

    character_id: int
    quantity: int = 1


class StashQuantityUpdate(BaseModel):
    """Update the quantity of an item in the stash."""

    quantity: int = Field(..., gt=0)
