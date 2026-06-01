"""Database module — sync psycopg2 for the scanner bot."""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

import psycopg2
import psycopg2.extras

from config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

logger = logging.getLogger("BotAlarm")

_conn: psycopg2.extensions.connection | None = None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    total_stocks INT,
    signals_found INT DEFAULT 0,
    signals_filtered INT DEFAULT 0,
    errors INT DEFAULT 0
);

-- Metriche di osservabilità della scansione (self-applied su DB esistenti).
ALTER TABLE scans ADD COLUMN IF NOT EXISTS download_failures INT DEFAULT 0;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS recovered INT DEFAULT 0;
ALTER TABLE scans ADD COLUMN IF NOT EXISTS duration_seconds INT;

CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    scan_id INT REFERENCES scans(id),
    ticker VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    signal_type VARCHAR(15) NOT NULL,
    close_price DOUBLE PRECISION NOT NULL,
    prev_high DOUBLE PRECISION NOT NULL,
    prev_low DOUBLE PRECISION NOT NULL,
    breakout_pct DOUBLE PRECISION NOT NULL,
    candle_time TIMESTAMPTZ NOT NULL,
    near_sr BOOLEAN NOT NULL DEFAULT FALSE,
    sr_level DOUBLE PRECISION,
    sr_distance DOUBLE PRECISION,
    atr_value DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notified BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(ticker, timeframe, candle_time)
);

CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals(ticker);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_near_sr ON signals(near_sr) WHERE near_sr = TRUE;

CREATE TABLE IF NOT EXISTS sr_levels (
    scan_id INT NOT NULL REFERENCES scans(id),
    ticker VARCHAR(20) NOT NULL,
    level_price DOUBLE PRECISION NOT NULL,
    is_high BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ticker, scan_id, level_price)
);

CREATE TABLE IF NOT EXISTS candles (
    ticker VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    candle_time TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (ticker, timeframe, candle_time)
);

CREATE INDEX IF NOT EXISTS idx_candles_ticker_tf ON candles(ticker, timeframe);

