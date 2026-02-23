# OSE Sheets — Development Roadmap

## Completed

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
thac0, saving_throws, spells slots, thief_skills, turning, abilities, domain).
4 default classes seeded: Fighter, Cleric, Magic-User, Thief.
Character creation auto-populates saving_throws and combat_stats.thac0 from
class template. Full CRUD API at /api/character-classes/.

### Phase 3C — XP & Level-Up ✅
`POST /api/characters/{id}/award-xp` (GM only, accumulates XP).
`POST /api/characters/{id}/level-up` (GM only, validates XP vs class xp table,
recalculates saving_throws and THAC0 from class template at new level).

---

## Upcoming Phases

---

## Phase 4 — Attribute Modifiers

**Goal:** Store and surface the OSE attribute modifier tables so the frontend
can display derived bonuses alongside raw ability scores.

### Modifier Tables

**Strength — Melee Adjustment & Open Doors**

| Score | Melee Adj. | Open Doors |
|-------|-----------|------------|
| 3     | –3        | 1-in-6     |
| 4–5   | –2        | 1-in-6     |
| 6–8   | –1        | 1-in-6     |
| 9–12  | —         | 2-in-6     |
| 13–15 | +1        | 3-in-6     |
| 16–17 | +2        | 4-in-6     |
| 18    | +3        | 5-in-6     |

**Intelligence — Spoken Languages & Literacy**

| Score | Additional Languages | Literacy    |
|-------|---------------------|-------------|
| 3     | 0                   | Illiterate  |
| 4–5   | 0                   | Illiterate  |
| 6–8   | 0                   | Illiterate  |
| 9–12  | 0                   | Literate    |
| 13–15 | +1                  | Literate    |
| 16–17 | +2                  | Literate    |
| 18    | +3                  | Literate    |

**Wisdom — Magic Saves**

| Score | Magic Save Bonus |
|-------|-----------------|
| 3     | –3              |
| 4–5   | –2              |
| 6–8   | –1              |
| 9–12  | —               |
| 13–15 | +1              |
| 16–17 | +2              |
| 18    | +3              |

**Dexterity — AC Adjustment, Missile Adjustment, Initiative Adjustment**

| Score | AC Adj. | Missile Adj. | Initiative Adj. |
|-------|---------|--------------|----------------|
| 3     | +3      | –3           | –2             |
| 4–5   | +2      | –2           | –1             |
| 6–8   | +1      | –1           | –1             |
| 9–12  | —       | —            | 0              |
| 13–15 | –1      | +1           | +1             |
| 16–17 | –2      | +2           | +1             |
| 18    | –3      | +3           | +2             |

*Note: AC adjustment is applied to the raw AC value. In OSE descending AC, a
negative adjustment means better AC (lower number). The frontend should display
the adjustment sign as-is (e.g. "–1") and let the sheet do the arithmetic.*

**Constitution — Hit Point Modifier**

| Score | HP per Die |
|-------|-----------|
| 3     | –3        |
| 4–5   | –2        |
| 6–8   | –1        |
| 9–12  | —         |
| 13–15 | +1        |
| 16–17 | +2        |
| 18    | +3        |

*Minimum 1 HP per die regardless of modifier.*

**Charisma — NPC Reactions, Max Retainers, Retainer Loyalty**

| Score | NPC Reactions | Max Retainers | Retainer Loyalty |
|-------|--------------|---------------|-----------------|
| 3     | –2           | 1             | 4               |
| 4–5   | –1           | 2             | 5               |
| 6–8   | –1           | 3             | 6               |
| 9–12  | —            | 4             | 7               |
| 13–15 | +1           | 5             | 8               |
| 16–17 | +1           | 6             | 9               |
| 18    | +2           | 7             | 10              |

### Prime Requisite XP Bonus

Applies to total XP earned when the character's prime requisite score falls
in the given range. For classes with multiple prime requisites, all listed
scores must qualify for the bonus (or take the lower applicable bonus).

| Score | XP Modifier |
|-------|------------|
| 3–5   | –20%       |
| 6–8   | –10%       |
| 9–12  | None       |
| 13–15 | +5%        |
| 16–18 | +10%       |

### Approach

Pure calculation service — no new DB columns. All modifiers are deterministic
from the ability score.

### Tasks

1. Create `app/services/modifiers.py` with lookup tables and a
   `calculate_modifiers(character)` function.
2. Add a `modifiers` computed field to the `Character` response schema
   (Pydantic `computed_field`) so the frontend gets everything in one response.
