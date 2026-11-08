"""Volume Flow v2: reference implementation (Pine twin: pine/volume_flow_v2.pine).

What it measures (docs/03_volume_flow_v2.md):
  RVOL   volume relative to what is normal for this bar (per time-of-day slot on intraday charts)
  F      bounded flow ratio in [-1, 1]: smoothed signed volume / smoothed volume
  A, Az  volume asymmetry: the part of F that comes from volume being heavier on up or down bars,
         i.e. the only part of a VFI-type indicator that is information about volume (Az = z-score)
  events climax, absorption, dry-up, accumulation/distribution crossings, divergences
  persistence (experimental) rolling estimate of whether high-volume moves continue or reverse
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .core import (atr1, phi, pivot_high, pivot_low, rolling_std_pop, slot_ewma_lagged,
                   slot_index, smooth2, span_from_window)


@dataclass(frozen=True)
class FlowParams:
    fast_window: int = 40            # SMA-equivalent bars (two-pole smoother)
    slow_window: int = 130           # same mean lag as the original 130-bar VFI
    norm_span_intraday: int = 20     # sessions, per time-of-day slot
    norm_span_daily: int = 50        # bars (D/W/M)
    vol_cap: float = 3.0             # cap on the relative-volume weight (winsorising)
    asym_window: int = 250           # bars for the asymmetry z-score
    ext_window: int = 50             # SMA-equivalent window of the extension baseline
    atr_len: int = 14
    climax_rvol: float = 3.0
    climax_z: float = 2.0
    climax_ext: float = 2.5
    absorb_rvol: float = 2.0
    absorb_z: float = 0.5
    absorb_ext: float = 1.5
    dryup_rvol: float = 0.6
    asym_threshold: float = 2.0
    piv_left: int = 5
    piv_right: int = 5
    div_max_gap: int = 60
    persist_window: int = 500
    persist_min_obs: int = 100


def _safe_div(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / b, np.nan)


def ltf_direction(ltf: pd.DataFrame, bar_id: np.ndarray, n_bars: int) -> np.ndarray:
    """Signed volume share in [-1, 1] per chart bar from lower-timeframe bars, using
    TradingView's Volume Delta rule: close > open up, close < open down; if equal, compare with
    the previous intrabar close; if still equal, repeat the last direction.
    ltf: frame with open, close, volume; bar_id[i] = chart-bar index of LTF row i (non-decreasing).
    Bars without intrabar data are NaN. Pine twin: the LTF block in volume_flow_v2.pine."""
    up = np.zeros(n_bars)
    dn = np.zeros(n_bars)
    has = np.zeros(n_bars, dtype=bool)
    last_c, last_d = np.nan, 0
    for o, c, v, b in zip(ltf["open"].to_numpy(), ltf["close"].to_numpy(),
                          ltf["volume"].to_numpy(), bar_id):
        if c > o:
            d = 1
        elif c < o:
            d = -1
        elif not np.isnan(last_c) and c > last_c:
            d = 1
        elif not np.isnan(last_c) and c < last_c:
            d = -1
        else:
            d = last_d
        if d > 0:
            up[b] += v
        elif d < 0:
            dn[b] += v
        has[b] = True
        last_d, last_c = d, c
    out = _safe_div(up - dn, up + dn)
    out[~has] = np.nan
    return out


def _rolling_ols_persistence(r, rvol, window: int, min_obs: int):
    """Llorente-Michaely-Saar-Wang (2002) style: r[t] = b0 + b1*r[t-1] + b2*r[t-1]*ln(RVOL[t-1]).
    b2 > 0: high-volume moves tend to continue; b2 < 0: they tend to reverse.
    Rolling OLS over `window` bars, solved by Cramer's rule exactly as in Pine.
    Plain OLS standard errors (no HAC): treat the t-stat as indicative only."""
    r = np.asarray(r, dtype=float)
    rv = np.asarray(rvol, dtype=float)
    lv = np.log(np.where(rv > 0, rv, np.nan))           # zero-volume bars are skipped
    x1 = np.r_[np.nan, r[:-1]]
    x2 = np.r_[np.nan, (r * lv)[:-1]]
    y = r
    ok = ~(np.isnan(y) | np.isnan(x1) | np.isnan(x2))
    z = lambda a: np.where(ok, a, 0.0)
    terms = {"n": ok.astype(float), "x1": z(x1), "x2": z(x2), "y": z(y),
             "x1x1": z(x1 * x1), "x2x2": z(x2 * x2), "x1x2": z(x1 * x2),
             "x1y": z(x1 * y), "x2y": z(x2 * y), "yy": z(y * y)}
    S = {k: pd.Series(v).rolling(window).sum().to_numpy() for k, v in terms.items()}
    a, b, c = S["n"], S["x1"], S["x2"]
    d, e, f = S["x1x1"], S["x1x2"], S["x2x2"]
    g, h, k = S["y"], S["x1y"], S["x2y"]
    det = a * (d * f - e * e) - b * (b * f - c * e) + c * (b * e - c * d)
    with np.errstate(divide="ignore", invalid="ignore"):
        b0 = (g * (d * f - e * e) - b * (h * f - e * k) + c * (h * e - d * k)) / det
        b1 = (a * (h * f - e * k) - g * (b * f - e * c) + c * (b * k - h * c)) / det
        b2 = (a * (d * k - h * e) - b * (b * k - h * c) + g * (b * e - d * c)) / det
        ssr = S["yy"] - (b0 * g + b1 * h + b2 * k)
        s2 = ssr / (a - 3.0)
        var_b2 = s2 * (a * d - b * b) / det
        t2 = b2 / np.sqrt(var_b2)
    bad = (a < min_obs) | ~(det > 0) | ~(var_b2 > 0)
    b2 = np.where(bad, np.nan, b2)
    t2 = np.where(bad, np.nan, t2)
    return b2, t2


def volume_flow_v2(df: pd.DataFrame, intraday: bool = False, p: FlowParams = FlowParams(),
                   ltf_dir: np.ndarray | None = None) -> pd.DataFrame:
    """Compute every Volume Flow v2 series. df: open, high, low, close, volume."""
    o, h, l, c, v = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    r = np.r_[np.nan, np.log(c[1:] / c[:-1])]
    slots = slot_index(df.index, intraday)
    span = p.norm_span_intraday if intraday else p.norm_span_daily

    # Normalisation per slot: expected volume and volatility from previous sessions/bars only
    sigma = np.sqrt(slot_ewma_lagged(r * r, slots, span))
    z = _safe_div(r, sigma)
    s_bvc = 2.0 * phi(z) - 1.0
    s = s_bvc if ltf_dir is None else np.where(np.isnan(ltf_dir), s_bvc, ltf_dir)
    ev = slot_ewma_lagged(v, slots, span)
    rvol = _safe_div(v, ev)
    # Weight = RELATIVE volume, capped. Raw volume would let the structurally busy opening and
    # closing bars dominate intraday flow (the VFI's U-shape bias); relative volume measures
    # abnormal participation. On D/W charts the two are nearly identical.
    w = np.where(np.isnan(rvol), np.nan, np.minimum(rvol, p.vol_cap))

    # Flow ratio (two-pole kernel) and volume asymmetry
    sv = w * s
    valid = ~np.isnan(sv)
    vw_m = np.where(valid, w, np.nan)
    s_m = np.where(valid, s, np.nan)
    nf, ns = span_from_window(p.fast_window), span_from_window(p.slow_window)
    f_fast = _safe_div(smooth2(sv, nf), smooth2(vw_m, nf))
    f_slow = _safe_div(smooth2(sv, ns), smooth2(vw_m, ns))
    f_unw = smooth2(s_m, ns)
    asym = f_slow - f_unw
    # Centre on the instrument's own normal asymmetry: E03 found a persistent negative baseline
    # (volume heavier on down bars) in every series tested. Pine twin: (A - ta.sma) / ta.stdev.
    asym_mean = pd.Series(asym).rolling(p.asym_window).mean().to_numpy()
    asym_z = _safe_div(asym - asym_mean, rolling_std_pop(asym, p.asym_window))

    # Price context: extension from a two-pole baseline in ATR units
    atr = atr1(h, l, c, p.atr_len)
    base = smooth2(c, span_from_window(p.ext_window))
    ext = _safe_div(c - base, atr)

    # Events (evaluated on closed bars; NaN comparisons are False)
    with np.errstate(invalid="ignore"):
        climax_up = (rvol >= p.climax_rvol) & (z >= p.climax_z) & (ext >= p.climax_ext)
        climax_dn = (rvol >= p.climax_rvol) & (z <= -p.climax_z) & (ext <= -p.climax_ext)
        absorb = (rvol >= p.absorb_rvol) & (np.abs(z) <= p.absorb_z) & (np.abs(ext) >= p.absorb_ext)
        absorb_top, absorb_bot = absorb & (ext > 0), absorb & (ext < 0)
        dryup = rvol <= p.dryup_rvol
        az_prev = np.r_[np.nan, asym_z[:-1]]
        accum = (asym_z > p.asym_threshold) & (az_prev <= p.asym_threshold)
        distrib = (asym_z < -p.asym_threshold) & (az_prev >= -p.asym_threshold)

    # Divergences: confirmed price pivots vs fast flow at the pivot bar
    ph, pl = pivot_high(h, p.piv_left, p.piv_right), pivot_low(l, p.piv_left, p.piv_right)
    bear, bull = np.zeros(n, bool), np.zeros(n, bool)
    lh = lhb = lhf = np.nan
    ll = llb = llf = np.nan
    R = p.piv_right
    for t in range(n):
        if not np.isnan(ph[t]):
            pb, fv = t - R, f_fast[t - R]
            if (not np.isnan(lh) and pb - lhb <= p.div_max_gap and ph[t] > lh
                    and not np.isnan(fv) and not np.isnan(lhf) and fv < lhf):
                bear[t] = True
            lh, lhb, lhf = ph[t], pb, fv
        if not np.isnan(pl[t]):
            pb, fv = t - R, f_fast[t - R]
            if (not np.isnan(ll) and pb - llb <= p.div_max_gap and pl[t] < ll
                    and not np.isnan(fv) and not np.isnan(llf) and fv > llf):
                bull[t] = True
            ll, llb, llf = pl[t], pb, fv

    pc, pt = _rolling_ols_persistence(r, rvol, p.persist_window, p.persist_min_obs)

    return pd.DataFrame({
        "r": r, "slot": slots, "sigma": sigma, "z": z, "s": s, "ev": ev, "rvol": rvol, "w": w,
        "f_fast": f_fast, "f_slow": f_slow, "f_unweighted": f_unw, "asym": asym, "asym_z": asym_z,
        "atr": atr, "ext": ext,
        "climax_up": climax_up, "climax_dn": climax_dn, "absorb_top": absorb_top,
        "absorb_bottom": absorb_bot, "dryup": dryup, "accumulation": accum, "distribution": distrib,
        "bear_div": bear, "bull_div": bull, "persist_c": pc, "persist_t": pt,
    }, index=df.index)
