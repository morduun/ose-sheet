from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema with common attributes."""

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for creating a new user."""

    google_id: str


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: str | None = None


class User(UserBase):
    """Schema for user responses."""

    id: int
    google_id: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserPublic(BaseModel):
    """Public user information (for displaying to other users)."""

    id: int
    name: str

    model_config = {"from_attributes": True}
