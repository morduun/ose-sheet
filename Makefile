.PHONY: backend frontend dev install install-backend install-frontend \
       migrate migrate-new seed seed-all seed-test-user seed-admin \
       seed-classes seed-items seed-spells build db-shell \
       backup restore list-backups

# ── Dev Servers ──────────────────────────────────────────────

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

# ── Setup ────────────────────────────────────────────────────

install: install-backend install-frontend

install-backend:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

# ── Database ─────────────────────────────────────────────────

migrate:
	cd backend && . .venv/bin/activate && alembic upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	cd backend && . .venv/bin/activate && alembic revision --autogenerate -m "$$msg"

db-shell:
	sqlite3 backend/data/ose_sheets.db

# ── Seed Data ────────────────────────────────────────────────

seed-all: seed-test-user seed-admin seed-classes seed-items seed-spells

seed-test-user:
	cd backend && . .venv/bin/activate && python seed_test_user.py

seed-admin:
	cd backend && . .venv/bin/activate && python seed_admin_user.py

seed-classes:
	cd backend && . .venv/bin/activate && python seed_default_character_classes.py

seed-items:
	cd backend && . .venv/bin/activate && python seed_default_items.py

seed-spells:
	cd backend && . .venv/bin/activate && python seed_default_spells.py

# ── Backups ──────────────────────────────────────────────────

backup:
	cd backend && . .venv/bin/activate && python -c "from app.services.backup import create_backup; p = create_backup('data/ose_sheets.db'); print(f'Backup created: {p}')"

restore:
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backups/ose_sheets_20260222.db" && exit 1)
	cd backend && . .venv/bin/activate && python -c "import shutil; shutil.copy2('$(FILE)', 'data/ose_sheets.db'); print('Restored from $(FILE)')"

list-backups:
	@ls -lh backend/backups/ose_sheets_*.db 2>/dev/null || echo "No backups found"

# ── Build ────────────────────────────────────────────────────

build:
	cd frontend && npm run build
