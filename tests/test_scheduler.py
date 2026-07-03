"""Test per lo scheduler e il calendario mercato di bot.py.

Regressione principale: _seconds_until_next_scan non deve mai restituire 0
(busy-loop che ha floodato i log con 153k righe/48h)."""

from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import bot


def _at(h, m, s, us=0):
    return datetime(2026, 7, 3, h, m, s, us)


def test_next_scan_never_zero_in_subsecond_window():
    # 0.4s prima dello slot :20 — il vecchio int() troncava a 0.
    with patch("bot.datetime", wraps=datetime) as mock_dt:
        mock_dt.now.return_value = _at(12, 19, 59, 600_000)
        wait, label = bot._seconds_until_next_scan()
    assert wait >= 1
    assert label == "12:20:00"


def test_next_scan_normal_wait():
    with patch("bot.datetime", wraps=datetime) as mock_dt:
        mock_dt.now.return_value = _at(12, 5, 0)
        wait, label = bot._seconds_until_next_scan()
    assert wait == 15 * 60
    assert label == "12:20:00"


def test_next_scan_rolls_to_next_hour():
    with patch("bot.datetime", wraps=datetime) as mock_dt:
        mock_dt.now.return_value = _at(12, 55, 30)
        wait, label = bot._seconds_until_next_scan()
    assert label == "13:20:00"
    assert wait == 24 * 60 + 30


NY = ZoneInfo("America/New_York")


def test_market_closed_on_observed_july_4th():
    # 4 luglio 2026 è sabato → osservato venerdì 3.
    assert bot._market_is_closed_day(datetime(2026, 7, 3, 10, 0, tzinfo=NY))


def test_market_open_on_regular_thursday():
    assert not bot._market_is_closed_day(datetime(2026, 7, 2, 10, 0, tzinfo=NY))


def test_market_closed_on_weekend():
    assert bot._market_is_closed_day(datetime(2026, 7, 4, 10, 0, tzinfo=NY))
    assert bot._market_is_closed_day(datetime(2026, 7, 5, 10, 0, tzinfo=NY))


def test_us_holidays_2026_contains_expected():
    holidays = bot._us_market_holidays(2026)
    assert date(2026, 7, 3) in holidays   # 4 luglio osservato
    assert date(2026, 1, 1) in holidays
    assert date(2026, 12, 25) in holidays
