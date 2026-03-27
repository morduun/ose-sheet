from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Character, Campaign, CharacterClass, User, Spell, MemorizedSpell, Item, Mercenary, Specialist, Monster
from app.models.item import character_items
from app.schemas import (
    Character as CharacterSchema,
    CharacterCreate,
    CharacterUpdate,
    MonsterRetainerCreate,
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
    compute_encumbrance,
    compute_equipped_weapons,
    get_item_ability_modifiers,
    get_item_skills,
    get_item_auras,
    get_item_round_effects,
)

# Spell caster mappings
ARCANE_SPELL_LISTS = {"magic-user", "illusionist"}
DIVINE_SPELL_LISTS = {"cleric", "druid"}
ORDINALS = ["1st", "2nd", "3rd", "4th", "5th", "6th"]


def _get_casting_info(character):
    """
    Derive spell class and casting type from class_data.spell_lists.
    Returns (spell_list_name, is_arcane, is_divine) or (None, False, False) for non-casters.
    """
    class_data = character.character_class.class_data if character.character_class else {}
    spell_lists = class_data.get("spell_lists", [])
    if not spell_lists:
        return None, False, False
    spell_list = spell_lists[0]["list"]
    is_arcane = spell_list in ARCANE_SPELL_LISTS
    is_divine = spell_list in DIVINE_SPELL_LISTS
    return spell_list, is_arcane, is_divine


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

    # Validate character class exists (if provided)
    char_class = None
    if character.character_class_id is not None:
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
    else:
        # Only retainers can have no class (monster retainers)
        if character.character_type != "retainer":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only retainers can be created without a character class",
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
    level = character_data.get("level", 1)
    level_index = max(0, level - 1)
    class_data = char_class.class_data if char_class else {}

    # Level 0 "Normal Man" stats (OSE: THAC0 20, saves D14/W15/P16/B17/S18)
    is_level_zero = level < 1

    # Auto-populate saving throws from class template if not provided
    if not character_data.get("saving_throws"):
        if is_level_zero:
            character_data["saving_throws"] = {
                "death": 14, "wands": 15, "paralyze": 16, "breath": 17, "spells": 18,
            }
        else:
            saves = class_data.get("saving_throws", {})
            if saves:
                character_data["saving_throws"] = {
                    key: values[level_index]
                    for key, values in saves.items()
                    if level_index < len(values)
                }

    # Auto-populate combat stats (THAC0) from class template if not provided
    if not character_data.get("combat_stats"):
        if is_level_zero:
            character_data["combat_stats"] = {"thac0": 20}
        else:
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
                "character_class_name": r.character_class.name if r.character_class else (r.combat_stats or {}).get("monster_name"),
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
    enc = compute_encumbrance(character, db)
    cs["encumbrance"] = enc["encumbrance"]
    cs["effective_movement"] = enc["effective_movement"]
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


import re as _re


