"""Pydantic schemas for mercenary units."""

from pydantic import BaseModel, Field


class MercenaryTypeInfo(BaseModel):
    """Reference data for a mercenary type (for dropdown/display)."""
    key: str
    name: str
    ac: int
    morale: int
    desc: str
    costs: dict[str, float | None]


class MercenaryUnit(BaseModel):
    """A hired mercenary unit with computed costs."""
    id: int
    merc_type: str
    race: str
    quantity: int
    wartime: bool
    name: str
    ac: int
    morale: int
    desc: str
    cost_per_unit: float
    total_cost: float

    model_config = {"from_attributes": True}


class MercenaryAddRequest(BaseModel):
    """Request to hire mercenaries."""
    merc_type: str
    race: str
    quantity: int = Field(default=1, ge=1)


class MercenaryUpdateRequest(BaseModel):
    """Request to update a mercenary unit."""
    quantity: int | None = Field(default=None, ge=1)
    wartime: bool | None = None


class MercenarySummary(BaseModel):
    """Summary of all mercenary units for a character."""
    units: list[MercenaryUnit] = []
    total_units: int = 0
    total_monthly_cost: float = 0.0
    wartime: bool = False


class WartimeRequest(BaseModel):
    """Request to bulk-toggle wartime for all units."""
    wartime: bool


class PaydayResponse(BaseModel):
    """Response after deducting monthly mercenary costs."""
    cost_gp: float
    platinum: int
    gold: int
    electrum: int
    silver: int
    copper: int
