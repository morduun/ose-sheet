"""Treasure type rolling engine and magic item reference tables for OSE."""

import random
import math


# ---------------------------------------------------------------------------
# Dice rolling utility
# ---------------------------------------------------------------------------

def roll_dice(notation: str) -> int:
    """Roll dice from notation like '2d6', '1d100', '3d8'. Returns total."""
    notation = notation.strip().lower()
    if 'd' not in notation:
        return int(notation)
    parts = notation.split('d')
    count = int(parts[0]) if parts[0] else 1
    sides = int(parts[1])
    return sum(random.randint(1, sides) for _ in range(count))


def roll_percentage() -> int:
    """Roll d100 (1-100)."""
    return random.randint(1, 100)


# ---------------------------------------------------------------------------
# Gem and Jewelry value tables
# ---------------------------------------------------------------------------

GEM_VALUE_TABLE = [
    (4, 10),     # d20 1-4:   10gp
    (9, 50),     # d20 5-9:   50gp
    (15, 100),   # d20 10-15: 100gp
    (19, 500),   # d20 16-19: 500gp
    (20, 1000),  # d20 20:    1000gp
]


def roll_gem_value() -> int:
    """Roll a single gem's value on the d20 table."""
    roll = random.randint(1, 20)
    for threshold, value in GEM_VALUE_TABLE:
        if roll <= threshold:
            return value
    return 1000


def roll_jewelry_value() -> int:
    """Roll a single piece of jewelry's value: 3d6 × 100 gp."""
    return roll_dice("3d6") * 100


# ---------------------------------------------------------------------------
# Magic Item Type Table (d%)
# ---------------------------------------------------------------------------

MAGIC_ITEM_TYPE_TABLE = [
    (10, "armor_shield"),
    (15, "misc_item"),
    (35, "potion"),
    (40, "ring"),
    (45, "rod_staff_wand"),
    (75, "scroll_map"),
    (95, "sword"),
    (100, "weapon"),
]

# ---------------------------------------------------------------------------
# Magic Item Sub-Tables (d% → item name)
# Each is a list of (upper_bound, item_name)
# ---------------------------------------------------------------------------

MAGIC_ARMOR_SHIELD = [
    (15, "Armour +1"), (25, "Armour +1, Shield +1"), (27, "Armour +1, Shield +2"),
    (28, "Armour +1, Shield +3"), (33, "Armour +2"), (36, "Armour +2, Shield +1"),
    (41, "Armour +2, Shield +2"), (42, "Armour +2, Shield +3"), (45, "Armour +3"),
    (46, "Armour +3, Shield +1"), (47, "Armour +3, Shield +2"), (48, "Armour +3, Shield +3"),
    (51, "Cursed Armour -1"), (53, "Cursed Armour -2"), (54, "Cursed Armour -2, Shield +1"),
    (56, "Cursed Armour, AC 9"), (62, "Cursed Shield -2"), (65, "Cursed Shield, AC 9"),
    (85, "Shield +1"), (95, "Shield +2"), (100, "Shield +3"),
]

MAGIC_POTIONS = [
    (3, "Potion of Clairaudience"), (7, "Potion of Clairvoyance"),
    (10, "Potion of Control Animal"), (13, "Potion of Control Dragon"),
    (16, "Potion of Control Giant"), (19, "Potion of Control Human"),
    (22, "Potion of Control Plant"), (25, "Potion of Control Undead"),
    (32, "Potion of Delusion"), (35, "Potion of Diminution"),
    (39, "Potion of ESP"), (43, "Potion of Fire Resistance"),
    (47, "Potion of Flying"), (51, "Potion of Gaseous Form"),
    (55, "Potion of Giant Strength"), (59, "Potion of Growth"),
    (63, "Potion of Healing"), (68, "Potion of Heroism"),
    (72, "Potion of Invisibility"), (76, "Potion of Invulnerability"),
    (80, "Potion of Levitation"), (84, "Potion of Longevity"),
    (86, "Potion of Poison"), (89, "Potion of Polymorph Self"),
    (97, "Potion of Speed"), (100, "Potion of Treasure Finding"),
]

