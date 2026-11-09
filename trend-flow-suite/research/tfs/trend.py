"""Trend & Setups: reference implementation (Pine twin: pine/trend_setups.pine).

Modules (docs/04_trend_setups.md):
  trend score  calibrated multi-horizon trend statistic: three EMA crossovers of log price, each
               divided by its exact standard deviation under a random walk -> N(0,1) with no trend
  regime       Schmitt trigger on the trend score (enter +-1.0, exit +-0.3): up / neutral / down
  structure    ATR-reversal swings (confirmed on close), HH/HL/LH/LL, structure breaks
  AVWAP        volume-weighted average price anchored at the last confirmed swing low / high
  setups       S1 pullback continuation, S2 compression breakout, S3 confirmed reversal (long side),
               initial stop, chandelier trail, regime exit, R-multiples
Every stateful step mirrors the Pine script line for line; the tests check no look-ahead.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .core import atr1, ema1, slot_ewma_lagged, slot_index, smooth2, span_from_window

PAIRS = ((8, 24), (16, 48), (32, 96))   # Baz et al. (2015) crossover pairs, fixed (not tuned)
MAX_LOOK = 1999                         # look-back cap of the recomputation loops (Pine history buffer)


def _g(q: float) -> float:
    return q / (1.0 - q)


def pair_null_sd(s: int, l: int) -> float:
    """Std of EMA_s(ln P) - EMA_l(ln P) per unit of return volatility under a random walk."""
    a, b = 1 - 2 / (l + 1), 1 - 2 / (s + 1)
    return math.sqrt(_g(a * a) - 2 * _g(a * b) + _g(b * b))


def pair_null_cov(p, q) -> float:
    a, b = 1 - 2 / (p[1] + 1), 1 - 2 / (p[0] + 1)
    c, d = 1 - 2 / (q[1] + 1), 1 - 2 / (q[0] + 1)
    return _g(a * c) - _g(a * d) - _g(b * c) + _g(b * d)


def composite_null_sd(pairs=PAIRS) -> float:
    """Std of the average of the per-pair z-scores under a random walk."""
    sds = [pair_null_sd(*p) for p in pairs]
    tot = sum(pair_null_cov(p, q) / (sds[i] * sds[j])
              for i, p in enumerate(pairs) for j, q in enumerate(pairs))
    return math.sqrt(tot) / len(pairs)


@dataclass(frozen=True)
class TrendParams:
    sigma_span: int = 100        # EWMA span of squared returns (previous bars only)
    enter_thr: float = 1.0       # regime enters at |score| >= 1.0
    exit_thr: float = 0.3        # ...and falls back to neutral below 0.3
    strong_thr: float = 2.0
    base_window: int = 50        # SMA-equivalent window of the two-pole baseline
    atr_len: int = 14
    atr_long: int = 100
    swing_atr: float = 2.0       # swing confirmed when close reverses 2 ATR from the extreme
    norm_span_intraday: int = 20
    norm_span_daily: int = 50
    pull_ext: float = 0.25       # S1 arms when close <= baseline + 0.25 ATR in an uptrend
    pull_vol_max: float = 1.0    # S1 needs average relative volume <= 1.0 during the pullback
    comp_ratio: float = 0.8      # S2 compression: ATR14 <= 0.8 x ATR100 on the prior bar
    brk_len: int = 20            # S2 breakout above the prior 20-bar high
    brk_rvol: float = 1.5        # S2 needs relative volume >= 1.5
    s2_stop_len: int = 10
    rev_lookback: int = 20       # S3: downtrend and oversold within the last 20 bars
    rev_ext: float = -2.0
    stop_buf: float = 0.25       # stop buffer in ATR
    trail_atr: float = 3.0       # chandelier trail: highest high since entry - 3 ATR
    warmup: int = 200            # no entries before this many bars (filters still settling)


def _safe_div(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / b, np.nan)


def trend_score(logp, sigma_span: int = 100, pairs=PAIRS) -> np.ndarray:
    """Calibrated trend z-score. Pine twin: trendScore()."""
    lp = np.asarray(logp, dtype=float)
    r = np.r_[np.nan, np.diff(lp)]
    sig = np.sqrt(slot_ewma_lagged(r * r, np.zeros(len(lp), dtype=int), sigma_span))
    zs = [_safe_div(ema1(lp, s) - ema1(lp, l), sig * pair_null_sd(s, l)) for s, l in pairs]
    return np.mean(zs, axis=0) / composite_null_sd(pairs)


def regime(ts, enter: float, exit_: float) -> np.ndarray:
    """Schmitt trigger: +1 up, 0 neutral, -1 down. Pine twin: trendDir()."""
    d, out = 0, np.zeros(len(ts), dtype=int)
    for t, v in enumerate(np.asarray(ts, dtype=float)):
        if not np.isnan(v):
            if v >= enter:
                d = 1
            elif v <= -enter:
                d = -1
            elif d == 1 and v < exit_:
                d = 0
            elif d == -1 and v > -exit_:
                d = 0
        out[t] = d
    return out


def trend_setups(df: pd.DataFrame, intraday: bool = False, p: TrendParams = TrendParams(),
                 bench_close=None, htf_dir=None, use_rs: bool = True):
    """All Trend & Setups series plus the list of completed trades (long side).

    bench_close : benchmark close aligned to df.index (relative strength); None = no RS filter
    htf_dir     : context-timeframe regime aligned to df.index, already lagged (non-repainting)
    """
    o, h, l, c, v = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    tp = (h + l + c) / 3.0
    ts = trend_score(np.log(c), p.sigma_span)
    d = regime(ts, p.enter_thr, p.exit_thr)
    atr = atr1(h, l, c, p.atr_len)
    atr_l = atr1(h, l, c, p.atr_long)
    base = smooth2(c, span_from_window(p.base_window))
    ext = _safe_div(c - base, atr)
    slots = slot_index(df.index, intraday)
    span = p.norm_span_intraday if intraday else p.norm_span_daily
    rvol = _safe_div(v, slot_ewma_lagged(v, slots, span))

    if bench_close is not None:
        rs_ts = trend_score(np.log(c / np.asarray(bench_close, dtype=float)), p.sigma_span)
        rs_d = regime(rs_ts, p.enter_thr, p.exit_thr)
    else:
        rs_ts, rs_d = np.full(n, np.nan), np.zeros(n, dtype=int)
    hd = np.zeros(n, dtype=int) if htf_dir is None else np.asarray(htf_dir, dtype=int)

    hh_prev = pd.Series(h).rolling(p.brk_len).max().shift(1).to_numpy()
    ll_stop = pd.Series(l).rolling(p.s2_stop_len).min().to_numpy()
    comp_prev = np.r_[False, (atr[:-1] <= p.comp_ratio * atr_l[:-1])]
    min_ext = pd.Series(ext).rolling(p.rev_lookback).min().to_numpy()

    cols = {k: np.full(n, np.nan) for k in
            ("last_sh", "last_sl", "avwap_low", "avwap_high", "stop_level", "entry_px", "stop_px", "exit_r")}
    ints = {k: np.zeros(n, dtype=int) for k in ("entry", "exit_reason")}
    bools = {k: np.zeros(n, dtype=bool) for k in
             ("new_sh", "new_sl", "break_up", "break_dn", "in_trade")}
    labels = np.full(n, "", dtype=object)
    trades = []

    # zigzag state (Pine: var ...)
    zdir = 0
    hi_px, hi_bar, lo_px, lo_bar = h[0], 0, l[0], 0
    lo_since_hi, lo_since_hi_bar, hi_since_lo, hi_since_lo_bar = l[0], 0, h[0], 0
    last_sh = last_sl = prev_sh = prev_sl = np.nan
    last_sh_bar = last_sl_bar = -1
    avl_pv = avl_v = avh_pv = avh_v = 0.0
    # trade state
    in_trade, entry_px, stop_px, trail, hi_since, setup, entry_bar = False, np.nan, np.nan, np.nan, np.nan, 0, -1
    armed, pb_low, pb_vs, pb_vn = False, np.nan, 0.0, 0
    last_down_bar = None
    vz = np.nan_to_num(v)

    for t in range(n):
        sh_prev, sl_prev = last_sh, last_sl
        # ---- zigzag extremes
        if zdir >= 0:
            if h[t] > hi_px:
                hi_px, hi_bar, lo_since_hi, lo_since_hi_bar = h[t], t, l[t], t
            elif l[t] < lo_since_hi:
                lo_since_hi, lo_since_hi_bar = l[t], t
        if zdir <= 0:
            if l[t] < lo_px:
                lo_px, lo_bar, hi_since_lo, hi_since_lo_bar = l[t], t, h[t], t
            elif h[t] > hi_since_lo:
                hi_since_lo, hi_since_lo_bar = h[t], t
        new_sh = new_sl = False
        if not np.isnan(atr[t]):
            if zdir >= 0 and c[t] < hi_px - p.swing_atr * atr[t]:
                new_sh = True
                prev_sh, last_sh, last_sh_bar = last_sh, hi_px, hi_bar
                zdir = -1
                lo_px, lo_bar = lo_since_hi, lo_since_hi_bar
                m, mb = -np.inf, lo_bar
                for i in range(t, max(lo_bar, t - MAX_LOOK) - 1, -1):   # most recent bar wins ties
                    if h[i] > m:
                        m, mb = h[i], i
                hi_since_lo, hi_since_lo_bar = m, mb
            elif zdir <= 0 and c[t] > lo_px + p.swing_atr * atr[t]:
                new_sl = True
                prev_sl, last_sl, last_sl_bar = last_sl, lo_px, lo_bar
                zdir = 1
                hi_px, hi_bar = hi_since_lo, hi_since_lo_bar
                m, mb = np.inf, hi_bar
                for i in range(t, max(hi_bar, t - MAX_LOOK) - 1, -1):
                    if l[i] < m:
                        m, mb = l[i], i
                lo_since_hi, lo_since_hi_bar = m, mb
        if new_sh:
            labels[t] = "HH" if (not np.isnan(prev_sh) and last_sh > prev_sh) else ("LH" if not np.isnan(prev_sh) else "SH")
        if new_sl:
            labels[t] = "HL" if (not np.isnan(prev_sl) and last_sl > prev_sl) else ("LL" if not np.isnan(prev_sl) else "SL")

        # ---- anchored VWAPs (recomputed from the pivot when a swing is confirmed)
        if new_sl:
            a0 = max(last_sl_bar, t - MAX_LOOK)
            avl_pv = float(np.sum(tp[a0:t + 1] * vz[a0:t + 1]))
            avl_v = float(np.sum(vz[a0:t + 1]))
        elif last_sl_bar >= 0:
            avl_pv += tp[t] * vz[t]
            avl_v += vz[t]
        if new_sh:
            a0 = max(last_sh_bar, t - MAX_LOOK)
            avh_pv = float(np.sum(tp[a0:t + 1] * vz[a0:t + 1]))
            avh_v = float(np.sum(vz[a0:t + 1]))
        elif last_sh_bar >= 0:
            avh_pv += tp[t] * vz[t]
            avh_v += vz[t]

        # ---- structure breaks (levels as of the previous bar)
        brk_up = t > 0 and not np.isnan(sh_prev) and c[t] > sh_prev and c[t - 1] <= sh_prev
        brk_dn = t > 0 and not np.isnan(sl_prev) and c[t] < sl_prev and c[t - 1] >= sl_prev

        # ---- trade management: exits first
        if d[t] == -1:
            last_down_bar = t
        exited = False
        if in_trade:
            hi_since = max(hi_since, h[t])
            cand = hi_since - p.trail_atr * atr[t]
            if not np.isnan(cand):
                trail = cand if np.isnan(trail) else max(trail, cand)
            level = stop_px if np.isnan(trail) else max(stop_px, trail)
            reason = 0
            if c[t] < level:
                reason = 2 if (not np.isnan(trail) and trail > stop_px) else 1
            elif d[t] == -1:
                reason = 3
            if reason:
                r_mult = (c[t] - entry_px) / (entry_px - stop_init)
                ints["exit_reason"][t], cols["exit_r"][t] = reason, r_mult
                trades.append({"setup": setup, "entry_bar": entry_bar, "exit_bar": t,
                               "entry": entry_px, "stop": stop_init, "exit": c[t], "r": r_mult,
                               "bars": t - entry_bar, "reason": reason})
                in_trade, exited = False, True
            else:
                cols["stop_level"][t] = level

        # ---- entries (flat, not on an exit bar)
        ctx_ok = hd[t] >= 0 and (not use_rs or rs_d[t] >= 0)
        new_entry, stop = 0, np.nan
        if not in_trade and not exited and t >= p.warmup:
            if armed:                                           # S1 pullback continuation
                pb_low = min(pb_low, l[t])
                if not np.isnan(rvol[t]):
                    pb_vs += rvol[t]
                    pb_vn += 1
                if d[t] != 1 or (not np.isnan(sl_prev) and c[t] < sl_prev):
                    armed = False
                elif t > 0 and c[t] > h[t - 1]:
                    vol_ok = pb_vn == 0 or pb_vs / pb_vn <= p.pull_vol_max
                    if ctx_ok and vol_ok:
                        new_entry, stop = 1, pb_low - p.stop_buf * atr[t]
                    armed = False
            elif d[t] == 1 and not np.isnan(atr[t]) and c[t] <= base[t] + p.pull_ext * atr[t]:
                armed, pb_low = True, l[t]
                pb_vs, pb_vn = (rvol[t], 1) if not np.isnan(rvol[t]) else (0.0, 0)
            if (new_entry == 0 and d[t] >= 0 and ctx_ok and comp_prev[t]
                    and not np.isnan(hh_prev[t]) and c[t] > hh_prev[t]
                    and (np.isnan(rvol[t]) or rvol[t] >= p.brk_rvol)):   # S2 compression breakout
                new_entry, stop = 2, ll_stop[t] - p.stop_buf * atr[t]
            if (new_entry == 0 and brk_up and d[t] <= 0 and ts[t] > -p.exit_thr
                    and last_down_bar is not None and t - last_down_bar <= p.rev_lookback
                    and min_ext[t] <= p.rev_ext and not np.isnan(last_sl)):  # S3 confirmed reversal
                new_entry, stop = 3, last_sl - p.stop_buf * atr[t]
            if new_entry and not np.isnan(stop) and c[t] - stop > 0:
                in_trade, entry_px, stop_px, stop_init = True, c[t], stop, stop
                trail, hi_since, setup, entry_bar = np.nan, h[t], new_entry, t
                ints["entry"][t], cols["entry_px"][t], cols["stop_px"][t] = new_entry, c[t], stop
                cols["stop_level"][t] = stop
                armed = False
        if in_trade:
            armed = False

        cols["last_sh"][t], cols["last_sl"][t] = last_sh, last_sl
        cols["avwap_low"][t] = avl_pv / avl_v if avl_v > 0 else np.nan
        cols["avwap_high"][t] = avh_pv / avh_v if avh_v > 0 else np.nan
        bools["new_sh"][t], bools["new_sl"][t] = new_sh, new_sl
        bools["break_up"][t], bools["break_dn"][t] = brk_up, brk_dn
        bools["in_trade"][t] = in_trade

    out = pd.DataFrame({"ts": ts, "dir": d, "atr": atr, "atr_long": atr_l, "base": base, "ext": ext,
                        "rvol": rvol, "rs_ts": rs_ts, "rs_dir": rs_d, "swing_label": labels,
                        **cols, **ints, **bools}, index=df.index)
    out["bos_up"] = out["break_up"] & (out["dir"] == 1)
    out["choch_up"] = out["break_up"] & (out["dir"] <= 0)
    out["bos_dn"] = out["break_dn"] & (out["dir"] == -1)
    out["choch_dn"] = out["break_dn"] & (out["dir"] >= 0)
    out["avwap"] = np.where(out["dir"] >= 0, out["avwap_low"], out["avwap_high"])
    return out, pd.DataFrame(trades)


def weekly_context_dir(daily: pd.DataFrame, p: TrendParams = TrendParams()) -> np.ndarray:
    """Weekly regime mapped onto daily bars WITHOUT look-ahead: each day sees the regime of the
    last COMPLETED week (Pine: request.security(..., expr[1], lookahead_on))."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    wk = daily.resample("W-FRI").agg(agg).dropna()
    wd = pd.Series(regime(trend_score(np.log(wk["close"].to_numpy()), p.sigma_span),
                          p.enter_thr, p.exit_thr), index=wk.index)
    # a week's value becomes usable on the first trading day AFTER the week ends
    return wd.reindex(daily.index, method="ffill").shift(1).fillna(0).astype(int).to_numpy()
