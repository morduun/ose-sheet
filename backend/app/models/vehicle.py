from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# Association table for vehicle cargo
vehicle_cargo = Table(
    "vehicle_cargo",
    Base.metadata,
    Column("vehicle_id", Integer, ForeignKey("campaign_vehicles.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("quantity", Integer, default=1),
)


class VehicleType(Base):
    """Reference catalog of vehicle types (carts, ships, etc.)."""

    __tablename__ = "vehicle_types"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    key = Column(String, nullable=False, index=True)  # e.g. "cart", "longship"
    name = Column(String, nullable=False)
    vehicle_class = Column(String, nullable=False)  # "land", "seaworthy", "unseaworthy"
    hp = Column(Integer, nullable=False)
    ac = Column(Integer, nullable=False)
    cargo_capacity = Column(Integer, nullable=False)
    movement_rate = Column(Integer, nullable=False)
    cost_gp = Column(Integer, nullable=True)
    crew_min = Column(Integer, default=0)
    passengers = Column(Integer, nullable=True)
    description = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign = relationship("Campaign", backref="vehicle_types")


class Vehicle(Base):
    """Campaign-level vehicle instance (a specific wagon, ship, etc.)."""

    __tablename__ = "campaign_vehicles"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vehicle_type_id = Column(Integer, ForeignKey("vehicle_types.id"), nullable=True)
    name = Column(String, nullable=False)
    vehicle_type = Column(String, nullable=False)  # "land", "seaworthy", "unseaworthy"
    base_type = Column(String, nullable=False)     # key reference
    hp_max = Column(Integer, nullable=False)
    hp_current = Column(Integer, nullable=False)
    ac = Column(Integer, nullable=False)
    cargo_capacity = Column(Integer, nullable=False)
    movement_rate = Column(Integer, nullable=False)
    cost_gp = Column(Integer, nullable=True)
    vehicle_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign = relationship("Campaign", back_populates="vehicles")
    type_ref = relationship("VehicleType")
