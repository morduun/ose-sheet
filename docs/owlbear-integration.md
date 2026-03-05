# Owlbear Rodeo Integration — Design Document

## Decision: Plugin, Not Custom Battlemap

Building a custom battlemap would mean implementing canvas rendering, grid
systems, fog of war, token movement, pan/zoom, image layering, drawing tools,
and real-time multiplayer sync — each a major engineering effort. Owlbear
Rodeo already solves all of these well.

Instead, we build an OBR extension that bridges OSE Sheets character data
with OBR's battlemap. The extension is a SvelteKit app (same stack) served
from an iframe inside OBR, communicating with our FastAPI backend.

---

## Owlbear Rodeo Extension Model

### Architecture

OBR extensions run as **iframes** sandboxed inside the OBR application.
They communicate with OBR through the `@owlbear-rodeo/sdk` (TypeScript,
npm package). Extensions cannot touch OBR's DOM directly — all interaction
goes through the SDK.

Each extension can register:
- **Action** — a panel in the sidebar
- **Context menu items** — right-click options on tokens
- **Custom tools** — toolbar buttons with popovers
- **Modals** — full overlay dialogs
- **Background script** — runs without UI, reacts to events

### SDK APIs Available

| API | What it does |
|-----|-------------|
| `OBR.scene.items` | CRUD scene items (tokens, images, shapes, labels). Filter, subscribe to changes via `onChange` |
| `OBR.player` | Current player info — user ID, role (GM/player), selection, metadata |
| `OBR.room` | Room-level metadata (~16kB limit). Persists across sessions |
| `OBR.party` | All connected players and their metadata |
| `OBR.contextMenu` | Register right-click menu items on tokens |
| `OBR.tool` | Register custom toolbar tools |
| `OBR.broadcast` | Send messages between extension instances (cross-player) |
| `OBR.interaction` | High-frequency updates with built-in interpolation for smooth networking |
| `OBR.notification` | Toast notifications |
| `OBR.modal` / `OBR.popover` | Open extension UI in modal or popover |
| `OBR.assets` | Upload/manage image assets |
| `OBR.viewport` | Camera control (pan, zoom, focus) |
| `OBR.theme` | Read OBR's current theme for styling consistency |

### Metadata System

Every scene item has a `metadata` property — a JSON object where extensions
store custom data, namespaced by extension ID to avoid collisions. Metadata
is saved with the scene and synced across all connected players automatically.

This is how we attach OSE character data to OBR tokens.

### Limitations

- Cannot manipulate OBR's native UI or DOM
- Cannot override built-in OBR behaviors (movement, fog, drawing)
- Room metadata capped at ~16kB (item metadata is per-item, more flexible)
- Extension must be hosted at a URL accessible to all players
- Cross-domain iframe restrictions apply (no cookie sharing with OBR)

---

## Integration Design

### Core Concept

Each OBR token on the CHARACTER layer can be **linked** to an OSE Sheets
character. Once linked, the extension:

1. Reads character data from our API
2. Writes combat-relevant stats into the token's metadata
3. Displays HP bars, AC labels, movement ranges on the map
4. Syncs changes bidirectionally — damage in OBR updates HP in OSE Sheets,
   HP changes in OSE Sheets update the token display

### Linking Flow

1. GM right-clicks a token → context menu shows "Link to OSE Character"
2. Extension opens a popover listing active characters in the campaign
3. GM selects a character → extension writes `{ characterId, campaignId }`
   into the token's metadata
4. Extension fetches character data from API and attaches combat stats
   to the token metadata

### Data on Tokens (via metadata)

```json
{
  "com.ose-sheets/character": {
    "characterId": 1,
    "campaignId": 1,
    "name": "Aldric",
    "hp_current": 14,
    "hp_max": 20,
    "ac": 5,
    "thac0": 17,
    "movement": 90,
    "movement_combat": 30,
    "encumbrance": 520,
    "weapons": [...],
    "status": "active"
  }
}
```

