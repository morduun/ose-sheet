"""Pydantic schemas for CharacterClass."""

from pydantic import BaseModel, Field
from datetime import datetime


class CharacterClassBase(BaseModel):
    """Base character class schema."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    class_data: dict = Field(..., description="OSE class data (hit dice, saves, XP, etc.)")


class CharacterClassCreate(CharacterClassBase):
    """Schema for creating a character class."""

    campaign_id: int | None = None  # None for default classes
    is_default: bool = False


class CharacterClassUpdate(BaseModel):
    """Schema for updating a character class."""

    name: str | None = None
    description: str | None = None
    class_data: dict | None = None


class CharacterClass(CharacterClassBase):
    """Schema for character class responses."""

    id: int
    campaign_id: int | None
    is_default: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
