"""API endpoints for character animal companions."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from sqlalchemy import select, update as sa_update, delete as sa_delete
from app.models import User, Character, Item
from app.models.animal import CharacterAnimal
from app.models.item import character_items
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

    if atype:
        # Template animal
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
    else:
        # Custom animal — require name and basic stats
        if not req.name:
            raise HTTPException(status_code=400, detail="Custom animals require a name")
        if req.hp is None or req.ac is None or req.hit_dice is None or req.base_movement is None:
            raise HTTPException(status_code=400, detail="Custom animals require hp, ac, hit_dice, and base_movement")

        animal = CharacterAnimal(
            character_id=character_id,
            name=req.name,
            animal_type=req.animal_type,
            hp_max=req.hp,
            hp_current=req.hp,
            ac=req.ac,
            morale=req.morale or 6,
            hit_dice=req.hit_dice,
            base_movement=req.base_movement,
            encumbered_movement=req.encumbered_movement,
            base_load=req.base_load,
            max_load=req.max_load,
            source=req.source,
            attacks=req.attacks or [],
            abilities=req.abilities or {},
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
    if req.animal_type is not None:
        animal.animal_type = req.animal_type
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


class AnimalLoadRequest(BaseModel):
    item_id: int
    quantity: int = 1


@router.post("/{animal_id}/load", response_model=AnimalResponse)
async def load_item_to_animal(
    character_id: int,
    animal_id: int,
    req: AnimalLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move an item from character inventory to an animal's inventory."""
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

    # Check animal has container capacity
    load = compute_animal_load(animal)
    if load["container_capacity"] <= 0:
        raise HTTPException(status_code=400, detail="Animal has no pack or saddlebags equipped")

    # Check character has the item
    char_qty = db.execute(
        select(character_items.c.quantity).where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == req.item_id)
        )
    ).scalar()
    if char_qty is None or char_qty < req.quantity:
        raise HTTPException(status_code=400, detail=f"Not enough in inventory (has: {char_qty or 0})")

    # Check weight fits
    item = db.query(Item).filter(Item.id == req.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item_weight = (item.weight or 0) * req.quantity
    if load["current_load"] + item_weight > load["container_capacity"]:
        raise HTTPException(status_code=400, detail="Too heavy for this animal's pack")

    # Remove from character
    new_qty = char_qty - req.quantity
    if new_qty <= 0:
        db.execute(
            sa_delete(character_items).where(
                (character_items.c.character_id == character_id)
                & (character_items.c.item_id == req.item_id)
            )
        )
    else:
        db.execute(
            sa_update(character_items).where(
                (character_items.c.character_id == character_id)
                & (character_items.c.item_id == req.item_id)
            ).values(quantity=new_qty)
        )

    # Add to animal inventory
    from sqlalchemy.orm.attributes import flag_modified
    inv = list(animal.inventory or [])
    existing = next((e for e in inv if e["item_id"] == req.item_id), None)
    if existing:
        existing["quantity"] = existing.get("quantity", 0) + req.quantity
    else:
        inv.append({"item_id": req.item_id, "quantity": req.quantity, "name": item.name, "weight": item.weight or 0})
    animal.inventory = inv
    flag_modified(animal, "inventory")

    db.commit()
    db.refresh(animal)
    return _animal_response(animal)


@router.post("/{animal_id}/unload", response_model=AnimalResponse)
async def unload_item_from_animal(
    character_id: int,
    animal_id: int,
    req: AnimalLoadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move an item from an animal's inventory back to the character."""
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

    # Check animal has the item
    from sqlalchemy.orm.attributes import flag_modified
    inv = list(animal.inventory or [])
    entry = next((e for e in inv if e["item_id"] == req.item_id), None)
    if not entry or entry.get("quantity", 0) < req.quantity:
        raise HTTPException(status_code=400, detail="Animal doesn't have enough of this item")

    # Remove from animal
    entry["quantity"] = entry.get("quantity", 0) - req.quantity
    if entry["quantity"] <= 0:
        inv = [e for e in inv if e["item_id"] != req.item_id]
    animal.inventory = inv
    flag_modified(animal, "inventory")

    # Add to character inventory
    from sqlalchemy import insert
    char_qty = db.execute(
        select(character_items.c.quantity).where(
            (character_items.c.character_id == character_id)
            & (character_items.c.item_id == req.item_id)
        )
    ).scalar()

    if char_qty is not None:
        db.execute(
            sa_update(character_items).where(
                (character_items.c.character_id == character_id)
                & (character_items.c.item_id == req.item_id)
            ).values(quantity=char_qty + req.quantity)
        )
    else:
        db.execute(
            insert(character_items).values(
                character_id=character_id,
                item_id=req.item_id,
                quantity=req.quantity,
            )
        )

    db.commit()
    db.refresh(animal)
    return _animal_response(animal)
