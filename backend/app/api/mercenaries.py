"""API endpoints for mercenary types and units."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Character, User, Campaign
from app.models.mercenary import Mercenary
from app.models.mercenary_type import MercenaryType
from app.schemas.mercenary import (
    MercenaryTypeInfo,
    MercenaryTypeCreate,
    MercenaryUnit,
    MercenaryAddRequest,
    MercenaryUpdateRequest,
    MercenarySummary,
    WartimeRequest,
    PaydayResponse,
)
from app.services.mercenaries import deduct_from_wealth
from app.services.permissions import can_view_character, can_edit_character


router = APIRouter()
types_router = APIRouter()


def _get_merc_type(key: str, db: Session) -> MercenaryType | None:
    """Look up a mercenary type by key."""
    return db.query(MercenaryType).filter(MercenaryType.key == key).first()


def _get_unit_cost(mtype: MercenaryType, race: str, wartime: bool = False) -> float | None:
    """Get cost per unit for a race. None if unavailable."""
    cost = mtype.race_costs.get(race)
    if cost is None:
        return None
    return cost * 2 if wartime else cost


def _build_unit(row: Mercenary, db: Session) -> MercenaryUnit:
    """Build a MercenaryUnit response from a DB row."""
    mtype = _get_merc_type(row.merc_type, db)
    if not mtype:
        # Fallback for orphaned rows
        return MercenaryUnit(
            id=row.id, merc_type=row.merc_type, race=row.race,
            quantity=row.quantity, wartime=row.wartime,
            name=row.merc_type, ac=9, morale=6, desc="Unknown type",
            cost_per_unit=0, total_cost=0,
        )
    cost_per = _get_unit_cost(mtype, row.race, row.wartime) or 0
    return MercenaryUnit(
        id=row.id,
        merc_type=row.merc_type,
        race=row.race,
        quantity=row.quantity,
        wartime=row.wartime,
        name=mtype.name,
        ac=mtype.ac,
        morale=mtype.morale,
        desc=mtype.description or "",
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


# --- Type CRUD ---

@types_router.get("", response_model=list[MercenaryTypeInfo])
async def list_mercenary_types(
    campaign_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List mercenary types (defaults + campaign-specific)."""
    query = db.query(MercenaryType)
    if campaign_id:
        query = query.filter(
            (MercenaryType.is_default == True) | (MercenaryType.campaign_id == campaign_id)
        )
    else:
        query = query.filter(MercenaryType.is_default == True)
    return query.order_by(MercenaryType.name).all()


@types_router.get("/{type_id}", response_model=MercenaryTypeInfo)
async def get_mercenary_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single mercenary type."""
    mt = db.query(MercenaryType).filter(MercenaryType.id == type_id).first()
    if not mt:
        raise HTTPException(status_code=404, detail="Mercenary type not found")
    return mt


@types_router.post("", response_model=MercenaryTypeInfo, status_code=status.HTTP_201_CREATED)
async def create_mercenary_type(
    req: MercenaryTypeCreate,
    campaign_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a mercenary type. Admins create defaults; GMs create campaign-specific."""
    is_default = False
    if campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.gm_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only the GM can create mercenary types")
    else:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can create default mercenary types")
        is_default = True

    mt = MercenaryType(
        campaign_id=campaign_id,
        key=req.key,
        name=req.name,
        ac=req.ac,
        morale=req.morale,
        description=req.description,
        race_costs=req.race_costs,
        is_default=is_default,
    )
    db.add(mt)
    db.commit()
    db.refresh(mt)
    return mt


@types_router.patch("/{type_id}", response_model=MercenaryTypeInfo)
async def update_mercenary_type(
    type_id: int,
    req: MercenaryTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a mercenary type."""
    mt = db.query(MercenaryType).filter(MercenaryType.id == type_id).first()
    if not mt:
        raise HTTPException(status_code=404, detail="Mercenary type not found")
    if mt.is_default and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can edit default mercenary types")

    mt.key = req.key
    mt.name = req.name
    mt.ac = req.ac
    mt.morale = req.morale
    mt.description = req.description
    mt.race_costs = req.race_costs
    db.commit()
    db.refresh(mt)
    return mt


@types_router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mercenary_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a mercenary type."""
    mt = db.query(MercenaryType).filter(MercenaryType.id == type_id).first()
    if not mt:
        raise HTTPException(status_code=404, detail="Mercenary type not found")
    if mt.is_default and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete default mercenary types")
    db.delete(mt)
    db.commit()


# --- Character mercenary unit endpoints ---

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
    units = [_build_unit(r, db) for r in rows]
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

    mtype = _get_merc_type(req.merc_type, db)
    if not mtype:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown mercenary type: {req.merc_type}",
        )

    cost = _get_unit_cost(mtype, req.race)
    if cost is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{req.race} {mtype.name} is not available",
        )

    existing = db.query(Mercenary).filter(
        Mercenary.character_id == character_id,
        Mercenary.merc_type == req.merc_type,
        Mercenary.race == req.race,
    ).first()

    if existing:
        existing.quantity += req.quantity
        db.commit()
        db.refresh(existing)
        return _build_unit(existing, db)

    merc = Mercenary(
        character_id=character_id,
        merc_type=req.merc_type,
        race=req.race,
        quantity=req.quantity,
    )
    db.add(merc)
    db.commit()
    db.refresh(merc)
    return _build_unit(merc, db)


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
    return _build_unit(merc, db)


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

    units = [_build_unit(r, db) for r in rows]
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

    total_cost = 0
    for r in rows:
        mtype = _get_merc_type(r.merc_type, db)
        if mtype:
            cost = _get_unit_cost(mtype, r.race, r.wartime) or 0
            total_cost += cost * r.quantity

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
