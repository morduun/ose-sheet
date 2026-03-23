"""Seed default vehicle types from OSE reference data."""

import sys
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.vehicle import VehicleType
from app.services.vehicles import VEHICLE_TYPES


def seed():
    db = SessionLocal()
    try:
        existing = db.query(VehicleType).filter(VehicleType.is_default == True).count()
        if existing > 0:
            print(f"Already have {existing} default vehicle types — skipping seed.")
            return

        count = 0
        for key, data in VEHICLE_TYPES.items():
            vt = VehicleType(
                key=key,
                name=data["name"],
                vehicle_class=data["vehicle_type"],
                hp=data["hp"],
                ac=data["ac"],
                cargo_capacity=data["cargo_capacity"],
                movement_rate=data["movement_rate"],
                cost_gp=data["cost_gp"],
                crew_min=data["crew_min"],
                passengers=data.get("passengers"),
                description=data["description"],
                is_default=True,
                campaign_id=None,
            )
            db.add(vt)
            count += 1

        db.commit()
        print(f"Seeded {count} default vehicle types.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
