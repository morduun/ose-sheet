"""API endpoints for character animal companions."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Character
from app.models.animal import CharacterAnimal
from app.schemas.animal import (
    AnimalTypeInfo,
    AnimalCreate,
    AnimalUpdate,
    AnimalResponse,
)
from app.services.animals import ANIMAL_TYPES, compute_animal_load
from app.services.permissions import can_view_character, can_edit_character


types_router = APIRouter()
router = APIRouter()


def _animal_response(a: CharacterAnimal) -> AnimalResponse:
    load = compute_animal_load(a)
    return AnimalResponse(
        id=a.id,
        character_id=a.character_id,
        name=a.name,
        animal_type=a.animal_type,
        hp_max=a.hp_max,
        hp_current=a.hp_current,
        ac=a.ac,
        effective_ac=load["effective_ac"],
        morale=a.morale,
        hit_dice=a.hit_dice,
        base_movement=a.base_movement,
        encumbered_movement=a.encumbered_movement,
        effective_movement=load["effective_movement"],
        base_load=a.base_load,
        max_load=a.max_load,
        current_load=load["current_load"],
        container_capacity=load["container_capacity"],
        load_tier=load["load_tier"],
        source=a.source or "purchased",
        attacks=a.attacks or [],
        abilities=a.abilities or {},
        equipment=a.equipment or {},
        inventory=a.inventory or [],
        notes=a.notes,
    )


# --- Animal Types ---

@types_router.get("", response_model=list[AnimalTypeInfo])
async def list_animal_types(current_user: User = Depends(get_current_user)):
    """List all available animal types."""
    return [AnimalTypeInfo(key=k, **v) for k, v in ANIMAL_TYPES.items()]


# --- Character Animals ---

@router.get("", response_model=list[AnimalResponse])
async def list_animals(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all animals for a character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if not can_view_character(current_user, character):
        raise HTTPException(status_code=403, detail="Access denied")

    animals = db.query(CharacterAnimal).filter(
        CharacterAnimal.character_id == character_id
    ).all()
    return [_animal_response(a) for a in animals]


@router.post("", response_model=AnimalResponse, status_code=status.HTTP_201_CREATED)
async def add_animal(
    character_id: int,
    req: AnimalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an animal to a character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=403, detail="Access denied")

    atype = ANIMAL_TYPES.get(req.animal_type)
    if not atype:
        raise HTTPException(status_code=400, detail=f"Unknown animal type: {req.animal_type}")

    animal = CharacterAnimal(
        character_id=character_id,
        name=req.name or atype["name"],
        animal_type=req.animal_type,
        hp_max=atype["hp"],
        hp_current=atype["hp"],
        ac=atype["ac"],
        morale=atype["morale"],
        hit_dice=atype["hit_dice"],
        base_movement=atype["base_movement"],
        encumbered_movement=atype.get("encumbered_movement"),
        base_load=atype.get("base_load"),
        max_load=atype.get("max_load"),
        source=req.source,
        attacks=atype.get("attacks", []),
        abilities=atype.get("abilities", {}),
        equipment={},
        inventory=[],
    )
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return _animal_response(animal)


@router.patch("/{animal_id}", response_model=AnimalResponse)
async def update_animal(
    character_id: int,
    animal_id: int,
    req: AnimalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an animal's name, HP, equipment, inventory, or notes."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=403, detail="Access denied")

    animal = db.query(CharacterAnimal).filter(
        CharacterAnimal.id == animal_id,
        CharacterAnimal.character_id == character_id,
    ).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    if req.name is not None:
        animal.name = req.name
    if req.hp_current is not None:
        animal.hp_current = max(0, min(req.hp_current, animal.hp_max))
    if req.equipment is not None:
        animal.equipment = {**(animal.equipment or {}), **req.equipment}
    if req.inventory is not None:
        animal.inventory = req.inventory
    if req.notes is not None:
        animal.notes = req.notes
    if req.source is not None:
        animal.source = req.source

    db.commit()
    db.refresh(animal)
    return _animal_response(animal)


@router.delete("/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_animal(
    character_id: int,
    animal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an animal from a character."""
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=403, detail="Access denied")

    animal = db.query(CharacterAnimal).filter(
        CharacterAnimal.id == animal_id,
        CharacterAnimal.character_id == character_id,
    ).first()
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    db.delete(animal)
    db.commit()
