"""Indicator primitives written to Pine Script's definitions, column-wise on [T, N] arrays.

Every research signal is built from these so that the Pine translation is mechanical and parity
can be checked bar for bar. Definitions follow the Pine v6 reference manual:

    ta.sma(src, n)      arithmetic mean of the last n values; na until n values exist
    ta.ema(src, n)      alpha = 2/(n+1); seeded with ta.sma(src, n) on the first bar it exists
    ta.rma(src, n)      alpha = 1/n;     seeded with ta.sma(src, n)
    ta.stdev(src, n)    population standard deviation (biased=true, the default)
    ta.highest/lowest   over the last n bars INCLUDING the current bar
    ta.tr(true)         max(h-l, |h-c[1]|, |l-c[1]|); h-l on the first bar
    ta.atr(n)           ta.rma(ta.tr(true), n)
    ta.rsi(src, n)      100 - 100/(1 + rma(up, n)/rma(down, n))
    ta.change(src, k)   src - src[k]
    ta.roc(src, k)      100 * (src - src[k]) / src[k]

NaN handling: a security's series starts at its first bar; functions return NaN until enough
bars exist. Holes inside a series (missing bars) are forward-filled by the caller (engine.prepare
gives `cf`); TradingView has no bar there either, so bar counts differ slightly around holes.
"""
from __future__ import annotations

import bottleneck as bn
import numpy as np


def shift(x: np.ndarray, k: int) -> np.ndarray:
    """x[k] in Pine notation: the value k bars ago."""
    if k == 0:
        return x
    if x.dtype == bool:                       # a boolean history is False before it exists
        out = np.zeros(x.shape, dtype=bool)
    else:
        out = np.full(x.shape, np.nan)
    out[k:] = x[:-k]
    return out


def sma(x: np.ndarray, n: int) -> np.ndarray:
    return bn.move_mean(x, window=n, min_count=n, axis=0)


def stdev(x: np.ndarray, n: int) -> np.ndarray:
    return bn.move_std(x, window=n, min_count=n, axis=0, ddof=0)


def highest(x: np.ndarray, n: int) -> np.ndarray:
    return bn.move_max(x, window=n, min_count=n, axis=0)


def lowest(x: np.ndarray, n: int) -> np.ndarray:
    return bn.move_min(x, window=n, min_count=n, axis=0)


def median(x: np.ndarray, n: int) -> np.ndarray:
    return bn.move_median(x, window=n, min_count=n, axis=0)


def _recursive(x: np.ndarray, n: int, alpha: float) -> np.ndarray:
    seed = sma(x, n)
    out = np.full(x.shape, np.nan)
    state = np.full(x.shape[1], np.nan)
    for t in range(x.shape[0]):
        xt = x[t]
        have = np.isfinite(state)
        ok = np.isfinite(xt)
        nxt = np.where(have & ok, alpha * xt + (1.0 - alpha) * state, state)
        start = ~have & np.isfinite(seed[t])
        state = np.where(start, seed[t], nxt)
        out[t] = state
    return out


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return _recursive(x, n, 2.0 / (n + 1.0))


def rma(x: np.ndarray, n: int) -> np.ndarray:
    return _recursive(x, n, 1.0 / n)


def true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    pc = shift(c, 1)
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    return np.where(np.isfinite(pc), tr, h - l)


def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int) -> np.ndarray:
    return rma(true_range(h, l, c), n)


def rsi(x: np.ndarray, n: int) -> np.ndarray:
    d = x - shift(x, 1)
    up = np.where(np.isfinite(d), np.maximum(d, 0.0), np.nan)
    dn = np.where(np.isfinite(d), np.maximum(-d, 0.0), np.nan)
    ru, rd = rma(up, n), rma(dn, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 100.0 - 100.0 / (1.0 + ru / rd)
    out = np.where(rd == 0, 100.0, out)
    return np.where(np.isfinite(ru) & np.isfinite(rd), out, np.nan)


def change(x: np.ndarray, k: int = 1) -> np.ndarray:
    return x - shift(x, k)


def roc(x: np.ndarray, k: int) -> np.ndarray:
    p = shift(x, k)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100.0 * (x - p) / p


def barssince(cond: np.ndarray) -> np.ndarray:
    """ta.barssince: bars since cond was last true (0 on the bar it is true); NaN before the first."""
    T = cond.shape[0]
    idx = np.where(cond, np.arange(T)[:, None], -1)
    last = np.maximum.accumulate(idx, axis=0)
    out = (np.arange(T)[:, None] - last).astype(float)
    out[last < 0] = np.nan
    return out


def rolling_sum(x: np.ndarray, n: int) -> np.ndarray:
    """math.sum(src, n)."""
    return bn.move_sum(x, window=n, min_count=n, axis=0)


def percentrank(x: np.ndarray, n: int) -> np.ndarray:
    """ta.percentrank(src, n): percent of the previous n values that are <= the current value."""
    out = np.full(x.shape, np.nan)
    T = x.shape[0]
    for t in range(n, T):
        w = x[t - n:t]
        cur = x[t]
        ok = np.isfinite(w).all(axis=0) & np.isfinite(cur)
        out[t] = np.where(ok, 100.0 * (w <= cur[None, :]).sum(axis=0) / n, np.nan)
    return out


def linreg_slope(x: np.ndarray, n: int) -> np.ndarray:
    """Slope of the least-squares line through the last n values (per bar), as in ta.linreg's fit."""
    k = np.arange(n, dtype=float)
    kbar = k.mean()
    den = ((k - kbar) ** 2).sum()
    # sum_j (k_j - kbar) * x[t-n+1+j]  =  sum_j k_j x_j - kbar * sum x
    s = bn.move_sum(x, window=n, min_count=n, axis=0)
    # weighted sum with weights 0..n-1 (oldest..newest) via cumulative trick
    out = np.full(x.shape, np.nan)
    cs = np.cumsum(np.nan_to_num(x), axis=0)
    ccs = np.cumsum(cs, axis=0)
    T = x.shape[0]
    for t in range(n - 1, T):
        # sum_{j=0}^{n-1} j*x[t-n+1+j] = (n-1)*cs[t] - (ccs[t-1] - ccs[t-n])   with care at edges
        a = t - n
        c_tm1 = ccs[t - 1] if t - 1 >= 0 else 0.0
        c_a = ccs[a] if a >= 0 else 0.0
        base = cs[a] if a >= 0 else 0.0
        # sum_{i=a+1}^{t} (i-a-1) x_i = sum_{i=a+1}^{t-1} (cs[t]-cs[i]) = (n-1)*cs[t] - (ccs[t-1]-ccs[a])
        wsum = (n - 1) * cs[t] - (c_tm1 - c_a)
        out[t] = (wsum - kbar * (cs[t] - base)) / den
    return np.where(np.isfinite(s), out, np.nan)


def median_tol(x: np.ndarray, n: int, min_count: int) -> np.ndarray:
    """Median of the last n rows that tolerates a few missing bars (at least min_count present).
    TradingView has no row for a day without a bar, so its 20-bar window is 20 real bars; this is
    the closest equivalent on a calendar grid."""
    return bn.move_median(x, window=n, min_count=min_count, axis=0)


def sma_tol(x: np.ndarray, n: int, min_count: int) -> np.ndarray:
    return bn.move_mean(x, window=n, min_count=min_count, axis=0)
