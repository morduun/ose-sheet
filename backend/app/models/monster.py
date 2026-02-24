from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Monster(Base):
    """Monster model for the bestiary/monster library."""

    __tablename__ = "monsters"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)

    # Basic Info
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)

    # Combat Stats
    ac = Column(Integer, nullable=True)
    hit_dice = Column(String, nullable=True)  # "1d8", "3d8+1", "1/2"
    hp = Column(Integer, nullable=True)
    thac0 = Column(Integer, nullable=True)
    movement_rate = Column(String, nullable=True)  # "120' (40')"
    morale = Column(Integer, nullable=True)
    alignment = Column(String, nullable=True)  # Lawful, Neutral, Chaotic
    xp = Column(Integer, nullable=True)

    # Flexible metadata (attacks, saves, number_appearing, treasure_type, abilities)
    monster_metadata = Column(JSON, nullable=True)

    # Default monsters are available to all campaigns
    is_default = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    campaign = relationship("Campaign", back_populates="monsters")

    def __repr__(self):
        return f"<Monster(id={self.id}, name='{self.name}', default={self.is_default})>"
