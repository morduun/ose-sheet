"""Items CRUD API endpoints with permission-based access."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Item, Character, User, Campaign
from app.schemas import (
    Item as ItemSchema,
    ItemCreate,
    ItemUpdate,
    ItemPublic,
    CharacterItemAssignment,
)
from app.services.permissions import (
    can_edit_item,
    can_view_item_full,
    can_assign_item_to_character,
)

router = APIRouter()


@router.post("/", response_model=ItemSchema, status_code=status.HTTP_201_CREATED)
async def create_item(
    item: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new item.

    - campaign_id: Creates campaign-specific item (must be GM)
    - is_default: Creates default item (Phase 3 - admin only, disabled for now)
    """
    # Verify campaign exists and user is GM
    if item.campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == item.campaign_id).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with id {item.campaign_id} not found",
            )

        if campaign.gm_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the campaign GM can create items for this campaign",
            )

    # Default items creation disabled in Phase 2
    if item.is_default:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creating default items is not yet supported",
        )

    db_item = Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/", response_model=list[ItemPublic])
async def list_items(
    campaign_id: int | None = None,
    item_type: str | None = None,
    is_default: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List items.

    - Default items are visible to all
    - Campaign items only visible to campaign members
    - Filters: campaign_id, item_type, is_default
    """
    query = db.query(Item)

    # Filter by campaign or defaults
    if campaign_id:
        # Verify user has access to campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign and campaign.gm_id != current_user.id and current_user not in campaign.players:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this campaign's items",
            )
        # Show default items + campaign items
        query = query.filter(
            (Item.campaign_id == campaign_id) | (Item.is_default == True)
        )
    else:
        # Show only default items when no campaign specified
        query = query.filter(Item.is_default == True)

    # Additional filters
    if item_type:
        query = query.filter(Item.item_type == item_type)

    if is_default is not None:
        query = query.filter(Item.is_default == is_default)

    items = query.offset(skip).limit(limit).all()
    return items


@router.get("/{item_id}")
async def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get item details.

    - GMs see full details (including description_gm)
    - Players see public details only
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    # Check if user can view full details (is GM)
    if can_view_item_full(current_user, item):
        return ItemSchema.model_validate(item)
    else:
        return ItemPublic.model_validate(item)


@router.patch("/{item_id}", response_model=ItemSchema)
async def update_item(
    item_id: int,
    item_update: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an item. GM only for campaign items."""
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    # Check if user can edit this item
    if not can_edit_item(current_user, db_item):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the campaign GM can update this item",
        )

    # Update only provided fields
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_item, field, value)

    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an item. GM only for campaign items."""
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    # Check if user can edit this item
    if not can_edit_item(current_user, db_item):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the campaign GM can delete this item",
        )

    db.delete(db_item)
    db.commit()
    return None


@router.post("/{item_id}/assign", response_model=dict)
async def assign_item_to_character(
    item_id: int,
    assignment: CharacterItemAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Assign an item to a character.

    Must be character owner or campaign GM.
    """
    # Verify item exists
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    # Verify character exists
    character = db.query(Character).filter(Character.id == assignment.character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {assignment.character_id} not found",
        )

    # Check if user can assign items to this character
    if not can_assign_item_to_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only assign items to your own characters or as campaign GM",
        )

    # Check if item is already assigned
    if item in character.items:
        # Update quantity if already assigned
        # Note: For simplicity in Phase 2, we'll just add to the relationship
        # In Phase 3, we might want to handle quantity updates
        return {"message": "Item already assigned to character"}

    # Assign item to character
    character.items.append(item)
    db.commit()

    return {"message": f"Item {item.name} assigned to character {character.name}"}


@router.delete("/{item_id}/assign/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_item_from_character(
    item_id: int,
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove an item from a character's inventory.

    Must be character owner or campaign GM.
    """
    # Verify character exists
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    # Verify item exists
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found",
        )

    # Check if user can modify this character's items
    if not can_assign_item_to_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove items from your own characters or as campaign GM",
        )

    # Remove item from character
    if item in character.items:
        character.items.remove(item)
        db.commit()

    return None
