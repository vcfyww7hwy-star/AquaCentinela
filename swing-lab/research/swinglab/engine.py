"""Measurement engine. Everything here follows docs/00_protocol.md sections 4 and 5.

Conventions
-----------
- Arrays are [T, N]: dates down, securities across. A signal at row t uses data up to the close
  of t only. The first price the trader can get is the OPEN of t+1.
- fwd_ret_open(h): total return from the open of t+1 to the close of t+h (h >= 1), dividends
  included, exit at the last close if the security stops trading (with a delisting haircut when
  it stopped "for cause").
- Inference is by date: one signal-minus-control number per day, Newey-West standard errors.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .data import Panel


# ----------------------------------------------------------------------------- basic helpers
def ffill(x: np.ndarray) -> np.ndarray:
    """Forward-fill NaN down the time axis."""
    x = np.asarray(x)
    T = x.shape[0]
    idx = np.where(np.isfinite(x), np.arange(T)[:, None], 0)
    np.maximum.accumulate(idx, axis=0, out=idx)
    out = np.take_along_axis(x, idx, axis=0)
    return out


def lag(x: np.ndarray, k: int = 1) -> np.ndarray:
    """Value k rows earlier (k >= 0); NaN where there is none."""
    if k == 0:
        return x
    out = np.full_like(x, np.nan, dtype=float)
    out[k:] = x[:-k]
    return out


def lead(x: np.ndarray, k: int = 1) -> np.ndarray:
    out = np.full_like(x, np.nan, dtype=float)
    out[:-k] = x[k:]
    return out


@dataclass
class Prepared:
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray          # NaN where no (good) bar
    cf: np.ndarray         # close forward-filled from the first bar on
    v: np.ndarray
    ret: np.ndarray        # close-to-close price log return (NaN where no bar today or before)
    tri: np.ndarray        # total-return index (dividends reinvested), forward-filled
    last: np.ndarray       # [N] index of last bar, or -1
    first: np.ndarray      # [N] index of first bar
    cause: np.ndarray      # [N] bool: stopped trading "for cause"
    alive: np.ndarray      # [N] bool: still trading at the end of the panel


def prepare(p: Panel) -> Prepared:
    bad = np.asarray(p.bad) != 0
    def clean(x):
        y = np.asarray(x, dtype=np.float64).copy()
        y[bad] = np.nan
        return y
    o, h, l, c, v = (clean(getattr(p, k)) for k in ("o", "h", "l", "c", "v"))
    div = np.nan_to_num(np.asarray(p.div, dtype=np.float64))
    has = np.isfinite(c)
    T, N = c.shape
    any_bar = has.any(axis=0)
    first = np.where(any_bar, has.argmax(axis=0), -1)
    last = np.where(any_bar, T - 1 - has[::-1].argmax(axis=0), -1)
    cf = ffill(c)
    cf[np.arange(T)[:, None] < first[None, :]] = np.nan
    prev = lag(cf, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = np.where(has, np.log(c / prev), np.nan)
        gross = np.where(has & np.isfinite(prev), (c + div) / prev, 1.0)
    gross[~np.isfinite(gross)] = 1.0
    tri = np.cumprod(gross, axis=0)
    tri[np.arange(T)[:, None] < first[None, :]] = np.nan
    alive = last >= T - 4
    c_raw = np.asarray(p.c_raw, dtype=np.float64)
    cols = np.arange(N)
    lc = np.where(any_bar, c_raw[np.clip(last, 0, T - 1), cols], np.nan)
    back = np.clip(last - 60, 0, T - 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        r60 = cf[np.clip(last, 0, T - 1), cols] / cf[back, cols] - 1.0
    cause = (~alive) & ((lc < 2.0) | (r60 < -0.5))
    return Prepared(o, h, l, c, cf, v, ret, tri, last, first, cause, alive)


def fwd_ret_open(P: Prepared, h: int, haircut: float = -0.30) -> np.ndarray:
    """Total simple return from the open of t+1 to the close of t+h. NaN if no bar at t+1 or if
    t+h is beyond the panel."""
    T, N = P.c.shape
    out = np.full((T, N), np.nan)
    if h < 1 or T <= h:
        return out
    e = slice(1, T - h + 1)            # entry rows  (t+1)
    x = slice(h, T)                    # exit rows   (t+h)
    with np.errstate(divide="ignore", invalid="ignore"):
        g1 = P.c[e] / P.o[e]           # open -> close on the entry day (needs a real bar)
        g2 = P.tri[x] / P.tri[e]       # close of entry day -> close of exit day
        r = g1 * g2
    # delisting: the last bar falls inside the holding window before the planned exit
    t_idx = np.arange(0, T - h)[:, None]
    in_window = (P.last[None, :] >= t_idx + 1) & (P.last[None, :] < t_idx + h) & (~P.alive)[None, :]
    r = np.where(in_window & P.cause[None, :], r * (1.0 + haircut), r)
    out[:T - h] = r - 1.0
    return out


def fwd_ret_close(P: Prepared, h: int) -> np.ndarray:
    """Close of t to close of t+h, total return. Not obtainable from a bar-close alert; used only
    to measure how much of an effect sits in the overnight gap the trader cannot capture."""
    T, N = P.c.shape
    out = np.full((T, N), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        out[:T - h] = P.tri[h:] / P.tri[:T - h] - 1.0
    out[~np.isfinite(P.c)] = np.nan
    return out


def overnight_gap(P: Prepared) -> np.ndarray:
    """Close of t to open of t+1 (simple return)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return lead(P.o, 1) / P.cf - 1.0


