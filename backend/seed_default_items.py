#!/usr/bin/env python
"""Seed default items from JSON files."""

import json
import sys
from pathlib import Path
from app.database import SessionLocal
from app.models import Item

def load_items_from_json(filepath: Path) -> list[dict]:
    with open(filepath, 'r') as f:
        return json.load(f)

def seed_items(db, items_data: list[dict], category: str):
    created = 0
    skipped = 0

    for item_data in items_data:
        existing = db.query(Item).filter(
            Item.name == item_data['name'],
            Item.is_default == True
        ).first()

        if existing:
            print(f"  ⊗ Skipped (exists): {item_data['name']}")
            skipped += 1
            continue

        item = Item(**item_data)
        db.add(item)
        created += 1
        print(f"  ✓ Created: {item_data['name']}")

    db.commit()
    return created, skipped

def main():
    db = SessionLocal()
    seed_dir = Path(__file__).parent / "seed_data" / "items"

    if not seed_dir.exists():
        print(f"❌ Seed directory not found: {seed_dir}")
        sys.exit(1)

    print("="*60)
    print("SEEDING DEFAULT ITEMS")
    print("="*60)

    total_created = 0
    total_skipped = 0

    categories = ["weapons", "armor", "equipment"]

    for category in categories:
        filepath = seed_dir / f"{category}.json"

        if not filepath.exists():
            print(f"\n⚠ Warning: {filepath.name} not found, skipping...")
            continue

        print(f"\n📦 Seeding {category}...")
        items_data = load_items_from_json(filepath)
        created, skipped = seed_items(db, items_data, category)
        total_created += created
        total_skipped += skipped

    print("\n" + "="*60)
    print(f"✅ Seeding complete!")
    print(f"   Created: {total_created}")
    print(f"   Skipped: {total_skipped}")
    print("="*60)

    db.close()

if __name__ == "__main__":
    main()
