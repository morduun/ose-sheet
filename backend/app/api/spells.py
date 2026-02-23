"""Spells CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Spell, Character, User
from app.schemas import (
    Spell as SpellSchema,
    SpellCreate,
    SpellBatchCreate,
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
    Create a new spell. Requires admin privileges.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to create spells",
        )

    db_spell = Spell(**spell.model_dump())
    db.add(db_spell)
    db.commit()
    db.refresh(db_spell)
    return db_spell


@router.post("/batch", response_model=list[SpellSchema], status_code=status.HTTP_201_CREATED)
async def batch_create_spells(
    batch: SpellBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Batch-create spells from a list. Requires admin privileges.

    Spells with a duplicate (name, spell_class) pair are skipped (idempotent).
    Returns only newly created spells.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to batch-create spells",
        )

    created = []
    for spell_data in batch.spells:
        existing = (
            db.query(Spell)
            .filter(Spell.name == spell_data.name, Spell.spell_class == spell_data.spell_class)
            .first()
        )
        if existing:
            continue
        db_spell = Spell(**spell_data.model_dump())
        db.add(db_spell)
        created.append(db_spell)

    db.commit()
    for s in created:
        db.refresh(s)
    return created


@router.get("/", response_model=list[SpellSchema])
async def list_spells(
    level: int | None = None,
    spell_class: str | None = None,
    name: str | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List spells, optionally filtered by level, spell_class, and/or name.

    Name filter is case-insensitive exact match. Useful for looking up a
    specific spell across all classes (e.g. name=Light returns cleric,
    magic-user, and illusionist versions).
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

    if name:
        query = query.filter(Spell.name.ilike(name))

    return query.order_by(Spell.spell_class, Spell.level, Spell.name).offset(skip).limit(limit).all()


@router.get("/{spell_id}", response_model=SpellSchema)
async def get_spell(
    spell_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a spell by ID."""
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
    """Update a spell. Requires admin privileges."""
    db_spell = db.query(Spell).filter(Spell.id == spell_id).first()
    if not db_spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found",
        )

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to update spells",
        )

    for field, value in spell_update.model_dump(exclude_unset=True).items():
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
    """Delete a spell. Requires admin privileges."""
    db_spell = db.query(Spell).filter(Spell.id == spell_id).first()
    if not db_spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found",
        )

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to delete spells",
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

    Must be the character owner or campaign GM.
    """
    spell = db.query(Spell).filter(Spell.id == spell_id).first()
    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found",
        )

    character = db.query(Character).filter(Character.id == assignment.character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {assignment.character_id} not found",
        )

    if not can_edit_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add spells to your own characters or as campaign GM",
        )

    if spell in character.spells:
        return {"message": "Spell already in character's spellbook"}

    character.spells.append(spell)
    db.commit()
    return {"message": f"Spell '{spell.name}' added to {character.name}'s spellbook"}


@router.delete("/{spell_id}/forget/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_spell_from_spellbook(
    spell_id: int,
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a spell from a character's spellbook.

    Must be the character owner or campaign GM.
    """
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )

    spell = db.query(Spell).filter(Spell.id == spell_id).first()
    if not spell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spell with id {spell_id} not found",
        )

    if not can_edit_character(current_user, character):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only remove spells from your own characters or as campaign GM",
        )

    if spell in character.spells:
        character.spells.remove(spell)
        db.commit()

    return None
