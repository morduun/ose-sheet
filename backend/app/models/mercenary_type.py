from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MercenaryType(Base):
    """Reference catalog of mercenary types."""

    __tablename__ = "mercenary_types"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    key = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    ac = Column(Integer, nullable=False)
    morale = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    race_costs = Column(JSON, nullable=False)  # {"human": 5, "elf": 10, ...} — only available races
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign", backref="mercenary_types")
