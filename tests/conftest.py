"""Fixture di import: bot.py a import-time costruisce l'universo stock via
scraping web (config.STOCKS = get_all_stocks()) e apre il file di log.
Stubbiamo il modulo stocks e le env necessarie PRIMA di importare bot."""

import os
import sys
import types

os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("LOG_FILE", "/tmp/test_alerts.log")

_fake_stocks = types.ModuleType("stocks")
_fake_stocks.get_all_stocks = lambda: ["AAA", "BBB", "CCC", "DDD"]
sys.modules.setdefault("stocks", _fake_stocks)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
