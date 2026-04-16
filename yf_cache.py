"""yfinance SQLite cache utilities.

yfinance keeps a local SQLite cache (cookies + ticker timezones) under
~/.cache/py-yfinance/. If the process is killed mid-write, the WAL/SHM
sidecar files get orphaned and SQLite refuses to reopen the .db with
``OperationalError('unable to open database file')``, silently breaking
every download until the lock files are removed.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("BotAlarm")

CACHE_DIR = Path.home() / ".cache" / "py-yfinance"


def _db_is_healthy(db_path: Path) -> bool:
    """Return True if SQLite can open the db and pass a quick integrity check."""
    try:
        with sqlite3.connect(db_path, timeout=2) as conn:
            row = conn.execute("PRAGMA quick_check").fetchone()
            return bool(row) and row[0] == "ok"
    except sqlite3.DatabaseError:
        return False


def cleanup_stale_locks() -> None:
    """Remove orphan -shm/-wal sidecar files when the parent .db is unreadable.

    Safe no-op if the cache dir does not exist. Only deletes sidecars when the
    main .db is unhealthy, so a healthy live process is not disturbed.
    """
    if not CACHE_DIR.is_dir():
        return

    removed: list[str] = []
    for db_path in CACHE_DIR.glob("*.db"):
        if _db_is_healthy(db_path):
            continue
        for suffix in ("-shm", "-wal"):
            sidecar = db_path.with_name(db_path.name + suffix)
            if sidecar.exists():
                try:
                    sidecar.unlink()
                    removed.append(sidecar.name)
                except OSError as e:
                    logger.warning(f"yfinance cache: impossibile rimuovere {sidecar.name}: {e}")

    if removed:
        logger.info(f"yfinance cache: rimossi file di lock orfani: {', '.join(removed)}")
