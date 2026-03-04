"""Mercenary reference data and helper functions for OSE."""

MERCENARY_TYPES = {
    "archer": {
        "name": "Archer",
        "ac": 6,
        "morale": 8,
        "desc": "Shortbow, leather armor, dagger, shield.",
        "costs": {"human": 5, "dwarf": None, "elf": 10, "orc": 3, "goblin": 2},
    },
    "archer_mounted": {
        "name": "Archer, Mounted",
        "ac": 9,
        "morale": 9,
        "desc": "Shortbow, dagger, riding horse.",
        "costs": {"human": 15, "dwarf": None, "elf": 30, "orc": None, "goblin": None},
    },
    "crossbowman": {
        "name": "Crossbowman",
        "ac": 5,
        "morale": 8,
        "desc": "Crossbow, chainmail.",
        "costs": {"human": 4, "dwarf": 6, "elf": None, "orc": 2, "goblin": None},
    },
    "crossbowman_mounted": {
        "name": "Crossbowman, Mounted",
        "ac": 9,
        "morale": 9,
        "desc": "Crossbow, horseman's hammer, mule.",
        "costs": {"human": None, "dwarf": 15, "elf": None, "orc": None, "goblin": None},
    },
    "footman_light": {
        "name": "Footman, Light",
        "ac": 6,
        "morale": 8,
        "desc": "Sword, leather armor, shield.",
        "costs": {"human": 2, "dwarf": None, "elf": 4, "orc": 1, "goblin": 0.5},
    },
    "footman_heavy": {
        "name": "Footman, Heavy",
        "ac": 4,
        "morale": 8,
        "desc": "Sword, chainmail, shield.",
        "costs": {"human": 3, "dwarf": 5, "elf": 6, "orc": 1.5, "goblin": None},
    },
    "horseman_light": {
        "name": "Horseman, Light",
        "ac": 7,
        "morale": 9,
        "desc": "Lance, short sword, leather armor, riding horse.",
        "costs": {"human": 10, "dwarf": None, "elf": 20, "orc": None, "goblin": None},
    },
    "horseman_medium": {
        "name": "Horseman, Medium",
        "ac": 5,
        "morale": 9,
        "desc": "Lance, arming sword, chainmail, light warhorse.",
        "costs": {"human": 15, "dwarf": None, "elf": None, "orc": None, "goblin": None},
    },
    "horseman_heavy": {
        "name": "Horseman, Heavy",
        "ac": 3,
        "morale": 9,
        "desc": "Lance, arming sword, plate mail, heavy warhorse.",
        "costs": {"human": 20, "dwarf": None, "elf": None, "orc": None, "goblin": None},
    },
    "longbowman": {
        "name": "Longbowman",
        "ac": 5,
        "morale": 8,
        "desc": "Longbow, sword, chainmail.",
        "costs": {"human": 10, "dwarf": None, "elf": 20, "orc": None, "goblin": None},
    },
    "peasant": {
        "name": "Peasant",
        "ac": 9,
        "morale": 6,
        "desc": "Staff.",
        "costs": {"human": 1, "dwarf": None, "elf": None, "orc": None, "goblin": None},
    },
    "wolf_rider": {
        "name": "Wolf Rider",
        "ac": 7,
        "morale": 9,
        "desc": "Spear, leather armor, wolf.",
        "costs": {"human": None, "dwarf": None, "elf": None, "orc": None, "goblin": 5},
    },
}

MERCENARY_RACES = ["human", "dwarf", "elf", "orc", "goblin"]


def get_available_races(merc_type: str) -> list[str]:
    """Return races that can be hired for the given mercenary type."""
    info = MERCENARY_TYPES.get(merc_type)
    if not info:
        return []
    return [race for race in MERCENARY_RACES if info["costs"].get(race) is not None]


def get_unit_cost(merc_type: str, race: str, wartime: bool = False) -> float | None:
    """Return monthly cost per unit, doubled if wartime. None if unavailable."""
    info = MERCENARY_TYPES.get(merc_type)
    if not info:
        return None
    cost = info["costs"].get(race)
    if cost is None:
        return None
    return cost * 2 if wartime else cost


def deduct_from_wealth(character, cost_gp: float) -> dict | None:
    """
    Deduct cost (in gp) from character's coin purse.

    Pays from gold first, then electrum, silver, copper.
    Breaks larger coins (gp → change, pp → change) when needed.
    Returns new coin values dict, or None if insufficient funds.
    """
    cost_cp = round(cost_gp * 100)

    pp = character.platinum
    gp = character.gold
    ep = character.electrum
    sp = character.silver
    cp = character.copper

    total_cp = pp * 500 + gp * 100 + ep * 50 + sp * 10 + cp
    if total_cp < cost_cp:
        return None

    remaining = cost_cp

    # 1. Whole gold coins
    use_gp = min(gp, remaining // 100)
    gp -= use_gp
    remaining -= use_gp * 100

    # 2. Whole electrum coins (50 cp each)
    if remaining > 0:
        use_ep = min(ep, remaining // 50)
        ep -= use_ep
        remaining -= use_ep * 50

    # 3. Whole silver coins (10 cp each)
    if remaining > 0:
        use_sp = min(sp, remaining // 10)
        sp -= use_sp
        remaining -= use_sp * 10

    # 4. Copper coins
    if remaining > 0:
        use_cp = min(cp, remaining)
        cp -= use_cp
        remaining -= use_cp

    # 5. Break a gold coin if remainder (e.g. 0.5 gp cost)
    if remaining > 0 and gp > 0:
        gp -= 1
        change = 100 - remaining
        remaining = 0
        sp += change // 10
        cp += change % 10

    # 6. Break an electrum coin
    if remaining > 0 and ep > 0:
        ep -= 1
        change = 50 - remaining
        remaining = 0
        sp += change // 10
        cp += change % 10

    # 7. Break a platinum coin
    if remaining > 0 and pp > 0:
        pp -= 1
        change = 500 - remaining
        remaining = 0
        gp += change // 100
        change %= 100
        ep += change // 50
        change %= 50
        sp += change // 10
        cp += change % 10

    if remaining > 0:
        return None  # shouldn't happen — total was checked

    return {"platinum": pp, "gold": gp, "electrum": ep, "silver": sp, "copper": cp}
