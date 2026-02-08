from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Character, Campaign, User
from app.schemas import (
    Character as CharacterSchema,
    CharacterCreate,
    CharacterUpdate,
)
from app.services.permissions import (
    can_view_campaign,
    can_view_character,
    can_edit_character,
    get_user_campaigns,
)

router = APIRouter()


@router.post("/", response_model=CharacterSchema, status_code=status.HTTP_201_CREATED)
async def create_character(
    character: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new character. User must be a member of the campaign."""
    # Verify campaign exists
    campaign = db.query(Campaign).filter(Campaign.id == character.campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with id {character.campaign_id} not found",
        )

    # Verify user has access to this campaign
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this campaign to create a character",
        )

    db_character = Character(
        **character.model_dump(exclude={"campaign_id"}),
        campaign_id=character.campaign_id,
        player_id=current_user.id,
    )
    db.add(db_character)
    db.commit()
    db.refresh(db_character)
    return db_character


@router.get("/", response_model=list[CharacterSchema])
async def list_characters(
    campaign_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List characters the user has access to."""
    query = db.query(Character)

    if campaign_id:
        # Verify user has access to the specified campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign and not can_view_campaign(current_user, campaign):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this campaign",
            )
        query = query.filter(Character.campaign_id == campaign_id)
    else:
        # Filter by campaigns user has access to
        user_campaign_ids = get_user_campaigns(current_user)
        query = query.filter(Character.campaign_id.in_(user_campaign_ids))

    characters = query.offset(skip).limit(limit).all()
    return characters


@router.get("/{character_id}", response_model=CharacterSchema)
async def get_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific character by ID. User must have access to view."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    # Check if user has access to this character
    if not can_view_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this character",
        )

    return character


@router.patch("/{character_id}", response_model=CharacterSchema)
async def update_character(
    character_id: int,
    character_update: CharacterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a character. Must be owner or campaign GM."""
    db_character = db.query(Character).filter(Character.id == character_id).first()
    if not db_character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    # Check if user can edit this character
    if not can_edit_character(current_user, db_character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the character owner or campaign GM can update this character",
        )

    # Update only provided fields
    update_data = character_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_character, field, value)

    db.commit()
    db.refresh(db_character)
    return db_character


@router.delete("/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_character(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a character. Must be owner or campaign GM."""
    db_character = db.query(Character).filter(Character.id == character_id).first()
    if not db_character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    # Check if user can edit this character
    if not can_edit_character(current_user, db_character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the character owner or campaign GM can delete this character",
        )

    db.delete(db_character)
    db.commit()
    return None
