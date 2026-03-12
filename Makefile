# ── Configuration ─────────────────────────────────────────────

PYTHON ?= python3

BACKEND := backend
FRONTEND := frontend

VENV := $(BACKEND)/.venv
VENV_BIN := $(VENV)/bin

ifeq ($(OS),Windows_NT)
	VENV_BIN := $(VENV)/Scripts
endif

# From repo root
PY := $(VENV_BIN)/python

# From inside ./backend after: cd backend
PY_IN_BACKEND := .venv/bin/python
ifeq ($(OS),Windows_NT)
	PY_IN_BACKEND := .venv/Scripts/python
endif

DB_DIR := $(BACKEND)/data
DB := $(DB_DIR)/ose_sheets.db

BACKUP_DIR := $(BACKEND)/backups
ALEMBIC_VERSIONS_DIR := $(BACKEND)/alembic/versions

.PHONY: backend frontend dev install install-backend install-frontend \
	preflight-dirs \
	migrate migrate-new db-shell \
	seed seed-all seed-test-user seed-admin seed-classes seed-items seed-spells \
	backup restore list-backups build clean

# ── Dev Servers ──────────────────────────────────────────────

backend: install-backend preflight-dirs
	cd $(BACKEND) && $(PY_IN_BACKEND) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd $(FRONTEND) && npm run dev

dev:
	make -j2 backend frontend

# ── Setup ────────────────────────────────────────────────────

install: install-backend install-frontend

install-backend:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating Python virtual environment..."; \
		$(PYTHON) -m venv "$(VENV)"; \
	fi
	@$(PY) -m ensurepip --upgrade >/dev/null 2>&1 || true
	@$(PY) -m pip install --upgrade pip setuptools wheel
	@$(PY) -m pip install -r "$(BACKEND)/requirements.txt"

install-frontend:
    # Ensuring directories exist before attempting to copy to it.
	$(PY) -m pip show pip > /dev/null && $(PY) -c "import os; os.makedirs('$(FRONTEND)/static/assets/dice-box', exist_ok=True)"
	cd $(FRONTEND) && npm install

# ── Preflight ────────────────────────────────────────────────

preflight-dirs:
	@mkdir -p "$(DB_DIR)" "$(BACKUP_DIR)" "$(ALEMBIC_VERSIONS_DIR)"

# ── Database ─────────────────────────────────────────────────

migrate: install-backend preflight-dirs
	@if [ ! -f "$(DB)" ]; then \
		latest_backup=$$(ls -t $(BACKUP_DIR)/ose_sheets_*.db 2>/dev/null | head -1); \
		if [ -n "$$latest_backup" ]; then \
			echo "No database found. Restoring from latest backup: $$latest_backup"; \
			cp "$$latest_backup" "$(DB)"; \
		else \
			echo "No database or backup found. Creating blank database..."; \
			sqlite3 "$(DB)" "PRAGMA journal_mode=WAL;"; \
		fi \
	fi
	cd $(BACKEND) && $(PY_IN_BACKEND) -m alembic upgrade head

# ── Seed Data ────────────────────────────────────────────────

seed-all: seed-test-user seed-admin seed-classes seed-items seed-spells

seed-test-user: install-backend preflight-dirs
	$(PY) $(BACKEND)/seed_test_user.py

seed-admin: install-backend preflight-dirs
	$(PY) $(BACKEND)/seed_admin_user.py

seed-classes: install-backend preflight-dirs
	$(PY) $(BACKEND)/seed_default_character_classes.py

seed-items: install-backend preflight-dirs
	$(PY) $(BACKEND)/seed_default_items.py

seed-spells: install-backend preflight-dirs
	$(PY) $(BACKEND)/seed_default_spells.py

# ── Backups ──────────────────────────────────────────────────

backup: install-backend preflight-dirs
	$(PY) -c "from app.services.backup import create_backup; p = create_backup('$(DB)'); print(f'Backup created: {p}')"

restore: install-backend preflight-dirs
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backend/backups/ose_sheets_YYYYMMDD.db" && exit 1)
	$(PY) -c "import shutil; shutil.copy2('$(FILE)', '$(DB)'); print('Restored from $(FILE)')"

list-backups: preflight-dirs
	@ls -lh $(BACKUP_DIR)/ose_sheets_*.db 2>/dev/null || echo "No backups found"

# ── Build ────────────────────────────────────────────────────

build:
	cd $(FRONTEND) && npm run build

# ── Cleanup ──────────────────────────────────────────────────

clean:
	rm -rf $(VENV)
	rm -rf $(FRONTEND)/node_modules