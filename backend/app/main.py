from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from app.database import engine, Base

# Import routers
from app.api import allowed_emails, animals, auth, backup, campaigns, characters, character_classes, dungeons, items, mercenaries, monsters, specialists, spells, treasure, vehicles

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API for managing Old-School Essentials character sheets and campaigns",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Session middleware (required by authlib for OAuth CSRF state)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Application startup. Alembic manages schema; create_all is a safety net for missing tables."""
    Base.metadata.create_all(bind=engine)
    print(f"🚀 {settings.app_name} v{settings.app_version} starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print(f"👋 {settings.app_name} shutting down...")


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/api/docs",
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(characters.router, prefix="/api/characters", tags=["Characters"])
app.include_router(character_classes.router, prefix="/api/character-classes", tags=["Character Classes"])
app.include_router(items.router, prefix="/api/items", tags=["Items"])
app.include_router(spells.router, prefix="/api/spells", tags=["Spells"])
app.include_router(mercenaries.types_router, prefix="/api/mercenary-types", tags=["Mercenaries"])
app.include_router(mercenaries.router, prefix="/api/characters/{character_id}/mercenaries", tags=["Mercenaries"])
app.include_router(specialists.types_router, prefix="/api/specialist-types", tags=["Specialists"])
app.include_router(specialists.router, prefix="/api/characters/{character_id}/specialists", tags=["Specialists"])
app.include_router(monsters.router, prefix="/api/monsters", tags=["Monsters"])
app.include_router(backup.router, prefix="/api/backups", tags=["Backups"])
app.include_router(allowed_emails.router, prefix="/api/allowed-emails", tags=["Allowed Emails"])
app.include_router(animals.types_router, prefix="/api/animal-types", tags=["Animals"])
app.include_router(animals.router, prefix="/api/characters/{character_id}/animals", tags=["Animals"])
app.include_router(dungeons.router, prefix="/api/campaigns/{campaign_id}/dungeons", tags=["Dungeons"])
app.include_router(treasure.types_router, prefix="/api/treasure-types", tags=["Treasure"])
app.include_router(treasure.roll_router, prefix="/api/treasure/roll", tags=["Treasure"])
app.include_router(vehicles.types_router, prefix="/api/vehicle-types", tags=["Vehicles"])
app.include_router(vehicles.router, prefix="/api/campaigns/{campaign_id}/vehicles", tags=["Vehicles"])
