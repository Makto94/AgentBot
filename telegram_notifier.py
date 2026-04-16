"""Telegram notification service using Bot API."""

import logging
import time

import requests

logger = logging.getLogger("BotAlarm")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Rate-limit di servizio per gli alert: massimo 1 ogni 30 minuti per non
# spammare il canale se il problema persiste su più scansioni consecutive.
_ALERT_MIN_INTERVAL_S = 30 * 60
_last_alert_ts: float = 0.0


def _post(text: str, bot_token: str, chat_id: str) -> bool:
    try:
        resp = requests.post(
            TELEGRAM_API.format(token=bot_token),
            json={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        logger.error(f"Telegram errore: {resp.status_code} {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Telegram errore di rete: {e}")
        return False


def send_telegram_alert(message: str, bot_token: str, chat_id: str) -> bool:
    """Invia un messaggio di servizio (failure / health) con rate-limit.

    Restituisce True se inviato, False se mancano credenziali, fallisce
    la POST, o è ancora attivo il cooldown.
    """
    global _last_alert_ts

    if not bot_token or not chat_id:
        logger.warning("Telegram non configurato (token o chat_id mancante)")
        return False

    now = time.monotonic()
    if now - _last_alert_ts < _ALERT_MIN_INTERVAL_S:
        logger.info("Alert Telegram soppresso (cooldown attivo)")
        return False

    if _post(message, bot_token, chat_id):
        _last_alert_ts = now
        logger.info("Telegram alert inviato")
        return True
    return False


def send_telegram(
    signals: list[dict],
    bot_token: str,
    chat_id: str,
) -> bool:
    """Invia segnali formattati al gruppo/chat Telegram.

    Returns True if message was sent successfully.
    """
    if not bot_token or not chat_id:
        logger.warning("Telegram non configurato (token o chat_id mancante)")
        return False

    if not signals:
        return False

    lines: list[str] = []
    for s in signals:
        emoji = "\U0001f7e2" if s["signal_type"] == "RIALZISTA" else "\U0001f534"
        pct_str = f"{s['breakout_pct'] * 100:.2f}%"
        sr_str = ""
        if s.get("near_sr") and s.get("sr_level"):
            sr_str = f" | S/R {s['sr_level']:.2f}"

        lines.append(
            f"{emoji} {s['ticker']} ({s['timeframe']}) "
            f"{s['signal_type']} +{pct_str}{sr_str}"
        )

    header = f"\U0001f4ca Stock Scanner - {len(signals)} segnali\n"
    text = header + "\n".join(lines)

    if _post(text, bot_token, chat_id):
        logger.info(f"Telegram: inviati {len(signals)} segnali")
        return True
    return False
