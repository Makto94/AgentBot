"""Diagnostica dei fallimenti finali, con download e servizi simulati."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import DEFAULT, patch
from zoneinfo import ZoneInfo

import bot


def test_scan_logs_all_final_failures_and_excludes_recovered():
    good = [f"OK{i:02}" for i in range(30)]
    failed = [f"FAIL{i:02}" for i in range(25)]
    tickers = good + ["RECOVER"] + failed
    frame = SimpleNamespace(empty=False)
    mocks = (
        "logger", "_market_now", "_tickers_to_scan", "_check_heartbeat",
        "create_scan", "complete_scan", "get_new_filtered_signals",
        "process_ticker", "_update_fail_streaks", "_grade_outcomes",
        "cleanup_stale_locks", "send_telegram_alert",
    )

    for recover_all in (False, True):
        def download(batch):
            return {
                ticker: frame for ticker in batch
                if ticker in good or ("OK00" not in batch and (
                    ticker == "RECOVER" or recover_all
                ))
            }

        with patch.multiple(bot, **dict.fromkeys(mocks, DEFAULT)) as mocked, \
                patch.object(bot, "download_batch", side_effect=download), \
                patch.object(bot, "BATCH_SIZE", len(tickers)), \
                patch.object(bot, "_last_scan_completed_at", None), \
                patch("bot.time.sleep"):
            mocked["_market_now"].return_value = datetime(
                2026, 9, 8, 10, tzinfo=ZoneInfo("America/New_York")
            )
            mocked["_tickers_to_scan"].return_value = tickers
            mocked["create_scan"].return_value = 42
            mocked["get_new_filtered_signals"].return_value = []
            mocked["process_ticker"].return_value = (0, 0, 0)
            bot.scan_all()

            remaining = [] if recover_all else failed
            mocked["complete_scan"].assert_called_once_with(
                42, 0, 0, 0, download_failures=len(remaining),
                recovered=26 if recover_all else 1,
            )
            mocked["_update_fail_streaks"].assert_called_once_with(remaining, tickers)
            assert mocked["process_ticker"].call_count == len(tickers) - len(remaining)
            if remaining:
                mocked["logger"].warning.assert_called_once_with(
                    "Download senza dati utilizzabili dopo retry (%d): %s",
                    25, ", ".join(failed),
                )
            else:
                mocked["logger"].warning.assert_not_called()
