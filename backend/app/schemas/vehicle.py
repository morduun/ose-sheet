from pydantic import BaseModel, Field
from app.schemas.item import ItemPublic


class VehicleTypeInfo(BaseModel):
    """Reference data for a vehicle type."""
    id: int
    key: str
    name: str
    vehicle_class: str
    hp: int
    ac: int
    cargo_capacity: int
    movement_rate: int
    cost_gp: int | None = None
    crew_min: int = 0
    passengers: int | None = None
    description: str | None = None
    is_default: bool = False
    campaign_id: int | None = None

    model_config = {"from_attributes": True}


class VehicleTypeCreate(BaseModel):
    """Request to create a custom vehicle type."""
    key: str
    name: str
    vehicle_class: str  # "land", "seaworthy", "unseaworthy"
    hp: int
    ac: int
    cargo_capacity: int
    movement_rate: int
    cost_gp: int | None = None
    crew_min: int = 0
    passengers: int | None = None
    description: str | None = None


class VehicleResponse(BaseModel):
    """A campaign vehicle with computed fields."""
    id: int
    campaign_id: int
    name: str
    vehicle_type: str
    base_type: str
    hp_max: int
    hp_current: int
    ac: int
    cargo_capacity: int
    movement_rate: int
    effective_movement: int
    cost_gp: int | None = None
    vehicle_metadata: dict | None = None
    cargo_weight: int = 0

    model_config = {"from_attributes": True}


class VehicleCreateRequest(BaseModel):
    """Request to add a vehicle to a campaign."""
    base_type: str
    name: str | None = None


class VehicleUpdateRequest(BaseModel):
    """Request to update a vehicle."""
    name: str | None = None
    hp_current: int | None = None
    vehicle_metadata: dict | None = None


class VehicleCargoEntry(BaseModel):
    """An item in a vehicle's cargo hold."""
    item: ItemPublic
    quantity: int


class VehicleCargoAddRequest(BaseModel):
    """Request to load an item into vehicle cargo."""
    item_id: int
    quantity: int = Field(default=1, ge=1)


class VehicleCargoTakeRequest(BaseModel):
    """Request to take cargo to a character."""
    character_id: int
    quantity: int = Field(default=1, ge=1)
