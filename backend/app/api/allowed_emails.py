"""Admin endpoints for managing the email allowlist."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models import User
from app.models.allowed_email import AllowedEmail

router = APIRouter()


class AllowedEmailOut(BaseModel):
    id: int
    email: str
    added_by_id: int | None = None
    model_config = {"from_attributes": True}


class AllowedEmailAdd(BaseModel):
    email: EmailStr


@router.get("/", response_model=list[AllowedEmailOut])
async def list_allowed_emails(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all allowed emails."""
    return db.query(AllowedEmail).order_by(AllowedEmail.email).all()


@router.post("/", response_model=AllowedEmailOut, status_code=status.HTTP_201_CREATED)
async def add_allowed_email(
    body: AllowedEmailAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Add an email to the allowlist."""
    email = body.email.lower()
    existing = db.query(AllowedEmail).filter(AllowedEmail.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{email} is already on the allowlist",
        )
    entry = AllowedEmail(email=email, added_by_id=current_user.id)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_allowed_email(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Remove an email from the allowlist."""
    entry = db.query(AllowedEmail).filter(AllowedEmail.id == entry_id).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Allowlist entry not found",
        )
    # Prevent admin from removing their own email
    if entry.email == current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own email from the allowlist",
        )
    db.delete(entry)
    db.commit()
