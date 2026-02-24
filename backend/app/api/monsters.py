"""Monsters CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Campaign
from app.models.monster import Monster
from app.schemas.monster import (
    Monster as MonsterSchema,
    MonsterCreate,
    MonsterUpdate,
)
from app.services.permissions import can_edit_monster

router = APIRouter()


@router.post("/", response_model=MonsterSchema, status_code=status.HTTP_201_CREATED)
async def create_monster(
    monster: MonsterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new monster.

    - campaign_id: Creates campaign-specific monster (must be GM)
    - is_default: Creates default monster (admin only)
    """
    if monster.campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == monster.campaign_id).first()
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with id {monster.campaign_id} not found",
            )
        if campaign.gm_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the campaign GM can create monsters for this campaign",
            )

    if monster.is_default:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to create default monsters",
            )
        if monster.campaign_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Default monsters cannot belong to a specific campaign",
            )

    db_monster = Monster(**monster.model_dump())
    db.add(db_monster)
    db.commit()
    db.refresh(db_monster)
    return db_monster


@router.get("/", response_model=list[MonsterSchema])
async def list_monsters(
    campaign_id: int | None = None,
    is_default: bool | None = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List monsters.

    - Default monsters are visible to all
    - Campaign monsters only visible to campaign members
    - With campaign_id: show defaults + campaign monsters
    """
    query = db.query(Monster)

    if campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign and campaign.gm_id != current_user.id and current_user not in campaign.players:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this campaign's monsters",
            )
        query = query.filter(
            (Monster.campaign_id == campaign_id) | (Monster.is_default == True)
        )
    else:
        if is_default is not None:
            query = query.filter(Monster.is_default == is_default)
        else:
            query = query.filter(Monster.is_default == True)

    monsters = query.order_by(Monster.name).offset(skip).limit(limit).all()
    return monsters


@router.get("/{monster_id}", response_model=MonsterSchema)
async def get_monster(
    monster_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get monster details."""
    monster = db.query(Monster).filter(Monster.id == monster_id).first()
    if not monster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monster with id {monster_id} not found",
        )
    return monster


@router.patch("/{monster_id}", response_model=MonsterSchema)
async def update_monster(
    monster_id: int,
    monster_update: MonsterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a monster. Admin for defaults, GM for campaign monsters."""
    db_monster = db.query(Monster).filter(Monster.id == monster_id).first()
    if not db_monster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monster with id {monster_id} not found",
        )

    if not can_edit_monster(current_user, db_monster):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this monster",
        )

    update_data = monster_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_monster, field, value)

    db.commit()
    db.refresh(db_monster)
    return db_monster


@router.delete("/{monster_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monster(
    monster_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a monster. Admin for defaults, GM for campaign monsters."""
    db_monster = db.query(Monster).filter(Monster.id == monster_id).first()
    if not db_monster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monster with id {monster_id} not found",
        )

    if not can_edit_monster(current_user, db_monster):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this monster",
        )

    db.delete(db_monster)
    db.commit()
    return None
