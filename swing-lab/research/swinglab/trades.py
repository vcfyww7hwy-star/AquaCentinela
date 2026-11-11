"""Trade simulator for entry/stop/exit rules (protocol section 5).

One position per security at a time. A signal at the close of t is entered at the OPEN of t+1.
Inside each later bar the order of checks is deliberately pessimistic:

    1. gap:    if the bar opens at or below the stop  -> exit at the open (gap-through)
    2. stop:   if the low touches the stop            -> exit at the stop
    3. target: if the high reaches the target         -> exit at the target (open if it gaps above)
    4. time:   after `max_hold` bars                  -> exit at that bar's close
    5. signal: if exit_sig is true at the close       -> exit at the NEXT bar's open
    then the trailing stop is raised for the next bar (never lowered).

On the entry bar only checks 2-5 apply (the fill is the open). Stop first, target second, when both
are touched in one bar. A position still open when the security stops trading exits at the last
close, with a haircut if it stopped "for cause". Costs are charged per side, plus an extra charge
on stop fills.

Returns one row per trade: col, entry row, exit row, net return, R multiple (net return divided by
the initial risk fraction), MAE and MFE in R, bars held, exit reason.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

from . import engine as E

REASONS = {0: "stop", 1: "gap_stop", 2: "target", 3: "time", 4: "signal", 5: "delist", 6: "end_of_sample"}


@njit(cache=True)
def _sim(o, h, l, c, div, atr, sig, exit_sig, last, cause, stop_k, trail_k, target_r, max_hold,
         cost, stop_extra, haircut, row_lo, row_hi):
    T, N = c.shape
    cap = 64
    out = np.empty((cap, 9))
    n_out = 0
    for n in range(N):
        t = row_lo
        while t < row_hi:
            if not sig[t, n] or t + 1 >= T or np.isnan(o[t + 1, n]) or np.isnan(atr[t, n]) or atr[t, n] <= 0:
                t += 1
                continue
            e = t + 1
            entry = o[e, n]
            risk = stop_k * atr[t, n]
            if risk <= 0:
                t += 1
                continue
            if risk >= entry:          # a stop at or below zero means "no stop": R is then the plain return
                risk = entry
                stop = -1.0
            else:
                stop = entry - risk
            target = entry + target_r * risk if target_r > 0 else np.inf
            hi_close = entry
            mae, mfe = 0.0, 0.0
            divs = 0.0
            exit_px, reason, x = np.nan, -1, e
            pending_signal_exit = False
            d = e
            while True:
                if d > last[n] or d >= T:
                    # security stopped trading (or the panel ended) while in the position
                    x = min(last[n], T - 1)
                    exit_px = c[x, n] if not np.isnan(c[x, n]) else entry
                    if last[n] < T - 4:
                        reason = 5
                        if cause[n]:
                            exit_px *= (1.0 + haircut)
                    else:
                        reason = 6
                    break
                if np.isnan(c[d, n]):            # hole in the data: carry the position
                    d += 1
                    continue
                if d > e:
                    divs += div[d, n]
                    if pending_signal_exit:
                        exit_px, reason, x = o[d, n], 4, d
                        break
                    if o[d, n] <= stop:
                        exit_px, reason, x = o[d, n], 1, d
                        break
                lo_r = (l[d, n] - entry) / risk
                hi_r = (h[d, n] - entry) / risk
                if l[d, n] <= stop:
                    mae = min(mae, (stop - entry) / risk)
                    exit_px, reason, x = stop, 0, d
                    break
                mae = min(mae, lo_r)
                if h[d, n] >= target:
                    px = max(target, o[d, n]) if d > e else target
                    mfe = max(mfe, (px - entry) / risk)
                    exit_px, reason, x = px, 2, d
                    break
                mfe = max(mfe, hi_r)
                if max_hold > 0 and d - e + 1 >= max_hold:
                    exit_px, reason, x = c[d, n], 3, d
                    break
                if exit_sig[d, n]:
                    pending_signal_exit = True
                if trail_k > 0 and not np.isnan(atr[d, n]):
                    hi_close = max(hi_close, c[d, n])
                    stop = max(stop, hi_close - trail_k * atr[d, n])
                d += 1
            gross = (exit_px + divs) / entry - 1.0
            net = gross - 2.0 * cost - (stop_extra if (reason == 0 or reason == 1) else 0.0)
            if n_out == cap:
                cap *= 2
                new = np.empty((cap, 9))
                new[:n_out] = out[:n_out]
                out = new
            out[n_out, 0] = n
            out[n_out, 1] = e
            out[n_out, 2] = x
            out[n_out, 3] = net
            out[n_out, 4] = net / (risk / entry)
            out[n_out, 5] = mae
            out[n_out, 6] = mfe
            out[n_out, 7] = x - e + 1
            out[n_out, 8] = reason
            n_out += 1
            t = x + 1 if x >= t + 1 else t + 1
    return out[:n_out]


def simulate(P: E.Prepared, sig: np.ndarray, atr: np.ndarray, *, rows: np.ndarray, stop_k: float = 2.0,
             trail_k: float = 0.0, target_r: float = 0.0, max_hold: int = 10,
             exit_sig: np.ndarray | None = None, cost_bp: float = 5.0, stop_extra_bp: float = 10.0,
             haircut: float = -0.30) -> pd.DataFrame:
    """Simulate. `rows` (bool over dates) limits ENTRIES to a sample; exits may run past its end
    only by the holding period, and trades whose exit falls outside `rows` are dropped so that no
    out-of-sample price is read."""
    r = np.flatnonzero(rows)
    row_lo, row_hi = int(r[0]), int(r[-1]) + 1
    ex = np.zeros(sig.shape, dtype=np.bool_) if exit_sig is None else exit_sig.astype(np.bool_)
    res = _sim(P.o, P.h, P.l, P.c, np.nan_to_num(_div_of(P)), atr, sig.astype(np.bool_), ex,
               P.last.astype(np.int64), P.cause.astype(np.bool_), float(stop_k), float(trail_k),
               float(target_r), int(max_hold), cost_bp / 1e4, stop_extra_bp / 1e4, float(haircut), row_lo, row_hi)
    df = pd.DataFrame(res, columns=["col", "entry", "exit", "ret", "R", "mae", "mfe", "bars", "reason"])
    for k in ("col", "entry", "exit", "bars", "reason"):
        df[k] = df[k].astype(int)
    df = df[(df["exit"] < row_hi) & (df["reason"] != 6)].reset_index(drop=True)
    df["reason"] = df["reason"].map(REASONS)
    return df


def _div_of(P: E.Prepared) -> np.ndarray:
    """Dividend per share on each bar, recovered from the total-return index."""
    prev = E.lag(P.cf, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        g = P.tri / E.lag(P.tri, 1)
        d = g * prev - P.cf
    return np.where(np.isfinite(d) & (d > 1e-9), d, 0.0)


def summarize(trades: pd.DataFrame, n_dates: int) -> dict:
    """Mean net return (bp) and mean R with t-statistics clustered by ENTRY date."""
    if len(trades) < 30:
        return {"trades": int(len(trades))}
    by_day = trades.groupby("entry")
    daily_ret = np.full(n_dates, np.nan)
    daily_r = np.full(n_dates, np.nan)
    cnt = np.zeros(n_dates)
    idx = by_day["ret"].sum().index.to_numpy()
    daily_ret[idx] = by_day["ret"].sum().to_numpy()
    daily_r[idx] = by_day["R"].sum().to_numpy()
    cnt[idx] = by_day.size().to_numpy()
    span = slice(idx.min(), idx.max() + 1)
    scale = cnt[span].mean()
    lags = int(max(2 * trades["bars"].median(), 1))
    m_ret, t_ret, _ = E.nw_mean(np.nan_to_num(daily_ret[span]) / scale, lags)
    m_r, t_r, _ = E.nw_mean(np.nan_to_num(daily_r[span]) / scale, lags)
    return {
        "trades": int(len(trades)), "ret_bp": round(1e4 * trades["ret"].mean(), 1), "ret_t": round(t_ret, 2),
        "R": round(trades["R"].mean(), 3), "R_t": round(t_r, 2), "win": round(float((trades["ret"] > 0).mean()), 3),
        "bars": round(float(trades["bars"].mean()), 1),
        "worst_R": round(float(trades["R"].min()), 1),
        "share_below_-1.5R": round(float((trades["R"] < -1.5).mean()), 4),
        "exit_mix": {k: round(float(v), 3) for k, v in trades["reason"].value_counts(normalize=True).items()},
    }


def placebo_signals(sig: np.ndarray, uni: np.ndarray, seed: int) -> np.ndarray:
    """Random entries matched to the real ones by DATE and count: on each day as many names as the
    signal picked, drawn at random from the universe names the signal did not pick."""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(sig, dtype=bool)
    k = (sig & uni).sum(axis=1)
    for t in np.flatnonzero(k):
        pool = np.flatnonzero(uni[t] & ~sig[t])
        if len(pool) == 0:
            continue
        pick = rng.choice(pool, size=min(int(k[t]), len(pool)), replace=False)
        out[t, pick] = True
    return out
