from pydantic import BaseModel
from datetime import datetime
from app.schemas.user import UserPublic


class CampaignBase(BaseModel):
    """Base campaign schema with common attributes."""

    name: str
    description: str | None = None


class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign."""

    pass


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""

    name: str | None = None
    description: str | None = None


class Campaign(CampaignBase):
    """Schema for campaign responses."""

    id: int
    gm_id: int
    invite_code: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CampaignWithDetails(Campaign):
    """Campaign with GM and player information."""

    gm: UserPublic
    players: list[UserPublic] = []

    model_config = {"from_attributes": True}


class CampaignJoin(BaseModel):
    """Schema for joining a campaign via invite code."""

    invite_code: str
