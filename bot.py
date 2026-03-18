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


def process_ticker(
    ticker: str,
    df_raw: pd.DataFrame,
    scan_id: int,
    sr_levels_cache: dict[str, list[float]],
    atr_cache: dict[str, float],
) -> tuple[int, int, int]:
    """Process a single ticker's raw 1h data. Returns (alerts, filtered, errors)."""
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

    for tf in TIMEFRAMES:
        df = candles_map.get(tf)
        if df is None or len(df) < 2:
            continue

        try:
            # Save candles to DB
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

            # Compute S/R levels on 4h
            cache_key = f"{ticker}_4h"
            if tf == "4h" and cache_key not in sr_levels_cache:
                levels = find_swing_levels(df, period=SR_PERIOD)
                atr = calc_atr(df, period=14)
                sr_levels_cache[cache_key] = levels
                atr_cache[cache_key] = atr

                highs_vals = df["High"].values
                level_types = [
                    "swing_high" if lvl in highs_vals else "swing_low"
                    for lvl in levels
                ]
                save_sr_levels(scan_id, ticker, tf, levels, level_types)

            # Check breakout
            prev_candle = df.iloc[-2]
            last_candle = df.iloc[-1]
            prev_high = float(prev_candle["High"])
            prev_low = float(prev_candle["Low"])
            last_close = float(last_candle["Close"])
            candle_ts = str(df.index[-1])

            signal_type = None
            breakout_pct = 0.0

            if last_close > prev_high:
                breakout_pct = (last_close - prev_high) / prev_high
                if breakout_pct >= PCT_THRESHOLD:
                    signal_type = "RIALZISTA"
            elif last_close < prev_low:
                breakout_pct = (prev_low - last_close) / prev_low
                if breakout_pct >= PCT_THRESHOLD:
                    signal_type = "RIBASSISTA"

            if signal_type is None:
                continue

            # S/R proximity check
            sr_key_4h = f"{ticker}_4h"
            levels = sr_levels_cache.get(sr_key_4h, [])
            atr = atr_cache.get(sr_key_4h, 0.0)
            near_sr = False
            sr_level = None
            sr_distance = None

            if levels and atr > 0:
                ref_price = prev_high if signal_type == "RIALZISTA" else prev_low
                sr_level, sr_distance = nearest_sr(ref_price, levels)
                near_sr = sr_distance <= SR_TOLERANCE * atr

            signal_data = {
                "ticker": ticker,
                "timeframe": tf,
                "signal_type": signal_type,
                "close_price": last_close,
                "prev_high": prev_high,
                "prev_low": prev_low,
                "breakout_pct": breakout_pct,
                "candle_time": candle_ts,
                "near_sr": near_sr,
                "sr_level": sr_level,
                "sr_distance": sr_distance,
                "atr_value": atr if atr > 0 else None,
            }

            signal_id = insert_signal(scan_id, signal_data)
            if signal_id is not None:
                logger.info(
                    f"{signal_type} | {ticker} | TF: {tf} | "
                    f"Close ({last_close:.4f}) | Breakout {breakout_pct*100:.2f}% | "
                    f"{'Near S/R' if near_sr else 'No S/R'} | "
                    f"Candela: {candle_ts}"
                )
                alerts += 1
                if near_sr:
                    filtered += 1

        except Exception as e:
            logger.error(f"Errore per {ticker} ({tf}): {e}")
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


def main() -> None:
    logger.info("*" * 60)
    logger.info("Stock Scanner avviato in modalita CONTINUA (h24)")
    logger.info(f"Intervallo tra scansioni: {SCAN_INTERVAL_MINUTES} minuti")
    logger.info(f"Stock monitorati: {len(STOCKS)}")
    logger.info(f"Filtro S/R: period={SR_PERIOD}, tolerance={SR_TOLERANCE}xATR, soglia={PCT_THRESHOLD*100:.0f}%")
    logger.info("*" * 60)

    init_db()

    while _running:
        try:
            scan_all()
        except Exception as e:
            logger.error(f"Errore critico nella scansione: {e}", exc_info=True)

        if not _running:
            break

        next_scan = datetime.now() + timedelta(minutes=SCAN_INTERVAL_MINUTES)
        logger.info(f"Prossima scansione: {next_scan.strftime('%H:%M:%S')}")

        wait_seconds = SCAN_INTERVAL_MINUTES * 60
        while wait_seconds > 0 and _running:
            time.sleep(min(wait_seconds, 5))
            wait_seconds -= 5

    close_connection()
    logger.info("Stock Scanner arrestato.")


if __name__ == "__main__":
    main()