# ----------------------------------------------------------------------------- rolling statistics
def roll_sum(x: np.ndarray, n: int, min_count: int | None = None) -> np.ndarray:
    import bottleneck as bn
    return bn.move_sum(x, window=n, min_count=min_count or n, axis=0)


def roll_mean(x: np.ndarray, n: int, min_count: int | None = None) -> np.ndarray:
    import bottleneck as bn
    return bn.move_mean(x, window=n, min_count=min_count or n, axis=0)


def roll_std(x: np.ndarray, n: int, min_count: int | None = None) -> np.ndarray:
    import bottleneck as bn
    return bn.move_std(x, window=n, min_count=min_count or n, axis=0, ddof=0)


def roll_max(x: np.ndarray, n: int, min_count: int | None = None) -> np.ndarray:
    import bottleneck as bn
    return bn.move_max(x, window=n, min_count=min_count or n, axis=0)


def roll_min(x: np.ndarray, n: int, min_count: int | None = None) -> np.ndarray:
    import bottleneck as bn
    return bn.move_min(x, window=n, min_count=min_count or n, axis=0)


def roll_median(x: np.ndarray, n: int, min_count: int | None = None) -> np.ndarray:
    import bottleneck as bn
    return bn.move_median(x, window=n, min_count=min_count or n, axis=0)


def ewma(x: np.ndarray, alpha: float) -> np.ndarray:
    """Pine-style recursive EMA down the time axis: y = alpha*x + (1-alpha)*y[1], seeded with the
    first finite value. NaN inputs leave the state unchanged (the previous value is carried)."""
    x = np.asarray(x, dtype=np.float64)
    out = np.full_like(x, np.nan)
    state = np.full(x.shape[1], np.nan)
    for t in range(x.shape[0]):
        xt = x[t]
        ok = np.isfinite(xt)
        seed = ok & ~np.isfinite(state)
        state = np.where(seed, xt, np.where(ok, alpha * xt + (1 - alpha) * state, state))
        out[t] = state
    return out


