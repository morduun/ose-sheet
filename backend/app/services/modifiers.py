"""OSE attribute modifier calculations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Lookup tables — all indexed by ability score (keys are ints 3–18)
# ---------------------------------------------------------------------------

_SCORE_BRACKET = [
    (3,   3),
    (4,   5),
    (6,   8),
    (9,  12),
    (13, 15),
    (16, 17),
    (18, 18),
]

_STR_MELEE = {3: -3, 4: -2, 5: -2, 6: -1, 7: -1, 8: -1,
              9: 0, 10: 0, 11: 0, 12: 0,
              13: 1, 14: 1, 15: 1, 16: 2, 17: 2, 18: 3}

_STR_OPEN_DOORS = {3: "1-in-6", 4: "1-in-6", 5: "1-in-6",
                   6: "1-in-6", 7: "1-in-6", 8: "1-in-6",
                   9: "2-in-6", 10: "2-in-6", 11: "2-in-6", 12: "2-in-6",
                   13: "3-in-6", 14: "3-in-6", 15: "3-in-6",
                   16: "4-in-6", 17: "4-in-6",
                   18: "5-in-6"}

_INT_LANGUAGES = {3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0,
                  9: 0, 10: 0, 11: 0, 12: 0,
                  13: 1, 14: 1, 15: 1, 16: 2, 17: 2, 18: 3}

_INT_LITERATE = {3: False, 4: False, 5: False, 6: False, 7: False, 8: False,
                 9: True, 10: True, 11: True, 12: True,
                 13: True, 14: True, 15: True, 16: True, 17: True, 18: True}

_WIS_MAGIC_SAVES = {3: -3, 4: -2, 5: -2, 6: -1, 7: -1, 8: -1,
                    9: 0, 10: 0, 11: 0, 12: 0,
                    13: 1, 14: 1, 15: 1, 16: 2, 17: 2, 18: 3}

_DEX_AC = {3: 3, 4: 2, 5: 2, 6: 1, 7: 1, 8: 1,
           9: 0, 10: 0, 11: 0, 12: 0,
           13: -1, 14: -1, 15: -1, 16: -2, 17: -2, 18: -3}

_DEX_MISSILE = {3: -3, 4: -2, 5: -2, 6: -1, 7: -1, 8: -1,
                9: 0, 10: 0, 11: 0, 12: 0,
                13: 1, 14: 1, 15: 1, 16: 2, 17: 2, 18: 3}

_DEX_INITIATIVE = {3: -2, 4: -1, 5: -1, 6: -1, 7: -1, 8: -1,
                   9: 0, 10: 0, 11: 0, 12: 0,
                   13: 1, 14: 1, 15: 1, 16: 1, 17: 1, 18: 2}

_CON_HP = {3: -3, 4: -2, 5: -2, 6: -1, 7: -1, 8: -1,
           9: 0, 10: 0, 11: 0, 12: 0,
           13: 1, 14: 1, 15: 1, 16: 2, 17: 2, 18: 3}

_CHA_REACTIONS = {3: -2, 4: -1, 5: -1, 6: -1, 7: -1, 8: -1,
                  9: 0, 10: 0, 11: 0, 12: 0,
                  13: 1, 14: 1, 15: 1, 16: 1, 17: 1, 18: 2}

_CHA_MAX_RETAINERS = {3: 1, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3,
                      9: 4, 10: 4, 11: 4, 12: 4,
                      13: 5, 14: 5, 15: 5, 16: 6, 17: 6, 18: 7}

_CHA_LOYALTY = {3: 4, 4: 5, 5: 5, 6: 6, 7: 6, 8: 6,
                9: 7, 10: 7, 11: 7, 12: 7,
                13: 8, 14: 8, 15: 8, 16: 9, 17: 9, 18: 10}

# Prime requisite XP bonus — keyed by score
_XP_BONUS_PCT = {3: -20, 4: -20, 5: -20,
                 6: -10, 7: -10, 8: -10,
                 9: 0, 10: 0, 11: 0, 12: 0,
                 13: 5, 14: 5, 15: 5,
                 16: 10, 17: 10, 18: 10}


def _clamp(score: int) -> int:
    """Clamp score to valid 3–18 range."""
    return max(3, min(18, score))


def _xp_bonus_for_class(scores: dict[str, int], class_data: dict) -> int:
    """
    Calculate XP bonus percentage based on prime requisite(s).

    For classes with a single prime requisite the bonus is looked up
    directly. For multiple prime requisites the lowest qualifying bonus
    applies (per OSE rules).
    """
    prime_reqs = class_data.get("prime_requisite", [])
    if not prime_reqs:
        return 0

    stat_map = {
        "STR": scores.get("strength", 10),
        "INT": scores.get("intelligence", 10),
        "WIS": scores.get("wisdom", 10),
        "DEX": scores.get("dexterity", 10),
        "CON": scores.get("constitution", 10),
        "CHA": scores.get("charisma", 10),
    }

    bonuses = [_XP_BONUS_PCT.get(_clamp(stat_map.get(pr, 10)), 0) for pr in prime_reqs]
    return min(bonuses)


def get_class_ability_modifiers(character) -> dict[str, int]:
    """
    Extract active ability_metadata modifiers at the character's current level.

    Returns a dict keyed by target (e.g. ``"ac"``) with the summed modifier
    value across all abilities of type ``"modifier"`` for that target.
    """
    if not character.character_class:
        return {}
    class_data = character.character_class.class_data or {}
    ability_meta = class_data.get("ability_metadata", {})
    if not ability_meta:
        return {}

    level_index = max(0, (character.level or 1) - 1)
    totals: dict[str, int] = {}
    for _name, meta in ability_meta.items():
        if meta.get("type") != "modifier":
            continue
        target = meta.get("target")
        values = meta.get("values", [])
        if not target or not values:
            continue
        idx = min(level_index, len(values) - 1)
        totals[target] = totals.get(target, 0) + values[idx]
    return totals


def get_equipped_identified_items(character_id: int, db: "Session") -> list[tuple]:
    """
    Query equipped + identified items for a character.

    Returns list of (Item, slot) tuples for items where slot IS NOT NULL
    and identified = true.
    """
    from app.models.item import character_items, Item

    rows = db.execute(
        character_items.select().where(
            (character_items.c.character_id == character_id)
            & (character_items.c.slot.isnot(None))
            & (character_items.c.identified == True)
        )
    ).fetchall()

    if not rows:
        return []

    item_ids = {row.item_id: row.slot for row in rows}
    items = db.query(Item).filter(Item.id.in_(item_ids.keys())).all()
    return [(item, item_ids[item.id]) for item in items]


def _extract_ability_metadata(item) -> list[dict]:
    """Extract the ability_metadata array from an item's item_metadata."""
    meta = item.item_metadata or {}
    return meta.get("ability_metadata", [])


