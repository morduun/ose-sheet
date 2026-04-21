"""Pydantic schemas for hex maps and cells."""

from pydantic import BaseModel, Field


# --- Cell content sub-schemas ---

class HexCellPOI(BaseModel):
    type: str  # "settlement", "dungeon", "lair", "landmark"
    name: str
    description: str | None = None
    linked_dungeon_id: int | None = None


# --- Cell schemas ---

class HexCellCreate(BaseModel):
    col: int
    row: int
    terrain_type: str
    name: str | None = None
    description: str | None = None
    notes: str | None = None
    pois: list[HexCellPOI] = []
    visited: bool = False


class HexCellUpdate(BaseModel):
    terrain_type: str | None = None
    name: str | None = None
    description: str | None = None
    notes: str | None = None
    pois: list[HexCellPOI] | None = None
    visited: bool | None = None


class HexCellResponse(BaseModel):
    id: int
    hex_map_id: int
    col: int
    row: int
    terrain_type: str
    name: str | None = None
    description: str | None = None
    notes: str | None = None
    pois: list[dict] = []
    visited: bool = False

    model_config = {"from_attributes": True}


class HexCellPlayerResponse(BaseModel):
    """Cell response for players — no GM notes."""
    id: int
    hex_map_id: int
    col: int
    row: int
    terrain_type: str
    name: str | None = None
    description: str | None = None
    pois: list[dict] = []
    visited: bool = True  # only visited cells returned to players

    model_config = {"from_attributes": True}


# --- Batch cell operations ---

class HexCellBatchEntry(BaseModel):
    """Single cell in a batch upsert — col/row identify the target."""
    col: int
    row: int
    terrain_type: str
    name: str | None = None
    description: str | None = None
    notes: str | None = None
    pois: list[HexCellPOI] | None = None
    visited: bool | None = None


class HexCellBatchRequest(BaseModel):
    cells: list[HexCellBatchEntry]


# --- Party movement ---

class PartyMoveRequest(BaseModel):
    col: int
    row: int


# --- Map schemas ---

class HexMapCreate(BaseModel):
    name: str
    width: int = Field(ge=1, le=100)
    height: int = Field(ge=1, le=100)
    hex_size_miles: int = Field(default=6, ge=1, le=24)


class HexMapUpdate(BaseModel):
    name: str | None = None
    width: int | None = Field(default=None, ge=1, le=100)
    height: int | None = Field(default=None, ge=1, le=100)
    hex_size_miles: int | None = Field(default=None, ge=1, le=24)


class HexMapSummary(BaseModel):
    id: int
    campaign_id: int
    name: str
    width: int
    height: int
    hex_size_miles: int
    party_col: int | None = None
    party_row: int | None = None
    cell_count: int = 0

    model_config = {"from_attributes": True}


class HexMapResponse(BaseModel):
    """Full hex map with all cells (GM view)."""
    id: int
    campaign_id: int
    name: str
    width: int
    height: int
    hex_size_miles: int
    party_col: int | None = None
    party_row: int | None = None
    cells: list[HexCellResponse] = []

    model_config = {"from_attributes": True}


class HexMapPlayerResponse(BaseModel):
    """Hex map for players — only visited cells, no GM notes."""
    id: int
    campaign_id: int
    name: str
    width: int
    height: int
    hex_size_miles: int
    party_col: int | None = None
    party_row: int | None = None
    cells: list[HexCellPlayerResponse] = []

    model_config = {"from_attributes": True}
