"""Test per la blacklist dei ticker con download sempre fallito."""

from datetime import datetime, timedelta

import pytest

import bot


@pytest.fixture(autouse=True)
def reset_state():
    bot._fail_streak.clear()
    bot._dead_tickers.clear()
    bot._last_reprobe_at = None
    yield
    bot._fail_streak.clear()
    bot._dead_tickers.clear()
    bot._last_reprobe_at = None


ALL = ["AAA", "BBB", "CCC", "DDD"]


def test_ticker_excluded_after_threshold_failures():
    for _ in range(bot.DEAD_TICKER_THRESHOLD):
        bot._update_fail_streaks(["AAA"], ALL)
    assert "AAA" in bot._dead_tickers
    assert "AAA" not in bot._tickers_to_scan()
    assert set(bot._tickers_to_scan()) == {"BBB", "CCC", "DDD"}


def test_streak_resets_on_success():
    for _ in range(bot.DEAD_TICKER_THRESHOLD - 1):
        bot._update_fail_streaks(["AAA"], ALL)
    bot._update_fail_streaks([], ALL)  # scan ok
    bot._update_fail_streaks(["AAA"], ALL)
    assert "AAA" not in bot._dead_tickers


def test_reprobe_reincludes_dead_tickers_after_window():
    for _ in range(bot.DEAD_TICKER_THRESHOLD):
        bot._update_fail_streaks(["AAA"], ALL)
    assert "AAA" not in bot._tickers_to_scan()      # dentro la finestra
    bot._last_reprobe_at = datetime.now() - timedelta(
        hours=bot.DEAD_TICKER_REPROBE_HOURS + 1
    )
    assert set(bot._tickers_to_scan()) == set(ALL)  # finestra scaduta


def test_dead_ticker_readmitted_when_download_recovers():
    for _ in range(bot.DEAD_TICKER_THRESHOLD):
        bot._update_fail_streaks(["AAA"], ALL)
    assert "AAA" in bot._dead_tickers
    # Al re-probe AAA scarica di nuovo con successo → riammesso.
    bot._update_fail_streaks([], ALL)
    assert "AAA" not in bot._dead_tickers
    assert "AAA" in bot._tickers_to_scan()