def get_item_ability_modifiers(character_id: int, db: "Session") -> dict[str, int]:
    """
    Sum modifier-type ability_metadata entries across equipped+identified items.

    Returns dict keyed by target (e.g. "ac", "dexterity") with summed values.
    """
    equipped = get_equipped_identified_items(character_id, db)
    totals: dict[str, int] = {}
    for item, _slot in equipped:
        for entry in _extract_ability_metadata(item):
            if entry.get("type") != "modifier":
                continue
            target = entry.get("target")
            value = entry.get("value", 0)
            if target and value:
                totals[target] = totals.get(target, 0) + value
    return totals


def get_item_round_effects(character_id: int, db: "Session") -> list[dict]:
    """
    Return round_effect entries from equipped+identified items.

    Returns [{item_id, item_name, effect, value, description}].
    """
    equipped = get_equipped_identified_items(character_id, db)
    results = []
    for item, _slot in equipped:
        for entry in _extract_ability_metadata(item):
            if entry.get("type") != "round_effect":
                continue
            results.append({
                "item_id": item.id,
                "item_name": item.name,
                "effect": entry.get("effect", "hp"),
                "value": entry.get("value", 0),
                "description": entry.get("description", ""),
            })
    return results


def get_item_skills(character_id: int, db: "Session") -> list[dict]:
    """
    Return skill entries from equipped+identified items.

    Returns [{item_id, item_name, rolls: {name: {chance, die}}}].
    """
    equipped = get_equipped_identified_items(character_id, db)
    results = []
    for item, _slot in equipped:
        for entry in _extract_ability_metadata(item):
            if entry.get("type") != "skill":
                continue
            rolls = entry.get("rolls", {})
            if rolls:
                results.append({
                    "item_id": item.id,
                    "item_name": item.name,
                    "rolls": rolls,
                })
    return results


def get_item_special_attacks(character_id: int, db: "Session") -> list[dict]:
    """
    Return special_attack entries from equipped+identified items.

    Returns [{item_id, item_name, attacks: [...]}].
    """
    equipped = get_equipped_identified_items(character_id, db)
    results = []
    for item, _slot in equipped:
        for entry in _extract_ability_metadata(item):
            if entry.get("type") != "special_attack":
                continue
            attacks = entry.get("attacks", [])
            if attacks:
                results.append({
                    "item_id": item.id,
                    "item_name": item.name,
                    "attacks": attacks,
                })
    return results


