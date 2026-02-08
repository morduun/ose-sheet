"""Spells CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Spell, Character, User
from app.schemas import (
    Spell as SpellSchema,
    SpellCreate,
    SpellUpdate,
    CharacterSpellAssignment,
)
from app.services.permissions import can_edit_character

router = APIRouter()


@router.post("/", response_model=SpellSchema, status_code=status.HTTP_201_CREATED)
async def create_spell(
    spell: SpellCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new spell.

    Phase 2: Any authenticated user can create (for testing)
    Phase 3: Admin-only for seeding spell database
    """
    db_spell = Spell(**spell.model_dump())
    db.add(db_spell)
    db.commit()
    db.refresh(db_spell)
    return db_spell


@router.get("/", response_model=list[SpellSchema])
async def list_spells(
    level: int | None = None,
    spell_class: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List spells.

    Filters:
    - level: Spell level (1-6)
    - spell_class: Class that can cast (magic-user, cleric, elf, druid)
    """
    query = db.query(Spell)

    if level is not None:
        if level < 1 or level > 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spell level must be between 1 and 6",
            )
        query = query.filter(Spell.level == level)

    if spell_class:
        query = query.filter(Spell.spell_class == spell_class)

    spells = query.offset(skip).limit(limit).all()
    return spells


@router.get("/{spell_id}", response_model=SpellSchema)
async def get_spell(
    spell_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get spell details by ID."""
    spell = db.query(Spell).filter(Spell.id == spell_id).first()
    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found",
        )
    return spell


@router.patch("/{spell_id}", response_model=SpellSchema)
async def update_spell(
    spell_id: int,
    spell_update: SpellUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a spell.

    Phase 2: Any authenticated user can update (for testing)
    Phase 3: Admin-only
    """
    db_spell = db.query(Spell).filter(Spell.id == spell_id).first()
    if not db_spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found",
        )

    # Update only provided fields
    update_data = spell_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_spell, field, value)

    db.commit()
    db.refresh(db_spell)
    return db_spell


@router.delete("/{spell_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spell(
    spell_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a spell.

    Phase 2: Any authenticated user can delete (for testing)
    Phase 3: Admin-only
    """
    db_spell = db.query(Spell).filter(Spell.id == spell_id).first()
    if not db_spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found",
        )

    db.delete(db_spell)
    db.commit()
    return None


@router.post("/{spell_id}/learn", response_model=dict)
async def add_spell_to_spellbook(
    spell_id: int,
    assignment: CharacterSpellAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a spell to a character's spellbook.

    Must be character owner or campaign GM.
    """
    # Verify spell exists
    spell = db.query(Spell).filter(Spell.id == spell_id).first()
    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found",
        )

    # Verify character exists
    character = db.query(Character).filter(Character.id == assignment.character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {assignment.character_id} not found",
        )

    # Check if user can edit this character
    if not can_edit_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add spells to your own characters or as campaign GM",
        )

    # Check if spell is already in spellbook
    if spell in character.spells:
        return {"message": "Spell already in character's spellbook"}

    # Add spell to spellbook
    character.spells.append(spell)
    db.commit()

    return {"message": f"Spell {spell.name} added to {character.name}'s spellbook"}


@router.delete("/{spell_id}/forget/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_spell_from_spellbook(
    spell_id: int,
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a spell from a character's spellbook.

    Must be character owner or campaign GM.
    """
    # Verify character exists
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    # Verify spell exists
    spell = db.query(Spell).filter(Spell.id == spell_id).first()
    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found",
        )

    # Check if user can edit this character
    if not can_edit_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove spells from your own characters or as campaign GM",
        )

    # Remove spell from spellbook
    if spell in character.spells:
        character.spells.remove(spell)
        db.commit()

    return None
