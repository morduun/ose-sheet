"""API endpoints for specialist hirelings."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Character, User
from app.models.specialist import Specialist
from app.schemas.specialist import (
    SpecialistTypeInfo,
    SpecialistEntry,
    SpecialistAddRequest,
    SpecialistUpdateRequest,
    SpecialistSummary,
    PaydayResponse,
)
from app.services.specialists import SPECIALIST_TYPES, get_specialist_wage
from app.services.mercenaries import deduct_from_wealth
from app.services.permissions import can_view_character, can_edit_character


router = APIRouter()
types_router = APIRouter()


def _build_entry(row: Specialist) -> SpecialistEntry:
    """Build a SpecialistEntry response from a DB row."""
    info = SPECIALIST_TYPES[row.spec_type]
    return SpecialistEntry(
        id=row.id,
        spec_type=row.spec_type,
        task=row.task,
        name=info["name"],
        wage=info["wage"],
    )


def _get_character_or_404(character_id: int, db: Session) -> Character:
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )
    return character


@types_router.get("", response_model=list[SpecialistTypeInfo])
async def list_specialist_types():
    """Get all specialist types with wages and descriptions."""
    return [
        SpecialistTypeInfo(key=key, **info)
        for key, info in SPECIALIST_TYPES.items()
    ]


@router.get("", response_model=SpecialistSummary)
async def get_specialists(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all hired specialists for a character."""
    character = _get_character_or_404(character_id, db)
    if not can_view_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    rows = db.query(Specialist).filter(Specialist.character_id == character_id).all()
    entries = [_build_entry(r) for r in rows]
    return SpecialistSummary(
        entries=entries,
        count=len(entries),
        total_monthly_cost=sum(e.wage for e in entries),
    )


@router.post("", response_model=SpecialistEntry, status_code=status.HTTP_201_CREATED)
async def hire_specialist(
    character_id: int,
    req: SpecialistAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hire a specialist. Each hire creates a new individual row (no merging)."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if req.spec_type not in SPECIALIST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown specialist type: {req.spec_type}",
        )

    spec = Specialist(
        character_id=character_id,
        spec_type=req.spec_type,
        task=req.task,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return _build_entry(spec)


@router.patch("/{spec_id}", response_model=SpecialistEntry)
async def update_specialist(
    character_id: int,
    spec_id: int,
    req: SpecialistUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a specialist's task description."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    spec = db.query(Specialist).filter(
        Specialist.id == spec_id,
        Specialist.character_id == character_id,
    ).first()
    if not spec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialist not found")

    spec.task = req.task
    db.commit()
    db.refresh(spec)
    return _build_entry(spec)


@router.delete("/{spec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_specialist(
    character_id: int,
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss (remove) a specialist."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    spec = db.query(Specialist).filter(
        Specialist.id == spec_id,
        Specialist.character_id == character_id,
    ).first()
    if not spec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialist not found")

    db.delete(spec)
    db.commit()


@router.post("/payday", response_model=PaydayResponse)
async def payday(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deduct one month's specialist wages from character's wealth."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    rows = db.query(Specialist).filter(Specialist.character_id == character_id).all()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No specialists to pay",
        )

    total_cost = sum(get_specialist_wage(r.spec_type) for r in rows)

    new_coins = deduct_from_wealth(character, total_cost)
    if new_coins is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Need {total_cost} gp but don't have enough wealth.",
        )

    character.platinum = new_coins["platinum"]
    character.gold = new_coins["gold"]
    character.electrum = new_coins["electrum"]
    character.silver = new_coins["silver"]
    character.copper = new_coins["copper"]
    db.commit()

    return PaydayResponse(cost_gp=total_cost, **new_coins)
