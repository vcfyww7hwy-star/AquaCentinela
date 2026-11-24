#!/usr/bin/env python3
"""E24 - Second external review, objection 3 (the day estimate) and part of objection 6.

Data: the cleaned intraday sample of experiments/intraday_common.py (5-minute bars from public
1-minute Yahoo bars, 29 Aug 2025 - 5 Oct 2026) and the daily file of the same stocks. The first run
of this experiment (31 Aug - 6 Nov 2026, uncleaned) gave the same answers to A and B; its intraday
flag rates were distorted by corrupted prints and are replaced by E26.

PLAN (written before the numbers were computed)
 A  The intraday bars sum to about 0.83 of the daily volume (E19). Which volume is missing? If it
    is the closing auction and late prints, the ratio must fall on days when the close carries
    index and expiry trades. Ratio by day; expiry and index-rebalance days against the other days;
    relation between a stock's ratio on a day and its relative volume that day.
 B  The day estimate of the v3 pane (copied below) was fitted with intraday volume on both sides.
    The pane divides the live volume so far by a normal built from DAILY bars and is judged against
    the DAILY final volume. Bias and error of the shipped constants in that setting, taking the
    intraday sum so far as the live volume (that is: assuming the live feed misses what these
    intraday bars miss). Normal = exp(mu) of tfs.relvol on the daily file (span 50).
 C  Control for the flag rate with a short history: each stock's DAILY series cut into 49-bar
    pieces, the estimator started afresh on each piece with the intraday warm-up of 10 bars.

  python3 -I experiments/e24_intraday_second_review.py --bars DIR --daily FILE.parquet
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json
import math

import numpy as np
import pandas as pd

from experiments.intraday_common import load_clean
from tfs.relvol import RelVolParams, log_level_lagged, mechanical_day

P = RelVolParams()

# The day estimate as shipped in Relative Volume v3 (constants from the first run of E19, Q4b), kept here
# because v4 removed it.
DAY_GRID = tuple(range(30, 361, 30))
DAY_SHARE = (0.081, 0.152, 0.220, 0.287, 0.348, 0.410, 0.468, 0.527, 0.588, 0.652, 0.719, 0.798)
DAY_BETA = (0.384, 0.519, 0.598, 0.653, 0.699, 0.740, 0.772, 0.798, 0.826, 0.850, 0.874, 0.902)
DAY_SD = (0.455, 0.417, 0.387, 0.362, 0.336, 0.310, 0.284, 0.259, 0.230, 0.198, 0.162, 0.111)


def day_estimate(rvol_so_far: float, elapsed_min: float):
    """(estimate, low, high) of the day's final relative volume from the relative volume so far."""
    if not (30.0 <= elapsed_min <= 360.0) or not (rvol_so_far > 0):
        return math.nan, math.nan, math.nan
    x = (elapsed_min - 30.0) / 30.0
    i = max(0, min(len(DAY_GRID) - 2, int(math.floor(x))))
    w = max(0.0, min(1.0, x - i))

    def lin(a):
        return a[i] * (1.0 - w) + a[i + 1] * w
    est = math.exp(lin(DAY_BETA) * math.log(rvol_so_far / lin(DAY_SHARE)))
    sd = lin(DAY_SD)
    return est, est * math.exp(-sd), est * math.exp(sd)


def zv_fresh(v, need):
    k = np.zeros(len(v), dtype=np.int64)
    mu, s, n = log_level_lagged(v, k, P.span_intraday, P.scale_span, P.clip, P.min_clip)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where((n >= need) & (s > 0) & (v > 0), (np.log(np.where(v > 0, v, 1.0)) - mu) / s, np.nan)
    return z, n


