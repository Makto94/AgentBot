import logging
import signal
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config import (
    STOCKS,
    TIMEFRAMES,
    LOG_FILE,
    BATCH_SIZE,
    BATCH_DELAY,
    SCAN_INTERVAL_MINUTES,
    ALERT_EXPIRY_HOURS,
)

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

# ── Dedup: tiene traccia degli alert già inviati ────────────────────────
# Chiave: (ticker, timeframe, candle_timestamp)  →  Valore: datetime di inserimento
_sent_alerts: dict[tuple, datetime] = {}


def _purge_old_alerts():
    """Rimuove alert scaduti per non accumulare memoria."""
    cutoff = datetime.now() - timedelta(hours=ALERT_EXPIRY_HOURS)
    expired = [k for k, v in _sent_alerts.items() if v < cutoff]
    for k in expired:
        del _sent_alerts[k]


def _is_duplicate(key: tuple) -> bool:
    return key in _sent_alerts


def _mark_sent(key: tuple):
    _sent_alerts[key] = datetime.now()


# ── Candele & Strategia ────────────────────────────────────────────────

TIMEFRAME_MAP = {
    "1h": {"period": "5d", "interval": "1h"},
    "4h": {"period": "30d", "interval": "1h"},
}


def resample_to_4h(df: pd.DataFrame) -> pd.DataFrame:
    return df.resample("4h").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()


def get_candles(ticker: str, timeframe: str) -> pd.DataFrame | None:
    params = TIMEFRAME_MAP[timeframe]
    data = yf.download(
        ticker,
        period=params["period"],
        interval=params["interval"],
        progress=False,
        auto_adjust=True,
    )

    if data.empty:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    if timeframe == "4h":
        data = resample_to_4h(data)

    return data


def check_breakout(ticker: str, timeframe: str) -> str | None:
    """
    STRATEGIA — Outside Candle Breakout:

    Prende le ultime 2 candele chiuse sul timeframe scelto (1h o 4h).
    - Candela N-1 (precedente): definisce il range [Low, High]
    - Candela N   (ultima chiusa): si guarda il Close

    Segnale RIALZISTA: Close(N) > High(N-1)
      → Il prezzo ha chiuso SOPRA il massimo della candela precedente,
        indicando forza e possibile continuazione al rialzo.

    Segnale RIBASSISTA: Close(N) < Low(N-1)
      → Il prezzo ha chiuso SOTTO il minimo della candela precedente,
        indicando debolezza e possibile continuazione al ribasso.

    Se il close resta dentro il range [Low, High] della candela precedente,
    non c'è segnale (la price action è contenuta / in consolidamento).
    """
    df = get_candles(ticker, timeframe)

    if df is None or len(df) < 2:
        return None

    prev_candle = df.iloc[-2]
    last_candle = df.iloc[-1]

    prev_high = prev_candle["High"]
    prev_low = prev_candle["Low"]
    last_close = last_candle["Close"]
    candle_ts = str(df.index[-1])

    dedup_key = (ticker, timeframe, candle_ts)
    if _is_duplicate(dedup_key):
        return None

    if last_close > prev_high:
        _mark_sent(dedup_key)
        return (
            f"BREAKOUT RIALZISTA | {ticker} | TF: {timeframe} | "
            f"Close ({last_close:.4f}) > Prev High ({prev_high:.4f}) | "
            f"Candela: {candle_ts}"
        )
    elif last_close < prev_low:
        _mark_sent(dedup_key)
        return (
            f"BREAKOUT RIBASSISTA | {ticker} | TF: {timeframe} | "
            f"Close ({last_close:.4f}) < Prev Low ({prev_low:.4f}) | "
            f"Candela: {candle_ts}"
        )
    return None


# ── Scansione ───────────────────────────────────────────────────────────

def scan_all():
    """Esegue una scansione completa su tutti gli stock e timeframe."""
    logger.info("=" * 60)
    logger.info(f"Avvio scansione - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Totale stock: {len(STOCKS)} | Timeframe: {', '.join(TIMEFRAMES)}")
    logger.info(f"Alert in memoria (dedup): {len(_sent_alerts)}")
    logger.info("=" * 60)

    _purge_old_alerts()

    alerts_count = 0
    errors_count = 0

    for i, ticker in enumerate(STOCKS, 1):
        for tf in TIMEFRAMES:
            try:
                result = check_breakout(ticker, tf)
                if result:
                    logger.info(result)
                    alerts_count += 1
            except Exception as e:
                logger.error(f"Errore per {ticker} ({tf}): {e}")
                errors_count += 1

        if i % BATCH_SIZE == 0:
            logger.info(f"  Progresso: {i}/{len(STOCKS)} ...")
            time.sleep(BATCH_DELAY)

    logger.info("─" * 60)
    logger.info(
        f"Scansione completata | {len(STOCKS)} stock | "
        f"{alerts_count} nuovi alert | {errors_count} errori"
    )
    logger.info("=" * 60)


# ── Loop principale h24 ────────────────────────────────────────────────

_running = True


def _handle_shutdown(signum, frame):
    global _running
    logger.info("Segnale di shutdown ricevuto. Arresto in corso...")
    _running = False


signal.signal(signal.SIGINT, _handle_shutdown)
signal.signal(signal.SIGTERM, _handle_shutdown)


def main():
    logger.info("*" * 60)
    logger.info("Bot Alarm avviato in modalità CONTINUA (h24)")
    logger.info(f"Intervallo tra scansioni: {SCAN_INTERVAL_MINUTES} minuti")
    logger.info(f"Stock monitorati: {len(STOCKS)}")
    logger.info("*" * 60)

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

    logger.info("Bot Alarm arrestato.")


if __name__ == "__main__":
    main()
