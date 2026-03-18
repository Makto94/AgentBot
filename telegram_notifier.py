"""Telegram notification service using Bot API."""

import logging

import requests

logger = logging.getLogger("BotAlarm")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


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

    try:
        url = TELEGRAM_API.format(token=bot_token)
        resp = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info(f"Telegram: inviati {len(signals)} segnali")
            return True
        else:
            logger.error(f"Telegram errore: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Telegram errore di rete: {e}")
        return False
