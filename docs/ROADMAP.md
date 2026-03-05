# OSE Sheets — Development Roadmap

All core phases are **complete**. The application is feature-complete for
running OSE campaigns with full character sheet management.

---

## Completed Phases

### Phase 1 — Core Models & CRUD ✅
Database models (User, Campaign, Character, Item, Spell), association tables,
Pydantic schemas, Campaign and Character CRUD endpoints, Alembic setup.

### Phase 2 — Auth & Item/Spell System ✅
Google OAuth + JWT, permission service (GM/Player roles), Items CRUD with dual
descriptions and metadata, Spells CRUD, item/spell assignment to characters,
dev token endpoint for testing.

### Phase 3A — Admin & Default Content ✅
Admin role, default item and spell seeding from JSON, admin-only endpoints
for managing default content.

### Phase 3B — Character Classes & Auto-Population ✅
CharacterClass model with comprehensive OSE class_data JSON (hit_dice, xp,
thac0, saving_throws, spell slots, thief_skills, turning, abilities, domain).
Default classes seeded. Character creation auto-populates saving_throws and
combat_stats.thac0 from class template. Full CRUD API at /api/character-classes/.

### Phase 3C — XP & Level-Up ✅
`POST /api/characters/{id}/award-xp` (GM only, accumulates XP).
`POST /api/characters/{id}/level-up` (GM only, validates XP vs class xp table,
recalculates saving_throws and THAC0 from class template at new level).

### Phase 4 — Attribute Modifiers ✅
Pure calculation service in `app/services/modifiers.py` with full OSE lookup
tables for all six ability scores. Prime requisite XP bonus calculated from
class template. Modifiers returned as part of character GET response.

### Phase 5 — Full Spell Database & Memorization Tracking ✅

- **5A — Spell Data:** Complete seed data for all 4 casting classes (Cleric,
  Druid, Illusionist, Magic-User) across all spell levels.
- **5B — Spellbook Management:** Spellbook assignment and character spellbook
  tracking for arcane casters. Divine casters memorize from full class list.
- **5C — Memorization Tracking:** Memorize/cast/rest cycle fully implemented.
  Slot validation against class template. Cast spells marked and restored on
  rest. Full frontend UI with slot counters per level.

### Phase 6 — Item Assignment & Inventory ✅
Item assignment with quantity tracking, increment on re-assign, removal and
quantity adjustment endpoints. Character inventory endpoint with full item
data. Equipment slot system (armor, shield, main-hand, off-hand, ammo).

### Phase 7 — Frontend ✅
SvelteKit 2 + Svelte 5 + Tailwind CSS. Google OAuth flow. Full campaign
management, character creation, and character sheet UI.

---

## Beyond the Roadmap

Features implemented that exceeded the original scope:

### Combat Engine
- **Dynamic AC computation** from equipped armor + DEX modifier + shield +
  class ability modifiers + item ability modifiers (e.g. Ring of Protection)
- **Equipped weapon stats** with effective THAC0 (STR/DEX modifiers, magical
  hit bonuses, dual-wield penalties), damage modifiers, range, and ammo tracking
- **Encumbrance system** — item weight + coin weight drives movement rate using
  OSE thresholds (400/600/800/1600 coins). Displayed as base' (combat') format
  with color-coded progress bar in inventory panel

### Item System
- **Equipment slots** — armor, shield, main-hand, off-hand, ammo
- **Item identification** — unidentified_name masking for magical items, GM
  identify button, stat masking for unidentified weapons
- **Item secrets** — per-item secrets with GM reveal/hide toggle, players see
  only revealed secrets
- **Item ability metadata** — modifiers (AC, ability scores, THAC0), round
  effects (regeneration), skills (rolls), special attacks, and auras from
  equipped items
- **Dual descriptions** — player-visible and GM-only descriptions

### Class System
- **Class skills** — unified skill system supporting thief, acrobat, assassin,
  barbarian, paladin, and ranger skills (14 skill keys total)
- **Class abilities** with markdown descriptions, filterable by level
- **Ability metadata** — level-scaling modifiers (e.g. Barbarian Agile Fighting)
- **Spell list associations** — classes link to spell lists with from_level
- **Turning undead** tables per class level
- **Full class editor** UI with level grid, ability editor, skill tables

### Campaign Management
- **Referee panel** — live combat dashboard with all active characters, HP
  tracking, AC/THAC0/weapon stats, movement rates, initiative, morale
- **Round effects** — GM applies per-round item effects (e.g. regeneration)
  to all campaign characters in one action
- **Retainers** — NPC retainers linked to PC employers with share, loyalty,
  morale tracking. Retainer rehiring between PCs
- **Mercenaries** — hired troop units with type, quantity, wage, morale
- **Specialists** — hired specialists by type with wages and task descriptions
- **Dungeon time tracker** — turn counter with event log and automatic
  wandering monster checks
- **Character status** — active, independent (left party), fallen (dead)

### Character Sheet UI
- **Tabbed interface** — Core, Inventory, Spells, Class Abilities, Notes
- **Attribute modifiers** displayed inline with ability scores
- **Saving throw display** with class-based values
- **Currency tracking** — 5 coin types with save
- **HP management** — delta-based HP adjustment with visual bar
- **XP tracking** — current XP, next level threshold, XP bonus percentage

---

## Out of Scope (for now)

- Multi-class characters
- Campaign item pool / shared loot tracking
- Mobile-native app
