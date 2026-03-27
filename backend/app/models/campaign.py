from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.item import campaign_stash
import secrets


# Association table for many-to-many relationship between campaigns and players
campaign_players = Table(
    "campaign_players",
    Base.metadata,
    Column("campaign_id", Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class Campaign(Base):
    """Campaign model for organizing characters and items."""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    gm_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invite_code = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    gm = relationship("User", back_populates="campaigns_as_gm")
    players = relationship(
        "User",
        secondary=campaign_players,
        back_populates="campaigns_as_player",
    )
    characters = relationship("Character", back_populates="campaign", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="campaign", cascade="all, delete-orphan")
    character_classes = relationship("CharacterClass", back_populates="campaign", cascade="all, delete-orphan")
    monsters = relationship("Monster", back_populates="campaign", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="campaign", cascade="all, delete-orphan")
    dungeons = relationship("Dungeon", back_populates="campaign", cascade="all, delete-orphan")
    stash_items = relationship(
        "Item",
        secondary=campaign_stash,
        backref="stash_campaigns",
        foreign_keys=[campaign_stash.c.campaign_id, campaign_stash.c.item_id],
    )

    def __init__(self, **kwargs):
        """Generate invite code on creation if not provided."""
        if "invite_code" not in kwargs:
            kwargs["invite_code"] = self.generate_invite_code()
        super().__init__(**kwargs)

    @staticmethod
    def generate_invite_code(length: int = 8) -> str:
        """Generate a random invite code for the campaign."""
        return secrets.token_urlsafe(length)[:length].upper()

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', invite_code='{self.invite_code}')>"
