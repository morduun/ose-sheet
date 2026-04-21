from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class HexMap(Base):
    """A hex map region belonging to a campaign."""

    __tablename__ = "hex_maps"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    width = Column(Integer, nullable=False)   # columns
    height = Column(Integer, nullable=False)  # rows
    hex_size_miles = Column(Integer, nullable=False, default=6)
    party_col = Column(Integer, nullable=True)
    party_row = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    campaign = relationship("Campaign", back_populates="hex_maps")
    cells = relationship(
        "HexCell",
        back_populates="hex_map",
        cascade="all, delete-orphan",
        order_by="HexCell.row, HexCell.col",
    )


class HexCell(Base):
    """A single hex cell within a hex map."""

    __tablename__ = "hex_cells"

    id = Column(Integer, primary_key=True, index=True)
    hex_map_id = Column(
        Integer,
        ForeignKey("hex_maps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    col = Column(Integer, nullable=False)
    row = Column(Integer, nullable=False)
    terrain_type = Column(String, nullable=False)  # matches icon filename: "grassland", "mountains", etc.
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    notes = Column(String, nullable=True)  # GM-only notes, hidden from players
    # pois: [{type, name, description, linked_dungeon_id}]
    pois = Column(JSON, nullable=True, default=list)
    visited = Column(Boolean, nullable=False, default=False)

    # Relationships
    hex_map = relationship("HexMap", back_populates="cells")
