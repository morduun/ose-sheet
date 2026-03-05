from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Character, Campaign, CharacterClass, User, Spell, MemorizedSpell, Item, Mercenary, Specialist
from app.models.item import character_items
from app.schemas import (
    Character as CharacterSchema,
    CharacterCreate,
    CharacterUpdate,
    CharacterSpellsResponse,
    MemorizedSpellEntry,
    MemorizeRequest,
    SpellSlotInfo,
    CharacterInventoryEntry,
    CharacterInventoryEntryGM,
)
from app.schemas.item import ItemPublic, Item as ItemSchema
from app.schemas.spell import Spell as SpellSchema
from app.services.permissions import (
    can_view_campaign,
    can_view_character,
    can_edit_character,
    is_campaign_gm,
    get_user_campaigns,
)
from app.services.mercenaries import MERCENARY_TYPES, get_unit_cost
from app.services.specialists import SPECIALIST_TYPES
from app.services.modifiers import (
    _DEX_AC,
    _CHA_MAX_RETAINERS,
    _CHA_LOYALTY,
    _clamp,
    compute_ac,
    compute_equipped_weapons,
    get_item_ability_modifiers,
    get_item_skills,
    get_item_auras,
    get_item_round_effects,
)

# Spell caster mappings
CLASS_SPELL_MAP = {
    "Magic-User": "magic-user",
    "Illusionist": "illusionist",
    "Cleric": "cleric",
    "Druid": "druid",
}
ARCANE_CLASSES = {"Magic-User", "Illusionist"}
DIVINE_CLASSES = {"Cleric", "Druid"}
ORDINALS = ["1st", "2nd", "3rd", "4th", "5th", "6th"]


def level_to_ordinal(level: int) -> str:
    return ORDINALS[level - 1]


class XPAward(BaseModel):
    """Request body for awarding XP to a character."""
    xp: int = Field(..., gt=0, description="Amount of XP to award")


class LevelUpRequest(BaseModel):
    """Request body for leveling up a character."""
    hp_increase: int | None = Field(
        default=None,
        ge=0,
        description="HP to add on level-up (die roll + CON mod, min 1, already computed by frontend)",
    )

router = APIRouter()


