"""API endpoints for treasure types and rolling."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Campaign
from app.models.treasure_type import TreasureType
from app.schemas.treasure import (
    TreasureTypeInfo,
    TreasureTypeCreate,
    TreasureRollRequest,
    TreasureRollResult,
)
from app.services.treasure import roll_treasure_type, parse_treasure_type_string


types_router = APIRouter()
roll_router = APIRouter()


# --- Type CRUD ---

@types_router.get("", response_model=list[TreasureTypeInfo])
async def list_treasure_types(
    campaign_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List treasure types (defaults + campaign-specific)."""
    query = db.query(TreasureType)
    if campaign_id:
        query = query.filter(
            (TreasureType.is_default == True) | (TreasureType.campaign_id == campaign_id)
        )
    else:
        query = query.filter(TreasureType.is_default == True)
    return query.order_by(TreasureType.key).all()


@types_router.get("/{type_id}", response_model=TreasureTypeInfo)
async def get_treasure_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single treasure type."""
    tt = db.query(TreasureType).filter(TreasureType.id == type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail="Treasure type not found")
    return tt


@types_router.post("", response_model=TreasureTypeInfo, status_code=status.HTTP_201_CREATED)
async def create_treasure_type(
    req: TreasureTypeCreate,
    campaign_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a treasure type. Admins create defaults; GMs create campaign-specific."""
    is_default = False
    if campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.gm_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only the GM can create treasure types")
    else:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can create default treasure types")
        is_default = True

    tt = TreasureType(
        campaign_id=campaign_id,
        key=req.key,
        name=req.name,
        category=req.category,
        average_gp=req.average_gp,
        entries=req.entries,
        is_default=is_default,
    )
    db.add(tt)
    db.commit()
    db.refresh(tt)
    return tt


@types_router.patch("/{type_id}", response_model=TreasureTypeInfo)
async def update_treasure_type(
    type_id: int,
    req: TreasureTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a treasure type."""
    tt = db.query(TreasureType).filter(TreasureType.id == type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail="Treasure type not found")
    if tt.is_default and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can edit default treasure types")

    tt.key = req.key
    tt.name = req.name
    tt.category = req.category
    tt.average_gp = req.average_gp
    tt.entries = req.entries
    db.commit()
    db.refresh(tt)
    return tt


@types_router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_treasure_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a treasure type."""
    tt = db.query(TreasureType).filter(TreasureType.id == type_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail="Treasure type not found")
    if tt.is_default and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete default treasure types")
    db.delete(tt)
    db.commit()


# --- Rolling ---

@roll_router.post("", response_model=list[TreasureRollResult])
async def roll_treasure(
    req: TreasureRollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Roll a treasure type one or more times.

    For individual types (P-T), count > 1 rolls once per monster.
    For hoard types, count is typically 1.
    Supports compound types like "C + 1000gp".
    """
    base_key, bonus = parse_treasure_type_string(req.treasure_type)

    tt = db.query(TreasureType).filter(TreasureType.key == base_key).first()
    if not tt:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown treasure type: {base_key}",
        )

    results = []
    for _ in range(req.count):
        raw = roll_treasure_type(tt.entries, bonus)
        results.append(TreasureRollResult(
            treasure_type=req.treasure_type,
            coins=raw["coins"],
            gems=[{"value": g["value"]} for g in raw["gems"]],
            jewelry=[{"value": j["value"]} for j in raw["jewelry"]],
            magic_items=raw["magic_items"],
            total_gp_value=raw["total_gp_value"],
            gem_total=sum(g["value"] for g in raw["gems"]),
            jewelry_total=sum(j["value"] for j in raw["jewelry"]),
        ))

    return results