def get_item_auras(character_id: int, db: "Session") -> list[dict]:
    """
    Return aura entries from equipped+identified items.

    Returns [{item_id, item_name, description}].
    """
    equipped = get_equipped_identified_items(character_id, db)
    results = []
    for item, _slot in equipped:
        for entry in _extract_ability_metadata(item):
            if entry.get("type") != "aura":
                continue
            desc = entry.get("description", "")
            if desc:
                results.append({
                    "item_id": item.id,
                    "item_name": item.name,
                    "description": desc,
                })
    return results


# ---------------------------------------------------------------------------
# Encumbrance table — OSE movement rates by total coin weight
# ---------------------------------------------------------------------------

_ENCUMBRANCE_TABLE = [
    (400,  120),
    (600,   90),
    (800,   60),
    (1600,  30),
]
_MAX_CARRY = 1600


def compute_encumbrance(character, db) -> dict:
    """
    Compute total encumbrance (in coins) and derived movement rate.

    Sums item.weight * quantity for ALL inventory items plus coin totals.
    Items with null weight are treated as 0 (weightless until GM assigns).
    """
    from app.models.item import character_items, Item

    rows = db.execute(
        character_items.select().where(
            character_items.c.character_id == character.id
        )
    ).fetchall()

    item_weight = 0
    if rows:
        item_ids = {}
        for row in rows:
            item_ids.setdefault(row.item_id, 0)
            item_ids[row.item_id] += row.quantity
        items = db.query(Item).filter(Item.id.in_(item_ids.keys())).all()
        for item in items:
            item_weight += (item.weight or 0) * item_ids[item.id]

    coin_weight = (
        (character.copper or 0)
        + (character.silver or 0)
        + (character.electrum or 0)
        + (character.gold or 0)
        + (character.platinum or 0)
    )

    total = item_weight + coin_weight

    movement = 0
    for threshold, rate in _ENCUMBRANCE_TABLE:
        if total <= threshold:
            movement = rate
            break

    return {
        "encumbrance": total,
        "effective_movement": movement,
    }


def compute_ac(character, db) -> dict:
    """
    Compute AC, rear_ac, shieldless_ac from equipped items + DEX + class ability modifiers.

    OSE rules:
    - Unarmored base AC = 9
    - Equipped armor sets base AC from item_metadata["ac"]
    - DEX modifier is added (high DEX gives negative modifier = better AC)
    - Shield gives -1 AC bonus
    - Class ability modifiers targeting "ac" apply to ac and shieldless_ac
      (NOT rear_ac, matching the DEX exclusion pattern)
    - Rear AC = base AC only (no DEX, no shield, no ability mods)
    - Shieldless AC = base AC + DEX mod + ability mods (no shield)
    """
    from app.models.item import character_items, Item

    rows = db.execute(
        character_items.select().where(
            (character_items.c.character_id == character.id)
            & (character_items.c.slot.isnot(None))
        )
    ).fetchall()

    equipped_item_ids = {row.item_id: row.slot for row in rows}
    base_ac = 9
    has_shield = False

    if equipped_item_ids:
        items = db.query(Item).filter(Item.id.in_(equipped_item_ids.keys())).all()
        for item in items:
            slot = equipped_item_ids[item.id]
            if slot == "armor" and item.item_metadata:
                ac_val = item.item_metadata.get("ac")
                if ac_val is not None:
                    base_ac = ac_val
            elif slot == "shield":
                has_shield = True

    dex_mod = _DEX_AC[_clamp(character.dexterity)]
    shield_bonus = -1 if has_shield else 0

    # Class ability modifiers (e.g. Barbarian "Agile Fighting")
    ability_mods = get_class_ability_modifiers(character)
    ac_ability_mod = ability_mods.get("ac", 0)

    # Item ability modifiers (e.g. Ring of Protection)
    item_mods = get_item_ability_modifiers(character.id, db)
    ac_item_mod = item_mods.get("ac", 0)

    return {
        "ac": base_ac + dex_mod + shield_bonus + ac_ability_mod + ac_item_mod,
        "rear_ac": base_ac,
        "shieldless_ac": base_ac + dex_mod + ac_ability_mod + ac_item_mod,
    }


