"""Vehicle management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Campaign, Item, Vehicle, VehicleType
from app.models.vehicle import VehicleCargo
from app.models.item import CharacterItem
from app.schemas.vehicle import (
    VehicleTypeInfo,
    VehicleTypeCreate,
    VehicleResponse,
    VehicleCreateRequest,
    VehicleUpdateRequest,
    VehicleCargoEntry,
    VehicleCargoAddRequest,
    VehicleCargoTakeRequest,
)
from app.schemas.item import ItemPublic
from app.services.vehicles import compute_effective_movement
from app.services.permissions import can_view_campaign, is_campaign_gm


# --- Reference data router ---
types_router = APIRouter()


@types_router.get("/", response_model=list[VehicleTypeInfo])
async def list_vehicle_types(
    campaign_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available vehicle types (defaults + campaign-specific)."""
    query = db.query(VehicleType)
    if campaign_id:
        query = query.filter(
            (VehicleType.is_default == True) | (VehicleType.campaign_id == campaign_id)
        )
    else:
        query = query.filter(VehicleType.is_default == True)
    return query.order_by(VehicleType.vehicle_class, VehicleType.name).all()


@types_router.post("/", response_model=VehicleTypeInfo, status_code=status.HTTP_201_CREATED)
async def create_vehicle_type(
    req: VehicleTypeCreate,
    campaign_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a vehicle type. Admins can create defaults; GMs can create campaign-specific types."""
    is_default = False
    if campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        if campaign.gm_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only the GM can create vehicle types")
    else:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can create default vehicle types")
        is_default = True

    vt = VehicleType(
        campaign_id=campaign_id,
        key=req.key,
        name=req.name,
        vehicle_class=req.vehicle_class,
        hp=req.hp,
        ac=req.ac,
        cargo_capacity=req.cargo_capacity,
        movement_rate=req.movement_rate,
        cost_gp=req.cost_gp,
        crew_min=req.crew_min,
        passengers=req.passengers,
        description=req.description,
        is_default=is_default,
    )
    db.add(vt)
    db.commit()
    db.refresh(vt)
    return vt


@types_router.get("/{type_id}", response_model=VehicleTypeInfo)
async def get_vehicle_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single vehicle type by ID."""
    vt = db.query(VehicleType).filter(VehicleType.id == type_id).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Vehicle type not found")
    return vt


@types_router.patch("/{type_id}", response_model=VehicleTypeInfo)
async def update_vehicle_type(
    type_id: int,
    req: VehicleTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a vehicle type. Only campaign-specific (non-default) types or by admin."""
    vt = db.query(VehicleType).filter(VehicleType.id == type_id).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Vehicle type not found")
    if vt.is_default and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can edit default vehicle types")
    if not vt.is_default and vt.campaign_id:
        campaign = db.query(Campaign).filter(Campaign.id == vt.campaign_id).first()
        if campaign and campaign.gm_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the GM can edit campaign vehicle types")

    vt.key = req.key
    vt.name = req.name
    vt.vehicle_class = req.vehicle_class
    vt.hp = req.hp
    vt.ac = req.ac
    vt.cargo_capacity = req.cargo_capacity
    vt.movement_rate = req.movement_rate
    vt.cost_gp = req.cost_gp
    vt.crew_min = req.crew_min
    vt.passengers = req.passengers
    vt.description = req.description
    db.commit()
    db.refresh(vt)
    return vt


@types_router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a vehicle type. Cannot delete defaults unless admin."""
    vt = db.query(VehicleType).filter(VehicleType.id == type_id).first()
    if not vt:
        raise HTTPException(status_code=404, detail="Vehicle type not found")
    if vt.is_default and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete default vehicle types")

    db.delete(vt)
    db.commit()


# --- Campaign-scoped router ---
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
        raise HTTPException(status_code=403, detail="Only the GM can manage vehicles")


def _cargo_weight(vehicle_id: int, db: Session) -> int:
    """Sum item weight * quantity for all cargo in a vehicle."""
    cargo_rows = db.query(VehicleCargo).filter(VehicleCargo.vehicle_id == vehicle_id).all()
    if not cargo_rows:
        return 0
    items = db.query(Item).filter(Item.id.in_([r.item_id for r in cargo_rows])).all()
    weight_map = {i.id: i.weight or 0 for i in items}
    return int(sum(weight_map.get(r.item_id, 0) * r.quantity for r in cargo_rows))


def _vehicle_response(v: Vehicle, db: Session) -> VehicleResponse:
    return VehicleResponse(
        id=v.id,
        campaign_id=v.campaign_id,
        name=v.name,
        vehicle_type=v.vehicle_type,
        base_type=v.base_type,
        hp_max=v.hp_max,
        hp_current=v.hp_current,
        ac=v.ac,
        cargo_capacity=v.cargo_capacity,
        movement_rate=v.movement_rate,
        effective_movement=compute_effective_movement(v.hp_current, v.hp_max, v.movement_rate),
        cost_gp=v.cost_gp,
        vehicle_metadata=v.vehicle_metadata,
        cargo_weight=_cargo_weight(v.id, db),
    )


def _item_to_public(item: Item) -> ItemPublic:
    revealed = []
    if item.secrets:
        revealed = [s["text"] for s in item.secrets if s.get("revealed")]
    return ItemPublic(
        id=item.id,
        name=item.name,
        unidentified_name=item.unidentified_name,
        item_type=item.item_type,
        weight=item.weight,
        cost_gp=item.cost_gp,
        equippable=item.equippable,
        description_player=item.description_player,
        revealed_secrets=revealed or None,
        item_metadata=item.item_metadata,
        is_default=item.is_default,
    )


# --- Vehicle CRUD ---

@router.get("/", response_model=list[VehicleResponse])
async def list_vehicles(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all vehicles in a campaign."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_view(current_user, campaign)
    vehicles = db.query(Vehicle).filter(Vehicle.campaign_id == campaign_id).all()
    return [_vehicle_response(v, db) for v in vehicles]


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    campaign_id: int,
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single vehicle."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_view(current_user, campaign)
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.campaign_id == campaign_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return _vehicle_response(v, db)


@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    campaign_id: int,
    req: VehicleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a vehicle from a base type."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    # Look up vehicle type from DB
    vtype = db.query(VehicleType).filter(
        VehicleType.id == req.base_type if req.base_type.isdigit()
        else VehicleType.key == req.base_type,
        (VehicleType.is_default == True) | (VehicleType.campaign_id == campaign_id),
    ).first()
    if not vtype:
        raise HTTPException(status_code=400, detail=f"Unknown vehicle type: {req.base_type}")

    v = Vehicle(
        campaign_id=campaign_id,
        vehicle_type_id=vtype.id,
        name=req.name or vtype.name,
        vehicle_type=vtype.vehicle_class,
        base_type=vtype.key,
        hp_max=vtype.hp,
        hp_current=vtype.hp,
        ac=vtype.ac,
        cargo_capacity=vtype.cargo_capacity,
        movement_rate=vtype.movement_rate,
        cost_gp=vtype.cost_gp,
        vehicle_metadata={
            "crew_min": vtype.crew_min,
            "passengers": vtype.passengers,
            "description": vtype.description,
        },
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return _vehicle_response(v, db)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    campaign_id: int,
    vehicle_id: int,
    req: VehicleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a vehicle's name, HP, or metadata."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.campaign_id == campaign_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if req.name is not None:
        v.name = req.name
    if req.hp_current is not None:
        v.hp_current = max(0, min(req.hp_current, v.hp_max))
    if req.vehicle_metadata is not None:
        v.vehicle_metadata = {**(v.vehicle_metadata or {}), **req.vehicle_metadata}

    db.commit()
    db.refresh(v)
    return _vehicle_response(v, db)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    campaign_id: int,
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a vehicle and its cargo."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.campaign_id == campaign_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    db.delete(v)
    db.commit()


# --- Cargo Management ---

@router.get("/{vehicle_id}/cargo", response_model=list[VehicleCargoEntry])
async def list_cargo(
    campaign_id: int,
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List items in a vehicle's cargo hold."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_view(current_user, campaign)

    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.campaign_id == campaign_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    rows = db.query(VehicleCargo).filter(VehicleCargo.vehicle_id == vehicle_id).all()
    if not rows:
        return []

    items = db.query(Item).filter(Item.id.in_([r.item_id for r in rows])).all()
    item_map = {i.id: i for i in items}
    return [
        VehicleCargoEntry(
            instance_id=row.id,
            item=_item_to_public(item_map[row.item_id]),
            quantity=row.quantity,
        )
        for row in rows
        if row.item_id in item_map
    ]


@router.post("/{vehicle_id}/cargo", response_model=list[VehicleCargoEntry], status_code=status.HTTP_201_CREATED)
async def add_cargo(
    campaign_id: int,
    vehicle_id: int,
    req: VehicleCargoAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an item to vehicle cargo."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.campaign_id == campaign_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    item = db.query(Item).filter(Item.id == req.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    cargo_row = VehicleCargo(
        vehicle_id=vehicle_id,
        item_id=req.item_id,
        quantity=req.quantity,
    )
    db.add(cargo_row)
    db.commit()

    return await list_cargo(campaign_id, vehicle_id, db, current_user)


@router.delete("/{vehicle_id}/cargo/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_cargo(
    campaign_id: int,
    vehicle_id: int,
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an item from vehicle cargo entirely."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_gm(current_user, campaign)

    cargo_row = db.query(VehicleCargo).filter(
        VehicleCargo.id == instance_id,
        VehicleCargo.vehicle_id == vehicle_id,
    ).first()
    if not cargo_row:
        raise HTTPException(status_code=404, detail="Cargo entry not found")

    db.delete(cargo_row)
    db.commit()


@router.post("/{vehicle_id}/cargo/{instance_id}/take", response_model=dict)
async def take_from_cargo(
    campaign_id: int,
    vehicle_id: int,
    instance_id: int,
    req: VehicleCargoTakeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Take an item from vehicle cargo into a character's inventory."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_view(current_user, campaign)

    from app.models import Character
    character = db.query(Character).filter(Character.id == req.character_id).first()
    if not character or character.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Character not in this campaign")

    # Look up the cargo row by instance_id
    cargo_row = db.query(VehicleCargo).filter(
        VehicleCargo.id == instance_id,
        VehicleCargo.vehicle_id == vehicle_id,
    ).first()
    if not cargo_row:
        raise HTTPException(status_code=404, detail="Cargo entry not found")

    if cargo_row.quantity < req.quantity:
        raise HTTPException(status_code=400, detail=f"Not enough in cargo (available: {cargo_row.quantity})")

    item = db.query(Item).filter(Item.id == cargo_row.item_id).first()

    # Decrement cargo or delete the row
    new_qty = cargo_row.quantity - req.quantity
    if new_qty <= 0:
        db.delete(cargo_row)
    else:
        cargo_row.quantity = new_qty

    # Create new CharacterItem row
    char_item = CharacterItem(
        character_id=req.character_id,
        item_id=cargo_row.item_id,
        quantity=req.quantity,
    )
    db.add(char_item)

    db.commit()
    return {"message": f"{character.name} took {req.quantity} {item.name} from the cargo hold"}


@router.post("/{vehicle_id}/cargo/{instance_id}/return", response_model=dict)
async def return_to_cargo(
    campaign_id: int,
    vehicle_id: int,
    instance_id: int,
    req: VehicleCargoTakeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return an item from a character's inventory to vehicle cargo."""
    campaign = _get_campaign_or_404(db, campaign_id)
    _check_view(current_user, campaign)

    from app.models import Character
    character = db.query(Character).filter(Character.id == req.character_id).first()
    if not character or character.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail="Character not in this campaign")

    # Look up the CharacterItem by instance_id from request body
    if req.instance_id is None:
        raise HTTPException(status_code=400, detail="instance_id is required to identify the character item")

    char_item = db.query(CharacterItem).filter(
        CharacterItem.id == req.instance_id,
        CharacterItem.character_id == req.character_id,
    ).first()
    if not char_item:
        raise HTTPException(status_code=404, detail="Character item not found")

    if char_item.quantity < req.quantity:
        raise HTTPException(status_code=400, detail=f"Character doesn't have enough (has: {char_item.quantity})")

    item = db.query(Item).filter(Item.id == char_item.item_id).first()

    # Decrement character inventory or delete the row
    new_qty = char_item.quantity - req.quantity
    if new_qty <= 0:
        db.delete(char_item)
    else:
        char_item.quantity = new_qty

    # Create new VehicleCargo row
    cargo_row = VehicleCargo(
        vehicle_id=vehicle_id,
        item_id=char_item.item_id,
        quantity=req.quantity,
    )
    db.add(cargo_row)

    db.commit()
    return {"message": f"{character.name} stored {req.quantity} {item.name} in the cargo hold"}
