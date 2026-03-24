"""API endpoints for specialist types and hirelings."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Character, User, Campaign
from app.models.specialist import Specialist
from app.models.specialist_type import SpecialistType
from app.schemas.specialist import (
    SpecialistTypeInfo,
    SpecialistTypeCreate,
    SpecialistEntry,
    SpecialistAddRequest,
    SpecialistUpdateRequest,
    SpecialistSummary,
    PaydayResponse,
)
from app.services.mercenaries import deduct_from_wealth
from app.services.permissions import can_view_character, can_edit_character


router = APIRouter()
types_router = APIRouter()


def _get_spec_type(key: str, db: Session) -> SpecialistType | None:
    """Look up a specialist type by key."""
    return db.query(SpecialistType).filter(SpecialistType.key == key).first()


def _build_entry(row: Specialist, db: Session) -> SpecialistEntry:
    """Build a SpecialistEntry response from a DB row."""
    stype = _get_spec_type(row.spec_type, db)
    if not stype:
        return SpecialistEntry(
            id=row.id, spec_type=row.spec_type, task=row.task,
            name=row.spec_type, wage=0,
        )
    return SpecialistEntry(
        id=row.id,
        spec_type=row.spec_type,
        task=row.task,
        name=stype.name,
        wage=stype.wage,
    )


def _get_character_or_404(character_id: int, db: Session) -> Character:
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )
    return character


# --- Type CRUD ---

@types_router.get("", response_model=list[SpecialistTypeInfo])
async def list_specialist_types(
    campaign_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List specialist types (defaults + campaign-specific)."""
    query = db.query(SpecialistType)
    if campaign_id:
        query = query.filter(
            (SpecialistType.is_default == True) | (SpecialistType.campaign_id == campaign_id)
        )
    else:
        query = query.filter(SpecialistType.is_default == True)
    return query.order_by(SpecialistType.name).all()


@types_router.get("/{type_id}", response_model=SpecialistTypeInfo)
async def get_specialist_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single specialist type."""
    st = db.query(SpecialistType).filter(SpecialistType.id == type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Specialist type not found")
    return st


@types_router.post("", response_model=SpecialistTypeInfo, status_code=status.HTTP_201_CREATED)
async def create_specialist_type(
    req: SpecialistTypeCreate,
    campaign_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a specialist type. Admins create defaults; GMs create campaign-specific."""
    is_default = False
    if campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.gm_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only the GM can create specialist types")
    else:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can create default specialist types")
        is_default = True

    st = SpecialistType(
        campaign_id=campaign_id,
        key=req.key,
        name=req.name,
        wage=req.wage,
        description=req.description,
        is_default=is_default,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


@types_router.patch("/{type_id}", response_model=SpecialistTypeInfo)
async def update_specialist_type(
    type_id: int,
    req: SpecialistTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a specialist type."""
    st = db.query(SpecialistType).filter(SpecialistType.id == type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Specialist type not found")
    if st.is_default and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can edit default specialist types")

    st.key = req.key
    st.name = req.name
    st.wage = req.wage
    st.description = req.description
    db.commit()
    db.refresh(st)
    return st


@types_router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_specialist_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a specialist type."""
    st = db.query(SpecialistType).filter(SpecialistType.id == type_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Specialist type not found")
    if st.is_default and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete default specialist types")
    db.delete(st)
    db.commit()


# --- Character specialist endpoints ---

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
    entries = [_build_entry(r, db) for r in rows]
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
    """Hire a specialist."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    stype = _get_spec_type(req.spec_type, db)
    if not stype:
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
    return _build_entry(spec, db)


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
    return _build_entry(spec, db)


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

    total_cost = 0
    for r in rows:
        stype = _get_spec_type(r.spec_type, db)
        if stype:
            total_cost += stype.wage

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
