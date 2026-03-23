"""Seed default mercenary and specialist types from OSE reference data."""

import sys
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.mercenary_type import MercenaryType
from app.models.specialist_type import SpecialistType
from app.services.mercenaries import MERCENARY_TYPES
from app.services.specialists import SPECIALIST_TYPES


def seed():
    db = SessionLocal()
    try:
        # --- Mercenary Types ---
        existing_mercs = db.query(MercenaryType).filter(MercenaryType.is_default == True).count()
        if existing_mercs > 0:
            print(f"Already have {existing_mercs} default mercenary types — skipping.")
        else:
            count = 0
            for key, data in MERCENARY_TYPES.items():
                # Filter race_costs to only include available races (non-None costs)
                race_costs = {
                    race: cost
                    for race, cost in data["costs"].items()
                    if cost is not None
                }
                mt = MercenaryType(
                    key=key,
                    name=data["name"],
                    ac=data["ac"],
                    morale=data["morale"],
                    description=data["desc"],
                    race_costs=race_costs,
                    is_default=True,
                    campaign_id=None,
                )
                db.add(mt)
                count += 1
            db.commit()
            print(f"Seeded {count} default mercenary types.")

        # --- Specialist Types ---
        existing_specs = db.query(SpecialistType).filter(SpecialistType.is_default == True).count()
        if existing_specs > 0:
            print(f"Already have {existing_specs} default specialist types — skipping.")
        else:
            count = 0
            for key, data in SPECIALIST_TYPES.items():
                st = SpecialistType(
                    key=key,
                    name=data["name"],
                    wage=data["wage"],
                    description=data["desc"],
                    is_default=True,
                    campaign_id=None,
                )
                db.add(st)
                count += 1
            db.commit()
            print(f"Seeded {count} default specialist types.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