MAGIC_RINGS = [
    (5, "Ring of Control Animals"), (10, "Ring of Control Humans"),
    (16, "Ring of Control Plants"), (26, "Ring of Delusion"),
    (29, "Ring of Djinni Summoning"), (39, "Ring of Fire Resistance"),
    (50, "Ring of Invisibility"), (55, "Ring of Protection +1, 5' radius"),
    (70, "Ring of Protection +1"), (72, "Ring of Regeneration"),
    (74, "Ring of Spell Storing"), (80, "Ring of Spell Turning"),
    (82, "Ring of Telekinesis"), (88, "Ring of Water Walking"),
    (94, "Ring of Weakness"), (96, "Ring of Wishes (1-2)"),
    (97, "Ring of Wishes (1-3)"), (98, "Ring of Wishes (2-4)"),
    (100, "Ring of X-Ray Vision"),
]

MAGIC_RODS_STAVES_WANDS = [
    (2, "Immovable Rod"), (5, "Rod of Absorption"), (11, "Rod of Cancellation"),
    (12, "Rod of Captivation"), (14, "Rod of Lordly Might"), (15, "Rod of Parrying"),
    (16, "Rod of Resurrection"), (17, "Rod of Striking"), (18, "Staff of Commanding"),
    (20, "Staff of Dispelling"), (26, "Staff of Healing"), (27, "Staff of Power"),
    (30, "Staff of Snakes"), (33, "Staff of Striking"), (36, "Staff of Swarming Insects"),
    (38, "Staff of the Healer"), (40, "Staff of Withering"), (41, "Staff of Wizardry"),
    (44, "Staff of the Woodlands"), (47, "Wand of Cold"), (51, "Wand of Enemy Detection"),
    (54, "Wand of Fear"), (57, "Wand of Fire Balls"), (61, "Wand of Illusion"),
    (64, "Wand of Lightning Bolts"), (69, "Wand of Magic Detection"),
    (74, "Wand of Magic Missiles"), (79, "Wand of Metal Detection"),
    (84, "Wand of Negation"), (87, "Wand of Paralysation"),
    (90, "Wand of Polymorph"), (94, "Wand of Radiance"),
    (97, "Wand of Secret Door Detection"), (98, "Wand of Summoning"),
    (100, "Wand of Trap Detection"),
]

MAGIC_SCROLLS = [
    (15, "Scroll: 1 Spell"), (25, "Scroll: 2 Spells"), (31, "Scroll: 3 Spells"),
    (34, "Scroll: 5 Spells"), (35, "Scroll: 7 Spells"), (40, "Cursed Scroll"),
    (50, "Scroll of Protection from Elementals"), (60, "Scroll of Protection from Lycanthropes"),
    (65, "Scroll of Protection from Magic"), (75, "Scroll of Protection from Undead"),
    (78, "Treasure Map I"), (80, "Treasure Map II"), (82, "Treasure Map III"),
    (83, "Treasure Map IV"), (84, "Treasure Map V"), (85, "Treasure Map VI"),
    (86, "Treasure Map VII"), (90, "Treasure Map VIII"), (95, "Treasure Map IX"),
    (96, "Treasure Map X"), (98, "Treasure Map XI"), (100, "Treasure Map XII"),
]

