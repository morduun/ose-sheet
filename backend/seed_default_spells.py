#!/usr/bin/env python
"""Seed default spells from JSON files."""

import json
import sys
from pathlib import Path
from app.database import SessionLocal
from app.models import Spell


def load_spells_from_json(filepath: Path) -> list[dict]:
    with open(filepath, 'r') as f:
        return json.load(f)


def seed_spells(db, spells_data: list[dict], display_name: str):
    created = 0
    skipped = 0

    for spell_data in spells_data:
        existing = db.query(Spell).filter(
            Spell.name == spell_data['name'],
            Spell.spell_class == spell_data['spell_class'],
            Spell.is_default == True
        ).first()

        if existing:
            print(f"  - Skipped (exists): {spell_data['name']}")
            skipped += 1
            continue

        spell = Spell(**spell_data)
        db.add(spell)
        created += 1
        print(f"  + Created: {spell_data['name']} (Level {spell_data['level']})")

    db.commit()
    return created, skipped


def main():
    db = SessionLocal()
    seed_dir = Path(__file__).parent / "seed_data" / "spells"

    if not seed_dir.exists():
        print(f"Seed directory not found: {seed_dir}")
        sys.exit(1)

    print("=" * 60)
    print("SEEDING DEFAULT SPELLS")
    print("=" * 60)

    total_created = 0
    total_skipped = 0

    spell_files = [
        ("cleric",      "Cleric"),
        ("magic_user",  "Magic-User"),
        ("druid",       "Druid"),
        ("illusionist", "Illusionist"),
    ]

    for filename, display_name in spell_files:
        filepath = seed_dir / f"{filename}.json"

        if not filepath.exists():
            print(f"\nWarning: {filepath.name} not found, skipping...")
            continue

        print(f"\n  Seeding {display_name} spells...")
        spells_data = load_spells_from_json(filepath)
        created, skipped = seed_spells(db, spells_data, display_name)
        total_created += created
        total_skipped += skipped

    print("\n" + "=" * 60)
    print("Seeding complete!")
    print(f"  Created: {total_created}")
    print(f"  Skipped: {total_skipped}")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()