def vol_ewma(P: Prepared, span: int = 20, warm: int = 20, floor: float = 0.002) -> np.ndarray:
    """Daily volatility forecast known at the close of t: sqrt of an EMA of squared log returns.

    Robust to single shocks: after a warm-up of `warm` observations each squared return is capped
    at 25x the running estimate (5 sigma), so one earnings gap does not dominate for weeks.
    The running estimate used for the cap is floored at `floor`**2, otherwise a security whose
    first returns are zero would get a zero estimate that can never recover. NaN until `warm`
    observations exist. Computable in Pine with one var and ta-free arithmetic.
    """
    alpha = 2.0 / (span + 1)
    r2 = P.ret ** 2
    out = np.full_like(r2, np.nan)
    state = np.full(r2.shape[1], np.nan)
    cnt = np.zeros(r2.shape[1], dtype=np.int32)
    f2 = floor * floor
    for t in range(r2.shape[0]):
        x = r2[t]
        ok = np.isfinite(x)
        seed = ok & ~np.isfinite(state)
        cap = 25.0 * np.maximum(np.where(np.isfinite(state), state, 0.0), f2)
        xc = np.where(cnt >= warm, np.minimum(x, cap), x)
        state = np.where(seed, x, np.where(ok, alpha * xc + (1 - alpha) * state, state))
        cnt += ok
        out[t] = np.where(cnt >= warm, np.maximum(state, f2), np.nan)
    return np.sqrt(out)


def xs_rank(x: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Cross-sectional percentile rank in (0, 1] per row, among mask & finite. NaN elsewhere."""
    out = np.full(x.shape, np.nan)
    for t in range(x.shape[0]):
        m = mask[t] & np.isfinite(x[t])
        n = int(m.sum())
        if n < 5:
            continue
        v = x[t, m]
        order = v.argsort(kind="mergesort")
        rk = np.empty(n)
        rk[order] = (np.arange(n) + 1) / n
        out[t, m] = rk
    return out


# ----------------------------------------------------------------------------- inference by date
def nw_mean(x: np.ndarray, lags: int) -> tuple[float, float, int]:
    """(mean, t-statistic, n) of a daily series with Newey-West (Bartlett) standard errors."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 20:
        return (float("nan"), float("nan"), n)
    m = x.mean()
    e = x - m
    var = (e @ e) / n
    for k in range(1, min(lags, n - 1) + 1):
        w = 1.0 - k / (lags + 1.0)
        var += 2.0 * w * (e[k:] @ e[:-k]) / n
    se = np.sqrt(max(var, 1e-300) / n)
    return (float(m), float(m / se), n)


def day_means(out: np.ndarray, mask: np.ndarray, min_n: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Per-row mean of `out` over mask & finite, and the count."""
    m = mask & np.isfinite(out)
    cnt = m.sum(axis=1)
    s = np.where(m, out, 0.0).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = np.where(cnt >= min_n, s / cnt, np.nan)
    return mean, cnt


def spread_series(out: np.ndarray, sig: np.ndarray, ctrl: np.ndarray, min_sig: int = 1,
                  min_ctrl: int = 20) -> tuple[np.ndarray, np.ndarray]:
    """Daily (signal mean - control mean) and the number of signal names per day."""
    ms, ns = day_means(out, sig, min_sig)
    mc, _ = day_means(out, ctrl, min_ctrl)
    return ms - mc, ns


def summarize(d: np.ndarray, n_sig: np.ndarray, p: Panel, h: int, parts=("DEV", "VAL")) -> dict:
    """Mean daily spread (bp), Newey-West t, number of days and of signal-days, per partition."""
    res = {}
    for part in parts:
        r = p.rows(part)
        m, t, n = nw_mean(d[r], lags=max(2 * h, 1))
        res[part] = {"bp": None if not np.isfinite(m) else round(1e4 * m, 2),
                     "t": None if not np.isfinite(t) else round(t, 2),
                     "days": n, "signals": int(n_sig[r][np.isfinite(d[r])].sum())}
    return res
