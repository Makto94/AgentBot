"""Environment-based configuration."""

import os

from stocks import get_all_stocks

# ── Stock list ────────────────────────────────────────────────────────
STOCKS = get_all_stocks()
TIMEFRAMES = ["1h", "4h"]

# ── Database ──────────────────────────────────────────────────────────
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "stock_scanner_db")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ.get("POSTGRES_DB", "stock_scanner")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "scanner")
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

# ── Telegram ──────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── Rate limiting ─────────────────────────────────────────────────────
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "50"))
BATCH_DELAY = int(os.environ.get("BATCH_DELAY", "1"))

# ── S/R Filter ────────────────────────────────────────────────────────
SR_PERIOD = int(os.environ.get("SR_PERIOD", "7"))
SR_TOLERANCE = float(os.environ.get("SR_TOLERANCE", "0.25"))
PCT_THRESHOLD = float(os.environ.get("PCT_THRESHOLD", "0.005"))

# ── EMA trend gate (opt-in: di default NON altera i segnali live) ──────
# Se attivo, un segnale RIALZISTA passa solo con close>EMA_SLOW e EMA_FAST>
# EMA_SLOW sul 4h (specchiato per il RIBASSISTA). Default disattivato.
EMA_GATE_ENABLED = os.environ.get("EMA_GATE_ENABLED", "false").lower() == "true"
EMA_FAST = int(os.environ.get("EMA_FAST", "20"))
EMA_SLOW = int(os.environ.get("EMA_SLOW", "50"))

# ── Outcome tracking ──────────────────────────────────────────────────
# Orizzonte (in candele 4h) a cui si valuta l'esito forward di un segnale.
OUTCOME_HORIZON_BARS = int(os.environ.get("OUTCOME_HORIZON_BARS", "6"))

# ── Heartbeat ─────────────────────────────────────────────────────────
# Gap massimo (min) tra due scansioni completate prima di allertare.
HEARTBEAT_MAX_GAP_MIN = int(os.environ.get("HEARTBEAT_MAX_GAP_MIN", "40"))

# ── Logging ───────────────────────────────────────────────────────────
LOG_FILE = os.environ.get("LOG_FILE", "/tmp/alerts.log")
