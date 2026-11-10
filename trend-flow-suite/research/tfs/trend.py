"""Trend & Setups v2: reference implementation (Pine twin: pine/trend_setups.pine).

Modules (docs/04_trend_setups.md):
  trend score  calibrated multi-horizon trend statistic: three EMA crossovers of log price, each
               divided by its exact standard deviation under a random walk -> N(0,1) with no trend.
               Volatility is a winsorised EWMA, so one earnings gap cannot distort it for months.
  regime       Schmitt trigger on the trend score (enter +-1.0, exit +-0.3): up / neutral / down
  context      the same regime on a higher timeframe, on the benchmark (market) and on the
               stock/benchmark ratio (relative strength)
  structure    ATR-reversal swings (confirmed on close), HH/HL/LH/LL, structure breaks
  AVWAP        volume-weighted average price anchored at the last confirmed swing low / high
  setups       detected on every bar, independently of any open position:
               D  dip in a long-term uptrend (default; docs/06_validation_lite.md)
               B  compression breakout, R confirmed reversal (off by default: no edge in tests)
               The v1 pullback rules ("swing", "baseline") are kept for research only.
  trades       one managed position at a time: intrabar stop, trailing exit, optional time exit,
               exit when the trend that justified the trade turns down, R-multiples
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
PB_LOOK = 199                           # look-back cap when averaging relative volume over a pullback


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
    # trend engine
    sigma_span: int = 100        # EWMA span of squared returns (previous bars only)
    sigma_clip: float = 3.0      # winsorise squared returns at (clip x sigma)^2; 0 = off
    enter_thr: float = 1.0       # regime enters at |score| >= 1.0
    exit_thr: float = 0.3        # ...and falls back to neutral below 0.3
    strong_thr: float = 2.0
    # structure and levels
    base_window: int = 50        # SMA-equivalent window of the two-pole baseline
    atr_len: int = 14
    atr_long: int = 100
    swing_atr: float = 2.0       # swing confirmed when close reverses 2 ATR from the extreme
    norm_span_intraday: int = 20
    norm_span_daily: int = 50
    # setups (ids: 1 = dip / pullback, 2 = breakout, 3 = reversal)
    use_s1: bool = True
    use_s2: bool = False         # off by default: no edge in E05/E08
    use_s3: bool = False         # off by default: negative in E08
    s1_mode: str = "dip"         # "dip": context regime up and the dip_len-bar return <= dip_z sigma,
                                 #        first bar of the dip; stop = close - dip_stop_atr ATR
                                 # research only -- "swing": first close above the prior high after a
                                 #        confirmed swing high; "baseline": v1 rule near the baseline
    dip_len: int = 5
    dip_z: float = -1.5
    dip_stop_atr: float = 2.0
    pull_ext: float = 0.25       # baseline mode only
    use_pull_vol: bool = False   # S1 needs average relative volume <= pull_vol_max in the pullback
    pull_vol_max: float = 1.0
    comp_ratio: float = 0.8      # S2 compression: ATR14 <= 0.8 x ATR100 on the prior bar
    brk_len: int = 20            # S2 breakout above the prior 20-bar high
    brk_rvol: float = 1.5        # S2 needs relative volume >= 1.5
    s2_stop_len: int = 10
    rev_lookback: int = 20       # S3: downtrend and oversold within the last 20 bars
    rev_ext: float = -2.0
    # optional filters for setups 1 and 2; all off by default (no reliable effect in E05/E08).
    # The dip setup always requires the context regime to be UP; that is part of its definition.
    use_ctx: bool = False        # higher-timeframe regime not down
    use_rs: bool = False         # relative strength vs benchmark not down
    use_mkt: bool = False        # benchmark's own regime not down
    # risk
    stop_buf: float = 0.25       # stop buffer in ATR
    min_stop_atr: float = 1.0    # the initial stop is never closer than this many ATR
    exit_mode: str = "chandelier"  # "chandelier": highest high since entry - trail_atr ATR;
                                   # "structure": last confirmed swing low - stop_buf ATR
    trail_atr: float = 3.0
    stop_mode: str = "intrabar"  # "intrabar": stop order (fills at the stop, or the open on a gap);
                                 # "close": exit at the close of a bar that closes below the stop
    max_bars: int = 0            # time exit: close the trade after this many bars; 0 = off
    tick: float = 0.0            # round stops to this tick size; 0 = no rounding
    warmup: int = 200            # no signals before this many bars (filters still settling)


def _safe_div(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / b, np.nan)


def _round_tick(x: float, tick: float) -> float:
    return x if (tick <= 0 or np.isnan(x)) else round(x / tick) * tick


def robust_var_lagged(r, span: int, clip: float) -> np.ndarray:
    """EWMA variance of returns, value BEFORE the current bar is included. After `span`
    observations each squared return is capped at (clip x current sigma)^2, so a single gap
    moves the estimate by a bounded amount. Pine twin: robustVarLagged()."""
    a = 2.0 / (span + 1.0)
    x = np.asarray(r, dtype=float)
    out = np.full(len(x), np.nan)
    v, n = np.nan, 0
    for t in range(len(x)):
        out[t] = v
        xt = x[t]
        if not np.isnan(xt):
            r2 = xt * xt
            if np.isnan(v) or v <= 0:
                v = r2
            elif n < span or clip <= 0:
                v = a * r2 + (1.0 - a) * v
            else:
                v = a * min(r2, clip * clip * v) + (1.0 - a) * v
            n += 1
    return out


def trend_score(logp, sigma_span: int = 100, clip: float = 3.0, pairs=PAIRS) -> np.ndarray:
    """Calibrated trend z-score. Pine twin: trendScore()."""
    lp = np.asarray(logp, dtype=float)
    r = np.r_[np.nan, np.diff(lp)]
    sig = np.sqrt(robust_var_lagged(r, sigma_span, clip))
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


def simulate_trades(o, h, l, c, atr, d, last_sl, sig, stop, p: TrendParams, d_dip=None):
    """One managed long position at a time. `sig[t]` > 0 with `stop[t]` proposes an entry at the
    close of bar t. Returns per-bar arrays and the list of completed trades.
    A trade is closed when the trend that justified it turns down: the regime `d` for setups 2
    and 3, and `d_dip` (the context regime) for setup 1 when it is given.
    Pine twin: the "Trade engine" block."""
    n = len(c)
    stop_level = np.full(n, np.nan)
    entry = np.zeros(n, dtype=int)
    exit_reason = np.zeros(n, dtype=int)
    exit_r = np.full(n, np.nan)
    exit_px = np.full(n, np.nan)
    in_trade_arr = np.zeros(n, dtype=bool)
    trades = []
    in_trade = False
    entry_px = stop_init = active = hi_since = np.nan
    setup, entry_bar = 0, -1
    intrabar = p.stop_mode == "intrabar"
    for t in range(n):
        exited = False
        if in_trade:
            reason, px = 0, np.nan
            if intrabar and l[t] <= active:
                reason = 2 if active > stop_init else 1
                px = min(o[t], active)                      # gap through the stop fills at the open
            else:
                hi_since = max(hi_since, h[t])
                if p.exit_mode == "structure":
                    cand = last_sl[t] - p.stop_buf * atr[t]
                else:
                    cand = hi_since - p.trail_atr * atr[t]
                level = active
                if not np.isnan(cand):
                    level = max(level, _round_tick(cand, p.tick))
                if (not intrabar) and c[t] < level:
                    reason, px = (2 if level > stop_init else 1), c[t]
                elif (d_dip[t] if (setup == 1 and d_dip is not None) else d[t]) == -1:
                    reason, px = 3, c[t]
                elif p.max_bars > 0 and t - entry_bar >= p.max_bars:
                    reason, px = 4, c[t]
                else:
                    active = level
                    stop_level[t] = level
            if reason:
                r_mult = (px - entry_px) / (entry_px - stop_init)
                exit_reason[t], exit_r[t], exit_px[t] = reason, r_mult, px
                trades.append({"setup": setup, "entry_bar": entry_bar, "exit_bar": t,
                               "entry": entry_px, "stop": stop_init, "exit": px, "r": r_mult,
                               "bars": t - entry_bar, "reason": reason})
                in_trade, exited = False, True
        if not in_trade and not exited and sig[t] > 0:
            in_trade, entry_px, stop_init, active = True, c[t], stop[t], stop[t]
            hi_since, setup, entry_bar = h[t], int(sig[t]), t
            entry[t] = setup
            stop_level[t] = active
        in_trade_arr[t] = in_trade
    return {"stop_level": stop_level, "entry": entry, "exit_reason": exit_reason, "exit_r": exit_r,
            "exit_px": exit_px, "in_trade": in_trade_arr}, trades


def trend_setups(df: pd.DataFrame, intraday: bool = False, p: TrendParams = TrendParams(),
                 bench_close=None, htf_dir=None):
    """All Trend & Setups series plus the list of completed trades (long side).

    bench_close : benchmark close aligned to df.index (market regime and relative strength);
                  None = both filters pass
    htf_dir     : context-timeframe regime aligned to df.index, already lagged (non-repainting);
                  None = filter passes
    """
    o, h, l, c, v = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    tp = (h + l + c) / 3.0
    ts = trend_score(np.log(c), p.sigma_span, p.sigma_clip)
    d = regime(ts, p.enter_thr, p.exit_thr)
    atr = atr1(h, l, c, p.atr_len)
    atr_l = atr1(h, l, c, p.atr_long)
    base = smooth2(c, span_from_window(p.base_window))
    ext = _safe_div(c - base, atr)
    slots = slot_index(df.index, intraday)
    span = p.norm_span_intraday if intraday else p.norm_span_daily
    rvol = _safe_div(v, slot_ewma_lagged(v, slots, span))

    if bench_close is not None:
        b = np.asarray(bench_close, dtype=float)
        rs_ts = trend_score(np.log(c / b), p.sigma_span, p.sigma_clip)
        rs_d = regime(rs_ts, p.enter_thr, p.exit_thr)
        mkt_ts = trend_score(np.log(b), p.sigma_span, p.sigma_clip)
        mkt_d = regime(mkt_ts, p.enter_thr, p.exit_thr)
    else:
        rs_ts, rs_d = np.full(n, np.nan), np.zeros(n, dtype=int)
        mkt_ts, mkt_d = np.full(n, np.nan), np.zeros(n, dtype=int)
    hd = np.zeros(n, dtype=int) if htf_dir is None else np.asarray(htf_dir, dtype=int)

    hh_prev = pd.Series(h).rolling(p.brk_len).max().shift(1).to_numpy()
    ll_stop = pd.Series(l).rolling(p.s2_stop_len).min().to_numpy()
    comp_prev = np.r_[False, (atr[:-1] <= p.comp_ratio * atr_l[:-1])]
    min_ext = pd.Series(ext).rolling(p.rev_lookback).min().to_numpy()

    cols = {k: np.full(n, np.nan) for k in
            ("last_sh", "last_sl", "avwap_low", "avwap_high", "stop1", "stop2", "stop3", "pb_rvol", "sig_stop")}
    bools = {k: np.zeros(n, dtype=bool) for k in
             ("new_sh", "new_sl", "break_up", "break_dn", "raw_s1", "raw_s2", "raw_s3")}
    sig = np.zeros(n, dtype=int)
    labels = np.full(n, "", dtype=object)

    # zigzag state (Pine: var ...)
    zdir = 0
    hi_px, hi_bar, lo_px, lo_bar = h[0], 0, l[0], 0
    lo_since_hi, lo_since_hi_bar, hi_since_lo, hi_since_lo_bar = l[0], 0, h[0], 0
    last_sh = last_sl = prev_sh = prev_sl = np.nan
    last_sh_bar = last_sl_bar = -1
    avl_pv = avl_v = avh_pv = avh_v = 0.0
    # S1 state
    s1_armed, s1_low, s1_hi_bar, pb_vs, pb_vn = False, np.nan, -1, 0.0, 0
    last_down_bar = None
    vz = np.nan_to_num(v)
    if p.s1_mode not in ("dip", "swing", "baseline"):
        raise ValueError("s1_mode must be 'dip', 'swing' or 'baseline'")
    swing_mode, dip_mode = p.s1_mode == "swing", p.s1_mode == "dip"
    # dip_len-bar return in risk units, with the same lagged volatility as the trend score
    lnc = np.log(c)
    sig_r = np.sqrt(robust_var_lagged(np.r_[np.nan, np.diff(lnc)], p.sigma_span, p.sigma_clip))
    dip_z = np.full(n, np.nan)
    k = p.dip_len
    dip_z[k:] = _safe_div(lnc[k:] - lnc[:-k], sig_r[k:] * math.sqrt(k))
    with np.errstate(invalid="ignore"):
        in_dip = dip_z <= p.dip_z                     # NaN compares False

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
        if d[t] == -1:
            last_down_bar = t

        # ---- raw setups (independent of any open position)
        raw1 = raw2 = raw3 = False
        stop1 = stop2 = stop3 = pbv = np.nan
        if dip_mode:
            # D "dip in a long-term uptrend": context regime up, first bar of a dip
            if in_dip[t] and not (t > 0 and in_dip[t - 1]) and hd[t] == 1 and not np.isnan(atr[t]):
                raw1, stop1 = True, c[t] - p.dip_stop_atr * atr[t]
        elif swing_mode:
            # S1 "higher low": uptrend, a confirmed swing high (>= swing_atr ATR pullback by close),
            # then the first close above the prior bar's high while the last swing low holds
            if s1_armed:
                s1_low = min(s1_low, l[t])
                if d[t] != 1 or (not np.isnan(sl_prev) and c[t] < sl_prev):
                    s1_armed = False
                elif t > 0 and c[t] > h[t - 1]:
                    raw1, stop1 = True, s1_low - p.stop_buf * atr[t]
                    seg = rvol[max(s1_hi_bar + 1, t - PB_LOOK):t + 1]
                    seg = seg[~np.isnan(seg)]
                    pbv = float(seg.mean()) if seg.size else np.nan
                    s1_armed = False
            if new_sh and d[t] == 1 and not raw1:
                s1_armed, s1_hi_bar, s1_low = True, last_sh_bar, lo_px
        else:
            # v1 rule: uptrend and close within pull_ext ATR of the baseline (or below it)
            if s1_armed:
                s1_low = min(s1_low, l[t])
                if not np.isnan(rvol[t]):
                    pb_vs += rvol[t]
                    pb_vn += 1
                if d[t] != 1 or (not np.isnan(sl_prev) and c[t] < sl_prev):
                    s1_armed = False
                elif t > 0 and c[t] > h[t - 1]:
                    raw1, stop1 = True, s1_low - p.stop_buf * atr[t]
                    pbv = pb_vs / pb_vn if pb_vn else np.nan
                    s1_armed = False
            elif d[t] == 1 and not np.isnan(atr[t]) and c[t] <= base[t] + p.pull_ext * atr[t]:
                s1_armed, s1_low = True, l[t]
                pb_vs, pb_vn = (rvol[t], 1) if not np.isnan(rvol[t]) else (0.0, 0)
        # S2 compression breakout
        if (d[t] >= 0 and comp_prev[t] and not np.isnan(hh_prev[t]) and c[t] > hh_prev[t]
                and (np.isnan(rvol[t]) or rvol[t] >= p.brk_rvol)):
            raw2, stop2 = True, ll_stop[t] - p.stop_buf * atr[t]
        # S3 confirmed reversal
        if (brk_up and d[t] <= 0 and ts[t] > -p.exit_thr and last_down_bar is not None
                and t - last_down_bar <= p.rev_lookback and min_ext[t] <= p.rev_ext
                and not np.isnan(last_sl)):
            raw3, stop3 = True, last_sl - p.stop_buf * atr[t]

        # ---- filters and the signal offered to the trade engine
        f_all = ((not p.use_ctx or hd[t] >= 0) and (not p.use_rs or rs_d[t] >= 0)
                 and (not p.use_mkt or mkt_d[t] >= 0))
        f_vol = (not p.use_pull_vol) or np.isnan(pbv) or pbv <= p.pull_vol_max
        s, st = 0, np.nan
        if t >= p.warmup:
            if p.use_s1 and raw1 and f_all and f_vol:
                s, st = 1, stop1
            elif p.use_s2 and raw2 and f_all:
                s, st = 2, stop2
            elif p.use_s3 and raw3:
                s, st = 3, stop3
            if s:
                st = _round_tick(min(st, c[t] - p.min_stop_atr * atr[t]), p.tick)
                if np.isnan(st) or c[t] - st <= 0:
                    s, st = 0, np.nan
        sig[t], cols["sig_stop"][t] = s, st

        cols["last_sh"][t], cols["last_sl"][t] = last_sh, last_sl
        cols["avwap_low"][t] = avl_pv / avl_v if avl_v > 0 else np.nan
        cols["avwap_high"][t] = avh_pv / avh_v if avh_v > 0 else np.nan
        cols["stop1"][t], cols["stop2"][t], cols["stop3"][t], cols["pb_rvol"][t] = stop1, stop2, stop3, pbv
        bools["new_sh"][t], bools["new_sl"][t] = new_sh, new_sl
        bools["break_up"][t], bools["break_dn"][t] = brk_up, brk_dn
        bools["raw_s1"][t], bools["raw_s2"][t], bools["raw_s3"][t] = raw1, raw2, raw3

    tr_cols, trades = simulate_trades(o, h, l, c, atr, d, cols["last_sl"], sig, cols["sig_stop"], p,
                                      d_dip=hd if dip_mode else None)
    out = pd.DataFrame({"ts": ts, "dir": d, "dip_z": dip_z, "atr": atr, "atr_long": atr_l, "base": base, "ext": ext,
                        "rvol": rvol, "rs_ts": rs_ts, "rs_dir": rs_d, "mkt_ts": mkt_ts, "mkt_dir": mkt_d,
                        "ctx_dir": hd, "swing_label": labels, "sig": sig, **cols, **bools, **tr_cols},
                       index=df.index)
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
    wd = pd.Series(regime(trend_score(np.log(wk["close"].to_numpy()), p.sigma_span, p.sigma_clip),
                          p.enter_thr, p.exit_thr), index=wk.index)
    # a week's value becomes usable on the first trading day AFTER the week ends
    return wd.reindex(daily.index, method="ffill").shift(1).fillna(0).astype(int).to_numpy()