@router.post("/", response_model=CharacterSchema, status_code=status.HTTP_201_CREATED)
async def create_character(
    character: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new character. User must be a member of the campaign.

    Auto-populates saving throws and combat stats (THAC0) from the
    character class template unless explicitly provided by the caller.
    """
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

    # Validate character class exists
    char_class = db.query(CharacterClass).filter(
        CharacterClass.id == character.character_class_id
    ).first()
    if not char_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character class with id {character.character_class_id} not found",
        )

    # Check class is available to this campaign (default or campaign-specific)
    if not char_class.is_default and char_class.campaign_id != campaign.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character class is not available for this campaign",
        )

    # Determine owner: GM can assign to a campaign player, otherwise self
    owner_id = current_user.id
    if character.player_id and character.player_id != current_user.id:
        if campaign.gm_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the GM can assign characters to other players",
            )
        # Verify target player is in the campaign
        player_ids = [p.id for p in campaign.players] + [campaign.gm_id]
        if character.player_id not in player_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target player is not a member of this campaign",
            )
        owner_id = character.player_id

    # --- Retainer validation ---
    if character.character_type == "retainer":
        if not character.master_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Retainers must have a master_id",
            )
        master = db.query(Character).filter(Character.id == character.master_id).first()
        if not master:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Master character with id {character.master_id} not found",
            )
        if master.campaign_id != character.campaign_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Retainer must be in the same campaign as the master",
            )
        if master.character_type != "pc":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PCs can have retainers",
            )
        if not master.is_alive:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot hire retainers for a fallen character",
            )
        # Enforce max retainers from CHA
        cha = _clamp(master.charisma)
        max_retainers = _CHA_MAX_RETAINERS[cha]
        current_retainers = db.query(Character).filter(
            Character.master_id == master.id,
            Character.status != "fallen",
        ).count()
        if current_retainers >= max_retainers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{master.name} already has {current_retainers}/{max_retainers} retainers (CHA {master.charisma})",
            )
        # Auto-set loyalty from master CHA if not provided
        if character.loyalty is None:
            character.loyalty = _CHA_LOYALTY[cha]
        # Force retainer owned by same player as master
        owner_id = master.player_id

    character_data = character.model_dump(exclude={"campaign_id", "player_id", "master_id"})
    level_index = character_data.get("level", 1) - 1
    class_data = char_class.class_data

    # Auto-populate saving throws from class template if not provided
    if not character_data.get("saving_throws"):
        saves = class_data.get("saving_throws", {})
        if saves:
            character_data["saving_throws"] = {
                key: values[level_index]
                for key, values in saves.items()
                if level_index < len(values)
            }

    # Auto-populate combat stats (THAC0) from class template if not provided
    if not character_data.get("combat_stats"):
        thac0_table = class_data.get("thac0", [])
        if thac0_table and level_index < len(thac0_table):
            character_data["combat_stats"] = {"thac0": thac0_table[level_index]}

    # Auto-populate AC with DEX modifier if still at default (9 = unarmored)
    if character_data.get("ac", 9) == 9:
        dex = _clamp(character_data.get("dexterity", 10))
        dex_ac_adj = _DEX_AC[dex]
        character_data["ac"] = 9 + dex_ac_adj

    db_character = Character(
        **character_data,
        campaign_id=character.campaign_id,
        player_id=owner_id,
        master_id=character.master_id,
    )
    db.add(db_character)
    db.commit()
    db.refresh(db_character)
    return db_character


@router.get("/", response_model=list[CharacterSchema])
async def list_characters(
    campaign_id: int | None = None,
    include_retainers: bool = False,
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

    if not include_retainers:
        query = query.filter(Character.character_type == "pc")

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

    # Force-load relationships before detaching from session
    _ = character.character_class
    _ = character.campaign

    gm_view = is_campaign_gm(current_user, character.campaign)

    # Get item ability modifiers BEFORE detaching (needs DB session)
    item_mods = get_item_ability_modifiers(character.id, db)
    item_skills = get_item_skills(character.id, db)
    item_auras = get_item_auras(character.id, db)
    item_round_effects = get_item_round_effects(character.id, db)

    # Load retainer summaries for PCs (before detaching)
    retainer_summaries = []
    if character.character_type == "pc":
        retainer_rows = db.query(Character).filter(
            Character.master_id == character.id,
            Character.is_alive == True,
        ).all()
        retainer_summaries = [
            {
                "id": r.id,
                "name": r.name,
                "character_class_name": r.character_class.name if r.character_class else None,
                "level": r.level,
                "hp_current": r.hp_current,
                "hp_max": r.hp_max,
                "ac": r.ac,
                "loyalty": r.loyalty,
                "is_alive": r.is_alive,
            }
            for r in retainer_rows
        ]

    # Load mercenary summaries for PCs (before detaching)
    mercenary_units = []
    if character.character_type == "pc":
        merc_rows = db.query(Mercenary).filter(
            Mercenary.character_id == character.id
        ).all()
        for r in merc_rows:
            info = MERCENARY_TYPES.get(r.merc_type)
            if not info:
                continue
            cost_per = get_unit_cost(r.merc_type, r.race, r.wartime)
            mercenary_units.append({
                "id": r.id,
                "merc_type": r.merc_type,
                "race": r.race,
                "quantity": r.quantity,
                "wartime": r.wartime,
                "name": info["name"],
                "ac": info["ac"],
                "morale": info["morale"],
                "desc": info["desc"],
                "cost_per_unit": cost_per,
                "total_cost": cost_per * r.quantity,
            })

    db.expunge(character)

    # Apply ability score modifiers from items to detached object (clamp 3-18)
    ability_targets = {"strength", "dexterity", "wisdom", "intelligence", "constitution", "charisma"}
    applied_item_mods = {}
    for target, value in item_mods.items():
        if target in ability_targets:
            old = getattr(character, target, 10)
            setattr(character, target, _clamp(old + value))
            applied_item_mods[target] = value
        else:
            applied_item_mods[target] = value

    # Recompute AC and weapons with modified ability scores
    fresh_ac = compute_ac(character, db)
    fresh_weapons = compute_equipped_weapons(character, db, is_gm=gm_view)

    # Override combat_stats on the detached object — no DB write on GET
    cs = dict(character.combat_stats or {})
    cs["equipped_weapons"] = fresh_weapons
    cs["rear_ac"] = fresh_ac["rear_ac"]
    cs["shieldless_ac"] = fresh_ac["shieldless_ac"]
    cs["item_ability_modifiers"] = applied_item_mods
    cs["item_skills"] = item_skills
    cs["item_auras"] = item_auras
    cs["item_round_effects"] = item_round_effects
    character.combat_stats = cs
    character.ac = fresh_ac["ac"]

    # Load specialist entries for PCs (before returning)
    specialist_entries = []
    if character.character_type == "pc":
        spec_rows = db.query(Specialist).filter(
            Specialist.character_id == character.id
        ).all()
        for r in spec_rows:
            info = SPECIALIST_TYPES.get(r.spec_type)
            if not info:
                continue
            specialist_entries.append({
                "id": r.id,
                "spec_type": r.spec_type,
                "task": r.task,
                "name": info["name"],
                "wage": info["wage"],
            })

    # Attach retainer summaries on detached object
    character.__dict__["retainers"] = retainer_summaries
    character.__dict__["mercenaries"] = mercenary_units
    character.__dict__["specialists"] = specialist_entries

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

    # Handle player_id reassignment (GM only)
    if "player_id" in update_data and update_data["player_id"] is not None:
        campaign = db.query(Campaign).filter(Campaign.id == db_character.campaign_id).first()
        if campaign.gm_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the GM can reassign character ownership",
            )
        player_ids = [p.id for p in campaign.players] + [campaign.gm_id]
        if update_data["player_id"] not in player_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target player is not a member of this campaign",
            )

    # Status/is_alive sync
    if "status" in update_data:
        s = update_data["status"]
        if s not in ("active", "independent", "fallen"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value. Must be 'active', 'independent', or 'fallen'.",
            )
        update_data["is_alive"] = (s != "fallen")
    elif "is_alive" in update_data:
        if not update_data["is_alive"]:
            update_data["status"] = "fallen"
        elif db_character.status == "fallen":
            update_data["status"] = "active"

    for field, value in update_data.items():
        setattr(db_character, field, value)

    # Recompute equipped weapons if STR or DEX changed (affects THAC0/damage)
    if "strength" in update_data or "dexterity" in update_data:
        combat_stats = dict(db_character.combat_stats or {})
        combat_stats["equipped_weapons"] = compute_equipped_weapons(db_character, db)
        db_character.combat_stats = combat_stats

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


@router.post("/{character_id}/dismiss", response_model=CharacterSchema)
async def dismiss_retainer(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dismiss a retainer — unlinks from master, becomes a standalone PC/NPC.

    Can be deleted separately if desired. Permissions: master's owner or campaign GM.
    """
    db_character = db.query(Character).filter(Character.id == character_id).first()
    if not db_character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if db_character.character_type != "retainer" or db_character.master_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Character is not a retainer",
        )

    if not can_edit_character(current_user, db_character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the character owner or campaign GM can dismiss retainers",
        )

    db_character.master_id = None
    db_character.character_type = "pc"
    db_character.loyalty = None
    db_character.status = "independent"
    db.commit()
    db.refresh(db_character)
    return db_character