3. Add `xp_bonus_pct` to the modifiers response (prime requisite lookup from
   the character's class template).

**Modifier fields to return:**
```json
{
  "strength":     { "melee_adj": 0, "open_doors": "2-in-6" },
  "intelligence": { "additional_languages": 0, "literate": true },
  "wisdom":       { "magic_saves": 0 },
  "dexterity":    { "ac_adj": 0, "missile_adj": 0, "initiative_adj": 0 },
  "constitution": { "hp_modifier": 0 },
  "charisma":     { "npc_reactions": 0, "max_retainers": 4, "retainer_loyalty": 7 },
  "xp_bonus_pct": 0
}
```

---

## Phase 5 — Full Spell Database & Memorization Tracking

**Goal:** Seed the complete OSE spell list from the reference PDF, and add
in-session memorization tracking (which spells a character has prepared and
which have been cast).

### 5A — Spell Data

The reference PDF contains spells for 4 classes:
- **Cleric**: 5 levels, ~27 spells
- **Druid**: 5 levels, ~34 spells (OSE Advanced)
- **Illusionist**: 6 levels, ~60 spells (OSE Advanced)
- **Magic-User**: 6 levels, ~60 spells

The existing `Spell` model has: `name`, `level`, `spell_class`, `description`,
`duration`, `range`, `is_default`, `campaign_id`.

**Tasks:**
1. Create seed JSON files for all 4 spell lists in `seed_data/spells/`.
2. Create `seed_all_spells.py` script (same pattern as items/classes).
3. Each spell entry format:
```json
{
  "name": "Magic Missile",
  "level": 1,
  "spell_class": "magic-user",
  "description": "1d6+1 damage, 6th level+: extra missile",
  "duration": "1 turn",
  "range": "150′",
  "is_default": true
}
```

### 5B — Spellbook Management

The current `character_spellbook` association table tracks which spells a
Magic-User/Illusionist has in their spellbook (known spells). This is correct
for arcane casters. No changes needed to the model here.

**Existing:** `POST /api/spells/{id}/assign` — adds spell to character's spellbook.

### 5C — Memorization Tracking

OSE has two layers for arcane casters:
1. **Spellbook** — spells the character has copied into their book (persistent)
2. **Memorized** — subset prepared each day, limited by slots from class template

For divine casters (Cleric/Druid), there is no spellbook — any known spell
can be memorized up to the slot limit.

**New model:** `character_memorized_spells` association table
```
character_id  (FK → characters, CASCADE)
spell_id      (FK → spells, CASCADE)
spell_level   (int — denormalized for query convenience)
cast          (bool, default False — has this been cast today?)
```

**New endpoints:**
- `POST /api/characters/{id}/memorize` — add spell to today's memorized list
  - Validates: spell exists in spellbook (arcane) or is known (divine)
  - Validates: slot limit not exceeded (from class_data.spells[level])
- `DELETE /api/characters/{id}/memorize/{spell_id}` — remove from memorized
- `POST /api/characters/{id}/cast/{spell_id}` — mark spell as cast (cast=True)
- `POST /api/characters/{id}/rest` — clear all cast flags (new day / rest)
- `GET /api/characters/{id}/spells` — return spellbook + memorized state + slots used/available

---

## Phase 6 — Item Assignment & Inventory

**Goal:** Items work as templates (the Item model is the class; assignment to
a character is a reference). Character inventory tracks what they carry and
in what quantity.

### Current State

- `character_items` association table exists with a `quantity` column.
- `POST /api/items/{id}/assign` endpoint exists.
- Items have `is_default` and `campaign_id` — default mundane equipment is
  available to all.

### What's Missing

1. **Assign item to character** — endpoint exists (`assign`), but needs review:
   - Should allow assigning a default item OR a campaign item to any character
     in that campaign.
   - Quantity should be specifiable at assignment time.
   - Re-assigning an already-held item should increment quantity, not duplicate.

2. **Remove item from character** — `DELETE /api/items/{id}/unassign` or
   `PATCH /api/characters/{id}/items/{item_id}` to adjust quantity.

3. **Character inventory endpoint** — `GET /api/characters/{id}/items` returning
   items with quantities.

4. **Item quantity update** — `PATCH /api/characters/{id}/items/{item_id}`
   with `{"quantity": N}`.

5. **No item pool needed** — The concept mentioned a shared pool but this has
   been descoped. Direct assignment is sufficient.

---

## Phase 7 — Frontend

**Goal:** A simple web interface for managing campaigns and character sheets.
Also serves as the real test of Google OAuth from Phase 2.

### Tech Stack (proposed)
- **Framework:** SvelteKit (lightweight, file-based routing, excellent for forms)
- **Styling:** Tailwind CSS
- **Auth:** Google OAuth via backend redirect flow (redirect to `/api/auth/google`,
  receive JWT, store in localStorage or httpOnly cookie)

### Pages / Routes

```
/                         → Landing page / login with Google
/campaigns                → List campaigns (GM and player views)
/campaigns/new            → Create campaign
/campaigns/{id}           → Campaign detail: roster, invite code
/campaigns/{id}/characters/new → Create character (class dropdown from API)
/characters/{id}          → Character sheet (main view)
/characters/{id}/edit     → Edit character stats
```

### Character Sheet View

The character sheet should display (referencing Character Sheet.pdf):
- Name, class (linked to class data), level, XP (with next-level threshold)
- Attribute scores + modifiers (from Phase 4)
- HP (current / max), AC, THAC0
- Saving throws (5 values)
- Inventory (items with quantities)
- Spellbook / memorized spells by level with slot counters (Phase 5)
- Currency (cp, sp, ep, gp, pp)
- Alignment, notes

### GM Controls (on character sheet)
- Award XP button
- Level Up button (enabled when XP threshold met)
- Assign item (search/select from campaign + default items)

### Authentication Flow
1. User visits `/` → clicks "Sign in with Google"
2. Frontend redirects to `GET /api/auth/google`
3. Backend handles OAuth, redirects back to frontend with JWT in query param
4. Frontend stores JWT, subsequent requests use `Authorization: Bearer <token>`
5. This validates the full Phase 2 OAuth implementation end-to-end

---

## Implementation Order

1. **Phase 4** — Attribute modifiers (small, high value, needed by frontend)
2. **Phase 5A** — Seed full spell database (data work, no model changes)
3. **Phase 5B/5C** — Memorization tracking (new model + endpoints)
4. **Phase 6** — Item inventory cleanup (mostly endpoint fixes)
5. **Phase 7** — Frontend (depends on all backend phases complete)

---

## Out of Scope (for now)

- Campaign item pool / shared loot
- Multi-class characters
- Demi-human class variants (Dwarf, Elf, Halfling) — schema supports them,
  just need JSON seed data added later
- OSE Advanced class seeds (Druid, Illusionist, Paladin, Ranger, etc.) —
  same pattern as basic classes, added when needed
- Mobile app
