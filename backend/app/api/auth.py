"""Authentication API endpoints for Google OAuth and JWT tokens."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import TokenResponse, TokenRequest
from app.schemas.user import UserPublic
from app.services.auth import (
    create_access_token,
    get_google_user_info,
    get_or_create_user,
    get_user_by_email,
)

router = APIRouter()

# Initialize OAuth client for Google
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google")
async def google_login(request: Request):
    """
    Initiate Google OAuth login flow.

    Redirects user to Google's OAuth consent screen.
    After user authorizes, Google redirects back to /api/auth/google/callback.

    Args:
        request: Starlette request object (for redirect URL construction)

    Returns:
        Redirect response to Google OAuth consent screen
    """
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env",
        )

    redirect_uri = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google OAuth callback.

    This endpoint receives the authorization code from Google,
    exchanges it for an access token, fetches user info,
    creates/updates user in database, and generates JWT token.

    Args:
        request: Starlette request object (contains auth code)
        db: Database session

    Returns:
        TokenResponse with JWT token and user info
    """
    try:
        # Get the access token from Google
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authorization failed: {str(e)}",
        )

    # Get user info from Google using the access token
    try:
        google_user_info = await get_google_user_info(token["access_token"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch user info from Google: {str(e)}",
        )

    # Create or update user in our database
    user = get_or_create_user(google_user_info, db)

    # Generate JWT access token for our API
    access_token = create_access_token(data={"user_id": user.id, "email": user.email})

    # Return token and user info
    # In a real app with frontend, you might redirect to a frontend URL with the token
    # For now, we return JSON response
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserPublic(id=user.id, name=user.name),
    )


@router.post("/token", response_model=TokenResponse)
async def dev_login(token_request: TokenRequest, db: Session = Depends(get_db)):
    """
    Development/testing endpoint for email-based login.

    This endpoint allows logging in with just an email for development and testing.
    In production, this should be disabled or protected.

    Args:
        token_request: Email of existing user
        db: Database session

    Returns:
        TokenResponse with JWT token and user info

    Raises:
        HTTPException: 404 if user not found
    """
    user = get_user_by_email(token_request.email, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {token_request.email} not found",
        )

    # Generate JWT access token
    access_token = create_access_token(data={"user_id": user.id, "email": user.email})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserPublic(id=user.id, name=user.name),
    )


@router.get("/me", response_model=UserPublic)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.

    This endpoint is used by frontends to verify login state
    and retrieve user info.

    Args:
        current_user: User from JWT token (dependency injection)

    Returns:
        UserPublic with current user's information
    """
    return UserPublic(id=current_user.id, name=current_user.name)
