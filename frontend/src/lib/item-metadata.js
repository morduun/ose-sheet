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
 *   ability_metadata array                Item abilities (see below)
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
 *   ability_metadata array                Item abilities (see below)
 *
 * ability_metadata (array, on any item type)
 * ------------------------------------------
 * Each entry has a "type" plus type-specific fields:
 *   modifier:       {type, target, value, condition?}
 *     target: strength|dexterity|wisdom|intelligence|constitution|charisma|
 *             ac|missile_thac0|melee_thac0|movement_rate
 *     value: int
 *   skill:          {type, rolls: {name: {chance, die}}}
 *   round_effect:   {type, effect: "hp", value: int, description: string}
 *   special_attack: {type, attacks: [{name, hit_bonus, damage_bonus}]}
 *   aura:           {type, description: string}
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
    ability_metadata: [],
  },
  wand: {
    effect: '',
    charges: 10,
    spell_level: null,
  },
  wondrous: {
    effect: '',
    ability_metadata: [],
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

/**
 * Contextual field reference for item_metadata, keyed by item type.
 * Each entry is an array of {key, type, description} objects.
 * Used by ItemForm to show available fields below the JSON editor.
 */
export const METADATA_FIELD_REFERENCE = {
  weapon: [
    { key: 'damage_dice', type: 'string', desc: 'Dice expression for damage (e.g. "1d8")' },
    { key: 'hit_bonus', type: 'int', desc: 'Magical bonus to attack rolls' },
    { key: 'damage_bonus', type: 'int', desc: 'Magical bonus to damage rolls' },
    { key: 'qualities', type: 'string[]', desc: 'Tags: melee, missile, slow, two-handed, reload, splash, charge, blunt, brace' },
    { key: 'range', type: 'string', desc: 'Short/medium/long in feet (e.g. "20/40/60"). On melee weapons, implies thrown' },
    { key: 'requires_ammo', type: 'string', desc: 'Ammo type consumed per shot (e.g. "arrows"); matched against ammo_type' },
  ],
  armor: [
    { key: 'armor_type', type: 'string', desc: '"light", "medium", "heavy", or "shield"' },
    { key: 'ac', type: 'int', desc: 'Base AC this armor provides (replaces unarmored 9)' },
    { key: 'ac_bonus', type: 'int', desc: 'Additive AC improvement (shields: -1)' },
  ],
  ammo: [
    { key: 'ammo_type', type: 'string', desc: 'Type key matched against weapon\'s requires_ammo (e.g. "arrows")' },
    { key: 'damage_bonus', type: 'int', desc: 'Bonus added to ranged weapon damage (magical ammo)' },
  ],
  potion: [
    { key: 'effect', type: 'string', desc: 'What the potion does when consumed' },
    { key: 'duration', type: 'string', desc: 'How long the effect lasts (e.g. "1d6+1 turns")' },
  ],
  scroll: [
    { key: 'spell_name', type: 'string', desc: 'Name of the spell on the scroll' },
    { key: 'spell_level', type: 'int', desc: 'Level of the spell' },
    { key: 'spell_class', type: 'string', desc: 'Casting class: cleric, magic-user, druid, illusionist' },
  ],
  ring: [
    { key: 'effect', type: 'string', desc: 'What the ring does when worn' },
    { key: 'charges', type: 'int|null', desc: 'Number of uses; null = permanent' },
  ],
  wand: [
    { key: 'effect', type: 'string', desc: 'What the wand does when activated' },
    { key: 'charges', type: 'int', desc: 'Number of charges remaining (typically 10)' },
    { key: 'spell_level', type: 'int', desc: 'Level of the spell effect' },
  ],
  wondrous: [
    { key: 'effect', type: 'string', desc: 'Description of the item\'s magical effect' },
  ],
  consumable: [
    { key: 'effect', type: 'string', desc: 'What happens when used' },
    { key: 'charges', type: 'int', desc: 'Number of uses' },
    { key: 'qualities', type: 'string[]', desc: 'Tags: "food", "drink", "poison", etc.' },
    { key: 'save', type: 'int', desc: 'Save-vs-poison target number (poisons)' },
    { key: 'detection', type: 'int', desc: 'Percent chance of detecting the poison' },
    { key: 'onset', type: 'string', desc: 'Time until effect (e.g. "1d4+1 rounds")' },
    { key: 'effect_saved', type: 'string', desc: 'Result on successful save' },
    { key: 'effect_failed', type: 'string', desc: 'Result on failed save (e.g. "25hp", "Death")' },
  ],
  tool: [
    { key: 'capacity_slots', type: 'int', desc: 'Carrying capacity (backpacks, sacks)' },
    { key: 'length_feet', type: 'int', desc: 'Length in feet (rope, poles)' },
    { key: 'light_radius', type: 'int', desc: 'Illumination radius in feet' },
    { key: 'duration_hours', type: 'number', desc: 'Burn time (torches, lanterns)' },
    { key: 'duration_days', type: 'int', desc: 'Consumable duration (rations)' },
  ],
  treasure: [
    { key: 'gp_value', type: 'int', desc: 'Appraised value in gold pieces' },
    { key: 'materials', type: 'string', desc: 'Composition (e.g. "gold and ruby")' },
  ],
};

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
