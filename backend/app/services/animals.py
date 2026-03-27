"""Animal reference data for OSE."""

ANIMAL_TYPES = {
    "camel": {
        "name": "Camel",
        "cost_gp": 100,
        "ac": 7,
        "hit_dice": 2.0,
        "hp": 9,
        "morale": 7,
        "base_movement": 150,
        "encumbered_movement": 75,
        "base_load": 3000,
        "max_load": 6000,
        "attacks": [{"name": "Bite", "damage": "1"}, {"name": "Hoof", "damage": "1d4"}],
        "abilities": {
            "Ill-tempered": "Bite or kick creatures in their way, including owners.",
            "Water": "After drinking well, can survive 2 weeks without water.",
            "Desert travel": "Move at full speed through broken lands and deserts.",
        },
    },
    "draft_horse": {
        "name": "Draft Horse",
        "cost_gp": 40,
        "ac": 7,
        "hit_dice": 3.0,
        "hp": 13,
        "morale": 6,
        "base_movement": 90,
        "encumbered_movement": 45,
        "base_load": 4500,
        "max_load": 9000,
        "attacks": [],
        "abilities": {"Non-combatant": "Flee, if attacked."},
    },
    "riding_horse": {
        "name": "Riding Horse",
        "cost_gp": 75,
        "ac": 7,
        "hit_dice": 2.0,
        "hp": 9,
        "morale": 7,
        "base_movement": 240,
        "encumbered_movement": 120,
        "base_load": 3000,
        "max_load": 6000,
        "attacks": [{"name": "Hoof", "damage": "1d4"}],
        "abilities": {},
    },
    "war_horse": {
        "name": "War Horse",
        "cost_gp": 250,
        "ac": 7,
        "hit_dice": 3.0,
        "hp": 13,
        "morale": 9,
        "base_movement": 120,
        "encumbered_movement": 60,
        "base_load": 4000,
        "max_load": 8000,
        "attacks": [{"name": "Hoof", "damage": "1d6"}],
        "abilities": {
            "Charge": "When not in melee, requires 20 yard run. Rider's lance inflicts double damage.",
            "Melee": "When in melee, both rider and horse can attack.",
        },
    },
    "mule": {
        "name": "Mule",
        "cost_gp": 30,
        "ac": 7,
        "hit_dice": 2.0,
        "hp": 9,
        "morale": 8,
        "base_movement": 120,
        "encumbered_movement": 60,
        "base_load": 2000,
        "max_load": 4000,
        "attacks": [{"name": "Kick", "damage": "1d4"}],
        "abilities": {
            "Tenacious": "Can be taken underground, if the referee allows it.",
            "Defensive": "May attack if threatened, but cannot be trained to attack on command.",
        },
    },
    "hunting_dog": {
        "name": "Hunting Dog",
        "cost_gp": 17,
        "ac": 7,
        "hit_dice": 1.5,  # 1+2
        "hp": 6,
        "morale": 10,
        "base_movement": 180,
        "encumbered_movement": None,
        "base_load": None,
        "max_load": None,
        "attacks": [{"name": "Bite", "damage": "1d6"}],
        "abilities": {
            "Tracking": "By scent. Once started, very difficult to put off the trail.",
            "Command": "Trained to attack on owner's command.",
        },
    },
    "war_dog": {
        "name": "War Dog",
        "cost_gp": 25,
        "ac": 8,
        "hit_dice": 2.5,  # 2+2
        "hp": 11,
        "morale": 11,
        "base_movement": 120,
        "encumbered_movement": None,
        "base_load": None,
        "max_load": None,
        "attacks": [{"name": "Bite", "damage": "2d4"}],
        "abilities": {
            "Armour": "Trained to wear armour (see Tack and Harness).",
            "Command": "Trained to attack on owner's command.",
        },
    },
}

# Equipment definitions
ANIMAL_EQUIPMENT = {
    "saddle": {"name": "Saddle & Bridle", "cost_gp": 25, "weight": 0, "ac_override": None, "capacity": None},
    "barding": {"name": "Horse Barding", "cost_gp": 150, "weight": 600, "ac_override": 5, "capacity": None},
    "saddlebags": {"name": "Saddle Bags", "cost_gp": 5, "weight": 0, "capacity": 300},
    "dog_armor": {"name": "Dog Armour", "cost_gp": 25, "weight": 0, "ac_override": 6, "capacity": None},
    "dog_pack": {"name": "Dog Pack", "cost_gp": 5, "weight": 0, "capacity": 50},
}


def compute_animal_load(animal) -> dict:
    """Compute current load, effective movement, and capacity for an animal."""
    equipment = animal.equipment or {}
    inventory = animal.inventory or []

    # Equipment weight
    equip_weight = 0
    if equipment.get("barding"):
        equip_weight += 600

    # Inventory weight (would need item lookup — simplified as stored weight)
    inv_weight = sum(entry.get("weight", 0) * entry.get("quantity", 1) for entry in inventory)

    current_load = equip_weight + inv_weight

    # Container capacity from saddlebags/dog_pack
    container_capacity = 0
    if equipment.get("saddlebags"):
        container_capacity += 300
    if equipment.get("dog_pack"):
        container_capacity += 50

    # Determine movement tier
    if animal.base_load is None:
        # Animals without load capacity (dogs without packs)
        effective_movement = animal.base_movement
        load_tier = "none"
    elif current_load <= (animal.base_load or 0):
        effective_movement = animal.base_movement
        load_tier = "unencumbered"
    elif current_load <= (animal.max_load or 0):
        effective_movement = animal.encumbered_movement or animal.base_movement
        load_tier = "encumbered"
    else:
        effective_movement = 0
        load_tier = "overloaded"

    # AC override from equipment
    effective_ac = animal.ac
    if equipment.get("barding"):
        effective_ac = 5
    elif equipment.get("dog_armor"):
        effective_ac = 6

    return {
        "current_load": current_load,
        "container_capacity": container_capacity,
        "effective_movement": effective_movement,
        "effective_ac": effective_ac,
        "load_tier": load_tier,
    }