MAGIC_SWORDS = [
    (3, "Short Sword +2, Quickness"), (6, "Sword -1, Berserker (Cursed)"),
    (9, "Sword -1, Cursed"), (12, "Sword -2, Cursed"), (28, "Sword +1"),
    (31, "Sword +1, +2 vs Lycanthropes"), (34, "Sword +1, +2 vs Spell Users"),
    (37, "Sword +1, +3 vs Dragons"), (40, "Sword +1, +3 vs Enchanted Creatures"),
    (43, "Sword +1, +3 vs Regenerating Creatures"), (46, "Sword +1, +3 vs Reptiles"),
    (49, "Sword +1, +3 vs Shape Changers"), (52, "Sword +1, +3 vs Undead"),
    (55, "Sword +1, Dragon Slayer"), (56, "Sword +1, Energy Drain"),
    (59, "Sword +1, Flaming"), (61, "Sword +1, Frost Brand"),
    (64, "Sword +1, Giant Slayer"), (69, "Sword +1, Light"),
    (71, "Sword +1, Locate Objects"), (72, "Sword +1, Luck Blade"),
    (73, "Sword +1, Sharpness"), (78, "Sword +1, Sun Blade"),
    (79, "Sword +1, Wishes"), (80, "Sword +1, Wounding"),
    (85, "Sword +2"), (87, "Sword +2, Charm Person"),
    (88, "Sword +2, Dancing"), (89, "Sword +2, Nine Lives Stealer"),
    (94, "Sword +2, Venger"), (95, "Sword +2, Vorpal"),
    (98, "Sword +3"), (99, "Sword +3, Defender"), (100, "Sword +3, Holy Avenger"),
]

MAGIC_WEAPONS = [
    (1, "Arrow +1, Slaying"), (10, "Arrows +1 (2d6)"), (12, "Arrows +1 (3d10)"),
    (15, "Arrows +2 (1d6)"), (19, "Axe +1"), (21, "Axe +2"),
    (24, "Bow +1"), (25, "Crossbow +1, Distance"), (26, "Crossbow +1, Speed"),
    (27, "Crossbow +2, Accuracy"), (29, "Crossbow Bolts +1 (2d6)"),
    (31, "Crossbow Bolts +1 (3d10)"), (36, "Crossbow Bolts +2 (1d6)"),
    (39, "Dagger +1"), (40, "Dagger +1, Buckle"), (41, "Dagger +1, Throwing"),
    (42, "Dagger +1, Venomous"), (45, "Dagger +2, +3 vs Orcs/Goblins/Kobolds"),
    (46, "Dagger +2, Biter"), (50, "Javelin of Lightning (1d4+1)"),
    (54, "Javelin of Seeking (2d4)"), (58, "Mace +1"), (59, "Mace +1, Disrupting"),
    (62, "Mace +2"), (63, "Mace +3"), (68, "Sling +1"),
    (69, "Sling Bullet +1, Impact (1d4)"), (71, "Spear -1, Backbiter (Cursed)"),
    (75, "Spear +1"), (77, "Spear +2"), (78, "Spear +3"),
    (80, "Staff +1, Growing"), (82, "Trident -2, Yearning (Cursed)"),
    (87, "Trident +1, Fish Command"), (89, "Trident +1, Submission"),
    (93, "Trident +2, Warning"), (96, "War Hammer +1"), (98, "War Hammer +2"),
    (99, "War Hammer +3, Dwarven Thrower"), (100, "War Hammer +3, Thunderbolts"),
]

MAGIC_ITEM_TABLES = {
    "armor_shield": MAGIC_ARMOR_SHIELD,
    "potion": MAGIC_POTIONS,
    "ring": MAGIC_RINGS,
    "rod_staff_wand": MAGIC_RODS_STAVES_WANDS,
    "scroll_map": MAGIC_SCROLLS,
    "sword": MAGIC_SWORDS,
    "weapon": MAGIC_WEAPONS,
    # misc_item handled specially (1d4 → sub-table)
}