CREATE TABLE IF NOT EXISTS signal_outcomes (
    signal_id INT PRIMARY KEY REFERENCES signals(id),
    ticker VARCHAR(20) NOT NULL,
    signal_type VARCHAR(15) NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    bars_forward INT NOT NULL,
    forward_return DOUBLE PRECISION,
    mfe DOUBLE PRECISION,
    mae DOUBLE PRECISION,
    outcome VARCHAR(10) NOT NULL,
    graded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outcomes_outcome ON signal_outcomes(outcome);
"""

MIGRATION_SQL = """
-- Migrazioni storiche idempotenti gestite a parte (vedi /migrations/*.sql).
-- Lo SCHEMA_SQL sopra rappresenta lo stato target — CREATE TABLE IF NOT EXISTS
-- è sufficiente per nuovi deploy; le tabelle esistenti sono già state migrate.
SELECT 1;
"""


def get_connection() -> psycopg2.extensions.connection:
    """Get or create database connection."""
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
        )
        _conn.autocommit = False
    return _conn


@contextmanager
def get_cursor() -> Generator[psycopg2.extras.RealDictCursor, None, None]:
    """Context manager for database cursor with auto-commit/rollback."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    try:
        with get_cursor() as cur:
            cur.execute(SCHEMA_SQL)
        logger.info("Database inizializzato")
    except Exception as e:
        logger.error(f"Errore inizializzazione DB: {e}")
        raise


def create_scan(total_stocks: int) -> int:
    """Create a new scan run and return its id."""
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO scans (total_stocks) VALUES (%s) RETURNING id",
            (total_stocks,),
        )
        row = cur.fetchone()
        assert row is not None
        return row["id"]


def complete_scan(
    scan_id: int,
    signals_found: int,
    signals_filtered: int,
    errors: int,
    download_failures: int = 0,
    recovered: int = 0,
) -> None:
    """Mark a scan as completed and persist observability metrics."""
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE scans
            SET ended_at = NOW(),
                signals_found = %s,
                signals_filtered = %s,
                errors = %s,
                download_failures = %s,
                recovered = %s,
                duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))::int
            WHERE id = %s
            """,
            (signals_found, signals_filtered, errors,
             download_failures, recovered, scan_id),
        )


def insert_signal(scan_id: int, signal: dict) -> int | None:
    """Insert a signal, returns id or None if duplicate."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO signals (
                scan_id, ticker, timeframe, signal_type,
                close_price, prev_high, prev_low, breakout_pct,
                candle_time, near_sr, sr_level, sr_distance, atr_value
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            ON CONFLICT (ticker, timeframe, candle_time) DO NOTHING
            RETURNING id
            """,
            (
                scan_id,
                signal["ticker"],
                signal["timeframe"],
                signal["signal_type"],
                signal["close_price"],
                signal["prev_high"],
                signal["prev_low"],
                signal["breakout_pct"],
                signal["candle_time"],
                signal["near_sr"],
                signal.get("sr_level"),
                signal.get("sr_distance"),
                signal.get("atr_value"),
            ),
        )
        row = cur.fetchone()
        return row["id"] if row else None


def _last_sr_levels(ticker: str) -> set[tuple[float, bool]]:
    """Restituisce l'insieme (level_price, is_high) dell'ultimo scan per ticker."""
    with get_cursor() as cur:
        cur.execute(
            """SELECT level_price, is_high FROM sr_levels
               WHERE ticker = %s
                 AND scan_id = (SELECT MAX(scan_id) FROM sr_levels WHERE ticker = %s)""",
            (ticker, ticker),
        )
        return {(float(r["level_price"]), bool(r["is_high"])) for r in cur.fetchall()}


def save_sr_levels(
    scan_id: int,
    ticker: str,
    levels: list[float],
    is_high_flags: list[bool],
) -> None:
    """Save S/R levels with scan_id for history using batch insert.

    Solo timeframe 4h (vedi bot.process_ticker). is_high_flags[i] = True per
    swing_high, False per swing_low.

    Skip dell'INSERT se i livelli sono identici all'ultimo scan dello stesso
    ticker — sui swing 4h cambiano raramente, evita ~80% di righe duplicate.
    """
    if not levels:
        return

    new_set = {(float(p), bool(h)) for p, h in zip(levels, is_high_flags)}
    if new_set == _last_sr_levels(ticker):
        return

    with get_cursor() as cur:
        values = [
            (scan_id, ticker, price, is_high)
            for price, is_high in zip(levels, is_high_flags)
        ]
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO sr_levels (scan_id, ticker, level_price, is_high) "
            "VALUES %s ON CONFLICT (ticker, scan_id, level_price) DO NOTHING",
            values,
            page_size=100,
        )


def save_candles(ticker: str, timeframe: str, candle_rows: list[dict]) -> None:
    """Upsert OHLCV candles using batch insert."""
    if not candle_rows:
        return
    with get_cursor() as cur:
        values = [
            (
                ticker, timeframe, c["candle_time"],
                c["open"], c["high"], c["low"], c["close"], c.get("volume"),
            )
            for c in candle_rows
        ]
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO candles (ticker, timeframe, candle_time, open, high, low, close, volume)
               VALUES %s
               ON CONFLICT (ticker, timeframe, candle_time) DO UPDATE
               SET open = EXCLUDED.open, high = EXCLUDED.high,
                   low = EXCLUDED.low, close = EXCLUDED.close,
                   volume = EXCLUDED.volume, updated_at = NOW()""",
            values,
            page_size=500,
        )


def get_new_filtered_signals(scan_id: int) -> list[dict]:
    """Get signals from this scan that are near S/R and >= 1% breakout."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT ticker, timeframe, signal_type, close_price,
                   prev_high, prev_low, breakout_pct, candle_time,
                   near_sr, sr_level, sr_distance, atr_value
            FROM signals
            WHERE scan_id = %s AND near_sr = TRUE AND notified = FALSE
            ORDER BY breakout_pct DESC
            """,
            (scan_id,),
        )
        rows = cur.fetchall()
        if rows:
            cur.execute(
                "UPDATE signals SET notified = TRUE WHERE scan_id = %s AND near_sr = TRUE AND notified = FALSE",
                (scan_id,),
            )
        return [dict(r) for r in rows]


def get_signals_pending_outcome(limit: int = 500) -> list[dict]:
    """Segnali senza esito definitivo (mai valutati o ancora OPEN)."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT s.id, s.ticker, s.signal_type, s.close_price, s.candle_time
            FROM signals s
            LEFT JOIN signal_outcomes o ON o.signal_id = s.id
            WHERE (o.signal_id IS NULL OR o.outcome = 'OPEN')
              AND s.candle_time > NOW() - INTERVAL '20 days'
            ORDER BY s.candle_time ASC
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_forward_candles(ticker: str, after_time: datetime, limit: int) -> list[dict]:
    """Candele 4h successive a after_time per un ticker (per il grading forward)."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT candle_time, high, low, close
            FROM candles
            WHERE ticker = %s AND timeframe = '4h' AND candle_time > %s
            ORDER BY candle_time ASC
            LIMIT %s
            """,
            (ticker, after_time, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def upsert_signal_outcome(outcome: dict) -> None:
    """Inserisce/aggiorna l'esito forward di un segnale."""
    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO signal_outcomes (
                signal_id, ticker, signal_type, entry_price,
                bars_forward, forward_return, mfe, mae, outcome, graded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (signal_id) DO UPDATE SET
                bars_forward = EXCLUDED.bars_forward,
                forward_return = EXCLUDED.forward_return,
                mfe = EXCLUDED.mfe,
                mae = EXCLUDED.mae,
                outcome = EXCLUDED.outcome,
                graded_at = NOW()
            """,
            (
                outcome["signal_id"], outcome["ticker"], outcome["signal_type"],
                outcome["entry_price"], outcome["bars_forward"],
                outcome.get("forward_return"), outcome.get("mfe"),
                outcome.get("mae"), outcome["outcome"],
            ),
        )


def close_connection() -> None:
    """Close the database connection."""
    global _conn
    if _conn and not _conn.closed:
        _conn.close()
        _conn = None
