#!/usr/bin/env python3
"""E12 - Volatility feedback after shocks, and the hidden left tail (review of the Relative Volume pane).

Reviewer claims under test
  (a) The pane's sigma is an UNCLIPPED EWMA (span 50) of squared returns. A 5-sigma gap inflates it
      by sqrt(1 + 24*2/51) = 1.39x at once; for weeks afterwards |z| is artificially small, so the
      |z| <= 0.5 leg of the "A" mark (absorption at lows) is easier to meet right after bad-news drops.
  (b) Survivorship is asymmetric: stocks that later die show volume explosions while collapsing, so
      deleting them inflates the high-volume group against the low-volume control.

Tests (all thresholds and windows were fixed before any set other than A was looked at)
  S1 event study around shocks (|z| >= 4, also >= 3): sigma / clipped sigma and P(|z| <= 0.5) by
     bars since the last shock, against bars with no shock in the previous 60 bars. Sets A, B, LH, MS.
  S2 share of absorb_bottom events with a shock in the previous 20 bars against the strict control
     (ext <= -1.5, |z| <= 0.5, rvol < 2); forward returns of events with and without a recent shock.
  S3 the event recomputed with the clipped sigma: kept / lost / gained and their forward returns.
  S4 left tail of the 20-bar forward return among survivors by relative-volume bucket.
  S5 break-even survivorship: the share of treatment events that would have to be missing deaths.
  S6 tickers whose data ends early or starts late inside each set.

Clipped sigma = sqrt(tfs.trend.robust_var_lagged(r, 50, 3.0)): same span as the pane, value before
the current bar, each squared return capped at (3 * current sigma)^2 once 50 observations exist.
"Level-matched" clipped sigma = clipped sigma * C_LEVEL, where C_LEVEL is the median of
sigma / clipped sigma on calm bars of set A (no |z| >= 3 in the previous 60 bars). It removes the
constant level difference between the two estimators and leaves only the shock-specific part.

Uncertainty: month-block bootstrap, 2000 resamples (experiments.e05_validation_lite.boot_diff /
boot_mean). Every boot_diff call is counted as one comparison and listed in the output.

  python3 -I experiments/e12_sigma_shock_and_tails.py [--panel DIR] [--sets A B LH MS DJ]
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import argparse
import json
import time

import numpy as np
import pandas as pd

import experiments.e05_validation_lite as e05
from tfs.trend import robust_var_lagged

DEFAULT_PANEL = "/tmp/claude-0/-home-user-AquaCentinela/b2916ecb-3cd8-557a-8730-1dacd8557876/scratchpad/panel"
SEED = 20261123
SET_ORDER = ("A", "B", "DJ", "LH", "MS")
SEED_OFFSET = {"A": 1, "B": 2, "DJ": 3, "LH": 4, "MS": 5}
S1_SETS = ("A", "B", "LH", "MS")
COLS = ["ticker", "date", "t", "month", "close", "sigma", "z", "sig0", "rvol", "ext", "absorb_bottom",
        "climax_dn", "f10", "f20", "fz10", "fzd10", "fz20", "eval", "half"]
SPAN, CLIP = 50, 3.0
THRESHOLDS = (4.0, 3.0)
WINDOWS = ((1, 1), (1, 5), (6, 20), (21, 40), (41, 60), (1, 20))
CALM = 60                     # "no shock in the previous 60 bars"
RECENT = 20                   # "shock in the previous 20 bars"
BUCKETS = ((0.0, 0.8, "<0.8"), (0.8, 1.25, "0.8-1.25"), (1.25, 2.0, "1.25-2"), (2.0, 3.0, "2-3"),
           (3.0, np.inf, ">=3"))
PUBLISHED_ABSORB = {"A": 439, "B": 499, "DJ": 60, "LH": 2386, "MS": 9312}
COMPARISONS: list[str] = []
TALLY = {"empty": 0, "interval_excludes_zero": 0}


# --------------------------------------------------------------------------- helpers
def cmp(label, v_s, m_s, v_c, m_c, rng):
    """Counted month-block bootstrap of mean(signal) - mean(control)."""
    COMPARISONS.append(label)
    v_s, v_c = np.asarray(v_s, dtype=float), np.asarray(v_c, dtype=float)
    out = e05.boot_diff(v_s, m_s, v_c, m_c, rng)
    out["n_control"] = int(np.isfinite(v_c).sum())
    if out["diff"] is None:
        TALLY["empty"] += 1
    elif out["lo"] > 0 or out["hi"] < 0:
        TALLY["interval_excludes_zero"] += 1
    return out


def mean_ci(v, m, rng):
    return e05.boot_mean(np.asarray(v, dtype=float), m, rng)


def rd(x, nd=4):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, nd)


def bars_since(flag, tstart):
    """Bars since the last True strictly before each row, inside the same ticker (inf if none)."""
    pos = np.arange(len(flag))
    last = np.maximum.accumulate(np.where(flag, pos, -1))
    last = np.r_[-1, last[:-1]]
    age = (pos - last).astype(float)
    age[last < tstart] = np.inf
    return age


def load(panel_dir, name):
    d = pd.read_parquet(pathlib.Path(panel_dir) / f"panel_{name}.parquet", columns=COLS)
    tk = d["ticker"].to_numpy()
    chg = np.r_[True, tk[1:] != tk[:-1]]
    starts = np.flatnonzero(chg)
    ends = np.r_[starts[1:], len(tk)]
    tstart = np.repeat(starts, ends - starts)
    assert (d["t"].to_numpy() == np.arange(len(d)) - tstart).all(), "panel not sorted by ticker, bar"
    lc = np.log(d["close"].to_numpy())
    r = np.r_[np.nan, np.diff(lc)]
    r[starts] = np.nan
    var_c = np.empty(len(r))
    for s, e in zip(starts, ends):
        var_c[s:e] = robust_var_lagged(r[s:e], SPAN, CLIP)
    with np.errstate(divide="ignore", invalid="ignore"):
        sig_c = np.sqrt(var_c)
        z_rob = np.where(sig_c > 0, r / sig_c, np.nan)
    a = {k: d[k].to_numpy() for k in COLS if k not in ("ticker", "date")}
    for k in ("sigma", "z", "sig0", "rvol", "ext", "f10", "f20", "fz10", "fzd10", "fz20"):
        a[k] = a[k].astype(float)
    a.update(ticker=tk, date=d["date"].to_numpy(), r=r, sig_c=sig_c, z_rob=z_rob, starts=starts, ends=ends,
             tstart=tstart)
    return a


def calm_level(a):
    """C_LEVEL: median sigma / clipped sigma on calm eval bars (no |z| >= 3 in the previous 60 bars)."""
    with np.errstate(invalid="ignore"):
        age = bars_since(np.abs(a["z"]) >= 3.0, a["tstart"])
    m = a["eval"] & (age > CALM)
    return float(np.median(a["sigma"][m] / a["sig_c"][m])), int(m.sum())


# --------------------------------------------------------------------------- S1
def s1_event_study(a, rng, name):
    ev, z, zr, mth = a["eval"], a["z"], a["z_rob"], a["month"]
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = a["sigma"] / a["sig_c"]
        ev = ev & np.isfinite(ratio) & np.isfinite(z) & np.isfinite(zr)
        small = (np.abs(z) <= 0.5).astype(float)
        small_r = (np.abs(zr) <= 0.5).astype(float)
        nxt = np.r_[a["sigma"][1:] / a["sigma"][:-1], np.nan]
    nxt[a["ends"] - 1] = np.nan
    stock_years = ev.sum() / 252.0
    out = {"theory_jump_5sigma": rd(np.sqrt(1 + 24 * 2 / 51), 4), "eval_rows": int(ev.sum()),
           "eval_rows_dropped_no_sigma": int(a["eval"].sum() - ev.sum()),
           "stock_years": rd(stock_years, 1)}
    for thr in THRESHOLDS:
        with np.errstate(invalid="ignore"):
            shock = np.abs(z) >= thr
            shock_dn = z <= -thr
        age = bars_since(shock, a["tstart"])
        age_dn = bars_since(shock_dn, a["tstart"])
        base = ev & (age > CALM)
        se = shock & ev
        near5 = se & (np.abs(z) >= 4.5) & (np.abs(z) < 5.5)
        o = {"n_shocks_eval": int(se.sum()), "shocks_per_stock_year": rd(se.sum() / stock_years, 3),
             "share_down_shocks_pct": rd(100 * (shock_dn & ev).sum() / max(se.sum(), 1), 1),
             "median_abs_z_of_shocks": rd(np.median(np.abs(z[se])), 2),
             "sigma_jump_next_bar_mean": rd(np.nanmean(nxt[se]), 4),
             "sigma_jump_next_bar_median": rd(np.nanmedian(nxt[se]), 4),
             "sigma_jump_next_bar_mean_for_abs_z_4.5_to_5.5": rd(np.nanmean(nxt[near5]), 4) if near5.any() else None,
             "share_eval_bars_within_20_after_shock_pct": rd(100 * (ev & (age <= 20)).sum() / ev.sum(), 2),
             "share_eval_bars_within_40_after_shock_pct": rd(100 * (ev & (age <= 40)).sum() / ev.sum(), 2),
             "share_eval_bars_calm_pct": rd(100 * base.sum() / ev.sum(), 2)}

        def calib(m):
            return {"n": int(m.sum()), "mean_ratio_sigma_over_clipped": rd(ratio[m].mean()),
                    "median_ratio": rd(np.median(ratio[m])),
                    "p_absz_le_0.5_pct": rd(100 * small[m].mean(), 2),
                    "p_absz_rob_le_0.5_pct": rd(100 * small_r[m].mean(), 2),
                    "median_absz": rd(np.median(np.abs(z[m])), 3),
                    "median_absz_rob": rd(np.median(np.abs(zr[m])), 3),
                    "p_absz_ge_2_pct": rd(100 * (np.abs(z[m]) >= 2).mean(), 2),
                    "p_absz_rob_ge_2_pct": rd(100 * (np.abs(zr[m]) >= 2).mean(), 2)}

        o["calm_baseline"] = calib(base)
        r0 = ratio[base].mean()
        curve = []
        for k in range(1, 41):
            m = ev & (age == k)
            c = calib(m)
            c["k"] = k
            c["ratio_excess_vs_calm_pct"] = rd(100 * (ratio[m].mean() / r0 - 1), 2)
            curve.append(c)
        o["by_bars_since_shock"] = curve
        p0, p0r = o["calm_baseline"]["p_absz_le_0.5_pct"], o["calm_baseline"]["p_absz_rob_le_0.5_pct"]
        o["first_k_with_p_small_z_above_calm"] = next((c["k"] for c in curve if c["p_absz_le_0.5_pct"] > p0), None)
        o["first_k_with_p_small_z_rob_above_calm"] = next((c["k"] for c in curve if c["p_absz_rob_le_0.5_pct"] > p0r), None)
        o["n_k_1_to_40_with_p_small_z_above_calm"] = int(sum(c["p_absz_le_0.5_pct"] > p0 for c in curve))
        wins = {}
        for lo, hi in WINDOWS:
            m = ev & (age >= lo) & (age <= hi)
            tag = f"k{lo}-{hi}"
            w = calib(m)
            w["ratio_excess_vs_calm_pct"] = rd(100 * (ratio[m].mean() / r0 - 1), 2)
            w["diff_ratio_vs_calm"] = cmp(f"S1 {name} thr{thr:g} {tag} ratio", ratio[m], mth[m], ratio[base], mth[base], rng)
            w["diff_p_absz_le_0.5_pp"] = cmp(f"S1 {name} thr{thr:g} {tag} P(|z|<=0.5)", 100 * small[m], mth[m],
                                           100 * small[base], mth[base], rng)
            w["diff_p_absz_rob_le_0.5_pp"] = cmp(f"S1 {name} thr{thr:g} {tag} P(|z_rob|<=0.5)", 100 * small_r[m], mth[m],
                                               100 * small_r[base], mth[base], rng)
            wins[tag] = w
        o["windows_vs_calm"] = wins
        dn = {}
        for lo, hi in ((1, 5), (1, 20)):
            m = ev & (age_dn >= lo) & (age_dn <= hi)
            tag = f"k{lo}-{hi}"
            w = calib(m)
            w["ratio_excess_vs_calm_pct"] = rd(100 * (ratio[m].mean() / r0 - 1), 2)
            w["diff_p_absz_le_0.5_pp"] = cmp(f"S1 {name} thr{thr:g} down {tag} P(|z|<=0.5)", 100 * small[m], mth[m],
                                           100 * small[base], mth[base], rng)
            w["diff_p_absz_rob_le_0.5_pp"] = cmp(f"S1 {name} thr{thr:g} down {tag} P(|z_rob|<=0.5)", 100 * small_r[m],
                                               mth[m], 100 * small_r[base], mth[base], rng)
            dn[tag] = w
        o["down_shock_windows_vs_calm"] = dn
        out[f"abs_z_ge_{thr:g}"] = o
    return out


# --------------------------------------------------------------------------- S2
def s2_recent_shock(a, rng, name):
    ev, z, zr, mth, ext, rvol = a["eval"], a["z"], a["z_rob"], a["month"], a["ext"], a["rvol"]
    with np.errstate(invalid="ignore"):
        low = ev & (ext <= -1.5)
        T = ev & a["absorb_bottom"]
        C = low & (np.abs(z) <= 0.5) & (rvol < 2.0)
    out = {"n_event": int(T.sum()), "n_strict_control": int(C.sum()), "n_ext_le_-1.5": int(low.sum()),
           "events_per_stock_year": rd(T.sum() / (ev.sum() / 252.0), 3)}
    ages = {}
    for thr in THRESHOLDS:
        with np.errstate(invalid="ignore"):
            ages[(thr, "any")] = bars_since(np.abs(z) >= thr, a["tstart"])
            ages[(thr, "down")] = bars_since(z <= -thr, a["tstart"])
    shares = {}
    for (thr, kind), age in ages.items():
        rec = (age <= RECENT).astype(float)
        tag = f"abs_z_ge_{thr:g}_{kind}"
        shares[tag] = {
            "share_event_pct": mean_ci(100 * rec[T], mth[T], rng),
            "share_strict_control_pct": mean_ci(100 * rec[C], mth[C], rng),
            "share_all_ext_le_-1.5_pct": rd(100 * rec[low].mean(), 2),
            "share_all_eval_bars_pct": rd(100 * rec[ev].mean(), 2),
            "diff_event_minus_control_pp": cmp(f"S2 {name} share recent shock {tag}", 100 * rec[T], mth[T],
                                               100 * rec[C], mth[C], rng)}
    out["share_with_shock_in_previous_20_bars"] = shares

    fwd = {}
    f10p = 100 * (np.exp(a["f10"]) - 1.0)
    for thr in THRESHOLDS:
        age = ages[(thr, "any")]
        w, wo = T & (age <= RECENT), T & ~(age <= RECENT)
        o = {"n_with": int(w.sum()), "n_without": int(wo.sum())}
        for key, v in (("fz10", a["fz10"]), ("fzd10", a["fzd10"]), ("f10_simple_pct", f10p)):
            o[key] = {"with": mean_ci(v[w], mth[w], rng), "without": mean_ci(v[wo], mth[wo], rng),
                      "with_minus_without": cmp(f"S2 {name} thr{thr:g} event with-without {key}", v[w], mth[w],
                                                v[wo], mth[wo], rng)}
        fwd[f"abs_z_ge_{thr:g}_any"] = o
    out["event_forward_returns_with_vs_without_recent_shock"] = fwd

    # how much easier is the mark to meet after a shock: rates per bar, shock window against calm bars
    calm = ev & (ages[(4.0, "any")] > CALM)
    dec = {}
    with np.errstate(invalid="ignore"):
        zs, zrs = np.abs(z) <= 0.5, np.abs(zr) <= 0.5
        hv = rvol >= 2.0
    for kind in ("down", "any"):
        g = ev & (ages[(4.0, kind)] <= RECENT)

        def rates(m):
            lo_ = m & low
            return {"n_bars": int(m.sum()), "p_ext_le_-1.5_pct": rd(100 * lo_.sum() / max(m.sum(), 1), 2),
                    "p_absz_le_0.5_given_ext_pct": rd(100 * (lo_ & zs).sum() / max(lo_.sum(), 1), 2),
                    "p_absz_rob_le_0.5_given_ext_pct": rd(100 * (lo_ & zrs).sum() / max(lo_.sum(), 1), 2),
                    "p_rvol_ge_2_given_ext_pct": rd(100 * (lo_ & hv).sum() / max(lo_.sum(), 1), 2),
                    "p_rvol_ge_2_given_ext_and_small_z_pct": rd(100 * (lo_ & zs & hv).sum() / max((lo_ & zs).sum(), 1), 2),
                    "events_per_1000_bars": rd(1000 * (m & a["absorb_bottom"]).sum() / max(m.sum(), 1), 3)}

        ab = a["absorb_bottom"].astype(float)
        dec[f"after_{kind}_shock_abs_z_ge_4"] = {
            "shock_window": rates(g), "calm": rates(calm),
            "diff_events_per_1000_bars": cmp(f"S2 {name} event rate after {kind} shock vs calm", 1000 * ab[g], mth[g],
                                             1000 * ab[calm], mth[calm], rng),
            "diff_p_absz_le_0.5_given_ext_pp": cmp(f"S2 {name} P(|z|<=0.5|ext) after {kind} shock vs calm",
                                                   100 * zs[g & low], mth[g & low], 100 * zs[calm & low], mth[calm & low], rng),
            "diff_p_absz_rob_le_0.5_given_ext_pp": cmp(f"S2 {name} P(|z_rob|<=0.5|ext) after {kind} shock vs calm",
                                                       100 * zrs[g & low], mth[g & low], 100 * zrs[calm & low],
                                                       mth[calm & low], rng),
            "diff_p_rvol_ge_2_given_ext_small_z_pp": cmp(f"S2 {name} P(rvol>=2|ext,small z) after {kind} shock vs calm",
                                                         100 * hv[g & low & zs], mth[g & low & zs],
                                                         100 * hv[calm & low & zs], mth[calm & low & zs], rng)}
    out["event_rate_after_shock_vs_calm"] = dec
    return out


# --------------------------------------------------------------------------- S3
def s3_clipped_event(a, rng, name, c_level):
    ev, z, zr, mth, ext, rvol = a["eval"], a["z"], a["z_rob"], a["month"], a["ext"], a["rvol"]
    f10p = 100 * (np.exp(a["f10"]) - 1.0)
    with np.errstate(invalid="ignore"):
        base = ev & (rvol >= 2.0) & (ext <= -1.5)
        low = ev & (ext <= -1.5)
        ship_re = base & (np.abs(z) <= 0.5)
        ship = ev & a["absorb_bottom"]
        age4 = bars_since(np.abs(z) >= 4.0, a["tstart"])
        age3 = bars_since(np.abs(z) >= 3.0, a["tstart"])
    out = {"n_shipped_flag": int(ship.sum()), "n_shipped_recomputed_from_float32": int(ship_re.sum()),
           "flag_mismatch_rows": int((ship != ship_re).sum()), "published_count": PUBLISHED_ABSORB.get(name)}
    metrics = (("fz10", a["fz10"]), ("fzd10", a["fzd10"]), ("f10_simple_pct", f10p))
    for tag, zz in (("clipped_same_threshold", zr), ("clipped_level_matched", zr / c_level)):
        with np.errstate(invalid="ignore"):
            small = np.abs(zz) <= 0.5
            rob = base & small
            ctl_rob = low & small & (rvol < 2.0)
            ctl_ship = low & (np.abs(z) <= 0.5) & (rvol < 2.0)
        kept, lost, gained = ship & rob, ship & ~rob, rob & ~ship
        o = {"n_shipped": int(ship.sum()), "n_clipped": int(rob.sum()), "kept": int(kept.sum()),
             "lost": int(lost.sum()), "gained": int(gained.sum()),
             "lost_pct_of_shipped": rd(100 * lost.sum() / max(ship.sum(), 1), 2),
             "gained_pct_of_shipped": rd(100 * gained.sum() / max(ship.sum(), 1), 2),
             "lost_with_shock4_in_prev_20_pct": rd(100 * (lost & (age4 <= RECENT)).sum() / max(lost.sum(), 1), 1),
             "lost_with_shock3_in_prev_20_pct": rd(100 * (lost & (age3 <= RECENT)).sum() / max(lost.sum(), 1), 1),
             "kept_with_shock4_in_prev_20_pct": rd(100 * (kept & (age4 <= RECENT)).sum() / max(kept.sum(), 1), 1),
             "kept_with_shock3_in_prev_20_pct": rd(100 * (kept & (age3 <= RECENT)).sum() / max(kept.sum(), 1), 1),
             "n_strict_control_shipped": int(ctl_ship.sum()), "n_strict_control_clipped": int(ctl_rob.sum())}
        for key, v in metrics:
            o[key] = {"kept": mean_ci(v[kept], mth[kept], rng), "lost": mean_ci(v[lost], mth[lost], rng),
                      "gained": mean_ci(v[gained], mth[gained], rng)}
            if tag == "clipped_same_threshold":
                o[key]["lost_minus_kept"] = cmp(f"S3 {name} lost-kept {key}", v[lost], mth[lost], v[kept], mth[kept], rng)
                o[key]["gained_minus_kept"] = cmp(f"S3 {name} gained-kept {key}", v[gained], mth[gained], v[kept],
                                                  mth[kept], rng)
            o[key]["clipped_event_minus_clipped_strict_control"] = cmp(
                f"S3 {name} {tag} event-strict control {key}", v[rob], mth[rob], v[ctl_rob], mth[ctl_rob], rng)
        out[tag] = o
    return out


# --------------------------------------------------------------------------- S4
def s4_left_tail(a, rng, name):
    ev, z, mth, ext, rvol, f20, fz20 = a["eval"], a["z"], a["month"], a["ext"], a["rvol"], a["f20"], a["fz20"]
    with np.errstate(invalid="ignore"):
        subsets = {"ext_le_-1.5": ev & (ext <= -1.5), "ext_le_-1.5_and_absz_le_0.5": ev & (ext <= -1.5) & (np.abs(z) <= 0.5)}
    tails = {"p_f20_le_-0.25_pct": 100 * (f20 <= -0.25), "p_f20_le_-0.40_pct": 100 * (f20 <= -0.40),
             "p_fz20_le_-2_pct": 100 * (fz20 <= -2.0), "p_fz20_le_-3_pct": 100 * (fz20 <= -3.0)}
    out = {"note": "f20 is a LOG return: -0.25 = -22.1% and -0.40 = -33.0% in simple terms; fz20 = f20 / (sig0 * sqrt(20))"}
    for sname, sm in subsets.items():
        o = {"n": int(sm.sum()), "buckets": {}}
        for lo, hi, lab in BUCKETS:
            with np.errstate(invalid="ignore"):
                m = sm & (rvol >= lo) & (rvol < hi)
            b = {"n": int(m.sum())}
            if m.sum():
                for k, v in tails.items():
                    b[k] = mean_ci(v[m].astype(float), mth[m], rng)
                b["n_f20_le_-0.25"] = int((f20[m] <= -0.25).sum())
                b["n_f20_le_-0.40"] = int((f20[m] <= -0.40).sum())
                b["p01_f20"] = rd(np.percentile(f20[m], 1))
                b["p05_f20"] = rd(np.percentile(f20[m], 5))
                b["mean_f20_pct"] = mean_ci(100 * f20[m], mth[m], rng)
                b["median_f20_pct"] = rd(100 * np.median(f20[m]), 3)
                b["mean_fz20"] = rd(fz20[m].mean())
                b["sd_f20"] = rd(f20[m].std())
                b["median_sig0_pct"] = rd(100 * np.median(a["sig0"][m]), 3)
            o["buckets"][lab] = b
        with np.errstate(invalid="ignore"):
            hi_, lo_ = sm & (rvol >= 2.0), sm & (rvol < 2.0)
        con = {"n_high": int(hi_.sum()), "n_low": int(lo_.sum())}
        for k, v in tails.items():
            v = v.astype(float)
            con[k] = {"high": rd(v[hi_].mean(), 4), "low": rd(v[lo_].mean(), 4),
                      "ratio_high_over_low": rd(v[hi_].mean() / v[lo_].mean(), 3) if v[lo_].mean() > 0 else None,
                      "diff_pp": cmp(f"S4 {name} {sname} rvol>=2 vs <2 {k}", v[hi_], mth[hi_], v[lo_], mth[lo_], rng)}
        con["mean_f20_pct"] = {"high": rd(100 * f20[hi_].mean(), 4), "low": rd(100 * f20[lo_].mean(), 4),
                               "diff_pp": cmp(f"S4 {name} {sname} rvol>=2 vs <2 mean f20", 100 * f20[hi_], mth[hi_],
                                              100 * f20[lo_], mth[lo_], rng)}
        bad = hi_ & (f20 <= -0.40)
        mo, cnt = np.unique(mth[bad], return_counts=True)
        top = np.argsort(-cnt)[:3]
        con["high_volume_f20_le_-0.40_concentration"] = {
            "events": int(bad.sum()), "tickers": int(len(np.unique(a["ticker"][bad]))), "months": int(len(mo)),
            "top_months": [{"month": f"{int(mo[i]) // 12}-{int(mo[i]) % 12 + 1:02d}", "events": int(cnt[i])} for i in top]}
        o["rvol_ge_2_vs_lt_2"] = con
        out[sname] = o
    return out


# --------------------------------------------------------------------------- S5
def breakeven(m_t, m_c, loss, ctrl_frac):
    """Share q of TRUE treatment events (observed + missing) that would have to be missing deaths with
    simple return `loss` for the true difference to be zero, when the control lost ctrl_frac * q:
      (1 - q) m_t + q L = (1 - f q) m_c + f q L   =>   q = (m_t - m_c) / ((m_t - L) - f (m_c - L))."""
    d = m_t - m_c
    if not d > 0:
        return 0.0
    return d / ((m_t - loss) - ctrl_frac * (m_c - loss))


def s5_breakeven(a, rng, name):
    ev, z, mth, ext, rvol = a["eval"], a["z"], a["month"], a["ext"], a["rvol"]
    s10 = np.exp(a["f10"]) - 1.0
    with np.errstate(invalid="ignore"):
        T = ev & a["absorb_bottom"]
        C = ev & (ext <= -1.5) & (np.abs(z) <= 0.5) & (rvol < 2.0)
        old = ev & (ext <= -1.5) & ~a["climax_dn"] & ~a["absorb_bottom"]
    d_simple = cmp(f"S5 {name} event-strict control f10 simple pct", 100 * s10[T], mth[T], 100 * s10[C], mth[C], rng)
    d_log = cmp(f"S5 {name} event-strict control f10 log pct", 100 * a["f10"][T], mth[T], 100 * a["f10"][C], mth[C], rng)
    d_fz = cmp(f"S5 {name} event-strict control fz10", a["fz10"][T], mth[T], a["fz10"][C], mth[C], rng)
    d_fzd = cmp(f"S5 {name} event-strict control fzd10", a["fzd10"][T], mth[T], a["fzd10"][C], mth[C], rng)
    d_old = cmp(f"S5 {name} event-old control fz10", a["fz10"][T], mth[T], a["fz10"][old], mth[old], rng)
    m_t, m_c = float(s10[T].mean()), float(s10[C].mean())
    out = {"n_event": int(T.sum()), "n_strict_control": int(C.sum()), "n_old_control": int(old.sum()),
           "mean_f10_simple_pct_event": rd(100 * m_t, 4), "mean_f10_simple_pct_strict_control": rd(100 * m_c, 4),
           "diff_f10_simple_pct": d_simple, "diff_f10_log_pct": d_log, "diff_fz10": d_fz, "diff_fzd10": d_fzd,
           "diff_fz10_vs_old_control": d_old,
           "observed_f10_le_-60pct_per_1000": {"event": rd(1000 * (s10[T] <= -0.6).mean(), 3),
                                               "strict_control": rd(1000 * (s10[C] <= -0.6).mean(), 3)},
           "observed_f10_le_-30pct_per_1000": {"event": rd(1000 * (s10[T] <= -0.3).mean(), 3),
                                               "strict_control": rd(1000 * (s10[C] <= -0.3).mean(), 3)},
           "note": "Sensitivity bound only. The true delisting rate cannot be observed in survivor-only data."}
    be = {}
    for dlab, d in (("point", d_simple["diff"]), ("ci_low", d_simple["lo"]), ("ci_high", d_simple["hi"])):
        mt = m_c + d / 100.0
        row = {"assumed_diff_pct": rd(d, 4)}
        for loss in (-0.6, -1.0):
            for flab, f in (("control_loses_none", 0.0), ("control_loses_half_q", 0.5)):
                q = breakeven(mt, m_c, loss, f)
                row[f"death_{int(100 * loss)}pct_{flab}_per_1000_events"] = rd(1000 * q, 2)
        be[dlab] = row
    out["breakeven_missing_deaths"] = be
    return out


# --------------------------------------------------------------------------- S6
def s6_coverage(a, name):
    dates, starts, ends, tk = a["date"], a["starts"], a["ends"], a["ticker"]
    cal = np.unique(dates)
    idx = np.searchsorted(cal, dates)
    first_i, last_i = idx[starts], idx[ends - 1]
    n_cal = len(cal)
    early = (n_cal - 1 - last_i) > 30
    late = first_i > 30
    gaps = np.r_[0, np.diff(idx)]
    gaps[starts] = 0
    max_gap = np.maximum.reduceat(gaps, starts)
    lc = np.log(a["close"])
    detail = []
    for j in np.flatnonzero(early):
        s, e = starts[j], ends[j]
        k = min(60, e - s - 1)
        detail.append({"ticker": str(tk[s]), "last_date": str(pd.Timestamp(dates[e - 1]).date()),
                       "trading_days_before_set_end": int(n_cal - 1 - last_i[j]),
                       "log_return_last_60_bars": rd(lc[e - 1] - lc[e - 1 - k], 3),
                       "max_rvol_last_20_bars": rd(np.nanmax(a["rvol"][max(s, e - 20):e]), 2),
                       "last_close": rd(a["close"][e - 1], 2)})
    lr = np.array([x["log_return_last_60_bars"] for x in detail], dtype=float)
    fd, fc = np.unique(dates[starts], return_counts=True)
    top_first = [{"date": str(pd.Timestamp(fd[i]).date()), "tickers": int(fc[i])} for i in np.argsort(-fc)[:3]]
    yrs, yc = np.unique(pd.DatetimeIndex(dates[starts]).year, return_counts=True)
    return {"tickers": int(len(starts)), "set_first_date": str(pd.Timestamp(cal[0]).date()),
            "set_last_date": str(pd.Timestamp(cal[-1]).date()), "set_trading_days": int(n_cal),
            "ends_more_than_30_trading_days_early": int(early.sum()),
            "ends_before_set_last_date": int((last_i < n_cal - 1).sum()),
            "max_trading_days_ending_early": int((n_cal - 1 - last_i).max()),
            "most_common_first_dates": top_first,
            "first_bar_year_counts": {str(int(y)): int(c) for y, c in zip(yrs, yc)},
            "starts_more_than_30_trading_days_late": int(late.sum()),
            "starts_more_than_252_trading_days_late": int((first_i > 252).sum()),
            "internal_gap_more_than_30_trading_days": int((max_gap > 30).sum()),
            "internal_gap_more_than_5_trading_days": int((max_gap > 5).sum()),
            "early_enders_median_log_return_last_60_bars": rd(np.median(lr), 3) if len(lr) else None,
            "early_enders_with_last_60_bar_log_return_below_-0.5": int((lr < -0.5).sum()) if len(lr) else 0,
            "early_enders_detail_first_40": sorted(detail, key=lambda x: x["last_date"])[:40]}


# --------------------------------------------------------------------------- second route
def second_route(a, panel_dir, name):
    """Independent recomputation of headline numbers with pandas rolling windows (no bars_since)."""
    d = pd.DataFrame({"ticker": a["ticker"], "z": a["z"], "zr": a["z_rob"], "eval": a["eval"],
                      "ab": a["absorb_bottom"], "rvol": a["rvol"], "ext": a["ext"]})
    d["shock"] = (d["z"].abs() >= 4.0).astype(float)
    g = d.groupby("ticker", sort=False)["shock"]
    prev = g.shift(1)
    d["s20"] = prev.groupby(d["ticker"], sort=False).rolling(20, min_periods=1).max().reset_index(level=0, drop=True)
    d["s60"] = prev.groupby(d["ticker"], sort=False).rolling(60, min_periods=1).max().reset_index(level=0, drop=True)
    e = d[d["eval"]]
    after, calm = e[e["s20"] == 1], e[e["s60"] != 1]
    p_after, p_calm = (after["z"].abs() <= 0.5).mean(), (calm["z"].abs() <= 0.5).mean()
    rob = e[(e["rvol"] >= 2.0) & (e["ext"] <= -1.5) & (e["zr"].abs() <= 0.5)]
    lost = e[e["ab"] & ~((e["zr"].abs() <= 0.5))]
    return {"set": name, "p_absz_le_0.5_after_shock4_k1-20_pct": rd(100 * p_after, 2),
            "p_absz_le_0.5_calm_pct": rd(100 * p_calm, 2), "diff_pp": rd(100 * (p_after - p_calm), 4),
            "n_after": int(len(after)), "n_calm": int(len(calm)), "n_clipped_event": int(len(rob)),
            "n_lost": int(len(lost)), "share_events_with_shock4_prev_20_pct": rd(100 * e.loc[e["ab"], "s20"].mean(), 4)}


# --------------------------------------------------------------------------- headline table
def headline(r):
    """The tests fixed after looking at set A only (A = development, every other set = one confirmation run)."""
    s2, s3, s4, s5 = r["S2_recent_shock"], r["S3_clipped_event"], r["S4_left_tail"], r["S5_breakeven_survivorship"]
    h = {}
    if "S1_event_study" in r:
        w = r["S1_event_study"]["abs_z_ge_4"]["windows_vs_calm"]["k1-20"]
        h["H1_p_small_z_k1-20_after_shock4_minus_calm_pp"] = w["diff_p_absz_le_0.5_pp"]
        h["H1b_same_with_clipped_sigma_pp"] = w["diff_p_absz_rob_le_0.5_pp"]
        h["H1c_sigma_over_clipped_excess_k1-20_pct"] = w["ratio_excess_vs_calm_pct"]
    sh = s2["share_with_shock_in_previous_20_bars"]["abs_z_ge_4_any"]
    h["H2_share_events_with_recent_shock4_pct"] = sh["share_event_pct"]
    h["H2_share_strict_control_with_recent_shock4_pct"] = sh["share_strict_control_pct"]
    h["H2_event_minus_control_pp"] = sh["diff_event_minus_control_pp"]
    dn = s2["event_rate_after_shock_vs_calm"]["after_down_shock_abs_z_ge_4"]
    h["H2b_p_small_z_given_ext_after_down_shock_minus_calm_pp"] = dn["diff_p_absz_le_0.5_given_ext_pp"]
    h["H2b_same_with_clipped_sigma_pp"] = dn["diff_p_absz_rob_le_0.5_given_ext_pp"]
    h["H2c_events_per_1000_bars_after_down_shock"] = dn["shock_window"]["events_per_1000_bars"]
    h["H2c_events_per_1000_bars_calm"] = dn["calm"]["events_per_1000_bars"]
    fw = s2["event_forward_returns_with_vs_without_recent_shock"]["abs_z_ge_4_any"]
    h["H3_event_fz10_with_minus_without_recent_shock4"] = fw["fz10"]["with_minus_without"]
    h["H3_event_fzd10_with_minus_without_recent_shock4"] = fw["fzd10"]["with_minus_without"]
    c = s3["clipped_same_threshold"]
    h["H4_events_shipped_kept_lost_gained"] = [c["n_shipped"], c["kept"], c["lost"], c["gained"]]
    h["H4_lost_pct_of_shipped"] = c["lost_pct_of_shipped"]
    h["H4_lost_pct_level_matched"] = s3["clipped_level_matched"]["lost_pct_of_shipped"]
    h["H4_gained_level_matched"] = s3["clipped_level_matched"]["gained"]
    h["H4b_fz10_lost_minus_kept"] = c["fz10"]["lost_minus_kept"]
    h["H4b_fzd10_lost_minus_kept"] = c["fzd10"]["lost_minus_kept"]
    for sub, tag in (("ext_le_-1.5", "H5"), ("ext_le_-1.5_and_absz_le_0.5", "H5b")):
        con = s4[sub]["rvol_ge_2_vs_lt_2"]
        for k in ("p_f20_le_-0.25_pct", "p_f20_le_-0.40_pct", "p_fz20_le_-2_pct"):
            h[f"{tag}_{k}_rvol_ge_2_vs_lt_2"] = {"high": con[k]["high"], "low": con[k]["low"], **con[k]["diff_pp"]}
    h["H6_event_minus_strict_control_f10_simple_pct"] = s5["diff_f10_simple_pct"]
    h["H6_event_minus_strict_control_fz10"] = s5["diff_fz10"]
    h["H6_event_minus_strict_control_fzd10"] = s5["diff_fzd10"]
    h["H6_breakeven_deaths_-60pct_control_none_per_1000"] = {
        k: v["death_-60pct_control_loses_none_per_1000_events"] for k, v in s5["breakeven_missing_deaths"].items()}
    return h


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=DEFAULT_PANEL)
    ap.add_argument("--sets", nargs="*", default=list(SET_ORDER))
    ap.add_argument("--out", default=str(ROOT / "results" / "e12_sigma_shock_and_tails.json"))
    ap.add_argument("--seed", type=int, default=SEED)
    a_ = ap.parse_args()
    t0 = time.time()
    res = {"experiment": "e12_sigma_shock_and_tails", "seed": a_.seed, "n_boot": e05.N_BOOT, "panel": a_.panel,
           "definitions": {
               "shock": "|z| >= 4 (also 3) with the shipped z; 'down' = z <= -thr",
               "clipped_sigma": "sqrt(tfs.trend.robust_var_lagged(r, 50, 3.0))",
               "calm_baseline": "eval bars with no shock of the same threshold in the previous 60 bars",
               "recent_shock": "a shock in bars t-20 .. t-1",
               "strict_control": "eval & ext <= -1.5 & |z| <= 0.5 & rvol < 2",
               "units": "probabilities and shares in percent / percentage points; fz in risk units; f10_simple in percent"},
           "sets": {}}
    dev = load(a_.panel, "A")
    c_level, n_calm = calm_level(dev)
    res["level_match_constant_from_A"] = {"c": rd(c_level, 5), "n_calm_bars": n_calm}
    res["sigma_reproduction_check_A"] = sigma_check(dev)
    for name in [s for s in SET_ORDER if s in a_.sets]:
        a = dev if name == "A" else load(a_.panel, name)
        rng = np.random.default_rng(a_.seed + SEED_OFFSET[name])
        n0 = len(COMPARISONS)
        r = {"eval_rows": int(a["eval"].sum()), "tickers": int(len(a["starts"]))}
        if name in S1_SETS:
            r["S1_event_study"] = s1_event_study(a, rng, name)
        r["S2_recent_shock"] = s2_recent_shock(a, rng, name)
        r["S3_clipped_event"] = s3_clipped_event(a, rng, name, c_level)
        r["S4_left_tail"] = s4_left_tail(a, rng, name)
        r["S5_breakeven_survivorship"] = s5_breakeven(a, rng, name)
        r["S6_coverage"] = s6_coverage(a, name)
        r["second_route_check"] = second_route(a, a_.panel, name)
        r["comparisons_in_set"] = len(COMPARISONS) - n0
        r["role"] = "development" if name == "A" else "confirmation (run once)"
        r["headline"] = headline(r)
        res["sets"][name] = r
        print(f"[{name}] done, {len(COMPARISONS) - n0} comparisons, {time.time() - t0:.0f}s", flush=True)
        del a
    res["comparisons_run"] = len(COMPARISONS)
    res["comparisons_without_data"] = TALLY["empty"]
    res["comparisons_with_95pct_interval_excluding_zero"] = TALLY["interval_excludes_zero"]
    res["protocol"] = (
        "Set A is the development set: the script was first run on A alone and every threshold, window and test "
        "was fixed there. B, DJ, LH and MS were then run once. The descriptive fields first_k_*, the S4 "
        "concentration block and the S6 first-date structure were added after that run; they use no resampling "
        "and the fixed seeds reproduce every earlier number exactly. No correction for multiple comparisons is "
        "applied: read single intervals with that in mind. S1 is not run on DJ (31 stocks inside LH).")
    res["comparison_labels"] = COMPARISONS
    pathlib.Path(a_.out).write_text(json.dumps(res, indent=1))
    print("wrote", a_.out, f"({len(COMPARISONS)} comparisons, {time.time() - t0:.0f}s)")


def sigma_check(a):
    """The panel sigma must equal the unclipped lagged EWMA recomputed here (clip = 0)."""
    worst = 0.0
    for s, e in list(zip(a["starts"], a["ends"]))[:40]:
        v = np.sqrt(robust_var_lagged(a["r"][s:e], SPAN, 0.0))
        m = a["eval"][s:e]
        worst = max(worst, float(np.nanmax(np.abs(v[m] - a["sigma"][s:e][m]) / a["sigma"][s:e][m])))
    return {"tickers_checked": 40, "max_relative_difference_on_eval_rows": float(f"{worst:.3g}")}


if __name__ == "__main__":
    main()
