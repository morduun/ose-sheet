#!/usr/bin/env python3
"""Add special_attacks to class_data for applicable character classes."""
import json
import sqlite3

DB_PATH = "data/ose_sheets.db"

SPECIAL_ATTACKS = {
    "Thief": [
        {
            "name": "Backstab",
            "hit_bonus": 4,
            "damage_multiplier": 2,
            "applies_to": ["melee"],
            "condition": "Opponent unaware",
        },
    ],
    "Assassin": [
        {
            "name": "Assassinate",
            "hit_bonus": 4,
            "applies_to": ["melee"],
            "condition": "Unaware humanoid",
            "effect": "Save vs Death",
            "effect_penalty": [0, 0, 0, -1, -1, -2, -2, -3, -3, -4, -4, -5, -5, -6],
        },
    ],
    "Acrobat": [
        {
            "name": "Tumble",
            "hit_bonus": 0,
            "damage_multiplier": 2,
            "applies_to": ["melee"],
            "condition": "Using Falling/Jumping",
        },
        {
            "name": "Tumble (Unaware)",
            "hit_bonus": 4,
            "damage_multiplier": 2,
            "applies_to": ["melee"],
            "condition": "Unaware target, using Falling/Jumping",
        },
    ],
    "Half-Orc": [
        {
            "name": "Backstab",
            "hit_bonus": 4,
            "damage_multiplier": 2,
            "applies_to": ["melee"],
            "condition": "Opponent unaware",
        },
    ],
    "Knight": [
        {
            "name": "Mounted",
            "hit_bonus": 1,
            "applies_to": ["melee"],
            "condition": "While mounted",
        },
    ],
}


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for class_name, attacks in SPECIAL_ATTACKS.items():
        cursor.execute(
            "SELECT id, class_data FROM character_classes WHERE name = ?",
            (class_name,),
        )
        row = cursor.fetchone()
        if not row:
            print(f"  SKIP: {class_name} not found")
            continue

        class_id, raw = row
        cd = json.loads(raw) if raw else {}
        cd["special_attacks"] = attacks
        cursor.execute(
            "UPDATE character_classes SET class_data = ? WHERE id = ?",
            (json.dumps(cd), class_id),
        )
        print(f"  OK: {class_name} (id={class_id})")

    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
