from pydantic import BaseModel
from datetime import datetime


class MonsterBase(BaseModel):
    """Base monster schema with common attributes."""

    name: str
    description: str | None = None
    ac: int | None = None
    hit_dice: str | None = None
    hp: int | None = None
    thac0: int | None = None
    movement_rate: str | None = None
    morale: int | None = None
    alignment: str | None = None
    xp: int | None = None
    monster_metadata: dict | None = None


class MonsterCreate(MonsterBase):
    """Schema for creating a new monster."""

    campaign_id: int | None = None
    is_default: bool = False


class MonsterUpdate(BaseModel):
    """Schema for updating a monster. All fields optional."""

    name: str | None = None
    description: str | None = None
    ac: int | None = None
    hit_dice: str | None = None
    hp: int | None = None
    thac0: int | None = None
    movement_rate: str | None = None
    morale: int | None = None
    alignment: str | None = None
    xp: int | None = None
    monster_metadata: dict | None = None


class Monster(MonsterBase):
    """Schema for monster responses."""

    id: int
    campaign_id: int | None = None
    is_default: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
