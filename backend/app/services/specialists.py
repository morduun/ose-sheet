"""Specialist reference data and helper functions for OSE."""

SPECIALIST_TYPES = {
    "alchemist": {
        "name": "Alchemist",
        "wage": 1000,
        "desc": "Recreates potions at half cost/double speed. Researches new potions at double cost/time.",
    },
    "animal_trainer": {
        "name": "Animal Trainer",
        "wage": 500,
        "desc": "Specialized in one animal type. Up to 6 animals at a time. Min 1 month per behavior.",
    },
    "armorer": {
        "name": "Armorer",
        "wage": 100,
        "desc": "Makes 5 weapons, 3 shields, or 1 suit of armor per month. Maintains gear for 50 troops.",
    },
    "assistant_armorer": {
        "name": "Assistant Armorer",
        "wage": 15,
        "desc": "Works under an armorer to increase production rate.",
    },
    "blacksmith": {
        "name": "Blacksmith",
        "wage": 25,
        "desc": "Works under an armorer to increase production rate.",
    },
    "engineer": {
        "name": "Engineer",
        "wage": 750,
        "desc": "Plans and oversees construction. One needed per 100,000gp project cost.",
    },
    "navigator": {
        "name": "Navigator",
        "wage": 150,
        "desc": "Reads naval charts and navigates by stars. Required when out of sight of coastline.",
    },
    "oarsman": {
        "name": "Oarsman",
        "wage": 2,
        "desc": "Unskilled human manning oars. Not trained for combat.",
    },
    "sage": {
        "name": "Sage",
        "wage": 2000,
        "desc": "Researches obscure knowledge. Time, cost, and success chance set by referee.",
    },
    "sailor": {
        "name": "Sailor",
        "wage": 10,
        "desc": "Skilled ship handler. Can fight with sword, shield, and leather armor.",
    },
    "ships_captain": {
        "name": "Ship's Captain",
        "wage": 250,
        "desc": "Required for large ships. Intimate knowledge of local coasts.",
    },
    "spy": {
        "name": "Spy",
        "wage": 500,
        "desc": "Gathers information. Often a thief. Reliability not guaranteed.",
    },
}


def get_specialist_wage(spec_type: str) -> int | None:
    """Return monthly wage for a specialist type, or None if unknown."""
    info = SPECIALIST_TYPES.get(spec_type)
    if not info:
        return None
    return info["wage"]
