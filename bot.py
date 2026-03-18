"""Stock Scanner Bot — Outside Candle Breakout with S/R filter, DB, and Telegram."""

import logging
import signal
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config import (
    BATCH_DELAY,
    BATCH_SIZE,
    LOG_FILE,
    PCT_THRESHOLD,
    SCAN_INTERVAL_MINUTES,
    SR_PERIOD,
    SR_TOLERANCE,
    STOCKS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TIMEFRAMES,
)
from db import (
    close_connection,
    complete_scan,
    create_scan,
    get_new_filtered_signals,
    init_db,
    insert_signal,
    save_candles,
    save_sr_levels,
)
from sr_filter import calc_atr, find_swing_levels, nearest_sr
from telegram_notifier import send_telegram

# ── Logger ──────────────────────────────────────────────────────────────

logger = logging.getLogger("BotAlarm")
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
)
logger.addHandler(console_handler)


# ── Candele ─────────────────────────────────────────────────────────────

def resample_to_4h(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.resample("4h")
        .agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        )
        .dropna()
    )


def download_batch(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """Download 1h data for a batch of tickers in one yfinance call."""
    data = yf.download(
        tickers,
        period="30d",
        interval="1h",
        progress=False,
        auto_adjust=True,
        group_by="ticker",
        threads=True,
    )

    result: dict[str, pd.DataFrame] = {}
    if data.empty:
        return result

    if len(tickers) == 1:
        # Single ticker — no MultiIndex on columns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        if not data.empty:
            result[tickers[0]] = data.dropna(how="all")
    else:
        # Multiple tickers — MultiIndex columns grouped by ticker
        for ticker in tickers:
            try:
                df = data[ticker].dropna(how="all")
                if not df.empty:
                    result[ticker] = df
            except (KeyError, TypeError):
                pass

    return result


def _check_breakout(df: pd.DataFrame) -> tuple[str | None, float]:
    """Check last candle for breakout. Returns (signal_type, breakout_pct)."""
    if df is None or len(df) < 2:
        return None, 0.0

    prev_high = float(df.iloc[-2]["High"])
    prev_low = float(df.iloc[-2]["Low"])
    last_close = float(df.iloc[-1]["Close"])

    if last_close > prev_high:
        pct = (last_close - prev_high) / prev_high
        if pct >= PCT_THRESHOLD:
            return "RIALZISTA", pct
    elif last_close < prev_low:
        pct = (prev_low - last_close) / prev_low
        if pct >= PCT_THRESHOLD:
            return "RIBASSISTA", pct

    return None, 0.0


def process_ticker(
    ticker: str,
    df_raw: pd.DataFrame,
    scan_id: int,
    sr_levels_cache: dict[str, list[float]],
    atr_cache: dict[str, float],
) -> tuple[int, int, int]:
    """Process a single ticker. Only saves signal if 4h+1h confirm same direction."""
    alerts = 0
    filtered = 0
    errors = 0

    # Derive both timeframes from single download
    try:
        df_4h = resample_to_4h(df_raw)
    except Exception:
        df_4h = pd.DataFrame()

    cutoff_1h = datetime.now() - timedelta(days=5)
    if df_raw.index.tz:
        cutoff_1h = cutoff_1h.replace(tzinfo=df_raw.index.tz)
    df_1h = df_raw[df_raw.index >= cutoff_1h]

    candles_map: dict[str, pd.DataFrame | None] = {
        "1h": df_1h if not df_1h.empty else None,
        "4h": df_4h if not df_4h.empty else None,
    }

    # Save candles to DB for both timeframes
    for tf, df in candles_map.items():
        if df is None or len(df) < 2:
            continue
        try:
            candle_rows = [
                {
                    "candle_time": str(ts),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]) if "Volume" in row else None,
                }
                for ts, row in df.iterrows()
            ]
            save_candles(ticker, tf, candle_rows)
        except Exception as e:
            logger.error(f"Errore salvataggio candele {ticker} ({tf}): {e}")

    # Compute S/R levels on 4h
    try:
        cache_key = f"{ticker}_4h"
        if df_4h is not None and len(df_4h) >= 2 and cache_key not in sr_levels_cache:
            levels = find_swing_levels(df_4h, period=SR_PERIOD)
            atr = calc_atr(df_4h, period=14)
            sr_levels_cache[cache_key] = levels
            atr_cache[cache_key] = atr

            highs_vals = df_4h["High"].values
            level_types = [
                "swing_high" if lvl in highs_vals else "swing_low"
                for lvl in levels
            ]
            save_sr_levels(scan_id, ticker, "4h", levels, level_types)
    except Exception as e:
        logger.error(f"Errore S/R {ticker}: {e}")
        errors += 1

    # Check breakout on BOTH timeframes
    type_4h, pct_4h = _check_breakout(candles_map.get("4h"))
    type_1h, pct_1h = _check_breakout(candles_map.get("1h"))

    # Only save if BOTH confirm same direction
    if type_4h is None or type_1h is None or type_4h != type_1h:
        return alerts, filtered, errors

    # Multi-timeframe confirmed signal — use 4h data as primary
    df_4h_valid = candles_map["4h"]
    assert df_4h_valid is not None
    prev_high = float(df_4h_valid.iloc[-2]["High"])
    prev_low = float(df_4h_valid.iloc[-2]["Low"])
    last_close = float(df_4h_valid.iloc[-1]["Close"])
    candle_ts = str(df_4h_valid.index[-1])

    # S/R proximity check
    sr_key = f"{ticker}_4h"
    levels = sr_levels_cache.get(sr_key, [])
    atr = atr_cache.get(sr_key, 0.0)
    near_sr = False
    sr_level = None
    sr_distance = None

    if levels and atr > 0:
        ref_price = prev_high if type_4h == "RIALZISTA" else prev_low
        sr_level, sr_distance = nearest_sr(ref_price, levels)
        near_sr = sr_distance <= SR_TOLERANCE * atr

    try:
        signal_data = {
            "ticker": ticker,
            "timeframe": "4h+1h",
            "signal_type": type_4h,
            "close_price": last_close,
            "prev_high": prev_high,
            "prev_low": prev_low,
            "breakout_pct": pct_4h,
            "candle_time": candle_ts,
            "near_sr": near_sr,
            "sr_level": sr_level,
            "sr_distance": sr_distance,
            "atr_value": atr if atr > 0 else None,
        }

        signal_id = insert_signal(scan_id, signal_data)
        if signal_id is not None:
            logger.info(
                f"CONFIRMED {type_4h} | {ticker} | 4h ({pct_4h*100:.2f}%) + 1h ({pct_1h*100:.2f}%) | "
                f"{'Near S/R' if near_sr else 'No S/R'} | Candela: {candle_ts}"
            )
            alerts += 1
            if near_sr:
                filtered += 1

    except Exception as e:
        logger.error(f"Errore segnale {ticker}: {e}")
        errors += 1

    return alerts, filtered, errors


