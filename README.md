# OSE Sheets

A free, open-source character sheet manager for [Old-School Essentials](https://necroticgnome.com/collections/old-school-essentials) and the broader OSR community.

![Character sheet screenshot](reference/osesheet-render1.png)

OSE Sheets is a web application for managing characters, campaigns, and party inventory in OSE games — particularly useful for online play. GMs create campaigns, players join with invite codes, and everyone gets live, interactive character sheets with 3D dice rolling, spell tracking, and automated combat math.

**This is a community project. Free to use, free to host, free to hack on.** If you play OSE or any B/X-derived game, this is for you.

## Features

### Character Sheets
- Full OSE stats, saving throws, attribute modifiers, and THAC0
- Class system with auto-populated saves, THAC0, spell slots, and class skills from templates
- 3D dice rolling — click any stat, attack roll, or damage roll to throw dice on screen
- XP tracking with GM-awarded XP and level-up with automatic stat recalculation
- Print-friendly character sheet view

### Spellcasting
- Spellbook management for arcane casters, divine casters get full spell access
- Daily memorization with slot tracking per spell level
- Cast/rest cycle — mark spells as cast, rest to restore all slots

### Inventory & Equipment
- Equip/unequip weapons and armor with auto-computed AC (including rear AC, shieldless AC)
- Weapon table with THAC0, damage, range, and special attack qualities
- Two-handed weapon validation — blocks off-hand and shield equipping
- Ammo tracking with auto-decrement on ranged attack rolls
- **Containers** — backpacks, sacks with capacity tracking and fullness meters
- **Drop/pick up containers** in combat for instant movement adjustment (encumbrance-based)
- **Fillable items** — waterskins, flasks with fill state (full/half/empty) and contents tracking
- Encumbrance system with effective movement rate calculation
- Item abilities — rings, wondrous items, and gear can grant attribute modifiers, skill rolls, auras, round effects, and special attacks
- Revealable item secrets — GMs attach hidden information and reveal it piece by piece as players identify things in-game
- Currency tracking (cp, sp, ep, gp, pp) with save to character

### Retainers
- Hire retainers as sub-characters linked to a PC master
- CHA-based limits on max retainers and base loyalty
- Loyalty checks via 2d6 dice roll
- Dismiss retainers to make them independent characters

### Mercenaries
- 12 OSE mercenary types (archers, footmen, horsemen, crossbowmen, longbowmen, peasants, wolf riders) with per-race costs
- Hire/dismiss controls with quantity adjustment
- Wartime toggle doubles all costs
- Morale checks via 2d6 dice roll
- Payday button deducts monthly wages from character wealth

### Vehicles
- **18 OSE vehicle types** — carts, wagons, longships, galleys, sailing ships, and more
- Hull points with damage tracking — movement degrades proportionally with hull damage
- Cargo holds with weight tracking and take/return to character inventories
- Custom vehicle type creation for homebrew

### Campaigns & Permissions
- GMs create campaigns, players join via invite code
- Permission system — GMs see everything; players see their own sheets and what the GM reveals
- Party stash — shared loot pool with container-aware transfers (stash a backpack, contents come along)
- Email allowlist — admin-controlled access gate
- Cloudflare Access integration with email OTP

### Treasure System
- **22 OSE treasure types** (A-V) with full roll tables — hoards, individual, and group
- One-click treasure rolling with percentage checks, dice, and multipliers
- Gem values (d20 table), jewelry values (3d6 x 100 gp)
- Magic item cascading through 10 sub-tables — names rolled automatically
- Compound treasure types ("C + 1000gp")
- **Referee panel integration** — "Roll Treasure" button rolls all encounter monsters at once
- Custom treasure type creation for homebrew

### Referee Tools
- **Encounter tracker** — initiative tracking, round management, HP adjustment, condition tracking with turn counters
- **Combat table** — unified view of PCs, retainers, and monsters with clickable THAC0/damage/morale rolls
- **Treasure roller** — one-click encounter treasure rolling for all monsters, individual per monster + lair per group
- **Monster bestiary** — full CRUD for campaign-specific and default monsters with stat blocks
- **Dungeon time tracker** — turn-by-turn tracking with torch/lantern life, ration consumption, custom timers, and event history

### Admin & Content Management
- Database backup and restore (server-side and file upload)
- Email allowlist for login control
- DB-backed reference catalogs with admin CRUD: character classes, items, spells, monsters, vehicle types, mercenary types, specialist types, treasure types
- All reference data supports `is_default` + campaign-specific custom entries for homebrew
- Print-ready character sheets with container grouping and fill states

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | SvelteKit 2, Svelte 5, Tailwind CSS 3 |
| Backend | FastAPI, SQLAlchemy 2, Alembic |
| Database | SQLite (trivially swappable to PostgreSQL) |
| Auth | Google OAuth 2.0, JWT tokens, Cloudflare Access |
| Dice | [dice-box](https://fantasticdice.games/) 3D physics engine |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Google Cloud OAuth client (for authentication)

### Setup

```bash
# Clone
git clone https://github.com/morduun/ose-sheet.git
cd ose-sheet

# Install everything
make install

# Set up the database
make migrate

# Seed default content (classes, items, spells)
make seed-all

# Configure OAuth (see backend/.env.example)
cp backend/.env.example backend/.env
# Edit backend/.env with your Google OAuth credentials
```

### Run

```bash
# In one terminal — backend API on :8000
make backend

# In another terminal — frontend on :5173
make frontend
```

Visit http://localhost:5173 to start playing.

### Development Token

For local development without Google OAuth, you can generate a token directly:

```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com"}'
```

## Make Targets

| Command | Description |
|---------|-------------|
| `make install` | Install backend + frontend dependencies |
| `make backend` | Start the API server with hot reload |
| `make frontend` | Start the frontend dev server |
| `make dev` | Start both backend and frontend |
| `make migrate` | Apply database migrations |
| `make migrate-new` | Create a new migration |
| `make seed-all` | Seed test user, admin, classes, items, spells, vehicles, mercenaries, specialists, and treasure types |
| `make build` | Production build of the frontend |
| `make backup` | Create a database backup |
| `make restore FILE=<path>` | Restore from a backup file |
| `make list-backups` | List available backups |
| `make db-shell` | Open a SQLite shell to the database |

## Project Structure

```
ose-sheet/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   └── services/       # Business logic (auth, permissions, modifiers)
│   ├── alembic/            # Database migrations
│   ├── seed_data/          # Default classes, items, spells as JSON
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   └── components/ # Svelte components (sheet, items, classes, shared)
│   │   └── routes/         # SvelteKit file-based routing
│   └── package.json
├── reference/              # OSE PDFs and screenshots
├── Makefile
└── docs/
```

## Contributing

This is an open project under the MIT license. Contributions are welcome — whether that's adding new character classes, fixing bugs, improving the UI, or adding features.

The default content covers the four core B/X classes (Fighter, Cleric, Magic-User, Thief). Adding the demi-human classes (Dwarf, Elf, Halfling) or OSE Advanced classes (Druid, Illusionist, Paladin, Ranger, etc.) is as simple as adding a JSON file to `backend/seed_data/character_classes/` or creating a new class using the Referee UI.

## Legal

This project is not affiliated with or endorsed by Necrotic Gnome. Old-School Essentials is a trademark of Necrotic Gnome. Game mechanics are used under the terms of the Open Game License.

## License

[MIT](LICENSE)
