from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class CharacterAnimal(Base):
    """An animal companion belonging to a character."""

    __tablename__ = "character_animals"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(
        Integer,
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    animal_type = Column(String, nullable=False)  # key into ANIMAL_TYPES
    hp_max = Column(Integer, nullable=False)
    hp_current = Column(Integer, nullable=False)
    ac = Column(Integer, nullable=False)
    morale = Column(Integer, nullable=False)
    hit_dice = Column(Float, nullable=False)  # e.g. 2.0, 1.5 for "1+2"

    base_movement = Column(Integer, nullable=False)
    encumbered_movement = Column(Integer, nullable=True)
    base_load = Column(Integer, nullable=True)  # unencumbered max load (coins)
    max_load = Column(Integer, nullable=True)   # encumbered max load (coins)

    source = Column(String, default="purchased")  # purchased, befriended, trained

    # Combat and abilities
    attacks = Column(JSON, nullable=True)     # [{name, damage}]
    abilities = Column(JSON, nullable=True)   # {key: description}

    # Equipment toggles
    equipment = Column(JSON, nullable=True, default=dict)  # {saddle, barding, saddlebags, dog_armor, dog_pack}

    # Mini-inventory
    inventory = Column(JSON, nullable=True, default=list)  # [{item_id, quantity}]

    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    character = relationship("Character", backref="animals")