# Misc items: 4 sub-tables, each d%
MAGIC_MISC_I = [
    (2, "Alchemist's Beaker"), (3, "Amulet of Prot. Against Possession"),
    (6, "Amulet of Prot. Against Scrying"), (8, "Apparatus of the Crab"),
    (11, "Arrow of Location"), (12, "Bag of Devouring"), (17, "Bag of Holding"),
    (18, "Bag of Transformation"), (19, "Book of Foul Corruption"),
    (20, "Book of Infinite Spells"), (21, "Book of Sublime Holiness"),
    (22, "Boots of Dancing"), (27, "Boots of Levitation"), (31, "Boots of Speed"),
    (35, "Boots of Travelling and Leaping"), (50, "Bracers of Armour"),
    (52, "Bracers of Defencelessness"), (59, "Brooch of Shielding"),
    (64, "Broom of Flying"), (70, "Candle of Invocation"),
    (72, "Chime of Opening"), (73, "Chime of Ravening"),
    (85, "Cloak of Defence"), (95, "Cloak of Flight"),
    (97, "Cloak of Poison"), (100, "Cloak of the Manta Ray"),
]

MAGIC_MISC_II = [
    (5, "Crystal Ball"), (7, "Crystal Ball with Clairaudience"),
    (8, "Crystal Ball with ESP"), (9, "Crystal Hypnosis Ball"),
    (11, "Cube of Force"), (13, "Cube of Frost Resistance"),
    (16, "Decanter of Endless Water"), (20, "Deck of Many Things"),
    (24, "Displacer Cloak"), (26, "Drums of Panic"), (27, "Drums of Thunder"),
    (33, "Dust of Appearance"), (39, "Dust of Disappearance"),
    (40, "Dust of Sneezing and Choking"), (41, "Efreeti Bottle"),
    (43, "Elemental Summoning Device: Air"), (45, "Elemental Summoning Device: Earth"),
    (47, "Elemental Summoning Device: Fire"), (49, "Elemental Summoning Device: Water"),
    (59, "Elven Cloak and Boots"), (60, "Eyes of Charming"),
    (62, "Eyes of Minuscule Sight"), (63, "Eyes of Petrification"),
    (65, "Eyes of the Eagle"), (80, "Feather Token"),
    (95, "Figurine of Wondrous Power"), (97, "Flying Carpet"),
    (98, "Folding Boat"), (100, "Gauntlets of Ogre Power"),
]

MAGIC_MISC_III = [
    (1, "Gem of Brightness"), (2, "Gem of Monster Attraction"),
    (3, "Gem of Pristine Faceting"), (4, "Gem of Seeing"),
    (5, "Girdle of Giant Strength"), (7, "Gloves of Dexterity"),
    (10, "Gloves of Swimming and Climbing"), (12, "Helm of Alignment Changing"),
    (17, "Helm of Read Languages and Magic"), (19, "Helm of Telepathy"),
    (20, "Helm of Teleportation"), (21, "Horn of Blasting"),
    (22, "Horn of Cave-Ins"), (24, "Horn of Frothing"),
    (28, "Horn of the Tritons"), (35, "Horn of Valhalla"),
    (37, "Horseshoes of a Zephyr"), (40, "Horseshoes of Speed"),
    (45, "Incense of Meditation"), (46, "Incense of Obsession"),
    (48, "Instant Fortress"), (49, "Ioun Stones"), (51, "Iron Flask"),
    (53, "Jug of Endless Liquids"), (54, "Libram of Arcane Power"),
    (56, "Loadstone"), (58, "Luckstone"), (59, "Lyre of Building"),
    (61, "Marvellous Pigments"), (64, "Medallion of ESP 30'"),
    (66, "Medallion of ESP 90'"), (68, "Medallion of Thought Projection"),
    (69, "Mirror of Life Trapping"), (70, "Mirror of Mental Prowess"),
    (71, "Mirror of Opposition"), (74, "Necklace of Adaptation"),
    (78, "Necklace of Fireballs"), (80, "Necklace of Strangulation"),
    (84, "Net of Aquatic Snaring"), (87, "Net of Snaring"),
    (90, "Oil of Insubstantiality"), (93, "Oil of Slipperiness"),
    (95, "Pearl of Power"), (97, "Pearl of Wisdom"),
    (100, "Periapt of Foul Rotting"),
]

