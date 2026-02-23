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
from app.schemas.user import UserPublic, User as UserSchema
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

    # Redirect to frontend with the token
    return RedirectResponse(
        url=f"{settings.frontend_url}/auth/callback?token={access_token}"
    )


@router.post("/token", response_model=TokenResponse)
async def email_login(token_request: TokenRequest, db: Session = Depends(get_db)):
    """
    Email-based login. Creates a new user if one doesn't exist.

    Args:
        token_request: Email and optional name
        db: Database session

    Returns:
        TokenResponse with JWT token and user info
    """
    user = get_user_by_email(token_request.email, db)

    if not user:
        # Auto-create user from email
        # First user in the system becomes admin (the GM running the server)
        is_first_user = db.query(User).count() == 0
        name = token_request.name or token_request.email.split("@")[0]
        user = User(
            email=token_request.email,
            name=name,
            is_admin=is_first_user,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Update name if provided and different
    if token_request.name and user.name != token_request.name:
        user.name = token_request.name
        db.commit()
        db.refresh(user)

    # Generate JWT access token
    access_token = create_access_token(data={"user_id": user.id, "email": user.email})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserPublic(id=user.id, name=user.name),
    )


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.

    This endpoint is used by frontends to verify login state
    and retrieve user info including admin status.

    Args:
        current_user: User from JWT token (dependency injection)

    Returns:
        User schema with current user's information (includes is_admin)
    """
    return current_user
