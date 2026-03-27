"""Pydantic schemas for dungeons and rooms."""

from pydantic import BaseModel, Field


# --- Room content sub-schemas ---

class RoomMonster(BaseModel):
    monster_id: int
    quantity: int = 1


class RoomItem(BaseModel):
    item_id: int
    quantity: int = 1
    hidden: bool = False
    search_chance: int | None = None  # X-in-6, e.g. 1 = 1-in-6


class RoomTrap(BaseModel):
    name: str
    trigger: str | None = None
    damage_dice: str | None = None
    save_type: str | None = None  # "death", "wands", "paralyze", "breath", "spells"
    save_target: int | None = None
    description: str | None = None


class RoomExit(BaseModel):
    direction: str
    description: str | None = None
    locked: bool = False
    key_hint: str | None = None


class RoomCurrency(BaseModel):
    cp: int = 0
    sp: int = 0
    ep: int = 0
    gp: int = 0
    pp: int = 0


# --- Room schemas ---

class DungeonRoomCreate(BaseModel):
    room_number: int
    name: str
    description: str | None = None
    notes: str | None = None
    state: str = "unvisited"
    treasure_type_key: str | None = None
    monsters: list[RoomMonster] = []
    items: list[RoomItem] = []
    traps: list[RoomTrap] = []
    exits: list[RoomExit] = []
    currency: RoomCurrency | None = None


class DungeonRoomUpdate(BaseModel):
    room_number: int | None = None
    name: str | None = None
    description: str | None = None
    notes: str | None = None
    state: str | None = None
    treasure_type_key: str | None = None
    monsters: list[RoomMonster] | None = None
    items: list[RoomItem] | None = None
    traps: list[RoomTrap] | None = None
    exits: list[RoomExit] | None = None
    currency: RoomCurrency | None = None


class DungeonRoomResponse(BaseModel):
    id: int
    dungeon_id: int
    room_number: int
    name: str
    description: str | None = None
    notes: str | None = None
    state: str = "unvisited"
    treasure_type_key: str | None = None
    monsters: list[dict] = []
    items: list[dict] = []
    traps: list[dict] = []
    exits: list[dict] = []
    currency: dict | None = None

    model_config = {"from_attributes": True}


# --- Dungeon schemas ---

class DungeonCreate(BaseModel):
    name: str
    description: str | None = None


class DungeonUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class DungeonSummary(BaseModel):
    """Compact dungeon info for list view."""
    id: int
    campaign_id: int
    name: str
    description: str | None = None
    room_count: int = 0
    cleared_count: int = 0

    model_config = {"from_attributes": True}


class DungeonResponse(BaseModel):
    """Full dungeon with rooms."""
    id: int
    campaign_id: int
    name: str
    description: str | None = None
    rooms: list[DungeonRoomResponse] = []

    model_config = {"from_attributes": True}


# --- Stash coin schemas ---

class StashCoinRequest(BaseModel):
    """Add or remove coins from the party treasury."""
    cp: int = 0
    sp: int = 0
    ep: int = 0
    gp: int = 0
    pp: int = 0


class StashCoinTakeRequest(BaseModel):
    """Take coins from treasury to a character."""
    character_id: int
    cp: int = 0
    sp: int = 0
    ep: int = 0
    gp: int = 0
    pp: int = 0
