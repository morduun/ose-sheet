.PHONY: backend frontend dev install install-backend install-frontend \
       migrate migrate-new seed seed-all seed-test-user seed-admin \
       seed-classes seed-items seed-spells build db-shell

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

# ── Build ────────────────────────────────────────────────────

build:
	cd frontend && npm run build