class RehireRequest(BaseModel):
    """Request body for rehiring an independent character as a retainer."""
    master_id: int = Field(..., description="ID of the PC who will be the new master")


@router.post("/{character_id}/rehire", response_model=CharacterSchema)
async def rehire_retainer(
    character_id: int,
    req: RehireRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rehire an independent character as a retainer.

    The target character must have status "independent" and be in the same
    campaign as the master. Standard CHA retainer limits apply.
    """
    db_character = db.query(Character).filter(Character.id == character_id).first()
    if not db_character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if db_character.status != "independent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only independent characters can be rehired as retainers",
        )

    master = db.query(Character).filter(Character.id == req.master_id).first()
    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Master character with id {req.master_id} not found",
        )

    if master.campaign_id != db_character.campaign_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Retainer must be in the same campaign as the master",
        )

    if master.character_type != "pc":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PCs can have retainers",
        )

    if master.status == "fallen":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot hire retainers for a fallen character",
        )

    if not can_edit_character(current_user, master):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the master's owner or campaign GM can rehire retainers",
        )

    # Enforce max retainers from CHA
    cha = _clamp(master.charisma)
    max_retainers = _CHA_MAX_RETAINERS[cha]
    current_retainers = db.query(Character).filter(
        Character.master_id == master.id,
        Character.status != "fallen",
    ).count()
    if current_retainers >= max_retainers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{master.name} already has {current_retainers}/{max_retainers} retainers (CHA {master.charisma})",
        )

    # Rehire: link to master, set loyalty from CHA
    db_character.master_id = master.id
    db_character.character_type = "retainer"
    db_character.status = "active"
    db_character.is_alive = True
    db_character.loyalty = _CHA_LOYALTY[cha]
    db_character.player_id = master.player_id

    db.commit()
    db.refresh(db_character)
    return db_character


@router.post("/{character_id}/award-xp", response_model=CharacterSchema)
async def award_xp(
    character_id: int,
    award: XPAward,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Award XP to a character.

    Only the campaign GM can award XP. The character's total XP is
    increased by the awarded amount.
    """
    db_character = db.query(Character).filter(Character.id == character_id).first()
    if not db_character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_view_character(current_user, db_character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this character",
        )

    # Only the campaign GM can award XP
    if not is_campaign_gm(current_user, db_character.campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the campaign GM can award XP",
        )

    db_character.xp += award.xp
    db.commit()
    db.refresh(db_character)
    return db_character


@router.post("/{character_id}/level-up", response_model=CharacterSchema)
async def level_up(
    character_id: int,
    req: LevelUpRequest = LevelUpRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Level up a character.

    Only the campaign GM can trigger a level-up. Validates that the
    character has sufficient XP for the next level, then increments
    the level and recalculates saving throws, THAC0, and HP from the
    class template.

    hp_increase: The total HP gained this level (die roll + CON mod,
    minimum 1). Computed by the frontend and sent here. If omitted,
    HP is left unchanged (backwards-compatible).
    """
    db_character = db.query(Character).filter(Character.id == character_id).first()
    if not db_character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_view_character(current_user, db_character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this character",
        )

    # Only the campaign GM can level up characters
    if not is_campaign_gm(current_user, db_character.campaign):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the campaign GM can level up characters",
        )

    char_class = db_character.character_class
    class_data = char_class.class_data
    current_level = db_character.level
    next_level = current_level + 1

    # Check max level
    max_level = class_data.get("max_level", 14)
    if current_level >= max_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{db_character.name} is already at the maximum level ({max_level}) for {char_class.name}",
        )

    # Validate XP requirement
    xp_table = class_data.get("xp", [])
    if next_level <= len(xp_table):
        xp_required = xp_table[next_level - 1]
        if db_character.xp < xp_required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{db_character.name} needs {xp_required} XP for level {next_level} "
                    f"({char_class.name}), but only has {db_character.xp} XP"
                ),
            )

    # Increment level
    db_character.level = next_level
    level_index = next_level - 1

    # Apply HP increase if provided
    if req.hp_increase is not None:
        db_character.hp_max += req.hp_increase
        db_character.hp_current += req.hp_increase

    # Recalculate saving throws from class template
    saves = class_data.get("saving_throws", {})
    if saves:
        db_character.saving_throws = {
            key: values[level_index]
            for key, values in saves.items()
            if level_index < len(values)
        }

    # Recalculate THAC0 from class template
    thac0_table = class_data.get("thac0", [])
    combat_stats = dict(db_character.combat_stats or {})
    if thac0_table and level_index < len(thac0_table):
        combat_stats["thac0"] = thac0_table[level_index]

    # Recompute equipped weapons (base THAC0 may have changed)
    combat_stats["equipped_weapons"] = compute_equipped_weapons(db_character, db)
    db_character.combat_stats = combat_stats

    # Recompute AC (class ability modifiers may change at new level)
    ac_values = compute_ac(db_character, db)
    db_character.ac = ac_values["ac"]
    combat_stats["rear_ac"] = ac_values["rear_ac"]
    combat_stats["shieldless_ac"] = ac_values["shieldless_ac"]
    db_character.combat_stats = combat_stats

    db.commit()
    db.refresh(db_character)
    return db_character


@router.get("/{character_id}/spells", response_model=CharacterSpellsResponse)
async def get_character_spells(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a character's spell state: spellbook, memorized list, and slot summary.

    Slots only includes levels where total > 0 (from the class template at current level).
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_view_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this character",
        )

    # Build slot summary from class template
    class_data = character.character_class.class_data
    level_index = character.level - 1

    slots: dict[str, SpellSlotInfo] = {}
    spell_slots_table = class_data.get("spells", {})
    for ordinal, totals in spell_slots_table.items():
        if level_index < len(totals):
            total = totals[level_index]
            if total > 0:
                spell_level = ORDINALS.index(ordinal) + 1
                used = sum(
                    1
                    for m in character.memorized_spells
                    if m.spell_level == spell_level and m.cast
                )
                slots[ordinal] = SpellSlotInfo(total=total, used=used)

    return CharacterSpellsResponse(
        spellbook=character.spells,
        memorized=character.memorized_spells,
        slots=slots,
    )


@router.post("/{character_id}/memorize", response_model=MemorizedSpellEntry, status_code=status.HTTP_201_CREATED)
async def memorize_spell(
    character_id: int,
    request: MemorizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a spell to a character's memorization list.

    Arcane casters (magic-user, illusionist): spell must be in spellbook.
    Divine casters (cleric, druid): any default spell of their class.
    Validates that a slot is available for the spell's level.
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_edit_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the character owner or campaign GM can modify memorized spells",
        )

    class_name = character.character_class.name
    if class_name not in CLASS_SPELL_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{class_name} cannot cast spells",
        )

    spell = db.query(Spell).filter(Spell.id == request.spell_id).first()
    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {request.spell_id} not found",
        )

    # Spell must match the character's caster type
    expected_spell_class = CLASS_SPELL_MAP[class_name]
    if spell.spell_class != expected_spell_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{class_name} can only memorize {expected_spell_class} spells",
        )

    # Arcane: spell must be in spellbook
    if class_name in ARCANE_CLASSES:
        if spell not in character.spells:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arcane casters can only memorize spells from their spellbook",
            )
    # Divine: must be a default spell
    elif class_name in DIVINE_CLASSES:
        if not spell.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Divine casters can only memorize default spells",
            )

    # Check slot availability
    class_data = character.character_class.class_data
    level_index = character.level - 1
    spell_slots_table = class_data.get("spells", {})
    ordinal = level_to_ordinal(spell.level)

    if ordinal not in spell_slots_table:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{class_name} has no {ordinal}-level spell slots",
        )

    totals = spell_slots_table[ordinal]
    total_slots = totals[level_index] if level_index < len(totals) else 0
    if total_slots == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{class_name} has no {ordinal}-level spell slots at level {character.level}",
        )

    current_memorized_count = sum(
        1 for m in character.memorized_spells if m.spell_level == spell.level
    )
    if current_memorized_count >= total_slots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"All {ordinal}-level spell slots are full ({total_slots}/{total_slots})",
        )

    memorized = MemorizedSpell(
        character_id=character_id,
        spell_id=spell.id,
        spell_level=spell.level,
        cast=False,
    )
    db.add(memorized)
    db.commit()
    db.refresh(memorized)
    return memorized


@router.delete("/{character_id}/memorize/{memorized_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unmemorize_spell(
    character_id: int,
    memorized_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a spell from the memorized list by memorized slot ID."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_edit_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the character owner or campaign GM can modify memorized spells",
        )

    memorized = db.query(MemorizedSpell).filter(
        MemorizedSpell.id == memorized_id,
        MemorizedSpell.character_id == character_id,
    ).first()
    if not memorized:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memorized spell slot {memorized_id} not found",
        )

    db.delete(memorized)
    db.commit()
    return None


@router.post("/{character_id}/cast/{memorized_id}", response_model=MemorizedSpellEntry)
async def cast_spell(
    character_id: int,
    memorized_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a memorized spell as cast. Idempotent."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_edit_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the character owner or campaign GM can cast spells",
        )

    memorized = db.query(MemorizedSpell).filter(
        MemorizedSpell.id == memorized_id,
        MemorizedSpell.character_id == character_id,
    ).first()
    if not memorized:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memorized spell slot {memorized_id} not found",
        )

    memorized.cast = True
    db.commit()
    db.refresh(memorized)
    return memorized


@router.post("/{character_id}/rest", response_model=dict)
async def rest(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rest and restore all spell slots.

    Resets cast=False on all memorized spells for the character.
    Returns the number of slots restored.
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_edit_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the character owner or campaign GM can rest this character",
        )

    restored = 0
    for memorized in character.memorized_spells:
        if memorized.cast:
            memorized.cast = False
            restored += 1

    db.commit()
    return {"restored": restored}


def _item_to_public(item: Item) -> ItemPublic:
    """Convert an Item model to ItemPublic, populating revealed_secrets."""
    pub = ItemPublic.model_validate(item)
    pub.revealed_secrets = [
        s["text"] for s in (item.secrets or []) if s.get("revealed")
    ] or None
    return pub


def _item_to_public_masked(item: Item, identified: bool) -> ItemPublic:
    """Convert an Item to ItemPublic, masking magical stats when unidentified."""
    pub = _item_to_public(item)
    if not identified and item.unidentified_name:
        pub.name = item.unidentified_name
        pub.unidentified_name = None  # Don't leak real name hint to player
        if pub.item_metadata:
            masked = dict(pub.item_metadata)
            masked.pop("hit_bonus", None)
            masked.pop("damage_bonus", None)
            masked.pop("qualities", None)
            masked.pop("ability_metadata", None)
            pub.item_metadata = masked
    return pub


class ItemQuantityUpdate(BaseModel):
    """Request body for updating item quantity in inventory."""
    quantity: int = Field(..., ge=0)


@router.get("/{character_id}/items")
async def get_character_items(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a character's inventory with quantities. GMs see full item details including secrets."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_view_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this character",
        )

    rows = db.execute(
        select(
            character_items.c.item_id,
            character_items.c.quantity,
            character_items.c.slot,
            character_items.c.identified,
        )
        .where(character_items.c.character_id == character_id)
    ).fetchall()

    if not rows:
        return []

    item_info = {
        row.item_id: {"quantity": row.quantity, "slot": row.slot, "identified": row.identified}
        for row in rows
    }
    items = db.query(Item).filter(Item.id.in_(item_info.keys())).all()

    gm_view = is_campaign_gm(current_user, character.campaign)

    if gm_view:
        return [
            CharacterInventoryEntryGM(
                item=ItemSchema.model_validate(i),
                quantity=item_info[i.id]["quantity"],
                slot=item_info[i.id]["slot"],
                identified=item_info[i.id]["identified"],
            )
            for i in items
        ]

    return [
        CharacterInventoryEntry(
            item=_item_to_public_masked(i, item_info[i.id]["identified"]),
            quantity=item_info[i.id]["quantity"],
            slot=item_info[i.id]["slot"],
            identified=item_info[i.id]["identified"],
        )
        for i in items
    ]


@router.patch("/{character_id}/items/{item_id}", response_model=CharacterInventoryEntry)
async def update_item_quantity(
    character_id: int,
    item_id: int,
    qty_update: ItemQuantityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set the quantity of an item in a character's inventory."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_edit_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the character owner or campaign GM can update inventory",
        )

    existing_qty = db.execute(
        select(character_items.c.quantity).where(
            (character_items.c.character_id == character_id) &
            (character_items.c.item_id == item_id)
        )
    ).scalar()

    if existing_qty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not in character's inventory",
        )

    db.execute(
        sa_update(character_items)
        .where(
            (character_items.c.character_id == character_id) &
            (character_items.c.item_id == item_id)
        )
        .values(quantity=qty_update.quantity)
    )
    db.commit()

    item = db.query(Item).filter(Item.id == item_id).first()
    return CharacterInventoryEntry(item=_item_to_public(item), quantity=qty_update.quantity)


def _build_inventory(character_id: int, db: Session) -> list[CharacterInventoryEntry]:
    """Helper to build the full inventory list for a character (player view)."""
    rows = db.execute(
        select(
            character_items.c.item_id,
            character_items.c.quantity,
            character_items.c.slot,
            character_items.c.identified,
        )
        .where(character_items.c.character_id == character_id)
    ).fetchall()
    if not rows:
        return []
    item_info = {
        row.item_id: {"quantity": row.quantity, "slot": row.slot, "identified": row.identified}
        for row in rows
    }
    items = db.query(Item).filter(Item.id.in_(item_info.keys())).all()
    return [
        CharacterInventoryEntry(
            item=_item_to_public(i),
            quantity=item_info[i.id]["quantity"],
            slot=item_info[i.id]["slot"],
            identified=item_info[i.id]["identified"],
        )
        for i in items
    ]


VALID_SLOTS = {"armor", "shield", "main-hand", "off-hand", "ammo", "worn"}


class EquipRequest(BaseModel):
    """Optional request body for equipping — only needed for weapons to override default slot."""
    slot: str | None = None


@router.post("/{character_id}/items/{item_id}/equip", response_model=list[CharacterInventoryEntry])
async def equip_item(
    character_id: int,
    item_id: int,
    body: EquipRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Equip an item from the character's inventory.

    Determines the target slot from item type:
    - armor (non-shield) -> "armor"
    - armor with armor_type=="shield" -> "shield"
    - weapon -> "main-hand" (or "off-hand" if specified in body)

    Auto-unequips any item currently in the target slot.
    Recomputes character AC from equipped items.
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail=f"Character with id {character_id} not found")

    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=403, detail="Only the character owner or campaign GM can equip items")

    # Verify item is in inventory
    row = db.execute(
        select(character_items.c.item_id)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not in character's inventory")

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item or not item.equippable:
        raise HTTPException(status_code=400, detail="Item is not equippable")

    # Determine target slot
    if item.item_type == "armor":
        armor_type = (item.item_metadata or {}).get("armor_type", "")
        target_slot = "shield" if armor_type == "shield" else "armor"
    elif item.item_type == "weapon":
        requested = body.slot if body else None
        if requested and requested in ("main-hand", "off-hand"):
            target_slot = requested
        else:
            target_slot = "main-hand"
    elif item.item_type == "ammo":
        target_slot = "ammo"
    elif item.equippable:
        # Rings, wondrous items, etc. — "worn" slot (multiple allowed)
        target_slot = "worn"
    else:
        raise HTTPException(status_code=400, detail=f"Cannot determine equipment slot for item type '{item.item_type}'")

    # Auto-unequip any item currently in the target slot
    # (skip for "worn" — multiple rings/gloves can be worn simultaneously)
    if target_slot != "worn":
        db.execute(
            sa_update(character_items)
            .where(
                (character_items.c.character_id == character_id)
                & (character_items.c.slot == target_slot)
            )
            .values(slot=None)
        )

    # Set slot on the target item
    db.execute(
        sa_update(character_items)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
        .values(slot=target_slot)
    )

    # Recompute AC
    db.flush()
    ac_values = compute_ac(character, db)
    character.ac = ac_values["ac"]
    combat_stats = dict(character.combat_stats or {})
    combat_stats["rear_ac"] = ac_values["rear_ac"]
    combat_stats["shieldless_ac"] = ac_values["shieldless_ac"]

    # Recompute equipped weapons
    combat_stats["equipped_weapons"] = compute_equipped_weapons(character, db)
    character.combat_stats = combat_stats

    db.commit()
    db.refresh(character)
    return _build_inventory(character_id, db)


@router.post("/{character_id}/items/{item_id}/unequip", response_model=list[CharacterInventoryEntry])
async def unequip_item(
    character_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unequip an item (set slot to null).

    Recomputes character AC from remaining equipped items.
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail=f"Character with id {character_id} not found")

    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=403, detail="Only the character owner or campaign GM can unequip items")

    # Verify item is in inventory
    row = db.execute(
        select(character_items.c.slot)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not in character's inventory")

    # Set slot to null
    db.execute(
        sa_update(character_items)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
        .values(slot=None)
    )

    # Recompute AC
    db.flush()
    ac_values = compute_ac(character, db)
    character.ac = ac_values["ac"]
    combat_stats = dict(character.combat_stats or {})
    combat_stats["rear_ac"] = ac_values["rear_ac"]
    combat_stats["shieldless_ac"] = ac_values["shieldless_ac"]

    # Recompute equipped weapons
    combat_stats["equipped_weapons"] = compute_equipped_weapons(character, db)
    character.combat_stats = combat_stats

    db.commit()
    db.refresh(character)
    return _build_inventory(character_id, db)


@router.patch("/{character_id}/items/{item_id}/identify", response_model=CharacterInventoryEntryGM)
async def identify_item(
    character_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an item in a character's inventory as identified. GM only."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail=f"Character with id {character_id} not found")

    if not is_campaign_gm(current_user, character.campaign):
        raise HTTPException(status_code=403, detail="Only the campaign GM can identify items")

    row = db.execute(
        select(character_items.c.item_id)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not in character's inventory")

    db.execute(
        sa_update(character_items)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
        .values(identified=True)
    )
    db.commit()

    item = db.query(Item).filter(Item.id == item_id).first()
    info = db.execute(
        select(character_items.c.quantity, character_items.c.slot, character_items.c.identified)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
    ).first()

    return CharacterInventoryEntryGM(
        item=ItemSchema.model_validate(item),
        quantity=info.quantity,
        slot=info.slot,
        identified=info.identified,
    )


@router.get("/{character_id}/item-abilities")
async def get_item_abilities(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get grouped item abilities for a character (equipped + identified items only)."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    if not can_view_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this character",
        )

    return {
        "modifiers": get_item_ability_modifiers(character.id, db),
        "skills": get_item_skills(character.id, db),
        "auras": get_item_auras(character.id, db),
        "round_effects": get_item_round_effects(character.id, db),
    }
