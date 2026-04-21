from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Campaign, User, Character
from app.models.item import CharacterItem, StashItem, Item
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
from app.schemas.dungeon import StashCoinRequest, StashCoinTakeRequest
from app.services.permissions import (
    can_view_campaign,
    can_edit_campaign,
    is_campaign_gm,
    can_assign_item_to_character,
    get_user_campaigns,
)
from app.services.modifiers import (
    _clamp,
    compute_ac,
    compute_encumbrance,
    compute_equipped_weapons,
    get_item_ability_modifiers,
    get_item_round_effects,
)

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

    rows = (
        db.query(StashItem)
        .filter(StashItem.campaign_id == campaign_id)
        .all()
    )

    entries = []
    for row in rows:
        if row.item:
            entries.append(StashEntry(
                instance_id=row.id,
                item=ItemPublic.model_validate(row.item),
                quantity=row.quantity,
                container_id=row.container_id,
                state=row.state,
            ))
    return entries


@router.post("/{campaign_id}/stash", response_model=StashEntry, status_code=status.HTTP_201_CREATED)
async def add_to_stash(
    campaign_id: int,
    req: StashAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an item to the party stash. GM only. Always creates a new instance."""
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

    # Always create a new stash instance
    stash_row = StashItem(
        campaign_id=campaign_id,
        item_id=req.item_id,
        quantity=req.quantity,
        state=req.state,
    )
    db.add(stash_row)
    db.commit()
    db.refresh(stash_row)

    return StashEntry(
        instance_id=stash_row.id,
        item=ItemPublic.model_validate(item),
        quantity=stash_row.quantity,
        container_id=stash_row.container_id,
        state=stash_row.state,
    )


@router.patch("/{campaign_id}/stash/{instance_id}", response_model=StashEntry)
async def update_stash_quantity(
    campaign_id: int,
    instance_id: int,
    req: StashQuantityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the quantity of a stash instance. GM only."""
    campaign = _get_campaign_or_404(db, campaign_id)
    if not is_campaign_gm(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can update stash quantities",
        )

    stash_row = (
        db.query(StashItem)
        .filter(StashItem.id == instance_id, StashItem.campaign_id == campaign_id)
        .first()
    )
    if not stash_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in stash",
        )

    stash_row.quantity = req.quantity
    db.commit()
    db.refresh(stash_row)

    return StashEntry(
        instance_id=stash_row.id,
        item=ItemPublic.model_validate(stash_row.item),
        quantity=stash_row.quantity,
        container_id=stash_row.container_id,
    )


