"""Character Classes CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import CharacterClass, User, Campaign
from app.schemas import (
    CharacterClass as CharacterClassSchema,
    CharacterClassCreate,
    CharacterClassUpdate,
)
from app.services.permissions import can_edit_character_class

router = APIRouter()


@router.post("/", response_model=CharacterClassSchema, status_code=status.HTTP_201_CREATED)
async def create_character_class(
    char_class: CharacterClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new character class.

    - For default classes: Requires admin privileges
    - For campaign classes: Requires GM of that campaign
    """
    # Validate campaign if provided
    if char_class.campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == char_class.campaign_id).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with id {char_class.campaign_id} not found",
            )

        if campaign.gm_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the campaign GM can create classes for this campaign",
            )

    # Default classes require admin privileges
    if char_class.is_default:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to create default classes",
            )
        # Default classes should not have a campaign_id
        if char_class.campaign_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Default classes cannot belong to a specific campaign",
            )

    db_class = CharacterClass(**char_class.model_dump())
    db.add(db_class)
    db.commit()
    db.refresh(db_class)
    return db_class


@router.get("/", response_model=list[CharacterClassSchema])
async def list_character_classes(
    campaign_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List character classes.

    Filters:
    - campaign_id: Campaign to filter by (shows default + campaign classes)
    - If no campaign_id: Shows only default classes
    """
    query = db.query(CharacterClass)

    # Filter by campaign or defaults
    if campaign_id:
        # Verify user has access to campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign and campaign.gm_id != current_user.id and current_user not in campaign.players:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this campaign's classes",
            )
        # Show default classes + campaign classes
        query = query.filter(
            (CharacterClass.campaign_id == campaign_id) | (CharacterClass.is_default == True)
        )
    else:
        # Show only default classes if no campaign specified
        query = query.filter(CharacterClass.is_default == True)

    return query.order_by(CharacterClass.name).offset(skip).limit(limit).all()


@router.get("/{class_id}", response_model=CharacterClassSchema)
async def get_character_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a character class by ID."""
    char_class = db.query(CharacterClass).filter(CharacterClass.id == class_id).first()

    if not char_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character class with id {class_id} not found",
        )

    # Check access for campaign-specific classes
    if char_class.campaign_id:
        campaign = char_class.campaign
        if campaign.gm_id != current_user.id and current_user not in campaign.players:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this character class",
            )

    return char_class


@router.patch("/{class_id}", response_model=CharacterClassSchema)
async def update_character_class(
    class_id: int,
    updates: CharacterClassUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a character class.

    - Admin-only for default classes
    - GM-only for campaign classes
    """
    char_class = db.query(CharacterClass).filter(CharacterClass.id == class_id).first()

    if not char_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character class with id {class_id} not found",
        )

    if not can_edit_character_class(current_user, char_class):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this character class",
        )

    # Apply updates
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(char_class, field, value)

    db.commit()
    db.refresh(char_class)
    return char_class


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a character class.

    Will fail if characters are using this class (RESTRICT constraint).
    """
    char_class = db.query(CharacterClass).filter(CharacterClass.id == class_id).first()

    if not char_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character class with id {class_id} not found",
        )

    if not can_edit_character_class(current_user, char_class):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this character class",
        )

    try:
        db.delete(char_class)
        db.commit()
    except Exception as e:
        # RESTRICT constraint prevents deletion if characters exist
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete class: characters are using it",
        )
