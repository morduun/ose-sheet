/**
 * Item metadata schemas and default templates per item type.
 *
 * The `item_metadata` JSON blob on each item holds type-specific properties.
 * These templates document the expected fields and provide sensible defaults
 * for the item creation form.
 *
 * FIELD REFERENCE
 * ===============
 *
 * weapon
 * ------
 *   weapon_type    "melee" | "ranged"     Which ability modifier applies (STR vs DEX)
 *   damage_dice    string, e.g. "1d8"     Dice expression for damage
 *   damage_bonus   int                    Flat bonus to damage (magical weapons)
 *   hit_bonus      int                    Flat bonus to attack roll (magical weapons)
 *   range          string, e.g. "10/20/30"  Short/medium/long range in feet
 *                                           On a melee weapon, implies "thrown"
 *   requires_ammo  string, e.g. "arrows"  Ammo type consumed per shot;
 *                                          matched against ammo's ammo_type field
 *   qualities      string[]               Weapon quality tags. Valid values:
 *                                          melee, missile, slow, two-handed, reload,
 *                                          splash, charge, blunt, brace
 *
 * armor
 * -----
 *   armor_type     "light" | "medium" | "heavy" | "shield"   Descriptive category
 *   ac             int                    Base AC (replaces unarmored 9)
 *   ac_bonus       int                    Additive AC improvement (shields)
 *
 * ammo
 * ----
 *   ammo_type      string, e.g. "arrows"  Matched against weapon's requires_ammo
 *   damage_bonus   int                    Added to ranged weapon damage
 *
 * consumable
 * ----------
 *   effect         string                 What happens when used
 *   charges        int                    Number of uses (potions=1, wands=varies)
 *   qualities      string | string[]      Tags: "food", "drink", "poison", etc.
 *   save           int                    Save-vs-poison target (poisons)
 *   detection      int                    Percent chance of detecting the poison
 *   onset          string                 Time until effect (e.g. "1d4+1 rounds")
 *   effect_saved   string                 Result on successful save
 *   effect_failed  string                 Result on failed save (e.g. "25hp", "Death")
 *
 * potion
 * ------
 *   effect         string                 What the potion does when consumed
 *   duration       string                 How long the effect lasts (e.g. "1d6+1 turns")
 *
 * scroll
 * ------
 *   spell_name     string                 Name of the spell on the scroll
 *   spell_level    int                    Level of the spell
 *   spell_class    string                 Casting class: cleric, magic-user, druid, illusionist
 *
 * ring
 * ----
 *   effect         string                 What the ring does when worn
 *   charges        int | null             Number of uses; null = permanent
 *
 * wand
 * ----
 *   effect         string                 What the wand does when activated
 *   charges        int                    Number of charges remaining (typically 10)
 *   spell_level    int                    Level of the spell effect, if applicable
 *
 * wondrous
 * --------
 *   effect         string                 Description of the item's magical effect
 *
 * tool
 * ----
 *   Freeform. Common keys from seed data:
 *   capacity_slots int                    Carrying capacity (backpacks, sacks)
 *   length_feet    int                    Length (rope, poles)
 *   light_radius   int                    Illumination radius in feet
 *   duration_hours number                 Burn time (torches, lanterns)
 *   duration_days  int                    Consumable duration (rations)
 *
 * treasure
 * --------
 *   gp_value       int                    Appraised value in gold pieces
 *   materials      string                 Composition ("gold and ruby", etc.)
 */

export const ITEM_METADATA_TEMPLATES = {
  weapon: {
    weapon_type: 'melee',
    damage_dice: '1d6',
    damage_bonus: 0,
    hit_bonus: 0,
    qualities: ['melee'],
  },
  armor: {
    armor_type: 'light',
    ac: 7,
  },
  ammo: {
    ammo_type: 'arrows',
    damage_bonus: 0,
  },
  potion: {
    effect: '',
    duration: '',
  },
  scroll: {
    spell_name: '',
    spell_level: null,
    spell_class: '',
  },
  ring: {
    effect: '',
    charges: null,
  },
  wand: {
    effect: '',
    charges: 10,
    spell_level: null,
  },
  wondrous: {
    effect: '',
  },
  consumable: {
    effect: '',
    charges: 1,
  },
  tool: {},
  treasure: {
    gp_value: 0,
  },
};

/**
 * Returns a display-friendly type label for an item.
 * Shields (armor with armor_type "shield") get labelled "shield" instead of "armor".
 */
export function itemTypeLabel(item) {
  if (
    item.item_type === 'armor' &&
    item.item_metadata?.armor_type === 'shield'
  ) {
    return 'shield';
  }
  return item.item_type;
}

/**
 * Normalize a qualities value to an array.
 * Handles string ("food") → ["food"] and passthrough for arrays.
 */
export function normalizeQualities(qualities) {
  if (!qualities) return [];
  if (Array.isArray(qualities)) return qualities;
  if (typeof qualities === 'string') return [qualities];
  return [];
}

/** Valid weapon qualities with tooltip descriptions. */
export const WEAPON_QUALITIES = {
  melee:       'Usable in hand-to-hand combat',
  missile:     'Ranged attack weapon',
  slow:        'Wielder always acts last in the round',
  'two-handed':'Requires both hands; no shield allowed',
  reload:      'Can only fire every other round',
  splash:      'Breaks on hit, doing listed damage for 2 rounds',
  charge:      'Double damage when mounted and moving 60\'+',
  blunt:       'Suitable for clerics',
  brace:       'Braced vs. charge: double damage to charging monsters',
};
