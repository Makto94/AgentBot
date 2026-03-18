"""S/R filter: swing levels, ATR, nearest support/resistance."""

import numpy as np
import pandas as pd


def find_swing_levels(df: pd.DataFrame, period: int = 7) -> list[float]:
    """Trova swing highs e swing lows su finestra di 2*period+1 candele."""
    levels: list[float] = []
    highs = df["High"].values
    lows = df["Low"].values
    for i in range(period, len(df) - period):
        if highs[i] == highs[i - period : i + period + 1].max():
            levels.append(float(highs[i]))
        if lows[i] == lows[i - period : i + period + 1].min():
            levels.append(float(lows[i]))
    return sorted(set(levels))


def calc_atr(df: pd.DataFrame, period: int = 14) -> float:
    """ATR a N periodi, ritorna l'ultimo valore."""
    high = df["High"].values
    low = df["Low"].values
    close = df["Close"].values
    tr = np.zeros(len(df))
    tr[0] = high[0] - low[0]
    for i in range(1, len(df)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )
    if len(tr) < period:
        return float(np.mean(tr))
    return float(np.mean(tr[-period:]))


def nearest_sr(price: float, levels: list[float]) -> tuple[float, float]:
    """Trova il livello S/R piu vicino e la distanza."""
    if not levels:
        return 0.0, float("inf")
    best = min(levels, key=lambda lvl: abs(price - lvl))
    return best, abs(price - best)
