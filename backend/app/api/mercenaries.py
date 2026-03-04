"""API endpoints for mercenary units."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Character, User
from app.models.mercenary import Mercenary
from app.schemas.mercenary import (
    MercenaryTypeInfo,
    MercenaryUnit,
    MercenaryAddRequest,
    MercenaryUpdateRequest,
    MercenarySummary,
    WartimeRequest,
    PaydayResponse,
)
from app.services.mercenaries import MERCENARY_TYPES, get_unit_cost, deduct_from_wealth
from app.services.permissions import can_view_character, can_edit_character


router = APIRouter()
types_router = APIRouter()


def _build_unit(row: Mercenary) -> MercenaryUnit:
    """Build a MercenaryUnit response from a DB row."""
    info = MERCENARY_TYPES[row.merc_type]
    cost_per = get_unit_cost(row.merc_type, row.race, row.wartime)
    return MercenaryUnit(
        id=row.id,
        merc_type=row.merc_type,
        race=row.race,
        quantity=row.quantity,
        wartime=row.wartime,
        name=info["name"],
        ac=info["ac"],
        morale=info["morale"],
        desc=info["desc"],
        cost_per_unit=cost_per,
        total_cost=cost_per * row.quantity,
    )


def _get_character_or_404(character_id: int, db: Session) -> Character:
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Character with id {character_id} not found",
        )
    return character


@types_router.get("", response_model=list[MercenaryTypeInfo])
async def list_mercenary_types():
    """Get all mercenary types with stats and costs."""
    return [
        MercenaryTypeInfo(key=key, **info)
        for key, info in MERCENARY_TYPES.items()
    ]


@router.get("", response_model=MercenarySummary)
async def get_mercenaries(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all mercenary units for a character."""
    character = _get_character_or_404(character_id, db)
    if not can_view_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    rows = db.query(Mercenary).filter(Mercenary.character_id == character_id).all()
    units = [_build_unit(r) for r in rows]
    any_wartime = any(r.wartime for r in rows) if rows else False
    return MercenarySummary(
        units=units,
        total_units=sum(u.quantity for u in units),
        total_monthly_cost=sum(u.total_cost for u in units),
        wartime=any_wartime,
    )


@router.post("", response_model=MercenaryUnit, status_code=status.HTTP_201_CREATED)
async def hire_mercenaries(
    character_id: int,
    req: MercenaryAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hire mercenary units. Merges with existing row if same type+race."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Validate type
    if req.merc_type not in MERCENARY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown mercenary type: {req.merc_type}",
        )

    # Validate race has a cost for this type
    cost = get_unit_cost(req.merc_type, req.race)
    if cost is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{req.race} {MERCENARY_TYPES[req.merc_type]['name']} is not available",
        )

    # Merge if same type+race already exists
    existing = db.query(Mercenary).filter(
        Mercenary.character_id == character_id,
        Mercenary.merc_type == req.merc_type,
        Mercenary.race == req.race,
    ).first()

    if existing:
        existing.quantity += req.quantity
        db.commit()
        db.refresh(existing)
        return _build_unit(existing)

    merc = Mercenary(
        character_id=character_id,
        merc_type=req.merc_type,
        race=req.race,
        quantity=req.quantity,
    )
    db.add(merc)
    db.commit()
    db.refresh(merc)
    return _build_unit(merc)


@router.patch("/{merc_id}", response_model=MercenaryUnit)
async def update_mercenary(
    character_id: int,
    merc_id: int,
    req: MercenaryUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update quantity or wartime for a mercenary unit."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    merc = db.query(Mercenary).filter(
        Mercenary.id == merc_id,
        Mercenary.character_id == character_id,
    ).first()
    if not merc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mercenary unit not found")

    if req.quantity is not None:
        merc.quantity = req.quantity
    if req.wartime is not None:
        merc.wartime = req.wartime

    db.commit()
    db.refresh(merc)
    return _build_unit(merc)


@router.delete("/{merc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_mercenary(
    character_id: int,
    merc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss (remove) a mercenary unit."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    merc = db.query(Mercenary).filter(
        Mercenary.id == merc_id,
        Mercenary.character_id == character_id,
    ).first()
    if not merc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mercenary unit not found")

    db.delete(merc)
    db.commit()


@router.post("/set-wartime", response_model=MercenarySummary)
async def set_wartime(
    character_id: int,
    req: WartimeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk toggle wartime for all mercenary units."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    rows = db.query(Mercenary).filter(Mercenary.character_id == character_id).all()
    for row in rows:
        row.wartime = req.wartime
    db.commit()

    units = [_build_unit(r) for r in rows]
    return MercenarySummary(
        units=units,
        total_units=sum(u.quantity for u in units),
        total_monthly_cost=sum(u.total_cost for u in units),
        wartime=req.wartime,
    )


@router.post("/payday", response_model=PaydayResponse)
async def payday(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deduct one month's mercenary wages from character's wealth."""
    character = _get_character_or_404(character_id, db)
    if not can_edit_character(current_user, character):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    rows = db.query(Mercenary).filter(Mercenary.character_id == character_id).all()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No mercenaries to pay",
        )

    total_cost = sum(get_unit_cost(r.merc_type, r.race, r.wartime) * r.quantity for r in rows)

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
