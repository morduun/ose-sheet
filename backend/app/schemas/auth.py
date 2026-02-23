"""Pydantic schemas for authentication requests and responses."""

from pydantic import BaseModel, EmailStr
from app.schemas.user import UserPublic


class Token(BaseModel):
    """JWT token response schema."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data encoded in the JWT token."""

    user_id: int
    email: str


class TokenResponse(BaseModel):
    """Complete authentication response with token and user info."""

    access_token: str
    token_type: str
    user: UserPublic


class TokenRequest(BaseModel):
    """Email-based login request. Creates user if not found."""

    email: EmailStr
    name: str | None = None
