from stocks import get_all_stocks

STOCKS = get_all_stocks()

TIMEFRAMES = ["1h", "4h"]

# ── Scheduling ──────────────────────────────────────────────────────────
# Intervallo tra una scansione completa e l'altra (in minuti).
# 30 min = cattura ogni chiusura di candela 1h con margine.
SCAN_INTERVAL_MINUTES = 30

# ── Rate limiting ───────────────────────────────────────────────────────
BATCH_SIZE = 20
BATCH_DELAY = 2  # secondi tra un batch e l'altro

# ── Dedup alert ─────────────────────────────────────────────────────────
# Ogni alert è univoco per (ticker, timeframe, timestamp candela).
# Scade dopo N ore, così non si accumula memoria all'infinito.
ALERT_EXPIRY_HOURS = 8

# ── Logging ─────────────────────────────────────────────────────────────
LOG_FILE = "alerts.log"

# ── Email (da implementare) ─────────────────────────────────────────────
EMAIL_TO = "tua_email@example.com"
