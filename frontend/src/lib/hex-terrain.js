/**
 * Hex terrain type definitions and helpers.
 * Icon filenames: hex_{key}.png in /hex-icons/
 * Art: Thorfinn Tait, CC BY-NC-SA 4.0
 */

export const TERRAIN_CATEGORIES = [
  {
    name: 'Plains',
    terrains: ['grassland', 'farmland', 'grazing-choice', 'grazing-poor', 'moor', 'MoorForest']
  },
  {
    name: 'Forest',
    terrains: ['forest-light', 'forest-heavy', 'forest-light-evergreen', 'forest-heavy-evergreen', 'forest-dead', 'forest-home-trees', 'taiga']
  },
  {
    name: 'Hills',
    terrains: ['hills', 'hills-forested', 'hills-forested-evergreen', 'hills-forested-dead', 'hills-home-trees', 'hills-jungle', 'hills-taiga', 'hills_caves', 'deadhills']
  },
  {
    name: 'Mountains',
    terrains: ['mountain', 'mountains', 'mountains_caves', 'mountains_world', 'snow_hills', 'glaciers']
  },
  {
    name: 'Desert',
    terrains: ['desert-sandy', 'desert-rocky', 'desert-clay', 'desert-black_sands', 'sand_dunes', 'badlands', 'barren', 'cactus-light', 'cactus-heavy']
  },
  {
    name: 'Water',
    terrains: ['water-sea', 'water-coastal']
  },
  {
    name: 'Wetland',
    terrains: ['swamp', 'swamp-trees', 'fens', 'mudbog', 'dead_swamp']
  },
  {
    name: 'Tropical',
    terrains: ['jungle']
  },
  {
    name: 'Cold',
    terrains: ['snow', 'tundra']
  },
  {
    name: 'Volcanic',
    terrains: ['volcano', 'volcano_inactive', 'volcano_extinct', 'volcanos', 'volcanic_formation', 'deadland']
  },
  {
    name: 'Settlements',
    terrains: ['village', 'town', 'city', 'capital', 'adobe', 'longhouse', 'tepee']
  },
  {
    name: 'Fortifications',
    terrains: ['castle', 'fort', 'tower', 'palace']
  },
  {
    name: 'Structures',
    terrains: ['temple', 'shrine', 'lighthouse', 'mining', 'post_house', 'camp', 'hunting_camp']
  },
  {
    name: 'Ruins',
    terrains: ['ruins', 'ruin_village', 'ruin_town', 'ruin_city']
  },
  {
    name: 'Monuments',
    terrains: ['monument', 'monolith', 'moongate', 'pyramid', 'pyramid_complex', 'pyramid_step', 'standing_stone', 'statue', 'totempole', 'mound']
  },
  {
    name: 'Special',
    terrains: ['battle', 'battle-naval', 'dragons', 'monster_lair', 'magic-good', 'magic-bad']
  },
  {
    name: 'Underground',
    terrains: ['underground_rocky', 'underground_sold_rock', 'underground_moss', 'underground_farmland', 'underground_fungal_forest', 'underground_fungal_jungle', 'underground_fungal_swamp', 'underground_spiders']
  },
];

/** All terrain keys in a flat array. */
export const ALL_TERRAINS = TERRAIN_CATEGORIES.flatMap(c => c.terrains);

/** Convert terrain key to human-readable label. */
export function terrainLabel(key) {
  return key
    .replace(/^underground_/, 'UG ')
    .replace(/_/g, ' ')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

/** Get icon path for a terrain key. */
export function terrainIcon(key) {
  return `/hex-icons/hex_${key}.png`;
}

// Hex geometry constants (flat-top hexes, matching 76x66 icons)
export const HEX_W = 76;
export const HEX_H = 66;
export const COL_STEP = 57;   // 3/4 of width
export const ROW_STEP = 66;
export const ODD_OFFSET = 33; // half of height

/** Hex polygon points string (flat-top, relative to 0,0). */
export const HEX_POINTS = '19,0 57,0 76,33 57,66 19,66 0,33';

/** Get pixel X for a hex column. */
export function hexX(col) { return col * COL_STEP; }

/** Get pixel Y for a hex at (col, row). */
export function hexY(col, row) { return row * ROW_STEP + (col % 2 ? ODD_OFFSET : 0); }

/** Compute SVG viewBox dimensions for a grid. */
export function gridViewBox(width, height) {
  const w = (width - 1) * COL_STEP + HEX_W;
  const h = (height - 1) * ROW_STEP + HEX_H + ODD_OFFSET;
  return { w, h };
}
