"""Relative Volume v4: reference implementation. Pine twin: pine/relative_volume.pine.

Why it looks like this: docs/07_relative_volume_review.md (two external reviews, experiments E10-E26).

Definitions (every reference value uses EARLIER bars of the same slot only):
  slot    one per time of day on intraday charts (clock time of the bar's open, plus the bar's
          length, so that a short half-day bar is never mixed with a full bar); a single slot on
          daily and higher timeframes.
  normal  exp(mu), where mu is an exponentially weighted average of ln(volume). Each new
          observation enters as mu + clip(ln(volume) - mu, +-3 s): one extreme day cannot move
          the reference by more than a few percent. s^2 is the same kind of average of the clipped
          squared innovations. Zero-volume bars are skipped. Averages are bias-corrected
          (weighted sum / sum of weights), so no value is ever "seeded" by one observation.
  rvol    volume / normal.                zV = (ln(volume) - mu) / s.
  sigma   clipped average of squared close-to-close returns (same slot, same span as normal).
          z = return / sigma.
A value is reported only after `min_obs` earlier observations of its slot.
Removed in v4, with the evidence in the review document: the mark "heavy volume, small move,
stretched low" and its extension and ATR series (E21), and the day estimate on the live daily bar
(E24; its constants are kept with experiments/e24_intraday_second_review.py).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RelVolParams:
    span_daily: int = 50            # bars, daily and higher
    span_intraday: int = 20         # sessions per time-of-day slot
    scale_span: int = 100           # observations of the slot, for the scale s of log volume
    clip: float = 3.0               # innovations and squared returns are clipped at 3 sd
    min_clip: int = 20              # clipping starts once a slot has this many earlier observations
    min_obs_daily: int = 25         # values are shown only after this many earlier observations
    min_obs_intraday: int = 10
    flag_z: float = 2.0             # unusual volume: zV >= 2 (about the busiest 4% of bars)
    extreme_z: float = 3.0          # extreme volume: zV >= 3 (about 1% of bars)


def slot_keys(index: pd.DatetimeIndex, intraday: bool, bar_minutes=None) -> np.ndarray:
    """Integer key of the time-of-day slot: (minutes after midnight of the bar's open) * 10000 +
    bar length in minutes. 0 on daily and higher timeframes. Pine twin: slotKey."""
    n = len(index)
    if not intraday:
        return np.zeros(n, dtype=np.int64)
    tod = (index.hour * 60 + index.minute).to_numpy().astype(np.int64)
    if bar_minutes is None:
        return tod * 10000
    return tod * 10000 + np.asarray(bar_minutes, dtype=np.int64)


def quarterly_expiry(index: pd.DatetimeIndex) -> np.ndarray:
    """True on the third Friday of March, June, September and December (quarterly option and futures
    expiry, with index rebalances), or, from 2022 on, the Thursday before when that Friday in June is
    the Juneteenth holiday (19 June on a Friday: Thursday the 18th) or the day it is observed (19 June
    on a Saturday: Thursday the 17th). Pine twin: qExpiry."""
    third_fri = (index.dayofweek == 4) & (index.day >= 15) & (index.day <= 21)
    june_thu = (index.year >= 2022) & (index.month == 6) & (index.dayofweek == 3) & ((index.day == 17) | (index.day == 18))
    return np.asarray((index.month % 3 == 0) & (third_fri | june_thu))


def russell_reconstitution(index: pd.DatetimeIndex) -> np.ndarray:
    """True on the fourth Friday of June (annual reconstitution of the Russell indexes). Pine twin: russell."""
    return np.asarray((index.month == 6) & (index.dayofweek == 4) & (index.day >= 22) & (index.day <= 28))


def mechanical_day(index: pd.DatetimeIndex) -> np.ndarray:
    """Days on which heavy volume is mostly mechanical for US stocks: quarterly expiry and the Russell
    reconstitution. In 2018-2026 about 37% of stocks had zV >= 2 on such a day, against 3.5% on other
    days (E21): 18% of all flags on 2% of the days. Pine twin: mechDay (US-listed symbols)."""
    return quarterly_expiry(index) | russell_reconstitution(index)


def log_level_lagged(volume, keys, span: int, scale_span: int, clip: float = 3.0, min_clip: int = 20):
    """Robust level and scale of ln(volume) per slot, as known BEFORE each bar.
    Returns (mu, s, n): mean of ln(volume), sd of its innovations, number of earlier observations.
    Pine twin: logLevelLagged."""
    v = np.asarray(volume, dtype=float)
    a, b = 2.0 / (span + 1), 2.0 / (scale_span + 1)
    n = len(v)
    mu_o, s_o, n_o = np.full(n, np.nan), np.full(n, np.nan), np.zeros(n, dtype=np.int64)
    state: dict = {}
    for i in range(n):
        k = int(keys[i])
        st = state.get(k)
        if st is None:
            st = [0.0, 0.0, 0.0, 0.0, 0]            # num, den, num2, den2, count
            state[k] = st
        num, den, num2, den2, cnt = st
        mu = num / den if cnt > 0 else math.nan
        s = math.sqrt(num2 / den2) if den2 > 0.0 and num2 > 0.0 else math.nan
        mu_o[i], s_o[i], n_o[i] = mu, s, cnt
        x = v[i]
        if x > 0.0 and math.isfinite(x):
            lx = math.log(x)
            if cnt == 0:
                st[0], st[1], st[4] = a * lx, a, 1
            else:
                e = lx - mu
                if cnt >= min_clip and s == s and s > 0.0:
                    lim = clip * s
                    e = lim if e > lim else (-lim if e < -lim else e)
                st[0] = (1.0 - a) * num + a * (mu + e)
                st[1] = (1.0 - a) * den + a
                st[2] = (1.0 - b) * num2 + b * e * e
                st[3] = (1.0 - b) * den2 + b
                st[4] = cnt + 1
    return mu_o, s_o, n_o


def var_lagged(r, keys, span: int, clip: float = 3.0, min_clip: int = 20):
    """Clipped, bias-corrected average of squared returns per slot, as known BEFORE each bar.
    Returns (variance, n). Zero returns are observations like any other. Pine twin: varLagged."""
    r = np.asarray(r, dtype=float)
    a = 2.0 / (span + 1)
    n = len(r)
    v_o, n_o = np.full(n, np.nan), np.zeros(n, dtype=np.int64)
    state: dict = {}
    c2 = clip * clip
    for i in range(n):
        k = int(keys[i])
        st = state.get(k)
        if st is None:
            st = [0.0, 0.0, 0]
            state[k] = st
        num, den, cnt = st
        var = num / den if cnt > 0 else math.nan
        v_o[i], n_o[i] = var, cnt
        x = r[i]
        if x == x and math.isfinite(x):
            x2 = x * x
            if cnt >= min_clip and var > 0.0 and x2 > c2 * var:
                x2 = c2 * var
            st[0] = (1.0 - a) * num + a * x2
            st[1] = (1.0 - a) * den + a
            st[2] = cnt + 1
    return v_o, n_o


def relative_volume(df: pd.DataFrame, intraday: bool = False, p: RelVolParams = RelVolParams(),
                    bar_minutes=None, keys=None) -> pd.DataFrame:
    """Every series of the Relative Volume v4 pane. df: close, volume (DatetimeIndex).
    keys: optional slot keys taken from the script itself (plot dbg_key of a chart export)."""
    c, v = (df[k].to_numpy(dtype=float) for k in ("close", "volume"))
    if intraday and keys is None and bar_minutes is None:
        raise ValueError("intraday: pass bar_minutes or keys (the slot key includes the bar's length)")
    keys = slot_keys(df.index, intraday, bar_minutes) if keys is None else np.asarray(keys, dtype=np.int64)
    span = p.span_intraday if intraday else p.span_daily
    need = p.min_obs_intraday if intraday else p.min_obs_daily
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.r_[np.nan, np.where((c[1:] > 0) & (c[:-1] > 0), np.log(c[1:] / c[:-1]), np.nan)]
        mu, s, n = log_level_lagged(v, keys, span, p.scale_span, p.clip, p.min_clip)
        ok = n >= need
        lv = np.where(v > 0, np.log(np.where(v > 0, v, 1.0)), np.nan)
        normal = np.where(ok, np.exp(mu), np.nan)
        rvol = np.where(ok, np.where(v > 0, v / np.exp(mu), 0.0), np.nan)
        zv = np.where(ok & (s > 0), (lv - mu) / s, np.nan)
        level = np.where(ok & (s > 0), np.exp(p.flag_z * s), np.nan)   # the "unusual" level as a multiple
        var, nv = var_lagged(r, keys, span, p.clip, p.min_clip)
        sigma = np.where((nv >= need) & (var > 0), np.sqrt(var), np.nan)
        z = r / sigma
        unusual = zv >= p.flag_z
        extreme = zv >= p.extreme_z
        # session pace (intraday): volume of the session so far / what is normal by this time of day.
        # The session is taken as the calendar day: regular trading hours, sessions that do not cross midnight.
        pace, pace_z = np.full(len(v), np.nan), np.full(len(v), np.nan)
        if intraday:
            cum = pd.Series(np.nan_to_num(v), index=df.index).groupby(df.index.normalize()).cumsum().to_numpy()
            mu_c, s_c, n_c = log_level_lagged(cum, keys, p.span_intraday, p.scale_span, p.clip, p.min_clip)
            pace = np.where((n_c >= need) & (cum > 0), cum / np.exp(mu_c), np.nan)
            lc = np.where(cum > 0, np.log(np.where(cum > 0, cum, 1.0)), np.nan)
            pace_z = np.where((n_c >= need) & (s_c > 0), (lc - mu_c) / s_c, np.nan)   # the pace in units of its own spread
    return pd.DataFrame({
        "key": keys, "r": r, "mu": mu, "s": s, "n": n, "normal": normal, "rvol": rvol, "zv": zv,
        "level": level, "sigma": sigma, "z": z, "unusual": unusual, "extreme": extreme, "pace": pace, "pace_z": pace_z,
        "q_expiry": quarterly_expiry(df.index), "mech_day": mechanical_day(df.index),
    }, index=df.index)
