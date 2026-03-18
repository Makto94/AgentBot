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
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    level_price DOUBLE PRECISION NOT NULL,
    level_type VARCHAR(10) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(ticker, timeframe, level_price)
);

CREATE INDEX IF NOT EXISTS idx_sr_levels_ticker ON sr_levels(ticker, timeframe);

CREATE TABLE IF NOT EXISTS candles (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    candle_time TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(ticker, timeframe, candle_time)
);

CREATE INDEX IF NOT EXISTS idx_candles_ticker_tf ON candles(ticker, timeframe);
CREATE INDEX IF NOT EXISTS idx_candles_time ON candles(ticker, timeframe, candle_time DESC);
"""

MIGRATION_SQL = """
-- Migration: add scan_id to sr_levels if missing, drop old unique constraint
DO $$
BEGIN
    -- Add scan_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sr_levels' AND column_name = 'scan_id'
    ) THEN
        ALTER TABLE sr_levels ADD COLUMN scan_id INT REFERENCES scans(id);
        ALTER TABLE sr_levels ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
        -- Drop old unique constraint
        ALTER TABLE sr_levels DROP CONSTRAINT IF EXISTS sr_levels_ticker_timeframe_level_price_key;
    END IF;

    -- Create candles table if not exists (handled by SCHEMA_SQL but just in case)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'candles'
    ) THEN
        CREATE TABLE candles (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            timeframe VARCHAR(5) NOT NULL,
            candle_time TIMESTAMPTZ NOT NULL,
            open DOUBLE PRECISION NOT NULL,
            high DOUBLE PRECISION NOT NULL,
            low DOUBLE PRECISION NOT NULL,
            close DOUBLE PRECISION NOT NULL,
            volume DOUBLE PRECISION,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(ticker, timeframe, candle_time)
        );
    END IF;
END $$;
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
    """Create tables if they don't exist, run migrations."""
    try:
        with get_cursor() as cur:
            cur.execute(SCHEMA_SQL)
        with get_cursor() as cur:
            cur.execute(MIGRATION_SQL)
        # Create indexes for new columns
        with get_cursor() as cur:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sr_levels_scan ON sr_levels(scan_id)")
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
) -> None:
    """Mark a scan as completed."""
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE scans
            SET ended_at = NOW(),
                signals_found = %s,
                signals_filtered = %s,
                errors = %s
            WHERE id = %s
            """,
            (signals_found, signals_filtered, errors, scan_id),
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


def save_sr_levels(
    scan_id: int,
    ticker: str,
    timeframe: str,
    levels: list[float],
    level_types: list[str],
) -> None:
    """Save S/R levels with scan_id for history using batch insert."""
    if not levels:
        return
    with get_cursor() as cur:
        values = [
            (scan_id, ticker, timeframe, price, lvl_type)
            for price, lvl_type in zip(levels, level_types)
        ]
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO sr_levels (scan_id, ticker, timeframe, level_price, level_type) VALUES %s",
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


def close_connection() -> None:
    """Close the database connection."""
    global _conn
    if _conn and not _conn.closed:
        _conn.close()
        _conn = None
