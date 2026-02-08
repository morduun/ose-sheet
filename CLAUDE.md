# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OSE Sheets is a web application for managing Old-School Essentials (OSE) tabletop RPG character sheets and campaigns. It provides an online repository for live characters and fallen heroes, particularly useful for online campaigns.

## Technology Stack

**Backend:**
- FastAPI - Modern async Python web framework
- uvicorn - ASGI server
- SQLAlchemy 2.0 - ORM for database operations
- Alembic - Database migrations
- SQLite - Database (easy migration to PostgreSQL if needed)
- Pydantic - Data validation and settings management
- python-jose - JWT tokens for authentication (not yet implemented)
- authlib - OAuth2/Google authentication (not yet implemented)

**Architecture:**
- REST API backend (FastAPI)
- Separate frontend (to be implemented)
- SQLite database for simplicity and easy deployment

## Development Commands

### Initial Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your settings (optional for local development)
```

### Running the Server

```bash
cd backend

# Development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

API will be available at:
- API: http://localhost:8000
- Interactive docs (Swagger): http://localhost:8000/api/docs
- Alternative docs (ReDoc): http://localhost:8000/api/redoc

### Database Migrations

```bash
cd backend

# Create a new migration (after model changes)
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

Note: The application will automatically create tables on startup, but using Alembic is recommended for production deployments and tracking schema changes.

### Development Tools

```bash
cd backend

# Format code with black
black app/

# Lint code with ruff
ruff check app/

# Run Phase 1 validation tests
python test_phase1.py

# Verify setup
python verify_setup.py

# Seed test user (required for testing)
python seed_test_user.py
```

## Backend Architecture

### Directory Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app initialization
│   ├── config.py            # Settings and configuration
│   ├── database.py          # SQLAlchemy setup
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py          # User model
│   │   ├── campaign.py      # Campaign model + campaign_players table
│   │   ├── character.py     # Character model
│   │   ├── item.py          # Item model + character_items table
│   │   └── spell.py         # Spell model + character_spellbook table
│   ├── schemas/             # Pydantic schemas (request/response)
│   │   ├── user.py
│   │   ├── campaign.py
│   │   ├── character.py
│   │   ├── item.py
│   │   └── spell.py
│   ├── api/                 # API route handlers
│   │   ├── campaigns.py     # Campaign CRUD endpoints
│   │   ├── characters.py    # Character CRUD endpoints
│   │   ├── auth.py          # Authentication (TODO)
│   │   ├── items.py         # Items (TODO)
│   │   └── spells.py        # Spells (TODO)
│   └── services/            # Business logic
│       ├── auth.py          # Auth service (TODO)
│       └── permissions.py   # Authorization logic (TODO)
├── alembic/                 # Database migrations
├── data/                    # SQLite database file location
├── requirements.txt
└── pyproject.toml
```

### Database Schema

**Core tables:**
- `users` - User accounts (Google OAuth)
- `campaigns` - Game campaigns with invite codes
- `campaign_players` - Many-to-many: campaigns and players
- `characters` - Player characters with full stats
- `items` - Equipment/items with dual descriptions
- `character_items` - Many-to-many: characters and items (with quantity)
- `spells` - Spell definitions
- `character_spellbook` - Many-to-many: characters and spells

**Key relationships:**
- Users can be GMs of multiple campaigns
- Users can be players in multiple campaigns
- Campaigns have multiple characters
- Characters belong to one campaign and one player
- Items can be campaign-specific or default (available to all)
- Characters can have multiple items and spells

### Data Storage Patterns

**JSON fields for flexibility:**
- `Character.saving_throws` - Dictionary of saving throw values
- `Character.combat_stats` - Attack matrices and bonuses
- `Item.item_metadata` - Type-specific item properties (weapon stats, armor AC, etc.)

**Important Notes:**
- Item model uses `item_metadata` (not `metadata`) to avoid conflicts with SQLAlchemy's reserved `Base.metadata`
- Test user (ID: 1) must exist for testing. Run `seed_test_user.py` to create it.
- Database file is created at `./data/ose_sheets.db` (relative to backend directory)
- Foreign keys are enforced with CASCADE deletes for data integrity

### Current Implementation Status

**Phase 1 - COMPLETE ✅ (Validated 2026-02-08)**
- Database models for all core entities (User, Campaign, Character, Item, Spell)
- Association tables with proper relationships and cascade deletes
- Pydantic schemas for request/response validation
- Campaign CRUD endpoints (create, list, get, update, delete)
- Character CRUD endpoints (create, list, filter by campaign, get, update, delete)
- Database configuration and Alembic setup
- FastAPI application structure with CORS
- Auto-generated API documentation (/api/docs)
- Comprehensive test suite (15 tests, all passing)
- Error handling and validation

See `PHASE1_TEST_RESULTS.md` for detailed test results.

**Phase 2 - COMPLETE ✅ (Implemented 2026-02-08)**
- Google OAuth authentication with callback handling
- JWT token generation and validation
- Protected route dependencies (`get_current_user`)
- Permission service layer (GM vs Player roles)
- Items CRUD with campaign-specific and default items (7 endpoints)
- Spells CRUD with character spellbook management (7 endpoints)
- Item/spell assignment to characters
- Development token endpoint for testing (`/api/auth/token`)
- Updated all existing endpoints with authentication
- Permission checks (401 unauthorized, 403 forbidden)

See `PHASE2_IMPLEMENTATION.md` for detailed implementation notes.

**Phase 3 - TODO:**
- Admin role for managing default content
- Auto-population logic for character classes (stats, saves, thac0)
- Default items seeding from OSE rules
- Spell database seeding from reference PDFs
- Campaign item pool management
- Enhanced item quantity tracking
- Character advancement (level up) logic

## Core Features

**Authentication (Phase 2)**
- Google OAuth 2.0 integration
- JWT token-based API access
- Development token endpoint for testing
- Permission system (GM, Player roles)
- Protected endpoints with 401/403 errors

**Campaign Management (Phases 1-2)**
- GMs create campaigns with auto-generated invite codes
- Players join via invite code
- Multi-campaign support per user
- Permission-based access (GM can edit, members can view)
- Filter campaigns by user access

**Character Sheets (Phases 1-2)**
- Full OSE character data (attributes, HP, AC, saves, etc.)
- Class-based auto-population (Phase 3 TODO)
- Currency tracking (5 coin types)
- Character state (alive/fallen)
- Permission-based editing (owner or campaign GM)
- Spellbook management with 6 spell levels

**Item System (Phase 2)**
- Dual descriptions (player-visible + GM-only)
- Type-specific metadata (JSON)
- Campaign-specific or default items
- Item assignment to characters
- Permission-based visibility (GMs see full details)
- Item CRUD with filtering by campaign/type

**Spellcasting**
- 6 spell levels per OSE rules
- Class-specific spell lists
- Character spellbook management

### Reference Materials

Important reference files in `/reference/`:
- `Character Sheet.pdf`: Primary character sheet layout
- `stonehell.webp`: Attribute modifier details
- `Spell Lists.pdf`: Complete spell list for all four casting classes