MAGIC_MISC_IV = [
    (2, "Periapt of Health"), (9, "Periapt of Proof Against Poison"),
    (13, "Periapt of Wound Closure"), (15, "Phylactery of Betrayal"),
    (21, "Phylactery of Faithfulness"), (25, "Phylactery of Longevity"),
    (33, "Pipes of the Sewers"), (34, "Portable Hole"),
    (36, "Purse of Plentiful Coin"), (44, "Restorative Ointment"),
    (51, "Robe of Blending"), (52, "Robe of Eyes"),
    (53, "Robe of Powerlessness"), (54, "Robe of Scintillating Colours"),
    (55, "Robe of the Archmagi"), (63, "Robe of Useful Items"),
    (69, "Rope of Climbing"), (73, "Rope of Entanglement"),
    (75, "Rope of Strangulation"), (76, "Rug of Suffocation"),
    (77, "Saw of Felling"), (79, "Scarab of Chaos"), (80, "Scarab of Death"),
    (86, "Scarab of Protection"), (89, "Scarab of Rage"),
    (90, "Spade of Mighty Digging"), (91, "Sphere of Annihilation"),
    (94, "Sweet Water"), (95, "Talisman of the Sphere"),
    (97, "Vacuous Grimoire"), (100, "Well of Many Worlds"),
]

MAGIC_MISC_TABLES = [MAGIC_MISC_I, MAGIC_MISC_II, MAGIC_MISC_III, MAGIC_MISC_IV]


# ---------------------------------------------------------------------------
# Magic item rolling
# ---------------------------------------------------------------------------

def _roll_on_table(table: list[tuple[int, str]]) -> str:
    """Roll d% and look up result on a (upper_bound, name) table."""
    roll = roll_percentage()
    for threshold, name in table:
        if roll <= threshold:
            return name
    return table[-1][1]  # fallback


def roll_magic_item(subtype: str = "any") -> str:
    """
    Roll a magic item. Subtype can be:
    - "any": roll on type table first, then sub-table
    - "potion", "scroll", "sword", etc.: roll directly on that sub-table
    - "sword_armor_weapon": roll on sword, armor, or weapon (equal chance)
    - "not_weapons": roll on type table, reroll weapons/swords
    """
    if subtype == "any":
        # Roll magic item type
        roll = roll_percentage()
        item_type = "weapon"
        for threshold, itype in MAGIC_ITEM_TYPE_TABLE:
            if roll <= threshold:
                item_type = itype
                break
        return _roll_on_subtable(item_type)

    if subtype == "sword_armor_weapon":
        choice = random.choice(["sword", "armor_shield", "weapon"])
        return _roll_on_table(MAGIC_ITEM_TABLES[choice])

    if subtype == "not_weapons":
        while True:
            roll = roll_percentage()
            item_type = "weapon"
            for threshold, itype in MAGIC_ITEM_TYPE_TABLE:
                if roll <= threshold:
                    item_type = itype
                    break
            if item_type not in ("sword", "weapon"):
                return _roll_on_subtable(item_type)

    # Direct sub-table
    if subtype in MAGIC_ITEM_TABLES:
        return _roll_on_table(MAGIC_ITEM_TABLES[subtype])
    if subtype == "scroll":
        return _roll_on_table(MAGIC_SCROLLS)
    if subtype == "potion":
        return _roll_on_table(MAGIC_POTIONS)

    return roll_magic_item("any")


def _roll_on_subtable(item_type: str) -> str:
    """Roll on the appropriate sub-table for a magic item type."""
    if item_type == "misc_item":
        table_idx = random.randint(0, 3)
        return _roll_on_table(MAGIC_MISC_TABLES[table_idx])
    if item_type in MAGIC_ITEM_TABLES:
        return _roll_on_table(MAGIC_ITEM_TABLES[item_type])
    return f"Unknown magic item type: {item_type}"