### Extension UI Panels

**Action Panel (sidebar):**
- Campaign selector (if GM has multiple)
- List of linked tokens with quick HP/status view
- Unlinked tokens with "Link" buttons
- Initiative tracker driven by OSE character data
- Round counter synced with dungeon time tracker

**Context Menu (right-click token):**
- Link/unlink character
- Quick HP adjustment (damage/heal)
- View character sheet (opens in modal)
- Cast spell (mark as cast in backend)
- Movement range overlay (based on encumbrance)

**Token Overlays:**
- HP bar (color-coded like our sheet)
- AC badge
- Status indicators (poisoned, held, etc.)
- Movement range circle (optional, toggled)

### Sync Strategy

**OBR → Backend (token changes reflected in character data):**
- HP adjustment via context menu → PATCH to character endpoint
- Token status change → update character status

**Backend → OBR (character changes reflected on map):**
- Extension polls character data on a reasonable interval (5-10 seconds)
  or when the action panel is focused
- Manual "refresh" button for immediate sync
- `onChange` listener updates display when GM modifies token metadata

**Why polling, not websockets (for now):**
Our backend is FastAPI + SQLite, single instance. Adding websocket support
is possible but adds complexity. Polling at 5-10 second intervals is fine
for tabletop combat pace. If we later need real-time push, FastAPI supports
websockets natively — it's an optimization, not an architecture change.

---

## Tech Stack for the Extension

- **SvelteKit** — same framework as the main frontend, builds to static
- **@owlbear-rodeo/sdk** — OBR communication
- **Tailwind CSS** — consistent styling (match OBR theme where possible)
- **Hosted alongside main frontend** or as a separate static build

The extension is essentially a small SvelteKit app that:
1. Imports the OBR SDK
2. Registers its manifest (action, context menus, background script)
3. Talks to our existing FastAPI API with the same JWT auth
4. Reads/writes OBR token metadata via the SDK

### Directory Structure (proposed)

```
owlbear-extension/
├── manifest.json           # OBR extension manifest
├── src/
│   ├── background.ts       # Background script (event listeners)
│   ├── action/             # Sidebar panel UI
│   ├── contextmenu/        # Context menu handlers
│   ├── popover/            # Popovers (link character, HP adjust)
│   └── lib/
│       ├── api.ts          # Calls to OSE Sheets backend
│       ├── obr.ts          # OBR SDK helpers
│       └── sync.ts         # Token ↔ character sync logic
├── static/
│   └── icon.svg            # Extension icon
└── package.json
```

---

## Development Phases

### Phase 1 — Scaffold & Link
- Extension manifest and build pipeline
- Action panel with campaign/character list
- Context menu "Link to OSE Character"
- Write character data to token metadata
- Basic HP bar overlay on linked tokens

### Phase 2 — Combat Integration
- HP adjustment via context menu (syncs to backend)
- AC and THAC0 display on tokens
- Initiative tracker in action panel
- Movement range circle based on encumbrance
- Round counter

### Phase 3 — Spell & Item Integration
- Cast spell from context menu (marks cast in backend)
- Rest button (clears cast spells)
- Equipped weapon display
- Consumable usage (arrows, oil, etc.)

### Phase 4 — Polish
- Theme matching with OBR
- Status effect indicators
- Token label customization
- Smooth animations on HP changes
- Error handling and offline resilience

---

## Open Questions

- **Auth flow in iframe context:** How does the extension authenticate with
  our backend? JWT stored in localStorage is accessible within the iframe's
  origin. May need a lightweight auth flow within the extension itself.
- **Multi-GM support:** If multiple GMs exist, how do we handle permission
  mapping between OBR roles and OSE Sheets roles?
- **Extension hosting:** Self-hosted alongside the main app? Separate static
  deploy? OBR requires the extension URL to be accessible to all players.
- **Offline/disconnected:** What happens if the backend is unreachable? Cache
  last-known state and queue changes? Or just show an error?
