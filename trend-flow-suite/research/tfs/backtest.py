"""Vectorised long/flat backtests for many strategy variants at once.

Timing convention (no look-ahead): a position decided with data up to the close of bar t
is held over bar t+1, i.e. strategy_return[t+1] = position[t] * market_return[t+1].
This equals trading at the close of the signal bar (market-on-close). Costs are charged
on every change of the held position, in basis points of notional.
"""
from __future__ import annotations

import numpy as np


def long_flat_returns(positions: np.ndarray, market_returns: np.ndarray,
                      cost_bps: float = 5.0) -> np.ndarray:
    """positions: T x N array of 0/1 decided at each close; market_returns: length-T array of
    close-to-close returns (r[t] = C[t]/C[t-1] - 1). Returns T x N strategy returns (float32)."""
    pos = np.asarray(positions, dtype=np.float32)
    if pos.ndim == 1:
        pos = pos[:, None]
    r = np.asarray(market_returns, dtype=np.float32)[:, None]
    held = np.vstack([np.zeros((1, pos.shape[1]), dtype=np.float32), pos[:-1]])
    prev_held = np.vstack([np.zeros((1, pos.shape[1]), dtype=np.float32), held[:-1]])
    turnover = np.abs(held - prev_held)
    return held * np.nan_to_num(r) - turnover * np.float32(cost_bps / 1e4)


def summary(strategy_returns: np.ndarray, periods_per_year: int = 252) -> dict:
    """Headline metrics for a single return series."""
    r = np.asarray(strategy_returns, dtype=float).ravel()
    eq = np.cumprod(1.0 + r)
    years = len(r) / periods_per_year
    sd = r.std(ddof=1)
    return {
        "cagr_pct": round(100 * (eq[-1] ** (1 / years) - 1), 2),
        "vol_pct": round(100 * sd * np.sqrt(periods_per_year), 2),
        "sharpe": round(float(r.mean() / sd * np.sqrt(periods_per_year)) if sd > 0 else 0.0, 3),
        "max_dd_pct": round(100 * float((eq / np.maximum.accumulate(eq) - 1).min()), 1),
    }