def moments(z):
    z = z[np.isfinite(z)]
    m, sd = z.mean(), z.std()
    return {"n": int(len(z)), "sd": round(float(sd), 3), "skew": round(float(((z - m) ** 3).mean() / sd ** 3), 3),
            "excess_kurtosis": round(float(((z - m) ** 4).mean() / sd ** 4 - 3), 3), "share_ge2_pct": round(100 * float((z >= 2).mean()), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", required=True)
    ap.add_argument("--daily", required=True)
    a = ap.parse_args()
    b, dly_all, clean = load_clean(a.bars, a.daily)
    days = np.sort(b["day"].unique())
    g = b.groupby(["ticker", "day"]).agg(n=("volume", "size"), vol=("volume", "sum"), px=("close", "last"))
    g["dv"] = g["vol"] * g["px"]
    t = g.groupby("ticker").agg(days=("n", "size"), full=("n", lambda x: (x >= 70).mean()), px=("px", "median"), dv=("dv", "median"))
    keep = t[(t["days"] >= 0.75 * len(days)) & (t["full"] >= 0.9) & (t["px"] >= 5) & (t["dv"] >= 5e6)].index
    b = b[b["ticker"].isin(keep)].copy()
    out = {"universe": int(len(keep)), "sessions": int(len(days)), "cleaning": clean}

    dly = dly_all[dly_all["ticker"].isin(set(keep))].sort_values(["ticker", "day"]).reset_index(drop=True)
    parts = []
    for _, d in dly.groupby("ticker", sort=False):
        v = d["dvol"].to_numpy(dtype=float)
        mu, s, n = log_level_lagged(v, np.zeros(len(v), dtype=np.int64), P.span_daily, P.scale_span, P.clip, P.min_clip)
        parts.append(np.where(n >= P.min_obs_daily, np.exp(mu), np.nan))
    dly["normal"] = np.concatenate(parts)
    full = dly[dly["day"] >= pd.Timestamp("2018-01-01")]
    dly = dly[dly["day"].isin(days)]

    # ---- A: which volume do the intraday bars miss?
    iv = b.groupby(["ticker", "day"])["volume"].sum().rename("iv").reset_index().merge(dly, on=["ticker", "day"])
    iv = iv[(iv["dvol"] > 0) & (iv["iv"] > 0)]
    iv["ratio"] = iv["iv"] / iv["dvol"]
    iv["rvol_day"] = iv["dvol"] / iv["normal"]
    byd = iv.groupby("day")["ratio"].median()
    md = mechanical_day(pd.DatetimeIndex(byd.index))
    mech_days = set(byd.index[md])
    plain = iv[~iv["day"].isin(mech_days)]
    out["A_missing_volume"] = {
        "median_ratio_all": round(float(iv["ratio"].median()), 3),
        "ordinary_days": {"median": round(float(byd[~md].median()), 3), "p05": round(float(byd[~md].quantile(0.05)), 3), "p95": round(float(byd[~md].quantile(0.95)), 3)},
        "expiry_and_index_rebalance_days": {str(k)[:10]: round(float(v), 3) for k, v in byd[md].items()},
        "five_lowest_other_days": {str(k)[:10]: round(float(v), 3) for k, v in byd[~md].sort_values().head(5).items()},
        "median_ratio_by_final_rvol_of_the_day": {lab: round(float(plain.loc[(plain["rvol_day"] >= lo) & (plain["rvol_day"] < hi), "ratio"].median()), 3)
                                                  for lab, lo, hi in (("<0.8x", 0, 0.8), ("0.8-1.25x", 0.8, 1.25), ("1.25-2x", 1.25, 2), (">=2x", 2, 1e9))},
        "share_of_intraday_volume_in_last_5_minutes": round(float(b.loc[b["mins"] >= 385, "volume"].sum() / b["volume"].sum()), 4),
        "share_of_intraday_volume_in_first_5_minutes": round(float(b.loc[b["mins"] < 5, "volume"].sum() / b["volume"].sum()), 4)}

    # ---- B: the shipped day estimate against the daily final, normal from daily bars
    resb = {}
    fin = plain.set_index(["ticker", "day"])
    for m in (30, 60, 120, 210, 300, 360):
        c = b[b["mins"] < m].groupby(["ticker", "day"])["volume"].sum().rename("c")
        j = fin.join(c, how="inner")
        j = j[np.isfinite(j["normal"]) & (j["c"] > 0)]
        est = np.array([day_estimate(x, m)[0] for x in (j["c"] / j["normal"]).to_numpy()])
        e = np.log(est / j["rvol_day"].to_numpy())
        hi = est >= 2.0
        resb[str(m)] = {"n": int(len(e)), "median_error_pct": round(100 * float(np.exp(np.median(e)) - 1), 1),
                        "mean_abs_error_ln": round(float(np.abs(e).mean()), 3),
                        "final_ge2_share_pct": round(100 * float((j["rvol_day"] >= 2).mean()), 2),
                        "estimate_ge2_share_pct": round(100 * float(hi.mean()), 2),
                        "days_ending_ge2_that_the_estimate_read_ge2_pct": round(100 * float(hi[(j["rvol_day"] >= 2).to_numpy()].mean()), 1),
                        "estimate_ge2_that_ended_ge2_pct": round(100 * float((j["rvol_day"].to_numpy()[hi] >= 2).mean()), 1) if hi.sum() else None}
    out["B_day_estimate_vs_daily_final"] = resb

    # ---- C: control, daily bars with a short history (49-bar pieces, fresh start, warm-up 10)
    zc, nc = [], []
    for _, d in full.groupby("ticker", sort=False):
        v = d["dvol"].to_numpy(dtype=float)
        for st in range(0, len(v) - 48, 49):
            z, n = zv_fresh(v[st:st + 49], P.min_obs_intraday)
            zc.append(z)
            nc.append(n)
    zc, nc = np.concatenate(zc), np.concatenate(nc)
    resc = {"all": moments(zc)}
    for lab, lo, hi in (("10-19", 10, 19), ("20-29", 20, 29), ("30-48", 30, 48)):
        resc[lab] = moments(zc[(nc >= lo) & (nc <= hi)])
    out["C_daily_bars_with_a_49_bar_history"] = resc

    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e24_intraday_second_review.json"
    p.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