def compute_equipped_weapons(character, db, is_gm: bool = True) -> list[dict]:
    """
    Compute effective THAC0, damage, and range for each equipped weapon.

    OSE combat rules:
    - Melee: THAC0 = base - STR_melee - hit_bonus; damage += STR_melee + damage_bonus
    - Thrown (melee w/ range): THAC0 = base - DEX_missile - hit_bonus; damage += damage_bonus only
    - Ranged: THAC0 = base - DEX_missile - hit_bonus; damage += ammo.damage_bonus only
    - Dual-wield: main-hand +2, off-hand +4 to THAC0

    When is_gm=False, unidentified weapons show their unidentified_name and
    magical bonuses (hit_bonus, damage_bonus) are zeroed out.
    """
    from app.models.item import character_items, Item

    rows = db.execute(
        character_items.select().where(
            (character_items.c.character_id == character.id)
            & (character_items.c.slot.in_(["main-hand", "off-hand", "ammo"]))
        )
    ).fetchall()

    if not rows:
        return []

    slot_map = {row.item_id: row.slot for row in rows}
    qty_map = {row.item_id: row.quantity for row in rows}
    identified_map = {row.item_id: row.identified for row in rows}
    items = db.query(Item).filter(Item.id.in_(slot_map.keys())).all()
    items_by_id = {item.id: item for item in items}

    # Identify weapons and ammo
    weapons = []  # (item, slot)
    ammo_item = None
    ammo_count = 0
    for item_id, slot in slot_map.items():
        item = items_by_id.get(item_id)
        if not item:
            continue
        if slot == "ammo":
            ammo_item = item
            ammo_count = qty_map.get(item_id, 0)
        elif item.item_type == "weapon":
            weapons.append((item, slot))

    if not weapons:
        return []

    base_thac0 = (character.combat_stats or {}).get("thac0", 19)
    str_mod = _STR_MELEE[_clamp(character.strength)]
    dex_mod = _DEX_MISSILE[_clamp(character.dexterity)]

    # Class ability modifiers (e.g. Halfling "Missile Combat Bonus")
    ability_mods = get_class_ability_modifiers(character)
    missile_thac0_mod = ability_mods.get("missile_thac0", 0)
    melee_thac0_mod = ability_mods.get("melee_thac0", 0)

    # Item ability modifiers (e.g. Gauntlets of Ogre Power)
    item_mods = get_item_ability_modifiers(character.id, db)
    missile_thac0_mod += item_mods.get("missile_thac0", 0)
    melee_thac0_mod += item_mods.get("melee_thac0", 0)

    # Dual-wield: both hand slots occupied by weapons
    dual_wield = (
        any(s == "main-hand" for _, s in weapons)
        and any(s == "off-hand" for _, s in weapons)
    )

    result = []
    for item, slot in weapons:
        meta = item.item_metadata or {}
        weapon_identified = identified_map.get(item.id, False)

        # When player view and weapon is unidentified with an unidentified_name,
        # mask magical bonuses and qualities
        mask = not is_gm and not weapon_identified and item.unidentified_name
        display_name = item.unidentified_name if mask else item.name

        hit_bonus = 0 if mask else meta.get("hit_bonus", 0)
        damage_bonus = 0 if mask else meta.get("damage_bonus", 0)
        damage_dice = meta.get("damage_dice", "1d6")
        weapon_range = meta.get("range")
        requires_ammo = meta.get("requires_ammo")
        qualities = [] if mask else meta.get("qualities", [])

        # Determine weapon type
        is_ranged = requires_ammo is not None
        is_thrown = (not is_ranged) and weapon_range is not None

        if is_ranged:
            # Pure ranged weapon (bow, crossbow)
            penalty = 0
            if dual_wield:
                penalty = 2 if slot == "main-hand" else 4
            eff_thac0 = base_thac0 - dex_mod - hit_bonus + penalty - missile_thac0_mod

            ammo_damage_bonus = 0
            ammo_name = None
            if ammo_item and ammo_item.item_metadata:
                ammo_meta = ammo_item.item_metadata
                if ammo_meta.get("ammo_type") == requires_ammo or requires_ammo is True:
                    ammo_damage_bonus = ammo_meta.get("damage_bonus", 0)
                    ammo_name = ammo_item.name

            total_dmg_mod = ammo_damage_bonus
            entry = {
                "slot": slot,
                "item_id": item.id,
                "name": display_name,
                "weapon_type": "ranged",
                "effective_thac0": eff_thac0,
                "damage_dice": damage_dice,
                "damage_mod": total_dmg_mod,
                "range": weapon_range,
                "qualities": qualities,
                "ammo_count": ammo_count,
                "identified": weapon_identified,
                "unidentified_name": item.unidentified_name,
            }
            if dual_wield:
                entry["dual_wield_penalty"] = penalty
            if ammo_name:
                entry["ammo_name"] = ammo_name
                entry["ammo_item_id"] = ammo_item.id
            # Item special attacks (from weapon's own ability_metadata)
            if weapon_identified:
                item_specials = [
                    e.get("attacks", [])
                    for e in _extract_ability_metadata(item)
                    if e.get("type") == "special_attack"
                ]
                flat_specials = [a for group in item_specials for a in group]
                if flat_specials:
                    entry["item_special_attacks"] = flat_specials
            result.append(entry)

        else:
            # Melee entry
            penalty = 0
            if dual_wield:
                penalty = 2 if slot == "main-hand" else 4
            eff_thac0 = base_thac0 - str_mod - hit_bonus + penalty - melee_thac0_mod
            total_dmg_mod = str_mod + damage_bonus

            entry = {
                "slot": slot,
                "item_id": item.id,
                "name": display_name,
                "weapon_type": "melee",
                "effective_thac0": eff_thac0,
                "damage_dice": damage_dice,
                "damage_mod": total_dmg_mod,
                "range": "Melee",
                "qualities": qualities,
                "identified": weapon_identified,
                "unidentified_name": item.unidentified_name,
            }
            if dual_wield:
                entry["dual_wield_penalty"] = penalty
            # Item special attacks (from weapon's own ability_metadata)
            if weapon_identified:
                item_specials = [
                    e.get("attacks", [])
                    for e in _extract_ability_metadata(item)
                    if e.get("type") == "special_attack"
                ]
                flat_specials = [a for group in item_specials for a in group]
                if flat_specials:
                    entry["item_special_attacks"] = flat_specials
            result.append(entry)

            # Thrown entry (if weapon has range but no requires_ammo)
            if is_thrown:
                thrown_thac0 = base_thac0 - dex_mod - hit_bonus + penalty - missile_thac0_mod
                entry_thrown = {
                    "slot": slot,
                    "item_id": item.id,
                    "name": display_name,
                    "weapon_type": "thrown",
                    "effective_thac0": thrown_thac0,
                    "damage_dice": damage_dice,
                    "damage_mod": damage_bonus,
                    "range": weapon_range,
                    "qualities": qualities,
                    "identified": weapon_identified,
                    "unidentified_name": item.unidentified_name,
                }
                if dual_wield:
                    entry_thrown["dual_wield_penalty"] = penalty
                # Copy item special attacks to thrown entry too
                if weapon_identified:
                    item_specials = [
                        e.get("attacks", [])
                        for e in _extract_ability_metadata(item)
                        if e.get("type") == "special_attack"
                    ]
                    flat_specials = [a for group in item_specials for a in group]
                    if flat_specials:
                        entry_thrown["item_special_attacks"] = flat_specials
                result.append(entry_thrown)

    return result


