"""Pydantic schemas for specialist hirelings."""

from pydantic import BaseModel, Field


class SpecialistTypeInfo(BaseModel):
    """Reference data for a specialist type (for dropdown/display)."""
    key: str
    name: str
    wage: int
    desc: str


class SpecialistEntry(BaseModel):
    """A hired specialist with computed name/wage from reference data."""
    id: int
    spec_type: str
    task: str | None = None
    name: str
    wage: int

    model_config = {"from_attributes": True}


class SpecialistAddRequest(BaseModel):
    """Request to hire a specialist."""
    spec_type: str
    task: str | None = Field(default=None, max_length=500)


class SpecialistUpdateRequest(BaseModel):
    """Request to update a specialist's task."""
    task: str | None = Field(default=None, max_length=500)


class SpecialistSummary(BaseModel):
    """Summary of all specialists for a character."""
    entries: list[SpecialistEntry] = []
    count: int = 0
    total_monthly_cost: int = 0


class PaydayResponse(BaseModel):
    """Response after deducting monthly specialist wages."""
    cost_gp: int
    platinum: int
    gold: int
    electrum: int
    silver: int
    copper: int
