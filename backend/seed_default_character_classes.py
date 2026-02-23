#!/usr/bin/env python
"""Seed default character classes from JSON files."""

import json
import sys
from pathlib import Path

from app.database import SessionLocal
from app.models import CharacterClass


def load_class_from_json(filepath: Path) -> dict:
    """Load character class data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def seed_class(db, class_data: dict, filename: str) -> tuple[int, int]:
    """
    Seed a single character class.

    Returns:
        Tuple of (created_count, skipped_count)
    """
    # Check if class already exists (by name and is_default=True)
    existing = db.query(CharacterClass).filter(
        CharacterClass.name == class_data['name'],
        CharacterClass.is_default == True
    ).first()

    if existing:
        print(f"  ⊗ Skipped (exists): {class_data['name']}")
        return 0, 1

    # Extract fields for CharacterClass model
    char_class = CharacterClass(
        name=class_data['name'],
        description=None,  # Could add this to JSON if desired
        class_data=class_data,  # Store entire structure as JSON
        is_default=True,
        campaign_id=None  # Default classes have no campaign
    )

    db.add(char_class)
    print(f"  ✓ Created: {class_data['name']}")
    return 1, 0


def main():
    """Main seeding function."""
    db = SessionLocal()
    seed_dir = Path(__file__).parent / "seed_data" / "character_classes"

    if not seed_dir.exists():
        print(f"❌ Seed directory not found: {seed_dir}")
        sys.exit(1)

    print("=" * 60)
    print("SEEDING DEFAULT CHARACTER CLASSES")
    print("=" * 60)

    total_created = 0
    total_skipped = 0

    # Classes to seed (in order)
    classes = ["fighter", "cleric", "magic_user", "thief"]

    for class_name in classes:
        filepath = seed_dir / f"{class_name}.json"

        if not filepath.exists():
            print(f"\n⚠ Warning: {filepath.name} not found, skipping...")
            continue

        print(f"\n⚔️  Seeding {class_name.replace('_', ' ').title()}...")

        try:
            class_data = load_class_from_json(filepath)
            created, skipped = seed_class(db, class_data, class_name)
            total_created += created
            total_skipped += skipped
            db.commit()
        except Exception as e:
            print(f"  ❌ Error seeding {class_name}: {e}")
            db.rollback()

    print("\n" + "=" * 60)
    print(f"✅ Seeding complete!")
    print(f"   Created: {total_created}")
    print(f"   Skipped: {total_skipped}")
    print("=" * 60)

    db.close()


if __name__ == "__main__":
    main()
