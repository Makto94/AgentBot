"""Database queries — asyncpg."""

from datetime import datetime, timedelta, UTC

import asyncpg

from config import DATABASE_URL

pool: asyncpg.Pool | None = None


async def init_db() -> None:
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=5)


async def close_db() -> None:
    global pool
    if pool:
        await pool.close()


async def get_scanner_status() -> dict:
    if not pool:
        return {}
    async with pool.acquire() as conn:
        # Last completed scan
        last_scan = await conn.fetchrow(
            "SELECT id, started_at, ended_at, total_stocks, signals_found, signals_filtered, errors "
            "FROM scans WHERE ended_at IS NOT NULL ORDER BY started_at DESC LIMIT 1"
        )
        # Current running scan (if any)
        running_scan = await conn.fetchrow(
            "SELECT id, started_at, total_stocks FROM scans WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        )
        # Signals from last 24h (avoids timezone issues with CURRENT_DATE)
        today_count = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '24 hours' AND near_sr = TRUE"
        )
    result: dict = {
        "last_scan": None,
        "running": False,
        "total_signals_today": today_count or 0,
    }
    if last_scan:
        result["last_scan"] = {
            "id": last_scan["id"],
            "started_at": last_scan["started_at"].isoformat() if last_scan["started_at"] else None,
            "ended_at": last_scan["ended_at"].isoformat() if last_scan["ended_at"] else None,
            "total_stocks": last_scan["total_stocks"],
            "signals_found": last_scan["signals_found"],
            "signals_filtered": last_scan["signals_filtered"],
            "errors": last_scan["errors"],
        }
    if running_scan:
        result["running"] = True
    return result


async def get_scanner_stats() -> dict:
    if not pool:
        return {}
    async with pool.acquire() as conn:
        today = await conn.fetchrow(
            """SELECT COUNT(*) as total,
                      COUNT(*) FILTER (WHERE signal_type = 'RIALZISTA') as bullish,
                      COUNT(*) FILTER (WHERE signal_type = 'RIBASSISTA') as bearish,
                      COUNT(*) FILTER (WHERE near_sr = TRUE) as near_sr
               FROM signals WHERE created_at >= NOW() - INTERVAL '24 hours'"""
        )
        week = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '7 days' AND near_sr = TRUE"
        )
        month = await conn.fetchval(
            "SELECT COUNT(*) FROM signals WHERE created_at >= NOW() - INTERVAL '30 days' AND near_sr = TRUE"
        )
        by_type = await conn.fetch(
            """SELECT signal_type, COUNT(*) as count
               FROM signals WHERE near_sr = TRUE
               GROUP BY signal_type"""
        )
        by_tf = await conn.fetch(
            """SELECT timeframe, COUNT(*) as count
               FROM signals WHERE near_sr = TRUE
               GROUP BY timeframe"""
        )
    return {
        "today": {
            "total": today["total"],
            "bullish": today["bullish"],
            "bearish": today["bearish"],
            "near_sr": today["near_sr"],
        } if today else {},
        "week": week or 0,
        "month": month or 0,
        "by_type": [{"type": r["signal_type"], "count": r["count"]} for r in by_type],
        "by_timeframe": [{"timeframe": r["timeframe"], "count": r["count"]} for r in by_tf],
    }


