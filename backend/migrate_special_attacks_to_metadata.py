#!/usr/bin/env python3
"""Migrate special_attacks from standalone field into ability_metadata as type 'special_attack'.

Each class's special_attacks entries are grouped under their matching ability name
and stored as ability_metadata[ability_name] = {type: "special_attack", attacks: [...]}.
The standalone special_attacks field is then removed.
"""
import json
import sqlite3

DB_PATH = "data/ose_sheets.db"

# Map: class_name -> ability_name that should hold the special_attack metadata
# The attacks data is already in special_attacks; we just need to know which ability key to file it under.
ABILITY_KEY_MAP = {
    "Thief": "Backstab",
    "Acrobat": "Tumbling Attack",
    "Assassin": "Assassin Skills",
    "Half-Orc": "Backstab",
    "Knight": "Mounted Combat",
}


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, class_data FROM character_classes "
        "WHERE json_extract(class_data, '$.special_attacks') IS NOT NULL"
    )
    rows = cursor.fetchall()

    for class_id, class_name, raw in rows:
        cd = json.loads(raw)
        attacks = cd.get("special_attacks", [])
        ability_key = ABILITY_KEY_MAP.get(class_name)

        if not ability_key or not attacks:
            print(f"  SKIP: {class_name} — no mapping or no attacks")
            continue

        # Ensure ability_metadata exists
        if "ability_metadata" not in cd:
            cd["ability_metadata"] = {}

        # Store as special_attack type under the matching ability name
        cd["ability_metadata"][ability_key] = {
            "type": "special_attack",
            "attacks": attacks,
        }

        # Remove the standalone field
        del cd["special_attacks"]

        cursor.execute(
            "UPDATE character_classes SET class_data = ? WHERE id = ?",
            (json.dumps(cd), class_id),
        )
        print(f"  OK: {class_name} — moved {len(attacks)} attack(s) to ability_metadata[\"{ability_key}\"]")

    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
