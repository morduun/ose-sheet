from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, insert, update as sa_update, delete as sa_delete
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Campaign, User, Character
from app.models.item import campaign_stash, character_items, Item
from app.schemas import (
    Campaign as CampaignSchema,
    Character as CharacterSchema,
    CampaignCreate,
    CampaignUpdate,
    CampaignWithDetails,
    CampaignJoin,
)
from app.schemas.item import (
    StashEntry,
    StashAddRequest,
    StashTakeRequest,
    StashReturnRequest,
    StashQuantityUpdate,
    ItemPublic,
)
from app.services.permissions import (
    can_view_campaign,
    can_edit_campaign,
    is_campaign_gm,
    can_assign_item_to_character,
    get_user_campaigns,
)
from app.services.modifiers import compute_ac, compute_equipped_weapons

router = APIRouter()


@router.post("/", response_model=CampaignSchema, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new campaign. Authenticated user becomes the GM."""
    db_campaign = Campaign(
        name=campaign.name,
        description=campaign.description,
        gm_id=current_user.id,
    )
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@router.get("/", response_model=list[CampaignSchema])
async def list_campaigns(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List campaigns the user has access to (as GM or player)."""
    # Get campaign IDs user has access to
    user_campaign_ids = get_user_campaigns(current_user)

    # Query campaigns user has access to
    campaigns = (
        db.query(Campaign)
        .filter(Campaign.id.in_(user_campaign_ids))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return campaigns


@router.get("/{campaign_id}", response_model=CampaignWithDetails)
async def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific campaign by ID. Requires GM or player access."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with id {campaign_id} not found",
        )

    # Check if user has access to this campaign
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this campaign",
        )

    return campaign


@router.patch("/{campaign_id}", response_model=CampaignSchema)
async def update_campaign(
    campaign_id: int,
    campaign_update: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a campaign. GM only."""
    db_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not db_campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with id {campaign_id} not found",
        )

    # Check if current user is the GM
    if not can_edit_campaign(current_user, db_campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can update this campaign",
        )

    # Update only provided fields
    update_data = campaign_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_campaign, field, value)

    db.commit()
    db.refresh(db_campaign)
    return db_campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a campaign. GM only."""
    db_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not db_campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with id {campaign_id} not found",
        )

    # Check if current user is the GM
    if not can_edit_campaign(current_user, db_campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can delete this campaign",
        )

    db.delete(db_campaign)
    db.commit()
    return None


@router.post("/join", response_model=CampaignSchema)
async def join_campaign(
    campaign_join: CampaignJoin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join a campaign using an invite code."""
    campaign = (
        db.query(Campaign)
        .filter(Campaign.invite_code == campaign_join.invite_code)
        .first()
    )
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code"
        )

    # Check if user is already in campaign
    if current_user in campaign.players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this campaign",
        )

    # Check if user is the GM
    if campaign.gm_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are the GM of this campaign",
        )

    # Add user to campaign players
    campaign.players.append(current_user)
    db.commit()
    db.refresh(campaign)

    return campaign


# --- Party Stash Endpoints ---


def _get_campaign_or_404(db: Session, campaign_id: int) -> Campaign:
    """Helper to fetch a campaign or raise 404."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign with id {campaign_id} not found",
        )
    return campaign


@router.get("/{campaign_id}/stash", response_model=list[StashEntry])
async def list_stash(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all items in the campaign's party stash."""
    campaign = _get_campaign_or_404(db, campaign_id)
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this campaign",
        )

    rows = db.execute(
        select(campaign_stash.c.item_id, campaign_stash.c.quantity)
        .where(campaign_stash.c.campaign_id == campaign_id)
    ).all()

    entries = []
    for item_id, quantity in rows:
        item = db.query(Item).filter(Item.id == item_id).first()
        if item:
            entries.append(StashEntry(
                item=ItemPublic.model_validate(item),
                quantity=quantity,
            ))
    return entries


