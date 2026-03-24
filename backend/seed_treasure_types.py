"""Seed default treasure types from OSE reference data."""

import sys
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.treasure_type import TreasureType


TREASURE_TYPES = [
    # --- Hoards A-O ---
    {
        "key": "A", "name": "Type A", "category": "hoard", "average_gp": 18000,
        "entries": [
            {"type": "cp", "chance": 25, "dice": "1d6", "multiplier": 1000},
            {"type": "sp", "chance": 30, "dice": "1d6", "multiplier": 1000},
            {"type": "ep", "chance": 20, "dice": "1d4", "multiplier": 1000},
            {"type": "gp", "chance": 35, "dice": "2d6", "multiplier": 1000},
            {"type": "pp", "chance": 25, "dice": "1d2", "multiplier": 1000},
            {"type": "gems", "chance": 50, "dice": "6d6"},
            {"type": "jewelry", "chance": 50, "dice": "6d6"},
            {"type": "magic", "chance": 30, "rolls": [{"count": 3, "table": "any"}]},
        ],
    },
    {
        "key": "B", "name": "Type B", "category": "hoard", "average_gp": 2000,
        "entries": [
            {"type": "cp", "chance": 50, "dice": "1d8", "multiplier": 1000},
            {"type": "sp", "chance": 25, "dice": "1d6", "multiplier": 1000},
            {"type": "ep", "chance": 25, "dice": "1d4", "multiplier": 1000},
            {"type": "gp", "chance": 25, "dice": "1d3", "multiplier": 1000},
            {"type": "gems", "chance": 25, "dice": "1d6"},
            {"type": "jewelry", "chance": 25, "dice": "1d6"},
            {"type": "magic", "chance": 10, "rolls": [{"count": 1, "table": "sword_armor_weapon"}]},
        ],
    },
    {
        "key": "C", "name": "Type C", "category": "hoard", "average_gp": 1000,
        "entries": [
            {"type": "cp", "chance": 20, "dice": "1d12", "multiplier": 1000},
            {"type": "sp", "chance": 30, "dice": "1d4", "multiplier": 1000},
            {"type": "ep", "chance": 10, "dice": "1d4", "multiplier": 1000},
            {"type": "gems", "chance": 25, "dice": "1d4"},
            {"type": "jewelry", "chance": 25, "dice": "1d4"},
            {"type": "magic", "chance": 10, "rolls": [{"count": 2, "table": "any"}]},
        ],
    },
    {
        "key": "D", "name": "Type D", "category": "hoard", "average_gp": 3900,
        "entries": [
            {"type": "cp", "chance": 10, "dice": "1d8", "multiplier": 1000},
            {"type": "sp", "chance": 15, "dice": "1d12", "multiplier": 1000},
            {"type": "gp", "chance": 60, "dice": "1d6", "multiplier": 1000},
            {"type": "gems", "chance": 30, "dice": "1d8"},
            {"type": "jewelry", "chance": 30, "dice": "1d8"},
            {"type": "magic", "chance": 15, "rolls": [{"count": 2, "table": "any"}, {"count": 1, "table": "potion"}]},
        ],
    },
    {
        "key": "E", "name": "Type E", "category": "hoard", "average_gp": 2300,
        "entries": [
            {"type": "cp", "chance": 5, "dice": "1d10", "multiplier": 1000},
            {"type": "sp", "chance": 30, "dice": "1d12", "multiplier": 1000},
            {"type": "ep", "chance": 25, "dice": "1d4", "multiplier": 1000},
            {"type": "gp", "chance": 25, "dice": "1d8", "multiplier": 1000},
            {"type": "gems", "chance": 10, "dice": "1d10"},
            {"type": "jewelry", "chance": 10, "dice": "1d10"},
            {"type": "magic", "chance": 25, "rolls": [{"count": 3, "table": "any"}, {"count": 1, "table": "scroll"}]},
        ],
    },
    {
        "key": "F", "name": "Type F", "category": "hoard", "average_gp": 7700,
        "entries": [
            {"type": "sp", "chance": 10, "dice": "2d10", "multiplier": 1000},
            {"type": "ep", "chance": 20, "dice": "1d8", "multiplier": 1000},
            {"type": "gp", "chance": 45, "dice": "1d12", "multiplier": 1000},
            {"type": "pp", "chance": 30, "dice": "1d3", "multiplier": 1000},
            {"type": "gems", "chance": 20, "dice": "2d12"},
            {"type": "jewelry", "chance": 10, "dice": "1d12"},
            {"type": "magic", "chance": 30, "rolls": [{"count": 3, "table": "not_weapons"}, {"count": 1, "table": "potion"}, {"count": 1, "table": "scroll"}]},
        ],
    },
    {
        "key": "G", "name": "Type G", "category": "hoard", "average_gp": 23000,
        "entries": [
            {"type": "gp", "chance": 50, "dice": "1d4", "multiplier": 10000},
            {"type": "pp", "chance": 50, "dice": "1d6", "multiplier": 1000},
            {"type": "gems", "chance": 25, "dice": "3d6"},
            {"type": "jewelry", "chance": 25, "dice": "1d10"},
            {"type": "magic", "chance": 35, "rolls": [{"count": 4, "table": "any"}, {"count": 1, "table": "scroll"}]},
        ],
    },
    {
        "key": "H", "name": "Type H", "category": "hoard", "average_gp": 60000,
        "entries": [
            {"type": "cp", "chance": 25, "dice": "3d8", "multiplier": 1000},
            {"type": "sp", "chance": 50, "dice": "1d100", "multiplier": 1000},
            {"type": "ep", "chance": 50, "dice": "1d4", "multiplier": 10000},
            {"type": "gp", "chance": 50, "dice": "1d6", "multiplier": 10000},
            {"type": "pp", "chance": 25, "dice": "5d4", "multiplier": 1000},
            {"type": "gems", "chance": 50, "dice": "1d100"},
            {"type": "jewelry", "chance": 50, "dice": "1d4", "multiplier": 10},
            {"type": "magic", "chance": 15, "rolls": [{"count": 4, "table": "any"}, {"count": 1, "table": "potion"}, {"count": 1, "table": "scroll"}]},
        ],
    },
    {
        "key": "I", "name": "Type I", "category": "hoard", "average_gp": 11000,
        "entries": [
            {"type": "pp", "chance": 30, "dice": "1d8", "multiplier": 1000},
            {"type": "gems", "chance": 50, "dice": "2d6"},
            {"type": "jewelry", "chance": 50, "dice": "2d6"},
            {"type": "magic", "chance": 15, "rolls": [{"count": 1, "table": "any"}]},
        ],
    },
    {
        "key": "J", "name": "Type J", "category": "hoard", "average_gp": 25,
        "entries": [
            {"type": "cp", "chance": 25, "dice": "1d4", "multiplier": 1000},
            {"type": "sp", "chance": 10, "dice": "1d3", "multiplier": 1000},
        ],
    },
    {
        "key": "K", "name": "Type K", "category": "hoard", "average_gp": 180,
        "entries": [
            {"type": "sp", "chance": 30, "dice": "1d6", "multiplier": 1000},
            {"type": "ep", "chance": 10, "dice": "1d2", "multiplier": 1000},
        ],
    },
    {
        "key": "L", "name": "Type L", "category": "hoard", "average_gp": 240,
        "entries": [
            {"type": "gems", "chance": 50, "dice": "1d4"},
        ],
    },
    {
        "key": "M", "name": "Type M", "category": "hoard", "average_gp": 50000,
        "entries": [
            {"type": "gp", "chance": 40, "dice": "2d4", "multiplier": 1000},
            {"type": "pp", "chance": 50, "dice": "5d6", "multiplier": 1000},
            {"type": "gems", "chance": 55, "dice": "5d4"},
            {"type": "jewelry", "chance": 45, "dice": "2d6"},
        ],
    },
    {
        "key": "N", "name": "Type N", "category": "hoard", "average_gp": 0,
        "entries": [
            {"type": "magic", "chance": 40, "rolls": [{"count": 2, "table": "potion"}]},
        ],
    },
    {
        "key": "O", "name": "Type O", "category": "hoard", "average_gp": 0,
        "entries": [
            {"type": "magic", "chance": 50, "rolls": [{"count": 1, "table": "scroll"}]},
        ],
    },

    # --- Individual P-T (no percentage rolls — guaranteed) ---
    {
        "key": "P", "name": "Type P (Individual)", "category": "individual", "average_gp": 0,
        "entries": [
            {"type": "cp", "dice": "3d8"},
        ],
    },
    {
        "key": "Q", "name": "Type Q (Individual)", "category": "individual", "average_gp": 1,
        "entries": [
            {"type": "sp", "dice": "3d6"},
        ],
    },
    {
        "key": "R", "name": "Type R (Individual)", "category": "individual", "average_gp": 3,
        "entries": [
            {"type": "ep", "dice": "2d6"},
        ],
    },
    {
        "key": "S", "name": "Type S (Individual)", "category": "individual", "average_gp": 5,
        "entries": [
            {"type": "gp", "dice": "2d4"},
        ],
    },
    {
        "key": "T", "name": "Type T (Individual)", "category": "individual", "average_gp": 17,
        "entries": [
            {"type": "pp", "dice": "1d6"},
        ],
    },

    # --- Group U-V ---
    {
        "key": "U", "name": "Type U (Group)", "category": "group", "average_gp": 160,
        "entries": [
            {"type": "cp", "chance": 10, "dice": "1d100"},
            {"type": "sp", "chance": 10, "dice": "1d100"},
            {"type": "gp", "chance": 5, "dice": "1d100"},
            {"type": "gems", "chance": 5, "dice": "1d4"},
            {"type": "jewelry", "chance": 5, "dice": "1d4"},
            {"type": "magic", "chance": 2, "rolls": [{"count": 1, "table": "any"}]},
        ],
    },
    {
        "key": "V", "name": "Type V (Group)", "category": "group", "average_gp": 330,
        "entries": [
            {"type": "sp", "chance": 10, "dice": "1d100"},
            {"type": "ep", "chance": 5, "dice": "1d100"},
            {"type": "gp", "chance": 10, "dice": "1d100"},
            {"type": "pp", "chance": 5, "dice": "1d100"},
            {"type": "gems", "chance": 10, "dice": "1d4"},
            {"type": "jewelry", "chance": 10, "dice": "1d4"},
            {"type": "magic", "chance": 5, "rolls": [{"count": 1, "table": "any"}]},
        ],
    },
]


def seed():
    db = SessionLocal()
    try:
        existing = db.query(TreasureType).filter(TreasureType.is_default == True).count()
        if existing > 0:
            print(f"Already have {existing} default treasure types — skipping.")
            return

        count = 0
        for tt in TREASURE_TYPES:
            row = TreasureType(
                key=tt["key"],
                name=tt["name"],
                category=tt["category"],
                average_gp=tt["average_gp"],
                entries=tt["entries"],
                is_default=True,
                campaign_id=None,
            )
            db.add(row)
            count += 1

        db.commit()
        print(f"Seeded {count} default treasure types.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
