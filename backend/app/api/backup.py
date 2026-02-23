from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from app.database import engine
from app.config import settings
from app.dependencies import require_admin
from app.models import User
from app.services.backup import (
    create_backup,
    restore_backup,
    list_backups,
    delete_backup,
    BACKUP_DIR,
    ensure_backup_dir,
)

router = APIRouter()

SQLITE_MAGIC = b"SQLite format 3\x00"


def _db_path() -> str:
    """Derive the filesystem path from the database URL."""
    url = settings.database_url
    return url.replace("sqlite:///", "")


@router.post("")
async def create_backup_endpoint(admin: User = Depends(require_admin)):
    """Create a new database backup."""
    path = create_backup(_db_path())
    stat = path.stat()
    return {
        "filename": path.name,
        "size_bytes": stat.st_size,
        "created_at": stat.st_mtime,
    }


@router.get("")
async def list_backups_endpoint(admin: User = Depends(require_admin)):
    """List all available backups."""
    return list_backups()


@router.get("/{filename}/download")
async def download_backup(filename: str, admin: User = Depends(require_admin)):
    """Download a backup file."""
    path = BACKUP_DIR / filename
    if not path.exists() or path.parent != BACKUP_DIR:
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(
        path=str(path),
        media_type="application/octet-stream",
        filename=filename,
    )


@router.post("/restore/{filename}")
async def restore_from_backup(filename: str, admin: User = Depends(require_admin)):
    """Restore the database from a server-side backup. Creates a pre-restore backup first."""
    path = BACKUP_DIR / filename
    if not path.exists() or path.parent != BACKUP_DIR:
        raise HTTPException(status_code=404, detail="Backup not found")

    db_path = _db_path()
    pre_restore = create_backup(db_path)
    restore_backup(db_path, path, engine)

    return {
        "message": f"Restored from {filename}",
        "pre_restore_backup": pre_restore.name,
    }


@router.post("/upload-restore")
async def upload_and_restore(
    file: UploadFile = File(...), admin: User = Depends(require_admin)
):
    """Upload a .db file and restore from it. Creates a pre-restore backup first."""
    content = await file.read()

    if not content.startswith(SQLITE_MAGIC):
        raise HTTPException(status_code=400, detail="Invalid SQLite file")

    ensure_backup_dir()
    tmp_path = BACKUP_DIR / f"upload_{file.filename}"
    tmp_path.write_bytes(content)

    db_path = _db_path()
    pre_restore = create_backup(db_path)

    try:
        restore_backup(db_path, tmp_path, engine)
    finally:
        tmp_path.unlink(missing_ok=True)

    return {
        "message": f"Restored from uploaded file {file.filename}",
        "pre_restore_backup": pre_restore.name,
    }


@router.delete("/{filename}")
async def delete_backup_endpoint(filename: str, admin: User = Depends(require_admin)):
    """Delete a backup file."""
    if not delete_backup(filename):
        raise HTTPException(status_code=404, detail="Backup not found")
    return {"message": f"Deleted {filename}"}
