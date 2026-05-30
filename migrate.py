"""Runner di migrazioni versionate.

init_db() (db.py) crea lo schema TARGET via CREATE TABLE IF NOT EXISTS, quindi un
DB nuovo è già allo stato post-003; il DB live è stato migrato a mano il
2026-05-29. Questo runner perciò PRE-REGISTRA le tre migrazioni storiche come
applicate (senza eseguirle) ed esegue solo i file NUOVI aggiunti in seguito
(004+), in autocommit così operazioni TimescaleDB/DDL non transazionali passano.
"""

import logging
import os

from db import get_connection, get_cursor

logger = logging.getLogger("BotAlarm")

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

# Migrazioni storiche già riflesse sia nel DB live (applicate a mano) sia nello
# schema target di SCHEMA_SQL: registrate come applicate SENZA rieseguirle
# (002/003 non sono ri-eseguibili).
BASELINE_MIGRATIONS = frozenset(
    {
        "001_step1_indexes_and_slim.sql",
        "002_step2_brin_indexes.sql",
        "003_step4_timescaledb_hypertable.sql",
    }
)


def _ensure_table() -> None:
    with get_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )


def _applied() -> set[str]:
    with get_cursor() as cur:
        cur.execute("SELECT filename FROM schema_migrations")
        return {r["filename"] for r in cur.fetchall()}


def _record(filename: str) -> None:
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO schema_migrations (filename) VALUES (%s) "
            "ON CONFLICT (filename) DO NOTHING",
            (filename,),
        )


def _execute_file(path: str) -> None:
    """Esegue un file .sql in autocommit (il file gestisce i propri BEGIN/COMMIT
    e può contenere DDL non transazionale come create_hypertable)."""
    with open(path, encoding="utf-8") as fh:
        sql = fh.read()
    conn = get_connection()
    previous = conn.autocommit
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
    finally:
        conn.autocommit = previous


def run_migrations() -> None:
    """Pre-registra le baseline storiche e applica le migrazioni nuove in ordine."""
    _ensure_table()
    applied = _applied()

    if not os.path.isdir(MIGRATIONS_DIR):
        return

    files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    for filename in files:
        if filename in applied:
            continue
        if filename in BASELINE_MIGRATIONS:
            _record(filename)
            logger.info(f"Migrazione baseline registrata (non eseguita): {filename}")
            continue
        try:
            _execute_file(os.path.join(MIGRATIONS_DIR, filename))
            _record(filename)
            logger.info(f"Migrazione applicata: {filename}")
        except Exception as e:
            logger.error(f"Migrazione FALLITA {filename}: {e}", exc_info=True)
            raise
