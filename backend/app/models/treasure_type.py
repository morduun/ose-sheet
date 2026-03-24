from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class TreasureType(Base):
    """Reference catalog of treasure types (A-V)."""

    __tablename__ = "treasure_types"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    key = Column(String, nullable=False, index=True)  # "A", "B", ..., "V"
    name = Column(String, nullable=False)              # "Type A", "Type P (Individual)"
    category = Column(String, nullable=False)          # "hoard", "individual", "group"
    average_gp = Column(Integer, nullable=True)
    entries = Column(JSON, nullable=False)              # Roll table entries
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign", backref="treasure_types")