# ---------------------------------------------------------------------------
# Treasure type rolling
# ---------------------------------------------------------------------------

def roll_treasure_type(entries: list[dict], bonus: dict | None = None) -> dict:
    """
    Roll a complete treasure type from its entries list.

    Each entry has: type, chance (optional), dice, multiplier (optional),
    and for magic: count, subtype, extras.

    Returns a result dict with coins, gems, jewelry, and magic items.
    """
    result = {
        "coins": {},    # {"cp": 3000, "gp": 7000, ...}
        "gems": [],     # [{"value": 100}, {"value": 50}, ...]
        "jewelry": [],  # [{"value": 800}, {"value": 300}, ...]
        "magic_items": [],  # ["Sword +1", "Potion of Healing", ...]
        "total_gp_value": 0,
    }

    for entry in entries:
        etype = entry.get("type")
        chance = entry.get("chance")
        dice = entry.get("dice")
        multiplier = entry.get("multiplier", 1)

        # Check percentage (if no chance, it's guaranteed — individual types)
        if chance is not None:
            if roll_percentage() > chance:
                continue

        if etype in ("cp", "sp", "ep", "gp", "pp"):
            amount = roll_dice(dice) * multiplier if dice else 0
            result["coins"][etype] = result["coins"].get(etype, 0) + amount

        elif etype == "gems":
            count = roll_dice(dice) if dice else 0
            for _ in range(count):
                result["gems"].append({"value": roll_gem_value()})

        elif etype == "jewelry":
            count = roll_dice(dice) if dice else 0
            for _ in range(count):
                result["jewelry"].append({"value": roll_jewelry_value()})

        elif etype == "magic":
            # Magic items can have complex structures
            rolls = entry.get("rolls", [])
            if rolls:
                for roll_spec in rolls:
                    count = roll_spec.get("count", 1)
                    subtype = roll_spec.get("table", "any")
                    for _ in range(count):
                        result["magic_items"].append(roll_magic_item(subtype))
            else:
                count = entry.get("count", 1)
                subtype = entry.get("subtype", "any")
                for _ in range(count):
                    result["magic_items"].append(roll_magic_item(subtype))

    # Apply bonus (e.g. "+ 1000gp")
    if bonus:
        for coin_type, amount in bonus.items():
            if coin_type in ("cp", "sp", "ep", "gp", "pp"):
                result["coins"][coin_type] = result["coins"].get(coin_type, 0) + amount

    # Calculate total GP value
    coin_values = {"cp": 0.01, "sp": 0.1, "ep": 0.5, "gp": 1, "pp": 5}
    for coin, amount in result["coins"].items():
        result["total_gp_value"] += amount * coin_values.get(coin, 0)
    for gem in result["gems"]:
        result["total_gp_value"] += gem["value"]
    for jewel in result["jewelry"]:
        result["total_gp_value"] += jewel["value"]
    result["total_gp_value"] = round(result["total_gp_value"], 2)

    return result


def parse_treasure_type_string(treasure_str: str) -> tuple[str, dict | None]:
    """
    Parse a treasure type string like "C", "B + 1000gp", "D + 2 potions".
    Returns (base_type_key, bonus_dict_or_none).
    """
    treasure_str = treasure_str.strip()
    if "+" not in treasure_str:
        return (treasure_str.strip().upper(), None)

    parts = treasure_str.split("+", 1)
    base = parts[0].strip().upper()
    bonus_str = parts[1].strip().lower()

    bonus = {}
    # Try to parse "1000gp", "500sp", etc.
    for coin in ["cp", "sp", "ep", "gp", "pp"]:
        if bonus_str.endswith(coin):
            try:
                amount = int(bonus_str[:-len(coin)].strip())
                bonus[coin] = amount
                return (base, bonus)
            except ValueError:
                pass

    # Could be "2 potions" or similar — not a coin bonus, ignore for V1
    return (base, None)
