"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import verify_token

# OAuth2 scheme for Swagger UI authentication
# This tells FastAPI where to look for the token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    This dependency:
    1. Extracts the JWT token from the Authorization header
    2. Verifies and decodes the token
    3. Looks up the user in the database
    4. Returns the user object

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        User object for the authenticated user

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify and decode the token
        payload = verify_token(token)
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Look up user in database
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Optional dependency for additional user validation.

    Currently just passes through the user, but can be extended
    to check for active/inactive status, banned users, etc.

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User object

    Raises:
        HTTPException: 403 if user is inactive/banned
    """
    # Future: Add checks for user.is_active, user.is_banned, etc.
    return current_user
