#!/usr/bin/env python
"""Update default spells from JSON files.

Reads each spell JSON file and updates any fields that differ from the
database. Useful after restructuring the seed data (e.g. adding aoe/save/
reversed fields) without needing to wipe and re-seed.

Fields compared and updated: description, range, duration, aoe, save, reversed.
The name, level, spell_class, and is_default fields are used as the lookup key
and are never changed by this script.
"""

import json
import logging
import sys
from pathlib import Path

# Suppress SQLAlchemy logging before importing app modules
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

from app.database import SessionLocal
from app.models import Spell

UPDATABLE_FIELDS = ["description", "range", "duration", "aoe", "save", "reversed"]


def load_spells_from_json(filepath: Path) -> list[dict]:
    with open(filepath, "r") as f:
        return json.load(f)


def update_spells(db, spells_data: list[dict], display_name: str):
    updated = 0
    skipped = 0
    missing = 0

    for spell_data in spells_data:
        existing = (
            db.query(Spell)
            .filter(
                Spell.name == spell_data["name"],
                Spell.spell_class == spell_data["spell_class"],
                Spell.is_default == True,
            )
            .first()
        )

        if not existing:
            print(f"  ! Not found (will not create): {spell_data['name']}")
            missing += 1
            continue

        changes = {}
        for field in UPDATABLE_FIELDS:
            json_val = spell_data.get(field)
            db_val = getattr(existing, field)
            if json_val != db_val:
                changes[field] = (db_val, json_val)

        if not changes:
            skipped += 1
            continue

        for field, (_, new_val) in changes.items():
            setattr(existing, field, new_val)

        change_summary = ", ".join(changes.keys())
        print(f"  ~ Updated [{change_summary}]: {existing.name}")
        updated += 1

    db.commit()
    return updated, skipped, missing


def main():
    db = SessionLocal()
    seed_dir = Path(__file__).parent / "seed_data" / "spells"

    if not seed_dir.exists():
        print(f"Seed directory not found: {seed_dir}")
        sys.exit(1)

    print("=" * 60)
    print("UPDATING DEFAULT SPELLS")
    print("=" * 60)

    total_updated = 0
    total_skipped = 0
    total_missing = 0

    spell_files = [
        ("cleric", "Cleric"),
        ("magic_user", "Magic-User"),
        ("druid", "Druid"),
        ("illusionist", "Illusionist"),
    ]

    for filename, display_name in spell_files:
        filepath = seed_dir / f"{filename}.json"

        if not filepath.exists():
            print(f"\nWarning: {filepath.name} not found, skipping...")
            continue

        print(f"\n  Updating {display_name} spells...")
        spells_data = load_spells_from_json(filepath)
        updated, skipped, missing = update_spells(db, spells_data, display_name)
        total_updated += updated
        total_skipped += skipped
        total_missing += missing

    print("\n" + "=" * 60)
    print("Update complete!")
    print(f"  Updated:  {total_updated}")
    print(f"  No change: {total_skipped}")
    if total_missing:
        print(f"  Not found: {total_missing}  (run seed_default_spells.py to create)")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()