def calculate_modifiers(character) -> dict:
    """
    Calculate all OSE attribute modifiers for a character.

    Args:
        character: Character model instance (or any object with the six
                   ability score attributes and character_class relationship).

    Returns:
        Dict of modifier values keyed by category.
    """
    str_ = _clamp(character.strength)
    int_ = _clamp(character.intelligence)
    wis  = _clamp(character.wisdom)
    dex  = _clamp(character.dexterity)
    con  = _clamp(character.constitution)
    cha  = _clamp(character.charisma)

    scores = {
        "strength": str_, "intelligence": int_, "wisdom": wis,
        "dexterity": dex, "constitution": con, "charisma": cha,
    }

    class_data = {}
    if character.character_class:
        class_data = character.character_class.class_data or {}

    return {
        "strength": {
            "melee_adj":   _STR_MELEE[str_],
            "open_doors":  _STR_OPEN_DOORS[str_],
        },
        "intelligence": {
            "additional_languages": _INT_LANGUAGES[int_],
            "literate":             _INT_LITERATE[int_],
        },
        "wisdom": {
            "magic_saves": _WIS_MAGIC_SAVES[wis],
        },
        "dexterity": {
            "ac_adj":          _DEX_AC[dex],
            "missile_adj":     _DEX_MISSILE[dex],
            "initiative_adj":  _DEX_INITIATIVE[dex],
        },
        "constitution": {
            "hp_modifier": _CON_HP[con],
        },
        "charisma": {
            "npc_reactions":    _CHA_REACTIONS[cha],
            "max_retainers":    _CHA_MAX_RETAINERS[cha],
            "retainer_loyalty": _CHA_LOYALTY[cha],
        },
        "xp_bonus_pct": _xp_bonus_for_class(scores, class_data),
    }