# ── Scansione ───────────────────────────────────────────────────────────


def scan_all() -> None:
    """Esegue una scansione completa con download batch."""
    logger.info("=" * 60)
    logger.info(f"Avvio scansione - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Totale stock: {len(STOCKS)} | Timeframe: {', '.join(TIMEFRAMES)}")
    logger.info("=" * 60)

    scan_id = create_scan(len(STOCKS))
    alerts_count = 0
    filtered_count = 0
    errors_count = 0

    sr_levels_cache: dict[str, list[float]] = {}
    atr_cache: dict[str, float] = {}

    # Download in batches
    for batch_start in range(0, len(STOCKS), BATCH_SIZE):
        batch = STOCKS[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1

        try:
            raw_data = download_batch(batch)
        except Exception as e:
            logger.error(f"Errore download batch {batch_num}: {e}")
            errors_count += len(batch)
            continue

        for ticker in batch:
            df_raw = raw_data.get(ticker)
            if df_raw is None or df_raw.empty:
                continue

            a, f, e = process_ticker(
                ticker, df_raw, scan_id, sr_levels_cache, atr_cache
            )
            alerts_count += a
            filtered_count += f
            errors_count += e

        done = min(batch_start + BATCH_SIZE, len(STOCKS))
        logger.info(f"  Progresso: {done}/{len(STOCKS)} ...")
        time.sleep(BATCH_DELAY)

    complete_scan(scan_id, alerts_count, filtered_count, errors_count)

    # Send Telegram for filtered signals (near S/R)
    filtered_signals = get_new_filtered_signals(scan_id)
    if filtered_signals:
        send_telegram(filtered_signals, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

    logger.info("-" * 60)
    logger.info(
        f"Scansione completata | {len(STOCKS)} stock | "
        f"{alerts_count} segnali totali | {filtered_count} near S/R | "
        f"{errors_count} errori"
    )
    logger.info("=" * 60)


# ── Loop principale h24 ────────────────────────────────────────────────

_running = True


def _handle_shutdown(signum: int, frame: object) -> None:
    global _running
    logger.info("Segnale di shutdown ricevuto. Arresto in corso...")
    _running = False


signal.signal(signal.SIGINT, _handle_shutdown)
signal.signal(signal.SIGTERM, _handle_shutdown)


SCAN_MINUTES = [20, 50]  # Scan at :20 and :50 of every hour


def _seconds_until_next_scan() -> tuple[int, str]:
    """Calculate seconds until next scan slot (:20 or :50)."""
    now = datetime.now()
    for minute in SCAN_MINUTES:
        target = now.replace(minute=minute, second=0, microsecond=0)
        if target > now:
            return int((target - now).total_seconds()), target.strftime('%H:%M:%S')
    # Next hour :20
    target = (now + timedelta(hours=1)).replace(minute=SCAN_MINUTES[0], second=0, microsecond=0)
    return int((target - now).total_seconds()), target.strftime('%H:%M:%S')


def main() -> None:
    logger.info("*" * 60)
    logger.info("Stock Scanner avviato in modalita CONTINUA (h24)")
    logger.info(f"Scan sincronizzati a :{SCAN_MINUTES[0]:02d} e :{SCAN_MINUTES[1]:02d} di ogni ora")
    logger.info(f"Stock monitorati: {len(STOCKS)}")
    logger.info(f"Filtro S/R: period={SR_PERIOD}, tolerance={SR_TOLERANCE}xATR, soglia={PCT_THRESHOLD*100:.1f}%")
    logger.info("*" * 60)

    init_db()

    # First scan immediately
    try:
        scan_all()
    except Exception as e:
        logger.error(f"Errore critico nella scansione: {e}", exc_info=True)

    while _running:
        wait_seconds, next_time = _seconds_until_next_scan()
        logger.info(f"Prossima scansione: {next_time} (tra {wait_seconds}s)")

        while wait_seconds > 0 and _running:
            time.sleep(min(wait_seconds, 5))
            wait_seconds -= 5

        if not _running:
            break

        try:
            scan_all()
        except Exception as e:
            logger.error(f"Errore critico nella scansione: {e}", exc_info=True)

    close_connection()
    logger.info("Stock Scanner arrestato.")


if __name__ == "__main__":
    main()
