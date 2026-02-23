import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "backups"


def ensure_backup_dir():
    BACKUP_DIR.mkdir(exist_ok=True)


def create_backup(db_path: str) -> Path:
    """Create a consistent backup using sqlite3.backup()."""
    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"ose_sheets_{timestamp}.db"
    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(str(dest))
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    return dest


def restore_backup(db_path: str, backup_path: Path, engine):
    """Replace the live DB with a backup file."""
    engine.dispose()
    shutil.copy2(str(backup_path), db_path)


def list_backups() -> list[dict]:
    """List available backups with name, size, and timestamp."""
    ensure_backup_dir()
    backups = []
    for f in sorted(BACKUP_DIR.glob("ose_sheets_*.db"), reverse=True):
        stat = f.stat()
        backups.append({
            "filename": f.name,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return backups


def delete_backup(filename: str) -> bool:
    """Delete a backup file by name. Returns True if deleted."""
    path = BACKUP_DIR / filename
    if path.exists() and path.parent == BACKUP_DIR:
        path.unlink()
        return True
    return False