@router.post("/{campaign_id}/stash", response_model=StashEntry, status_code=status.HTTP_201_CREATED)
async def add_to_stash(
    campaign_id: int,
    req: StashAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an item to the party stash. GM only. Upserts (increments quantity if exists)."""
    campaign = _get_campaign_or_404(db, campaign_id)
    if not is_campaign_gm(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can add items to the stash",
        )

    # Validate item exists and is accessible to this campaign
    item = db.query(Item).filter(Item.id == req.item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {req.item_id} not found",
        )
    if not item.is_default and item.campaign_id != campaign_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item does not belong to this campaign",
        )

    # Check if already in stash — upsert
    existing = db.execute(
        select(campaign_stash.c.quantity).where(
            (campaign_stash.c.campaign_id == campaign_id)
            & (campaign_stash.c.item_id == req.item_id)
        )
    ).scalar()

    if existing is not None:
        new_qty = existing + req.quantity
        db.execute(
            sa_update(campaign_stash)
            .where(
                (campaign_stash.c.campaign_id == campaign_id)
                & (campaign_stash.c.item_id == req.item_id)
            )
            .values(quantity=new_qty)
        )
    else:
        new_qty = req.quantity
        db.execute(
            insert(campaign_stash).values(
                campaign_id=campaign_id,
                item_id=req.item_id,
                quantity=req.quantity,
            )
        )
    db.commit()

    return StashEntry(item=ItemPublic.model_validate(item), quantity=new_qty)


@router.patch("/{campaign_id}/stash/{item_id}", response_model=StashEntry)
async def update_stash_quantity(
    campaign_id: int,
    item_id: int,
    req: StashQuantityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the quantity of an item in the stash. GM only."""
    campaign = _get_campaign_or_404(db, campaign_id)
    if not is_campaign_gm(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can update stash quantities",
        )

    existing = db.execute(
        select(campaign_stash.c.quantity).where(
            (campaign_stash.c.campaign_id == campaign_id)
            & (campaign_stash.c.item_id == item_id)
        )
    ).scalar()
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in stash",
        )

    db.execute(
        sa_update(campaign_stash)
        .where(
            (campaign_stash.c.campaign_id == campaign_id)
            & (campaign_stash.c.item_id == item_id)
        )
        .values(quantity=req.quantity)
    )
    db.commit()

    item = db.query(Item).filter(Item.id == item_id).first()
    return StashEntry(item=ItemPublic.model_validate(item), quantity=req.quantity)


@router.delete("/{campaign_id}/stash/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_stash(
    campaign_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an item from the stash entirely. GM only."""
    campaign = _get_campaign_or_404(db, campaign_id)
    if not is_campaign_gm(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can remove items from the stash",
        )

    existing = db.execute(
        select(campaign_stash.c.quantity).where(
            (campaign_stash.c.campaign_id == campaign_id)
            & (campaign_stash.c.item_id == item_id)
        )
    ).scalar()
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in stash",
        )

    db.execute(
        sa_delete(campaign_stash).where(
            (campaign_stash.c.campaign_id == campaign_id)
            & (campaign_stash.c.item_id == item_id)
        )
    )
    db.commit()
    return None


@router.post("/{campaign_id}/stash/{item_id}/take", response_model=dict)
async def take_from_stash(
    campaign_id: int,
    item_id: int,
    req: StashTakeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Take an item from the stash into a character's inventory."""
    campaign = _get_campaign_or_404(db, campaign_id)
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this campaign",
        )

    # Validate character
    character = db.query(Character).filter(Character.id == req.character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {req.character_id} not found",
        )
    if character.campaign_id != campaign_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character does not belong to this campaign",
        )
    if not can_assign_item_to_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only take items for your own characters or as campaign GM",
        )

    # Check stash quantity
    stash_qty = db.execute(
        select(campaign_stash.c.quantity).where(
            (campaign_stash.c.campaign_id == campaign_id)
            & (campaign_stash.c.item_id == item_id)
        )
    ).scalar()
    if stash_qty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in stash",
        )
    if stash_qty < req.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough in stash (available: {stash_qty})",
        )

    # Decrement stash
    new_stash_qty = stash_qty - req.quantity
    if new_stash_qty <= 0:
        db.execute(
            sa_delete(campaign_stash).where(
                (campaign_stash.c.campaign_id == campaign_id)
                & (campaign_stash.c.item_id == item_id)
            )
        )
    else:
        db.execute(
            sa_update(campaign_stash)
            .where(
                (campaign_stash.c.campaign_id == campaign_id)
                & (campaign_stash.c.item_id == item_id)
            )
            .values(quantity=new_stash_qty)
        )

    # Increment character inventory
    char_qty = db.execute(
        select(character_items.c.quantity).where(
            (character_items.c.character_id == req.character_id)
            & (character_items.c.item_id == item_id)
        )
    ).scalar()

    if char_qty is not None:
        db.execute(
            sa_update(character_items)
            .where(
                (character_items.c.character_id == req.character_id)
                & (character_items.c.item_id == item_id)
            )
            .values(quantity=char_qty + req.quantity)
        )
    else:
        db.execute(
            insert(character_items).values(
                character_id=req.character_id,
                item_id=item_id,
                quantity=req.quantity,
            )
        )

    db.commit()
    item = db.query(Item).filter(Item.id == item_id).first()
    return {"message": f"{character.name} took {req.quantity} {item.name} from the stash"}


