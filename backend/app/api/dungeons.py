"""API endpoints for dungeon and room management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Campaign
from app.models.dungeon import Dungeon, DungeonRoom
from app.schemas.dungeon import (
    DungeonCreate,
    DungeonUpdate,
    DungeonSummary,
    DungeonResponse,
    DungeonRoomCreate,
    DungeonRoomUpdate,
    DungeonRoomResponse,
)
from app.services.permissions import can_view_campaign, is_campaign_gm


router = APIRouter()


def _get_campaign_or_404(db: Session, campaign_id: int) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
    return campaign


def _check_view(user: User, campaign: Campaign):
    if not can_view_campaign(user, campaign):
        raise HTTPException(status_code=403, detail="Not a member of this campaign")


def _check_gm(user: User, campaign: Campaign):
    if not is_campaign_gm(user, campaign):
        raise HTTPException(status_code=403, detail="Only the GM can manage dungeons")


# --- Dungeon CRUD ---

@router.get("/", response_model=list[DungeonSummary])
async def list_dungeons(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all dungeons in a campaign with room count and progress."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    dungeons = db.query(Dungeon).filter(Dungeon.campaign_id == campaign_id).order_by(Dungeon.name).all()
    result = []
    for d in dungeons:
        rooms = db.query(DungeonRoom).filter(DungeonRoom.dungeon_id == d.id).all()
        result.append(DungeonSummary(
            id=d.id,
            campaign_id=d.campaign_id,
            name=d.name,
            description=d.description,
            room_count=len(rooms),
            cleared_count=sum(1 for r in rooms if r.state == "cleared"),
        ))
    return result


@router.get("/{dungeon_id}", response_model=DungeonResponse)
async def get_dungeon(
    campaign_id: int,
    dungeon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a dungeon with all its rooms."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    dungeon = db.query(Dungeon).filter(
        Dungeon.id == dungeon_id, Dungeon.campaign_id == campaign_id
    ).first()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")
    return dungeon


@router.post("/", response_model=DungeonResponse, status_code=status.HTTP_201_CREATED)
async def create_dungeon(
    campaign_id: int,
    req: DungeonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new dungeon."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    dungeon = Dungeon(
        campaign_id=campaign_id,
        name=req.name,
        description=req.description,
    )
    db.add(dungeon)
    db.commit()
    db.refresh(dungeon)
    return dungeon


@router.patch("/{dungeon_id}", response_model=DungeonResponse)
async def update_dungeon(
    campaign_id: int,
    dungeon_id: int,
    req: DungeonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a dungeon's name or description."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    dungeon = db.query(Dungeon).filter(
        Dungeon.id == dungeon_id, Dungeon.campaign_id == campaign_id
    ).first()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")

    if req.name is not None:
        dungeon.name = req.name
    if req.description is not None:
        dungeon.description = req.description

    db.commit()
    db.refresh(dungeon)
    return dungeon


@router.delete("/{dungeon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dungeon(
    campaign_id: int,
    dungeon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a dungeon and all its rooms."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    dungeon = db.query(Dungeon).filter(
        Dungeon.id == dungeon_id, Dungeon.campaign_id == campaign_id
    ).first()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")

    db.delete(dungeon)
    db.commit()


# --- Room CRUD ---

@router.post("/{dungeon_id}/rooms", response_model=DungeonRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    campaign_id: int,
    dungeon_id: int,
    req: DungeonRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a room to a dungeon."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    dungeon = db.query(Dungeon).filter(
        Dungeon.id == dungeon_id, Dungeon.campaign_id == campaign_id
    ).first()
    if not dungeon:
        raise HTTPException(status_code=404, detail="Dungeon not found")

    room = DungeonRoom(
        dungeon_id=dungeon_id,
        room_number=req.room_number,
        name=req.name,
        description=req.description,
        notes=req.notes,
        state=req.state,
        treasure_type_key=req.treasure_type_key,
        monsters=[m.model_dump() for m in req.monsters],
        items=[i.model_dump() for i in req.items],
        traps=[t.model_dump() for t in req.traps],
        exits=[e.model_dump() for e in req.exits],
        currency=req.currency.model_dump() if req.currency else None,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.patch("/{dungeon_id}/rooms/{room_id}", response_model=DungeonRoomResponse)
async def update_room(
    campaign_id: int,
    dungeon_id: int,
    room_id: int,
    req: DungeonRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a room's details, contents, or state."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    room = db.query(DungeonRoom).filter(
        DungeonRoom.id == room_id, DungeonRoom.dungeon_id == dungeon_id
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if req.room_number is not None:
        room.room_number = req.room_number
    if req.name is not None:
        room.name = req.name
    if req.description is not None:
        room.description = req.description
    if req.notes is not None:
        room.notes = req.notes
    if req.state is not None:
        room.state = req.state
    if req.treasure_type_key is not None:
        room.treasure_type_key = req.treasure_type_key
    if req.monsters is not None:
        room.monsters = [m.model_dump() for m in req.monsters]
    if req.items is not None:
        room.items = [i.model_dump() for i in req.items]
    if req.traps is not None:
        room.traps = [t.model_dump() for t in req.traps]
    if req.exits is not None:
        room.exits = [e.model_dump() for e in req.exits]
    if req.currency is not None:
        room.currency = req.currency.model_dump()

    db.commit()
    db.refresh(room)
    return room


@router.delete("/{dungeon_id}/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    campaign_id: int,
    dungeon_id: int,
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a room from a dungeon."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    room = db.query(DungeonRoom).filter(
        DungeonRoom.id == room_id, DungeonRoom.dungeon_id == dungeon_id
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    db.delete(room)
    db.commit()


# --- Room state shortcut ---

@router.post("/{dungeon_id}/rooms/{room_id}/state", response_model=DungeonRoomResponse)
async def set_room_state(
    campaign_id: int,
    dungeon_id: int,
    room_id: int,
    state: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Quick state toggle for a room."""
    if state not in ("unvisited", "visited", "cleared"):
        raise HTTPException(status_code=400, detail="State must be: unvisited, visited, or cleared")

    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    room = db.query(DungeonRoom).filter(
        DungeonRoom.id == room_id, DungeonRoom.dungeon_id == dungeon_id
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    room.state = state
    db.commit()
    db.refresh(room)
    return room


# --- Room item reveal ---

@router.post("/{dungeon_id}/rooms/{room_id}/reveal/{item_index}", response_model=DungeonRoomResponse)
async def reveal_room_item(
    campaign_id: int,
    dungeon_id: int,
    room_id: int,
    item_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reveal a hidden item in a room."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    room = db.query(DungeonRoom).filter(
        DungeonRoom.id == room_id, DungeonRoom.dungeon_id == dungeon_id
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    items = list(room.items or [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=400, detail="Invalid item index")

    items[item_index]["hidden"] = False
    # Force SQLAlchemy to detect the JSON mutation
    from sqlalchemy.orm.attributes import flag_modified
    room.items = items
    flag_modified(room, "items")

    db.commit()
    db.refresh(room)
    return room
