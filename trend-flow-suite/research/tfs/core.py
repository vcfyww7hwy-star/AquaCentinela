"""Shared numerical primitives, written to match their Pine v6 twins exactly.

Every function here has a counterpart in the Pine scripts with the same seeding and NaN
handling, so Python and TradingView agree bar for bar (see research/tools/parity_check.py).

Conventions (identical in Pine):
- Recursive filters are seeded with the first non-NaN input, not with an SMA.
- A NaN input after seeding leaves the filter state unchanged ("hold").
- Nothing uses data from bars after the current one.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _recursive(x, alpha: float) -> np.ndarray:
    """e[t] = alpha*x[t] + (1-alpha)*e[t-1], seeded with the first non-NaN x; holds on NaN.
    Works on 1-D arrays or column-wise on 2-D arrays."""
    arr = np.asarray(x, dtype=float)
    squeeze = arr.ndim == 1
    X = arr[:, None] if squeeze else arr
    out = np.empty_like(X)
    e = np.full(X.shape[1], np.nan)
    for t in range(X.shape[0]):
        v = X[t]
        e = np.where(np.isnan(e), v, np.where(np.isnan(v), e, alpha * v + (1.0 - alpha) * e))
        out[t] = e
    return out[:, 0] if squeeze else out


def ema1(x, n: int) -> np.ndarray:
    """EMA with alpha = 2/(n+1). Pine twin: ema1()."""
    return _recursive(x, 2.0 / (n + 1.0))


def rma1(x, n: int) -> np.ndarray:
    """Wilder's moving average, alpha = 1/n. Pine twin: rma1()."""
    return _recursive(x, 1.0 / n)


def smooth2(x, n: int) -> np.ndarray:
    """Two-pole smoother: EMA of an EMA (span n each). Mean lag n-1 bars, i.e. the same mean
    lag as an SMA of 2n-1 bars, with far fewer whipsaws (docs/01_vfi_critique.md)."""
    return ema1(ema1(x, n), n)


def span_from_window(window: int) -> int:
    """Two-pole span with the same mean lag as an SMA(window): n = floor((window+1)/2)."""
    return (int(window) + 1) // 2


def phi(x) -> np.ndarray:
    """Standard normal CDF via Abramowitz & Stegun 7.1.26 (|error| < 1.5e-7). Pine twin: phi()."""
    x = np.asarray(x, dtype=float)
    z = np.abs(x) / np.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * z)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
                 - 0.284496736) * t + 0.254829592) * t * np.exp(-z * z)
    return np.where(x >= 0, 0.5 * (1.0 + y), 0.5 * (1.0 - y))


def true_range(high, low, close) -> np.ndarray:
    h, l, c = (np.asarray(a, dtype=float) for a in (high, low, close))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    return tr


def atr1(high, low, close, n: int = 14) -> np.ndarray:
    return rma1(true_range(high, low, close), n)


def slot_index(index: pd.DatetimeIndex, intraday: bool) -> np.ndarray:
    """Bar position within the trading session (0 = first bar). All zeros for D/W/M charts.
    Pine twin: counter reset by session.isfirstbar."""
    n = len(index)
    if not intraday:
        return np.zeros(n, dtype=int)
    days = pd.DatetimeIndex(index).normalize()
    new = np.r_[True, days[1:] != days[:-1]]
    slots = np.zeros(n, dtype=int)
    c = -1
    for i in range(n):
        c = 0 if new[i] else c + 1
        slots[i] = c
    return slots


def slot_ewma_lagged(x, slots, span: int) -> np.ndarray:
    """Per-slot EWMA (alpha = 2/(span+1)), returning for each bar the slot's value BEFORE this
    bar is included (no self-inclusion). With all slots = 0 this is a lagged plain EWMA.
    Pine twin: slotEwmaLagged()."""
    a = 2.0 / (span + 1.0)
    x = np.asarray(x, dtype=float)
    state: dict[int, float] = {}
    out = np.full(len(x), np.nan)
    for t in range(len(x)):
        s = int(slots[t])
        prev = state.get(s, np.nan)
        out[t] = prev
        v = x[t]
        if not np.isnan(v):
            state[s] = v if np.isnan(prev) else a * v + (1.0 - a) * prev
    return out


def rolling_std_pop(x, n: int) -> np.ndarray:
    """Population standard deviation over n bars (Pine ta.stdev, biased=true)."""
    return pd.Series(np.asarray(x, dtype=float)).rolling(n).std(ddof=0).to_numpy()


def _pivot(src, left: int, right: int, high: bool) -> np.ndarray:
    x = np.asarray(src, dtype=float)
    n = len(x)
    out = np.full(n, np.nan)
    for t in range(left + right, n):
        p = x[t - right]
        if np.isnan(p):
            continue
        nb = np.r_[x[t - right - left: t - right], x[t - right + 1: t + 1]]
        if (np.all(p > nb) if high else np.all(p < nb)):
            out[t] = p
    return out


def pivot_high(src, left: int, right: int) -> np.ndarray:
    """Confirmed pivot high, reported on the confirmation bar (`right` bars after the pivot),
    NaN elsewhere. Strictly higher than the `left` bars before and the `right` bars after.
    Pine twin: pivotHi()."""
    return _pivot(src, left, right, True)


def pivot_low(src, left: int, right: int) -> np.ndarray:
    return _pivot(src, left, right, False)