@router.delete("/{campaign_id}/stash/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_stash(
    campaign_id: int,
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a stash instance entirely. GM only."""
    campaign = _get_campaign_or_404(db, campaign_id)
    if not is_campaign_gm(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can remove items from the stash",
        )

    stash_row = (
        db.query(StashItem)
        .filter(StashItem.id == instance_id, StashItem.campaign_id == campaign_id)
        .first()
    )
    if not stash_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in stash",
        )

    db.delete(stash_row)
    db.commit()
    return None


@router.post("/{campaign_id}/stash/{instance_id}/take", response_model=dict)
async def take_from_stash(
    campaign_id: int,
    instance_id: int,
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

    # Lookup stash instance
    stash_row = (
        db.query(StashItem)
        .filter(StashItem.id == instance_id, StashItem.campaign_id == campaign_id)
        .first()
    )
    if not stash_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in stash",
        )
    if stash_row.quantity < req.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough in stash (available: {stash_row.quantity})",
        )

    item = stash_row.item
    is_container = bool(item and (item.item_metadata or {}).get("capacity"))

    # Decrement stash or delete if exhausted
    new_stash_qty = stash_row.quantity - req.quantity
    if new_stash_qty <= 0:
        db.delete(stash_row)
    else:
        stash_row.quantity = new_stash_qty

    # Create new CharacterItem row (carry state from stash for treasure details)
    new_char_item = CharacterItem(
        character_id=req.character_id,
        item_id=item.id,
        quantity=req.quantity,
        state=stash_row.state,
    )
    db.add(new_char_item)
    db.flush()  # get new_char_item.id for container contents

    # If this is a container, also take all contents from stash
    contents_moved = []
    if is_container:
        content_rows = (
            db.query(StashItem)
            .filter(
                StashItem.campaign_id == campaign_id,
                StashItem.container_id == instance_id,
            )
            .all()
        )

        for crow in content_rows:
            # Create CharacterItem for each content, container_id = new container instance
            content_char_item = CharacterItem(
                character_id=req.character_id,
                item_id=crow.item_id,
                quantity=crow.quantity,
                container_id=new_char_item.id,
            )
            db.add(content_char_item)
            if crow.item:
                contents_moved.append(crow.item.name)
            # Remove content from stash
            db.delete(crow)

    db.commit()
    msg = f"{character.name} took {req.quantity} {item.name} from the stash"
    if contents_moved:
        msg += f" (with {', '.join(contents_moved)})"
    return {"message": msg}


@router.post("/{campaign_id}/stash/return", response_model=dict)
async def return_to_stash(
    campaign_id: int,
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

    # Lookup character inventory instance
    char_item = (
        db.query(CharacterItem)
        .filter(
            CharacterItem.id == req.instance_id,
            CharacterItem.character_id == req.character_id,
        )
        .first()
    )
    if not char_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found in character inventory",
        )
    if char_item.quantity < req.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Character doesn't have enough of this item (has: {char_item.quantity})",
        )

    item = char_item.item
    is_container = bool(item and (item.item_metadata or {}).get("capacity"))

    # Create new StashItem row for the returned item (carry state for treasure details)
    new_stash_item = StashItem(
        campaign_id=campaign_id,
        item_id=item.id,
        quantity=req.quantity,
        state=char_item.state,
    )
    db.add(new_stash_item)
    db.flush()  # get new_stash_item.id for container contents

    # If this is a container, also return all contents to stash
    contents_moved = []
    if is_container:
        content_rows = (
            db.query(CharacterItem)
            .filter(
                CharacterItem.character_id == req.character_id,
                CharacterItem.container_id == req.instance_id,
            )
            .all()
        )

        for crow in content_rows:
            # Create StashItem for each content, container_id = new stash container instance
            content_stash_item = StashItem(
                campaign_id=campaign_id,
                item_id=crow.item_id,
                quantity=crow.quantity,
                container_id=new_stash_item.id,
            )
            db.add(content_stash_item)
            if crow.item:
                contents_moved.append(crow.item.name)
            # Remove content from character inventory
            db.delete(crow)

    # Decrement character inventory or delete if exhausted
    new_char_qty = char_item.quantity - req.quantity
    if new_char_qty <= 0:
        db.delete(char_item)
    else:
        char_item.quantity = new_char_qty

    db.commit()
    msg = f"{character.name} returned {req.quantity} {item.name} to the stash"
    if contents_moved:
        msg += f" (with {', '.join(contents_moved)})"
    return {"message": msg}


# --- Party Treasury (Stash Coins) ---


@router.get("/{campaign_id}/treasury")
async def get_stash_coins(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the party treasury coin totals."""
    from app.services.currency import get_stash_coin_totals
    campaign = _get_campaign_or_404(db, campaign_id)
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(status_code=403, detail="Not a member of this campaign")
    return get_stash_coin_totals(campaign_id, db)


@router.post("/{campaign_id}/treasury")
async def add_stash_coins_endpoint(
    campaign_id: int,
    req: StashCoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add coins to the party treasury."""
    from app.services.currency import add_stash_coins as _add_stash_coins, get_stash_coin_totals
    campaign = _get_campaign_or_404(db, campaign_id)
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(status_code=403, detail="Not a member of this campaign")

    amounts = {"cp": req.cp, "sp": req.sp, "ep": req.ep, "gp": req.gp, "pp": req.pp}
    _add_stash_coins(campaign_id, amounts, db)
    db.commit()

    return get_stash_coin_totals(campaign_id, db)


@router.post("/{campaign_id}/treasury/take")
async def take_stash_coins_endpoint(
    campaign_id: int,
    req: StashCoinTakeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Take coins from the party treasury to a character's inventory."""
    from app.services.currency import (
        take_stash_coins as _take_stash_coins,
        add_coins,
        get_stash_coin_totals,
    )
    campaign = _get_campaign_or_404(db, campaign_id)
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(status_code=403, detail="Not a member of this campaign")

    character = db.query(Character).filter(Character.id == req.character_id).first()
    if not character or character.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Character not in this campaign")

    amounts = {"cp": req.cp, "sp": req.sp, "ep": req.ep, "gp": req.gp, "pp": req.pp}
    if not _take_stash_coins(campaign_id, amounts, db):
        raise HTTPException(status_code=400, detail="Not enough coins in treasury")

    add_coins(character.id, amounts, db)
    db.commit()

    return {
        "message": f"{character.name} took coins from the treasury",
        "treasury": get_stash_coin_totals(campaign_id, db),
    }


@router.post("/{campaign_id}/treasury/return")
async def return_stash_coins_endpoint(
    campaign_id: int,
    req: StashCoinTakeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return coins from a character's inventory to the party treasury."""
    from app.services.currency import (
        spend_coins,
        add_stash_coins as _add_stash_coins,
        get_stash_coin_totals,
    )
    campaign = _get_campaign_or_404(db, campaign_id)
    if not can_view_campaign(current_user, campaign):
        raise HTTPException(status_code=403, detail="Not a member of this campaign")

    character = db.query(Character).filter(Character.id == req.character_id).first()
    if not character or character.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Character not in this campaign")

    amounts = {"cp": req.cp, "sp": req.sp, "ep": req.ep, "gp": req.gp, "pp": req.pp}
    if not spend_coins(character.id, amounts, db):
        raise HTTPException(
            status_code=400,
            detail=f"{character.name} doesn't have enough coins",
        )

    _add_stash_coins(campaign_id, amounts, db)
    db.commit()

    return {
        "message": f"{character.name} returned coins to the treasury",
        "treasury": get_stash_coin_totals(campaign_id, db),
    }


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
            Character.status == "active",
        )
        .all()
    )

    ability_targets = {"strength", "dexterity", "wisdom", "intelligence", "constitution", "charisma"}
    result = []
    for char in characters:
        _ = char.character_class  # force-load relationship

        # Get item ability modifiers before detaching
        item_mods = get_item_ability_modifiers(char.id, db)
        db.expunge(char)

        # Apply ability score modifiers from items
        for target, value in item_mods.items():
            if target in ability_targets:
                old = getattr(char, target, 10)
                setattr(char, target, _clamp(old + value))

        fresh_ac = compute_ac(char, db)
        fresh_weapons = compute_equipped_weapons(char, db)
        cs = dict(char.combat_stats or {})
        cs["equipped_weapons"] = fresh_weapons
        cs["rear_ac"] = fresh_ac["rear_ac"]
        cs["shieldless_ac"] = fresh_ac["shieldless_ac"]
        enc = compute_encumbrance(char, db)
        cs["encumbrance"] = enc["encumbrance"]
        cs["effective_movement"] = enc["effective_movement"]
        char.combat_stats = cs
        char.ac = fresh_ac["ac"]
        result.append(char)

    return result


@router.post("/{campaign_id}/round-effects")
async def apply_round_effects(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Apply round effects (e.g. regeneration) from equipped+identified items
    to all living characters in the campaign. GM only.

    Returns a log of effects applied.
    """
    campaign = _get_campaign_or_404(db, campaign_id)
    if not is_campaign_gm(current_user, campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the GM can apply round effects",
        )

    characters = (
        db.query(Character)
        .filter(
            Character.campaign_id == campaign_id,
            Character.status == "active",
        )
        .all()
    )

    log = []
    for char in characters:
        effects = get_item_round_effects(char.id, db)
        if not effects:
            continue

        char_effects = []
        for eff in effects:
            if eff["effect"] == "hp" and eff["value"] != 0:
                old_hp = char.hp_current
                new_hp = max(0, min(char.hp_max, old_hp + eff["value"]))
                if new_hp != old_hp:
                    char.hp_current = new_hp
                    char_effects.append({
                        "item_name": eff["item_name"],
                        "effect": eff["effect"],
                        "value": eff["value"],
                        "old_hp": old_hp,
                        "new_hp": new_hp,
                    })

        if char_effects:
            log.append({
                "character_id": char.id,
                "character_name": char.name,
                "effects": char_effects,
            })

    if log:
        db.commit()

    return log
