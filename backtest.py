"""Backtest / parameter sweep offline per la strategia breakout + S/R.

Standalone: importa solo le funzioni pure di sr_filter e rigioca la strategia su
dati storici yfinance. Approssima la conferma dual-timeframe live (1h AND 4h) e
valuta ogni segnale col forward-return a un orizzonte fisso, scrivendo un CSV con
il ranking delle combinazioni di parametri.

NON è una garanzia di edge reale — solo ranking RELATIVO tra parametri.
Volutamente indipendente da config.py (che all'import scarica ~2800 ticker).

Uso:
    python backtest.py                 # campione di default, sweep di default
    python backtest.py AAPL MSFT NVDA  # ticker specifici
"""

import csv
import os
import sys
from itertools import product

import pandas as pd
import yfinance as yf

from sr_filter import calc_atr, find_swing_levels, nearest_sr

DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "JPM"]
HORIZON_BARS = 6  # candele 4h su cui misurare l'esito forward
SR_PERIOD = 7
PCT_GRID = [0.003, 0.005, 0.008, 0.012]
SR_TOL_GRID = [0.0, 0.25, 0.5]  # 0.0 = filtro S/R disattivato
OUTPUT_CSV = os.environ.get("BACKTEST_OUTPUT", "backtest_results.csv")


def resample_to_4h(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.resample("4h")
        .agg({"Open": "first", "High": "max", "Low": "min",
              "Close": "last", "Volume": "sum"})
        .dropna()
    )


def _download(tickers: list[str], period: str = "60d") -> dict[str, pd.DataFrame]:
    data = yf.download(tickers, period=period, interval="1h", progress=False,
                       auto_adjust=True, group_by="ticker", threads=True)
    out: dict[str, pd.DataFrame] = {}
    if data.empty:
        return out
    if len(tickers) == 1:
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        out[tickers[0]] = data.dropna(how="all")
    else:
        for t in tickers:
            try:
                df = data[t].dropna(how="all")
                if not df.empty:
                    out[t] = df
            except (KeyError, TypeError):
                pass
    return out


def _breakout(prev: pd.Series, last_close: float, pct_threshold: float) -> str | None:
    if last_close > prev["High"]:
        if (last_close - prev["High"]) / prev["High"] >= pct_threshold:
            return "RIALZISTA"
    elif last_close < prev["Low"]:
        if (prev["Low"] - last_close) / prev["Low"] >= pct_threshold:
            return "RIBASSISTA"
    return None


def _replay(df_4h: pd.DataFrame, df_1h: pd.DataFrame, pct: float, sr_tol: float):
    """Genera (signal_type, entry, forward_return) per ogni segnale storico."""
    results = []
    for i in range(SR_PERIOD * 2 + 2, len(df_4h) - HORIZON_BARS):
        prev4 = df_4h.iloc[i - 1]
        cur4 = df_4h.iloc[i]
        sig4 = _breakout(prev4, float(cur4["Close"]), pct)
        if sig4 is None:
            continue

        # Conferma 1h: bar 1h che chiude piu vicino al close del bar 4h.
        ts = df_4h.index[i]
        df_1h_upto = df_1h[df_1h.index <= ts]
        if len(df_1h_upto) < 2:
            continue
        sig1 = _breakout(df_1h_upto.iloc[-2], float(df_1h_upto.iloc[-1]["Close"]), pct)
        if sig1 != sig4:
            continue

        # Filtro S/R sul 4h fino a i (no lookahead).
        if sr_tol > 0:
            window = df_4h.iloc[:i]
            levels = find_swing_levels(window, period=SR_PERIOD)
            atr = calc_atr(window, period=14)
            ref = float(prev4["High"]) if sig4 == "RIALZISTA" else float(prev4["Low"])
            _, dist = nearest_sr(ref, levels)
            if not (levels and atr > 0 and dist <= sr_tol * atr):
                continue

        entry = float(cur4["Close"])
        fwd_close = float(df_4h.iloc[i + HORIZON_BARS]["Close"])
        direction = 1.0 if sig4 == "RIALZISTA" else -1.0
        results.append((sig4, entry, direction * (fwd_close - entry) / entry))
    return results


def run(tickers: list[str]) -> None:
    print(f"Scarico {len(tickers)} ticker (1h, 60d)...")
    frames = _download(tickers)
    print(f"Dati disponibili per {len(frames)} ticker.")

    rows = []
    for pct, sr_tol in product(PCT_GRID, SR_TOL_GRID):
        returns = []
        for df_1h in frames.values():
            df_4h = resample_to_4h(df_1h)
            if len(df_4h) < SR_PERIOD * 2 + HORIZON_BARS + 4:
                continue
            for _, _, ret in _replay(df_4h, df_1h, pct, sr_tol):
                returns.append(ret)
        n = len(returns)
        if n == 0:
            rows.append((pct, sr_tol, 0, 0.0, 0.0))
            continue
        wins = sum(1 for r in returns if r > 0)
        rows.append((pct, sr_tol, n, wins / n, sum(returns) / n))

    rows.sort(key=lambda r: r[4], reverse=True)
    out_path = OUTPUT_CSV
    try:
        fh = open(out_path, "w", newline="")
    except PermissionError:
        out_path = os.path.join("/tmp", os.path.basename(OUTPUT_CSV))
        fh = open(out_path, "w", newline="")
    with fh:
        w = csv.writer(fh)
        w.writerow(["pct_threshold", "sr_tolerance", "signals", "win_rate", "avg_return"])
        w.writerows(rows)

    print(f"\nRisultati ({HORIZON_BARS}-bar forward), ordinati per avg_return:")
    print(f"{'pct':>6} {'sr_tol':>7} {'signals':>8} {'win_rate':>9} {'avg_ret':>9}")
    for pct, sr_tol, n, wr, avg in rows:
        print(f"{pct:>6.3f} {sr_tol:>7.2f} {n:>8} {wr:>9.1%} {avg:>9.3%}")
    print(f"\nCSV scritto: {out_path}")


if __name__ == "__main__":
    run(sys.argv[1:] or DEFAULT_TICKERS)
