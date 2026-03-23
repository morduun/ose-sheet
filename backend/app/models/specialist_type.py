from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SpecialistType(Base):
    """Reference catalog of specialist types."""

    __tablename__ = "specialist_types"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    key = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    wage = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign", backref="specialist_types")
