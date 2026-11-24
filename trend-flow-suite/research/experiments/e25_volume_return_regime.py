#!/usr/bin/env python3
"""E25 - Second external review, objection 4: the per-stock "continuation regime" of Llorente,
Michaely, Saar and Wang (2002), the study that was planned as E15 and never ran.

PLAN (written before the numbers were computed)
LMSW: r[t+1] = c0 + c1 r[t] + c2 r[t] V[t] + e, with V the detrended log volume. c2 > 0 (returns
on heavy volume continue) for stocks with much informed trading, c2 < 0 (they reverse) for the
rest. The reviewer's objection: averaging all stocks cancels the two regimes, so E18 could not see
them; a rolling estimate of c2 per stock might separate them and would justify a complementary
"continuation regime" indicator.
Test, out of sample by construction:
  - returns in risk units, clipped at +-4; V = ln(volume) - its lagged robust level (tfs.relvol),
    clipped at +-3;
  - c2 of each stock on each day from the previous 250 pairs (r[s], r[s+1]) with s+1 <= t
    (a 750-pair window was added afterwards as a robustness check);
  - stocks ranked by c2 into fifths on each day.
  Outcomes for the top fifth minus the bottom fifth:
   O1  on days with unusual volume (zV >= 2): the product r[t] x r[t+1] in risk units (the regime
       itself, one bar ahead);
   O2  on strong moves with unusual volume (zV >= 2, |move| >= 1.5 sigma): the signed forward return
       sign(r[t]) x fzd over 1, 2, 3, 5 and 10 bars (date-demeaned, risk-scaled; + = continuation).
  Also: persistence of c2 (rank correlation with its own value one window later) and its relation to
  dollar volume. Month-block bootstrap. MS (2006-2017) and EM (2018-2026). Survivors only.
Decision rule fixed in advance: a complementary indicator is worth designing only if O1 and O2 at
1-3 bars are positive with intervals excluding zero in BOTH sets.

  python3 -I experiments/e25_volume_return_regime.py [--panel DIR]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json
from multiprocessing import Pool

import numpy as np
import pandas as pd

import experiments.e18_relvol_v3_confirmation as e18
from tfs.relvol import RelVolParams, log_level_lagged, var_lagged

P = RelVolParams()
WINDOWS = (250, 750)                        # 750 bars: robustness, added after the plan
HS = (1, 2, 3, 5, 10)
COLS = ["ticker", "date", "month", "eval", "close", "volume", "dvol", "r", "sig0"]


def one(args):
    v, r, sig0, c, W = args
    MIN_PAIRS = int(0.6 * W)
    n = len(v)
    k = np.zeros(n, dtype=np.int64)
    mu, s, cnt = log_level_lagged(v, k, P.span_daily, P.scale_span, P.clip, P.min_clip)
    var, nv = var_lagged(r, k, P.span_daily, P.clip, P.min_clip)
    with np.errstate(divide="ignore", invalid="ignore"):
        lv = np.where(v > 0, np.log(np.where(v > 0, v, 1.0)), np.nan)
        ok = cnt >= P.min_obs_daily
        V = np.clip(np.where(ok, lv - mu, np.nan), -3.0, 3.0)
        zv = np.where(ok & (s > 0), (lv - mu) / s, np.nan)
        z3 = np.where((nv >= P.min_obs_daily) & (var > 0), r / np.sqrt(var), np.nan)
        zr = np.clip(r / sig0, -4.0, 4.0)
    x1, x2 = zr[:-1], (zr * V)[:-1]
    y = zr[1:]
    good = np.isfinite(x1) & np.isfinite(x2) & np.isfinite(y)

    def cs(a):
        return np.concatenate([[0.0], np.cumsum(np.where(good, a, 0.0))])
    one_ = np.ones(n - 1)
    names = {"n": one_, "x1": x1, "x2": x2, "y": y, "x1x1": x1 * x1, "x1x2": x1 * x2, "x2x2": x2 * x2, "x1y": x1 * y, "x2y": x2 * y}
    C = {kk: cs(np.nan_to_num(a)) for kk, a in names.items()}
    c2 = np.full(n, np.nan)
    t = np.arange(W + 1, n)                       # pairs s in [t-W, t-1]  ->  C[t] - C[t-W]
    if len(t):
        S = {kk: C[kk][t] - C[kk][t - W] for kk in C}
        A = np.empty((len(t), 3, 3))
        A[:, 0, 0], A[:, 0, 1], A[:, 0, 2] = S["n"], S["x1"], S["x2"]
        A[:, 1, 0], A[:, 1, 1], A[:, 1, 2] = S["x1"], S["x1x1"], S["x1x2"]
        A[:, 2, 0], A[:, 2, 1], A[:, 2, 2] = S["x2"], S["x1x2"], S["x2x2"]
        b = np.stack([S["y"], S["x1y"], S["x2y"]], axis=1)
        okm = (S["n"] >= MIN_PAIRS) & (np.abs(np.linalg.det(A)) > 1e-6)
        if okm.any():
            sol = np.linalg.solve(A[okm], b[okm][:, :, None])[:, :, 0]
            c2[t[okm]] = sol[:, 2]
    lnc = np.log(c)
    fw = []
    for h in HS:
        f = np.full(n, np.nan)
        f[:-h] = lnc[h:] - lnc[:-h]
        fw.append(f.astype(np.float32))
    nxt = np.r_[zr[1:], np.nan]
    return (zv.astype(np.float32), z3.astype(np.float32), c2.astype(np.float32), (zr * nxt).astype(np.float32), *fw)


def run_set(name, panel, seed, W):
    d = pd.read_parquet(pathlib.Path(panel) / f"panel_{name}.parquet", columns=COLS)
    gs = [tuple(g[k].to_numpy(dtype=float) for k in ("volume", "r", "sig0", "close")) + (W,) for _, g in d.groupby("ticker", sort=False)]
    with Pool(3) as pool:
        res = pool.map(one, gs, chunksize=16)
    for i, k in enumerate(["zv", "z3", "c2", "prod1"] + [f"f{h}" for h in HS]):
        d[k] = np.concatenate([x[i] for x in res])
    for h in HS:
        d[f"fd{h}"] = (d[f"f{h}"] - d.groupby("date")[f"f{h}"].transform("mean")) / (d["sig0"] * np.sqrt(h))
    # persistence of c2 and its relation to size, sampled once a month
    d["c2_fwd"] = d.groupby("ticker", sort=False)["c2"].shift(-W)
    d["dv_med"] = d.groupby("ticker", sort=False)["dvol"].transform("median")
    first = d[d["c2"].notna()].groupby(["ticker", "month"], sort=False).head(1)
    e = d[d["eval"] & d["c2"].notna()].copy()
    e["q"] = e.groupby("date")["c2"].transform(lambda x: pd.qcut(x.rank(method="first"), 5, labels=False) if len(x) >= 50 else np.nan)
    e = e[e["q"].notna()]
    rng = np.random.default_rng(seed)
    top, bot = (e["q"] == 4).to_numpy(), (e["q"] == 0).to_numpy()
    with np.errstate(invalid="ignore"):
        hv = (e["zv"] >= 2).to_numpy()
        ev = hv & (np.abs(e["z3"].to_numpy()) >= 1.5)
    sg = np.sign(e["r"].to_numpy())
    out = {"set": name, "window": W, "rows": int(len(e)), "stocks": int(e["ticker"].nunique()),
           "c2_quantiles": {str(q): round(float(e["c2"].quantile(q)), 4) for q in (0.1, 0.5, 0.9)},
           "c2_rank_corr_with_itself_one_window_later": round(float(first[["c2", "c2_fwd"]].corr(method="spearman").iloc[0, 1]), 3),
           "c2_rank_corr_with_median_dollar_volume": round(float(first[["c2", "dv_med"]].corr(method="spearman").iloc[0, 1]), 3),
           "O1_product_next_bar_on_unusual_volume": e18.cmp(e, hv & top, hv & bot, "prod1", rng),
           "O1_levels": {"top_fifth": round(float(np.nanmean(e["prod1"].to_numpy()[hv & top])), 4),
                         "bottom_fifth": round(float(np.nanmean(e["prod1"].to_numpy()[hv & bot])), 4),
                         "all": round(float(np.nanmean(e["prod1"].to_numpy()[hv])), 4)},
           "O2_signed_forward_return_after_strong_move_on_unusual_volume": {}}
    for h in HS:
        e[f"s{h}"] = sg * e[f"fd{h}"].to_numpy()
        x = e18.cmp(e, ev & top, ev & bot, f"s{h}", rng)
        x["level_top"] = round(float(np.nanmean(e[f"s{h}"].to_numpy()[ev & top])), 4)
        x["level_bottom"] = round(float(np.nanmean(e[f"s{h}"].to_numpy()[ev & bot])), 4)
        x["level_all_events"] = round(float(np.nanmean(e[f"s{h}"].to_numpy()[ev])), 4)
        out["O2_signed_forward_return_after_strong_move_on_unusual_volume"][str(h)] = x
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=e18.DEFAULT_PANEL)
    a = ap.parse_args()
    res = {}
    for W in WINDOWS:
        for i, name in enumerate(("MS", "EM")):
            res[f"{name}_w{W}"] = r = run_set(name, a.panel, 250 + i, W)
            print(name, "window", W, "rows", r["rows"], "stocks", r["stocks"], "c2", r["c2_quantiles"], "persistence", r["c2_rank_corr_with_itself_one_window_later"],
                  "size corr", r["c2_rank_corr_with_median_dollar_volume"])
            o = r["O1_product_next_bar_on_unusual_volume"]
            print(f"  O1 top-bottom {o['diff']} [{o['lo']}, {o['hi']}] n={o['n']}/{o['n_c']}  levels {r['O1_levels']}")
            for h, x in r["O2_signed_forward_return_after_strong_move_on_unusual_volume"].items():
                print(f"  O2 h={h:>2s} top-bottom {x['diff']} [{x['lo']}, {x['hi']}] n={x['n']}/{x['n_c']}  top {x['level_top']} bottom {x['level_bottom']} all {x['level_all_events']}")
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e25_volume_return_regime.json"
    p.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