async def get_signals_paginated(
    page: int = 1,
    page_size: int = 25,
    ticker: str | None = None,
    signal_type: str | None = None,
    timeframe: str | None = None,
    near_sr: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    if not pool:
        return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    conditions = []
    params: list = []
    idx = 1

    if ticker:
        conditions.append(f"ticker ILIKE ${idx}")
        params.append(f"%{ticker}%")
        idx += 1

    if signal_type in ("RIALZISTA", "RIBASSISTA"):
        conditions.append(f"signal_type = ${idx}")
        params.append(signal_type)
        idx += 1

    if timeframe in ("1h", "4h"):
        conditions.append(f"timeframe = ${idx}")
        params.append(timeframe)
        idx += 1

    if near_sr is not None:
        conditions.append(f"near_sr = ${idx}")
        params.append(near_sr)
        idx += 1

    if date_from:
        conditions.append(f"created_at >= ${idx}::timestamptz")
        params.append(date_from)
        idx += 1

    if date_to:
        conditions.append(f"created_at <= ${idx}::timestamptz")
        params.append(date_to + "T23:59:59Z")
        idx += 1

    where = " AND ".join(conditions) if conditions else "TRUE"

    allowed_sort = {
        "created_at": "created_at",
        "breakout_pct": "breakout_pct",
        "ticker": "ticker",
        "candle_time": "candle_time",
    }
    sort_col = allowed_sort.get(sort_by, "created_at")
    order = "ASC" if sort_order == "asc" else "DESC"

    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM signals WHERE {where}", *params)
        total_pages = max(1, (total + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        rows = await conn.fetch(
            f"""SELECT id, scan_id, ticker, timeframe, signal_type, close_price,
                       prev_high, prev_low, breakout_pct, candle_time,
                       near_sr, sr_level, sr_distance, atr_value, created_at
                FROM signals WHERE {where}
                ORDER BY {sort_col} {order}
                LIMIT ${idx} OFFSET ${idx + 1}""",
            *params, page_size, offset,
        )

    items = [
        {
            "id": r["id"],
            "scan_id": r["scan_id"],
            "ticker": r["ticker"],
            "timeframe": r["timeframe"],
            "signal_type": r["signal_type"],
            "close_price": float(r["close_price"]),
            "prev_high": float(r["prev_high"]),
            "prev_low": float(r["prev_low"]),
            "breakout_pct": float(r["breakout_pct"]),
            "candle_time": r["candle_time"].isoformat() if r["candle_time"] else None,
            "near_sr": r["near_sr"],
            "sr_level": float(r["sr_level"]) if r["sr_level"] else None,
            "sr_distance": float(r["sr_distance"]) if r["sr_distance"] else None,
            "atr_value": float(r["atr_value"]) if r["atr_value"] else None,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def get_latest_signals(limit: int = 20) -> list[dict]:
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, ticker, timeframe, signal_type, close_price,
                      prev_high, prev_low, breakout_pct, candle_time,
                      sr_level, sr_distance, atr_value, created_at
               FROM signals WHERE near_sr = TRUE
               ORDER BY candle_time DESC, created_at DESC LIMIT $1""",
            limit,
        )
    return [
        {
            "id": r["id"],
            "ticker": r["ticker"],
            "timeframe": r["timeframe"],
            "signal_type": r["signal_type"],
            "close_price": float(r["close_price"]),
            "prev_high": float(r["prev_high"]),
            "prev_low": float(r["prev_low"]),
            "breakout_pct": float(r["breakout_pct"]),
            "candle_time": r["candle_time"].isoformat() if r["candle_time"] else None,
            "sr_level": float(r["sr_level"]) if r["sr_level"] else None,
            "sr_distance": float(r["sr_distance"]) if r["sr_distance"] else None,
            "atr_value": float(r["atr_value"]) if r["atr_value"] else None,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def get_ticker_chart(ticker: str, timeframe: str = "4h") -> dict:
    """Get candle data, S/R levels, and signals for a ticker from DB."""
    if not pool:
        return {"candles": [], "sr_levels": [], "signals": []}

    async with pool.acquire() as conn:
        candle_rows = await conn.fetch(
            """SELECT candle_time, open, high, low, close
               FROM candles
               WHERE ticker = $1 AND timeframe = $2
               ORDER BY candle_time ASC""",
            ticker, timeframe,
        )

        sr_rows = await conn.fetch(
            """SELECT level_price, level_type
               FROM sr_levels
               WHERE ticker = $1 AND timeframe = $2
                 AND scan_id = (
                   SELECT MAX(scan_id) FROM sr_levels
                   WHERE ticker = $1 AND timeframe = $2
                 )
               ORDER BY level_price""",
            ticker, timeframe,
        )

        signal_rows = await conn.fetch(
            """SELECT candle_time, signal_type, breakout_pct, near_sr
               FROM signals
               WHERE ticker = $1 AND timeframe = $2
               ORDER BY candle_time ASC""",
            ticker, timeframe,
        )

    candles = [
        {
            "time": int(r["candle_time"].timestamp()),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
        }
        for r in candle_rows
    ]
    sr_levels = [{"price": float(r["level_price"]), "type": r["level_type"]} for r in sr_rows]
    signals = [
        {
            "time": int(r["candle_time"].timestamp()),
            "type": r["signal_type"],
            "pct": float(r["breakout_pct"]),
            "near_sr": r["near_sr"],
        }
        for r in signal_rows
    ]
    return {"candles": candles, "sr_levels": sr_levels, "signals": signals}


async def get_ticker_signals(ticker: str) -> list[dict]:
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, timeframe, signal_type, close_price, prev_high, prev_low,
                      breakout_pct, candle_time, near_sr, sr_level, sr_distance,
                      atr_value, created_at
               FROM signals WHERE ticker = $1
               ORDER BY created_at DESC LIMIT 50""",
            ticker,
        )
    return [
        {
            "id": r["id"],
            "timeframe": r["timeframe"],
            "signal_type": r["signal_type"],
            "close_price": float(r["close_price"]),
            "prev_high": float(r["prev_high"]),
            "prev_low": float(r["prev_low"]),
            "breakout_pct": float(r["breakout_pct"]),
            "candle_time": r["candle_time"].isoformat() if r["candle_time"] else None,
            "near_sr": r["near_sr"],
            "sr_level": float(r["sr_level"]) if r["sr_level"] else None,
            "sr_distance": float(r["sr_distance"]) if r["sr_distance"] else None,
            "atr_value": float(r["atr_value"]) if r["atr_value"] else None,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


async def get_all_tickers(q: str = "") -> list[str]:
    """Get all distinct tickers from candles, optionally filtered."""
    if not pool:
        return []
    async with pool.acquire() as conn:
        if q:
            rows = await conn.fetch(
                """SELECT DISTINCT ticker FROM candles
                   WHERE ticker ILIKE $1
                   ORDER BY ticker LIMIT 30""",
                f"%{q}%",
            )
        else:
            rows = await conn.fetch(
                "SELECT DISTINCT ticker FROM candles ORDER BY ticker"
            )
    return [r["ticker"] for r in rows]


async def get_tickers_list() -> list[dict]:
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT ticker, COUNT(*) as signal_count
               FROM signals
               WHERE created_at >= CURRENT_DATE - INTERVAL '7 days' AND near_sr = TRUE
               GROUP BY ticker
               ORDER BY signal_count DESC"""
        )
    return [{"ticker": r["ticker"], "signal_count_7d": r["signal_count"]} for r in rows]


async def get_scans(limit: int = 20) -> list[dict]:
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, started_at, ended_at, total_stocks, signals_found,
                      signals_filtered, errors
               FROM scans ORDER BY started_at DESC LIMIT $1""",
            limit,
        )
    return [
        {
            "id": r["id"],
            "started_at": r["started_at"].isoformat() if r["started_at"] else None,
            "ended_at": r["ended_at"].isoformat() if r["ended_at"] else None,
            "total_stocks": r["total_stocks"],
            "signals_found": r["signals_found"],
            "signals_filtered": r["signals_filtered"],
            "errors": r["errors"],
        }
        for r in rows
    ]
