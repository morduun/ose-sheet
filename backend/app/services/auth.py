"""Authentication service for JWT token management and Google OAuth."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import httpx

from app.config import settings
from app.models import User


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing claims to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    # Include standard 'sub' claim for frontend compatibility
    if "user_id" in to_encode and "sub" not in to_encode:
        to_encode["sub"] = str(to_encode["user_id"])

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )

    return encoded_jwt


def verify_token(token: str) -> Dict:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Dictionary containing the decoded token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError as e:
        raise JWTError(f"Invalid token: {str(e)}")


async def get_google_user_info(access_token: str) -> Dict:
    """
    Fetch user information from Google using an access token.

    Args:
        access_token: Google OAuth access token

    Returns:
        Dictionary containing user info from Google

    Raises:
        httpx.HTTPError: If the request to Google fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def get_or_create_user(google_user_info: Dict, db: Session) -> User:
    """
    Get existing user or create new user from Google OAuth info.

    Args:
        google_user_info: User information from Google OAuth
        db: Database session

    Returns:
        User object (either existing or newly created)
    """
    google_id = google_user_info.get("id")
    email = google_user_info.get("email")
    name = google_user_info.get("name", email)

    # Try to find existing user by google_id
    user = db.query(User).filter(User.google_id == google_id).first()

    if user:
        # Update user info if it changed
        if user.email != email or user.name != name:
            user.email = email
            user.name = name
            db.commit()
            db.refresh(user)
        return user

    # Create new user
    user = User(
        google_id=google_id,
        email=email,
        name=name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_user_by_email(email: str, db: Session) -> Optional[User]:
    """
    Get user by email (for development/testing).

    Args:
        email: User's email address
        db: Database session

    Returns:
        User object if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()