@router.post("/{master_id}/retainers/from-monster", response_model=CharacterSchema)
async def create_retainer_from_monster(
    master_id: int,
    req: MonsterRetainerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a retainer from a monster (e.g. an adopted goblin or pet).

    Maps monster stats to a Character record with no character class.
    """
    # Validate master
    master = db.query(Character).filter(Character.id == master_id).first()
    if not master:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {master_id} not found",
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
    if not can_edit_character(current_user, master):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the master's owner or campaign GM can adopt monster retainers",
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

    # Validate monster exists and is accessible
    monster = db.query(Monster).filter(Monster.id == req.monster_id).first()
    if not monster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monster with id {req.monster_id} not found",
        )
    if not monster.is_default and monster.campaign_id != master.campaign_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Monster is not available for this campaign",
        )

    # Parse movement rate: "120' (40')" → 120; None → 120
    movement = 120
    if monster.movement_rate:
        m = _re.search(r"(\d+)", monster.movement_rate)
        if m:
            movement = int(m.group(1))

    # Build combat_stats with monster_name for display
    combat_stats = {
        "thac0": monster.thac0,
        "monster_name": monster.name,
        "monster_id": monster.id,
    }

    # Build notes from monster description and abilities
    notes_parts = []
    if monster.description:
        notes_parts.append(monster.description)
    meta = monster.monster_metadata or {}
    if meta.get("abilities"):
        for aname, adesc in meta["abilities"].items():
            notes_parts.append(f"**{aname}:** {adesc}")
    notes = "\n\n".join(notes_parts) if notes_parts else None

    # Build saving throws from monster metadata
    saving_throws = None
    saves = meta.get("saves")
    if saves:
        saving_throws = {
            "death": saves.get("D"),
            "wands": saves.get("W"),
            "paralyze": saves.get("P"),
            "breath": saves.get("B"),
            "spells": saves.get("S"),
        }

    loyalty = _CHA_LOYALTY[cha]

    db_character = Character(
        name=req.name,
        campaign_id=master.campaign_id,
        player_id=master.player_id,
        master_id=master.id,
        character_type="retainer",
        character_class_id=None,
        level=1,
        alignment=monster.alignment,
        hp_max=monster.hp or 1,
        hp_current=monster.hp or 1,
        ac=monster.ac if monster.ac is not None else 9,
        movement_rate=movement,
        saving_throws=saving_throws,
        combat_stats=combat_stats,
        loyalty=loyalty,
        notes=notes,
    )
    db.add(db_character)
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
    if char_class is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Monster retainers cannot level up",
        )
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
    level_index = max(0, character.level - 1)

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

    class_name = character.character_class.name if character.character_class else "Unknown"
    spell_list, is_arcane, is_divine = _get_casting_info(character)
    if not spell_list:
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

    # Spell must match the character's spell list
    if spell.spell_class != spell_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{class_name} can only memorize {spell_list} spells",
        )

    # Arcane: spell must be in spellbook
    if is_arcane:
        if spell not in character.spells:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arcane casters can only memorize spells from their spellbook",
            )
    # Divine: must be a default spell
    elif is_divine:
        if not spell.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Divine casters can only memorize default spells",
            )

    # Check slot availability
    class_data = character.character_class.class_data
    level_index = max(0, character.level - 1)
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
            character_items.c.container_item_id,
            character_items.c.dropped,
            character_items.c.stashed,
            character_items.c.state,
        )
        .where(character_items.c.character_id == character_id)
    ).fetchall()

    if not rows:
        return []

    item_info = {
        row.item_id: {
            "quantity": row.quantity,
            "slot": row.slot,
            "identified": row.identified,
            "container_item_id": row.container_item_id,
            "dropped": row.dropped,
            "stashed": row.stashed,
            "state": row.state,
        }
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
                container_item_id=item_info[i.id]["container_item_id"],
                dropped=item_info[i.id]["dropped"],
                stashed=item_info[i.id]["stashed"],
                state=item_info[i.id]["state"],
            )
            for i in items
        ]

    return [
        CharacterInventoryEntry(
            item=_item_to_public_masked(i, item_info[i.id]["identified"]),
            quantity=item_info[i.id]["quantity"],
            slot=item_info[i.id]["slot"],
            identified=item_info[i.id]["identified"],
            container_item_id=item_info[i.id]["container_item_id"],
            dropped=item_info[i.id]["dropped"],
            stashed=item_info[i.id]["stashed"],
            state=item_info[i.id]["state"],
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

    existing = db.execute(
        select(
            character_items.c.quantity,
            character_items.c.slot,
            character_items.c.identified,
            character_items.c.container_item_id,
            character_items.c.dropped,
            character_items.c.stashed,
            character_items.c.state,
        ).where(
            (character_items.c.character_id == character_id) &
            (character_items.c.item_id == item_id)
        )
    ).first()

    if existing is None:
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
    return CharacterInventoryEntry(
        item=_item_to_public(item),
        quantity=qty_update.quantity,
        slot=existing.slot,
        identified=existing.identified,
        container_item_id=existing.container_item_id,
        dropped=existing.dropped,
        stashed=existing.stashed if hasattr(existing, 'stashed') else False,
        state=existing.state,
    )


def _build_inventory(character_id: int, db: Session) -> list[CharacterInventoryEntry]:
    """Helper to build the full inventory list for a character (player view)."""
    rows = db.execute(
        select(
            character_items.c.item_id,
            character_items.c.quantity,
            character_items.c.slot,
            character_items.c.identified,
            character_items.c.container_item_id,
            character_items.c.dropped,
            character_items.c.stashed,
            character_items.c.state,
        )
        .where(character_items.c.character_id == character_id)
    ).fetchall()
    if not rows:
        return []
    item_info = {
        row.item_id: {
            "quantity": row.quantity,
            "slot": row.slot,
            "identified": row.identified,
            "container_item_id": row.container_item_id,
            "dropped": row.dropped,
            "stashed": row.stashed,
            "state": row.state,
        }
        for row in rows
    }
    items = db.query(Item).filter(Item.id.in_(item_info.keys())).all()
    return [
        CharacterInventoryEntry(
            item=_item_to_public(i),
            quantity=item_info[i.id]["quantity"],
            slot=item_info[i.id]["slot"],
            identified=item_info[i.id]["identified"],
            container_item_id=item_info[i.id]["container_item_id"],
            dropped=item_info[i.id]["dropped"],
            stashed=item_info[i.id]["stashed"],
            state=item_info[i.id]["state"],
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
        select(character_items.c.item_id, character_items.c.container_item_id)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not in character's inventory")

    # Block equipping items inside a dropped container
    if row.container_item_id is not None:
        container_dropped = db.execute(
            select(character_items.c.dropped)
            .where(
                (character_items.c.character_id == character_id)
                & (character_items.c.item_id == row.container_item_id)
            )
        ).scalar()
        if container_dropped:
            raise HTTPException(
                status_code=400,
                detail="Cannot equip an item from a dropped container — pick it up first",
            )

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item or not item.equippable:
        raise HTTPException(status_code=400, detail="Item is not equippable")

    # Determine target slot
    if item.item_type == "armor":
        armor_type = (item.item_metadata or {}).get("armor_type", "")
        target_slot = "shield" if armor_type == "shield" else "armor"

        # Block shield when two-handed weapon is equipped
        if target_slot == "shield":
            mh_row = db.execute(
                select(character_items.c.item_id)
                .where(
                    (character_items.c.character_id == character_id)
                    & (character_items.c.slot == "main-hand")
                )
            ).first()
            if mh_row:
                mh_item = db.query(Item).filter(Item.id == mh_row.item_id).first()
                if mh_item and "two-handed" in (mh_item.item_metadata or {}).get("qualities", []):
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot equip a shield while a two-handed weapon is in the main hand",
                    )
    elif item.item_type == "weapon":
        requested = body.slot if body else None
        if requested and requested in ("main-hand", "off-hand"):
            target_slot = requested
        else:
            target_slot = "main-hand"

        # Two-handed weapon validation
        qualities = (item.item_metadata or {}).get("qualities", [])
        is_two_handed = "two-handed" in qualities

        if is_two_handed and target_slot == "off-hand":
            raise HTTPException(
                status_code=400,
                detail="A two-handed weapon must be equipped in the main hand",
            )

        # Check current equipment for conflicts
        current_slots = {
            row.slot: row.item_id
            for row in db.execute(
                select(character_items.c.slot, character_items.c.item_id)
                .where(
                    (character_items.c.character_id == character_id)
                    & (character_items.c.slot.in_(["main-hand", "off-hand"]))
                )
            ).fetchall()
        }

        if is_two_handed and "off-hand" in current_slots:
            raise HTTPException(
                status_code=400,
                detail="Cannot equip a two-handed weapon while an off-hand item is equipped",
            )

        if target_slot == "off-hand" and "main-hand" in current_slots:
            mh_item = db.query(Item).filter(Item.id == current_slots["main-hand"]).first()
            if mh_item and "two-handed" in (mh_item.item_metadata or {}).get("qualities", []):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot equip an off-hand item while a two-handed weapon is in the main hand",
                )
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


class StashItemRequest(BaseModel):
    """Stash or unstash an item (home base storage)."""
    stashed: bool


@router.post("/{character_id}/items/{item_id}/stash", response_model=list[CharacterInventoryEntry])
async def stash_item(
    character_id: int,
    item_id: int,
    body: StashItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move an item to/from home base stash. Stashed items don't count toward encumbrance."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail=f"Character with id {character_id} not found")
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=403, detail="Only the character owner or campaign GM can stash items")

    row = db.execute(
        select(character_items.c.item_id, character_items.c.slot)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not in character's inventory")

    # Must unequip before stashing
    if body.stashed and row.slot:
        raise HTTPException(status_code=400, detail="Unequip the item before stashing it")

    db.execute(
        sa_update(character_items)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
        .values(stashed=body.stashed, container_item_id=None if body.stashed else None)
    )
    db.commit()
    return _build_inventory(character_id, db)


class ItemStateUpdate(BaseModel):
    """Update per-character item state (fill level, contents, etc.)."""
    state: dict


@router.patch("/{character_id}/items/{item_id}/state", response_model=CharacterInventoryEntry)
async def update_item_state(
    character_id: int,
    item_id: int,
    body: ItemStateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update per-character item state (fill level, contents, etc.)."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail=f"Character with id {character_id} not found")
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=403, detail="Only the character owner or campaign GM can update item state")

    existing = db.execute(
        select(
            character_items.c.quantity,
            character_items.c.slot,
            character_items.c.identified,
            character_items.c.container_item_id,
            character_items.c.dropped,
            character_items.c.stashed,
            character_items.c.state,
        ).where(
            (character_items.c.character_id == character_id) &
            (character_items.c.item_id == item_id)
        )
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Item not in character's inventory")

    # Merge new state with existing
    merged = dict(existing.state or {})
    merged.update(body.state)

    db.execute(
        sa_update(character_items)
        .where(
            (character_items.c.character_id == character_id) &
            (character_items.c.item_id == item_id)
        )
        .values(state=merged)
    )
    db.commit()

    item = db.query(Item).filter(Item.id == item_id).first()
    return CharacterInventoryEntry(
        item=_item_to_public(item),
        quantity=existing.quantity,
        slot=existing.slot,
        identified=existing.identified,
        container_item_id=existing.container_item_id,
        dropped=existing.dropped,
        state=merged,
    )


class MoveItemRequest(BaseModel):
    """Move an item into or out of a container."""
    container_item_id: int | None = None  # null = remove from container


class DropContainerRequest(BaseModel):
    """Drop or pick up a container."""
    dropped: bool


@router.post("/{character_id}/items/{item_id}/move", response_model=list[CharacterInventoryEntry])
async def move_item_to_container(
    character_id: int,
    item_id: int,
    body: MoveItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move an item into or out of a container."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail=f"Character with id {character_id} not found")
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=403, detail="Only the character owner or campaign GM can move items")

    # Verify item is in inventory
    row = db.execute(
        select(character_items.c.item_id, character_items.c.slot, character_items.c.quantity)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Item not in character's inventory")

    item = db.query(Item).filter(Item.id == item_id).first()

    if body.container_item_id is not None:
        # Moving INTO a container — validate
        # Cannot nest containers
        if item and (item.item_metadata or {}).get("capacity"):
            raise HTTPException(status_code=400, detail="Cannot place a container inside another container")

        # Must unequip first
        if row.slot:
            raise HTTPException(status_code=400, detail="Unequip the item before placing it in a container")

        # Verify container is in inventory and is a container
        container_row = db.execute(
            select(character_items.c.item_id)
            .where(
                (character_items.c.character_id == character_id)
                & (character_items.c.item_id == body.container_item_id)
            )
        ).first()
        if not container_row:
            raise HTTPException(status_code=404, detail="Container not in character's inventory")

        container_item = db.query(Item).filter(Item.id == body.container_item_id).first()
        capacity = (container_item.item_metadata or {}).get("capacity") if container_item else None
        if not capacity:
            raise HTTPException(status_code=400, detail="Target item is not a container")

        # Check capacity — sum current contents weight
        content_rows = db.execute(
            select(character_items.c.item_id, character_items.c.quantity)
            .where(
                (character_items.c.character_id == character_id)
                & (character_items.c.container_item_id == body.container_item_id)
                & (character_items.c.item_id != item_id)  # exclude self if already in this container
            )
        ).fetchall()
        current_load = 0
        if content_rows:
            content_items = db.query(Item).filter(
                Item.id.in_([r.item_id for r in content_rows])
            ).all()
            weight_map = {i.id: i.weight or 0 for i in content_items}
            for r in content_rows:
                current_load += weight_map.get(r.item_id, 0) * r.quantity

        item_weight = (item.weight or 0) * row.quantity
        if current_load + item_weight > capacity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough room — {current_load + item_weight:.0f}/{capacity} coins (need {item_weight:.0f} free)",
            )

    # Update container assignment
    db.execute(
        sa_update(character_items)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
        .values(container_item_id=body.container_item_id)
    )
    db.commit()
    return _build_inventory(character_id, db)


@router.post("/{character_id}/items/{item_id}/drop", response_model=list[CharacterInventoryEntry])
async def drop_or_pickup_container(
    character_id: int,
    item_id: int,
    body: DropContainerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Drop or pick up a container. Dropped containers and their contents don't count toward encumbrance."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail=f"Character with id {character_id} not found")
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=403, detail="Only the character owner or campaign GM can drop items")

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

    # Verify item is a container
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item or not (item.item_metadata or {}).get("capacity"):
        raise HTTPException(status_code=400, detail="Only containers can be dropped")

    db.execute(
        sa_update(character_items)
        .where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == item_id)
        )
        .values(dropped=body.dropped)
    )

    # Recompute encumbrance and movement
    db.flush()
    enc = compute_encumbrance(character, db)
    combat_stats = dict(character.combat_stats or {})
    combat_stats["effective_movement"] = enc["effective_movement"]
    combat_stats["encumbrance"] = enc["encumbrance"]
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
