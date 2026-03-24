"""Pydantic schemas for treasure types and roll results."""

from pydantic import BaseModel


class TreasureTypeInfo(BaseModel):
    """Reference data for a treasure type."""
    id: int
    key: str
    name: str
    category: str
    average_gp: int | None = None
    entries: list[dict]
    is_default: bool = False
    campaign_id: int | None = None

    model_config = {"from_attributes": True}


class TreasureTypeCreate(BaseModel):
    """Request to create a custom treasure type."""
    key: str
    name: str
    category: str = "hoard"
    average_gp: int | None = None
    entries: list[dict]


class TreasureRollRequest(BaseModel):
    """Request to roll a treasure type."""
    treasure_type: str  # key like "A", or compound like "C + 1000gp"
    count: int = 1      # number of times to roll (for individual types per monster)


class GemResult(BaseModel):
    value: int


class JewelryResult(BaseModel):
    value: int


class TreasureRollResult(BaseModel):
    """Result of rolling a treasure type."""
    treasure_type: str
    coins: dict[str, int]
    gems: list[GemResult]
    jewelry: list[JewelryResult]
    magic_items: list[str]
    total_gp_value: float
    gem_total: int = 0
    jewelry_total: int = 0