@router.post("/{campaign_id}/stash/{item_id}/return", response_model=dict)
async def return_to_stash(
    campaign_id: int,
    item_id: int,
    req: StashReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return an item from a character's inventory back to the stash."""
    campaign = _get_campaign_or_404(db, campaign_id)
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this campaign",
        )

    # Validate character
    character = db.query(Character).filter(Character.id == req.character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {req.character_id} not found",
        )
    if character.campaign_id != campaign_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character does not belong to this campaign",
        )
    if not can_assign_item_to_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only return items from your own characters or as campaign GM",
        )

    # Check character inventory quantity
    char_qty = db.execute(
        select(character_items.c.quantity).where(
            (character_items.c.character_id == req.character_id)
            & (character_items.c.item_id == item_id)
        )
    ).scalar()
    if char_qty is None or char_qty < req.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Character doesn't have enough of this item (has: {char_qty or 0})",
        )

    # Decrement character inventory
    new_char_qty = char_qty - req.quantity
    if new_char_qty <= 0:
        db.execute(
            sa_delete(character_items).where(
                (character_items.c.character_id == req.character_id)
                & (character_items.c.item_id == item_id)
            )
        )
    else:
        db.execute(
            sa_update(character_items)
            .where(
                (character_items.c.character_id == req.character_id)
                & (character_items.c.item_id == item_id)
            )
            .values(quantity=new_char_qty)
        )

    # Increment stash
    stash_qty = db.execute(
        select(campaign_stash.c.quantity).where(
            (campaign_stash.c.campaign_id == campaign_id)
            & (campaign_stash.c.item_id == item_id)
        )
    ).scalar()

    if stash_qty is not None:
        db.execute(
            sa_update(campaign_stash)
            .where(
                (campaign_stash.c.campaign_id == campaign_id)
                & (campaign_stash.c.item_id == item_id)
            )
            .values(quantity=stash_qty + req.quantity)
        )
    else:
        db.execute(
            insert(campaign_stash).values(
                campaign_id=campaign_id,
                item_id=item_id,
                quantity=req.quantity,
            )
        )

    db.commit()
    item = db.query(Item).filter(Item.id == item_id).first()
    return {"message": f"{character.name} returned {req.quantity} {item.name} to the stash"}


# --- Referee Panel Endpoint ---


@router.get("/{campaign_id}/referee", response_model=list[CharacterSchema])
async def get_referee_panel(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all living characters with computed weapons/AC for the referee panel. GM only."""
    campaign = _get_campaign_or_404(db, campaign_id)
    if not is_campaign_gm(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can access the referee panel",
        )

    characters = (
        db.query(Character)
        .filter(
            Character.campaign_id == campaign_id,
            Character.is_alive == True,
        )
        .all()
    )

    result = []
    for char in characters:
        _ = char.character_class  # force-load relationship
        fresh_weapons = compute_equipped_weapons(char, db)
        fresh_ac = compute_ac(char, db)
        db.expunge(char)
        cs = dict(char.combat_stats or {})
        cs["equipped_weapons"] = fresh_weapons
        cs["rear_ac"] = fresh_ac["rear_ac"]
        cs["shieldless_ac"] = fresh_ac["shieldless_ac"]
        char.combat_stats = cs
        char.ac = fresh_ac["ac"]
        result.append(char)

    return result
