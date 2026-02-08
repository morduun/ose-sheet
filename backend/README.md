# OSE Sheets - Backend

FastAPI backend for the OSE Sheets character management application.

## Quick Start

1. **Create virtual environment and install dependencies:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure Google OAuth credentials:**

First, set up a Google Cloud project:
- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project or select an existing one
- Enable the Google+ API (or People API)
- Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
- Select "Web application"
- Add authorized redirect URI: `http://localhost:8000/api/auth/google/callback`
- Copy the Client ID and Client Secret

Then configure your environment:
```bash
cp .env.example .env
# Edit .env and add:
# - GOOGLE_CLIENT_ID=your-client-id-here
# - GOOGLE_CLIENT_SECRET=your-client-secret-here
# - SECRET_KEY=generate-with-openssl-rand-hex-32
```

Generate a secure secret key:
```bash
openssl rand -hex 32
```

3. **Run the development server:**
```bash
uvicorn app.main:app --reload
```

4. **Visit the API documentation:**
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Authentication

**Phase 2** includes full Google OAuth authentication. All endpoints except `/` and `/api/health` require authentication.

### Testing with Development Token (recommended for development)

```bash
# First, create a test user (run seed script)
python seed_test_user.py

# Get a token using the dev endpoint
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Use the token in subsequent requests
TOKEN="your-token-here"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/campaigns/
```

### Testing with Google OAuth

1. Visit http://localhost:8000/api/auth/google
2. Complete Google login
3. Copy the access token from the response
4. Use it in the Authorization header

### Using Swagger UI

1. Go to http://localhost:8000/api/docs
2. Click the "Authorize" button
3. Get a token from `/api/auth/token` endpoint
4. Paste the token and click "Authorize"
5. All endpoints will now include the authentication token

## Testing the API

Example authenticated requests:

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}' | jq -r '.access_token')

# Create a campaign
curl -X POST http://localhost:8000/api/campaigns/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My First Campaign", "description": "A test campaign"}'

# List your campaigns
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/campaigns/

# Create a character
curl -X POST http://localhost:8000/api/characters/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Thorin Ironforge",
    "character_class": "Fighter",
    "campaign_id": 1,
    "strength": 16,
    "constitution": 14,
    "hp_max": 8
  }'
```

## Database

The application uses SQLite by default, with the database file stored in `../data/ose_sheets.db`.

To reset the database, simply delete the file and restart the application.

## Project Structure

See the main CLAUDE.md file for detailed architecture documentation.

## Features

**Phase 1 (Complete):**
- Campaign CRUD with auto-generated invite codes
- Character CRUD with full OSE stats
- SQLite database with proper relationships

**Phase 2 (Complete):**
- Google OAuth authentication
- JWT token-based API access
- Permission system (GM vs Player roles)
- Items CRUD with campaign-specific and default items
- Spells CRUD with character spellbook management
- Item/spell assignment to characters

**Phase 3 (TODO):**
- Auto-population of character stats based on class
- Default items seeding (mundane equipment)
- Spell database seeding from reference PDFs
- Admin role for managing default content

## Development

### Running Tests

```bash
# Verify setup
python verify_setup.py

# Run Phase 1 tests
python test_phase1.py
```

### Database Management

```bash
# Create a migration after model changes
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```
