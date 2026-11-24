#!/usr/bin/env python3
"""E18 - Does anything in the Relative Volume pane carry information, old or new definition,
including the years after 2018?

PLAN (written before the v3 numbers were computed; P0 had been run once and is repeated here)
Definitions under test are those of tfs/relvol.py (v3), fixed in advance from E12 and E13, which
used no returns: normal volume = clipped average of ln(volume), flag zV >= 2, clipped sigma.

Primary family (difference of means of fzd10, month-block bootstrap, Holm over the 7 tests):
  P0      shipped mark on the modern set EM: S & rvol>=2 versus S & rvol<2, S = eval & ext<=-1.5 & |z|<=0.5
  P1..P6  v3 mark on A, B, DJ, LH, MS, EM: S3 & zV>=2 versus S3 & zV<2, S3 = eval & ext<=-1.5 & |z3|<=0.5
Secondary (descriptive, no multiplicity adjustment):
  S1  generalisation (the "high-volume premium without a price move"): among bars with |z3|<=0.5,
      zV>=2 versus zV<2 inside three extension buckets (<=-1.5, between, >=+1.5): fzd10, fzd20
  S2  Gervais-Kaniel-Mingelgrin design: today's volume against its own previous 49 days,
      HIGH = above at least 45 of them, LOW = above at most 4, NORMAL otherwise:
      HIGH-NORMAL and LOW-NORMAL on fzd10, fzd20 and fx20 (percent)
  S3  strong move on unusual volume: |z3|>=1.5 & zV>=2: sign(r)*fzd5 and sign(r)*fzd10
      (positive = continuation), against strong moves on ordinary volume (zV<1)
  S4  the v3 mark on EM by period; counts of shipped and v3 marks and their overlap
Sets: A (development), B, DJ, LH, MS (see E10) and EM (2018-02-08 .. 2026-10, see E10b).
All sets hold survivors only. Daily bars.

  python3 -I experiments/e18_relvol_v3_confirmation.py [--panel DIR]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

import experiments.e05_validation_lite as e05
from tfs.relvol import RelVolParams, log_level_lagged, var_lagged

DEFAULT_PANEL = "/tmp/claude-0/-home-user-AquaCentinela/b2916ecb-3cd8-557a-8730-1dacd8557876/scratchpad/panel"
SETS = ("A", "B", "DJ", "LH", "MS", "EM")
COLS = ["ticker", "date", "month", "eval", "volume", "r", "ext", "rvol", "z", "fzd5", "fzd10", "fzd20",
        "fz10", "fx10", "fx20", "f10"]
P = RelVolParams()
N_BOOT = 2000


def feats(args):
    v, r = args
    n = len(v)
    keys = np.zeros(n, dtype=np.int64)
    mu, s, cnt = log_level_lagged(v, keys, P.span_daily, P.scale_span, P.clip, P.min_clip)
    var, nv = var_lagged(r, keys, P.span_daily, P.clip, P.min_clip)
    with np.errstate(divide="ignore", invalid="ignore"):
        lv = np.where(v > 0, np.log(np.where(v > 0, v, 1.0)), np.nan)
        ok = cnt >= P.min_obs_daily
        zv = np.where(ok & (s > 0), (lv - mu) / s, np.nan)
        z3 = np.where((nv >= P.min_obs_daily) & (var > 0), r / np.sqrt(var), np.nan)
    # rank of today's volume among the previous 49 (number of them strictly below today)
    below = np.full(n, np.nan)
    if n > 49:
        w = np.lib.stride_tricks.sliding_window_view(v, 49)[:-1]          # row j = v[j .. j+48]
        below[49:] = (w < v[49:, None]).sum(axis=1)
    return zv.astype(np.float32), z3.astype(np.float32), below.astype(np.float32)


def boot(v_s, m_s, v_c, m_c, rng):
    ks, kc = np.isfinite(v_s), np.isfinite(v_c)
    v_s, m_s, v_c, m_c = v_s[ks], m_s[ks], v_c[kc], m_c[kc]
    if len(v_s) < 5 or len(v_c) < 5:
        return {"diff": None, "lo": None, "hi": None, "p": None, "n": int(len(v_s)), "n_c": int(len(v_c))}
    mc = np.unique(np.concatenate([m_s, m_c]))
    ss, ns = e05._agg(v_s, m_s, mc)
    sc, nc = e05._agg(v_c, m_c, mc)
    est = ss.sum() / ns.sum() - sc.sum() / nc.sum()
    idx = rng.integers(0, len(mc), (N_BOOT, len(mc)))
    with np.errstate(divide="ignore", invalid="ignore"):
        bt = ss[idx].sum(1) / ns[idx].sum(1) - sc[idx].sum(1) / nc[idx].sum(1)
    bt = bt[np.isfinite(bt)]
    lo, hi = np.percentile(bt, [2.5, 97.5])
    p = 2.0 * min((bt <= 0).mean(), (bt >= 0).mean())
    return {"diff": round(float(est), 4), "lo": round(float(lo), 4), "hi": round(float(hi), 4),
            "p": round(float(max(p, 1.0 / N_BOOT)), 4), "n": int(len(v_s)), "n_c": int(len(v_c))}


def cmp(d, mask_s, mask_c, col, rng, scale=1.0):
    v, m = d[col].to_numpy() * scale, d["month"].to_numpy()
    return boot(v[mask_s], m[mask_s], v[mask_c], m[mask_c], rng)


def run_set(name, panel, seed):
    t0 = time.time()
    d = pd.read_parquet(pathlib.Path(panel) / f"panel_{name}.parquet", columns=COLS)
    groups = [(g["volume"].to_numpy(dtype=float), g["r"].to_numpy(dtype=float)) for _, g in d.groupby("ticker", sort=False)]
    with Pool(3) as pool:
        res = pool.map(feats, groups, chunksize=16)
    d["zv"] = np.concatenate([x[0] for x in res])
    d["z3"] = np.concatenate([x[1] for x in res])
    d["below"] = np.concatenate([x[2] for x in res])
    d = d[d["eval"]].reset_index(drop=True)
    rng = np.random.default_rng(seed)
    ext, z, rvol, zv, z3 = (d[k].to_numpy() for k in ("ext", "z", "rvol", "zv", "z3"))
    out = {"set": name, "eval_rows": int(len(d)), "stocks": int(d["ticker"].nunique()),
           "first": str(d["date"].min())[:10], "last": str(d["date"].max())[:10]}
    with np.errstate(invalid="ignore"):
        S = (ext <= -1.5) & (np.abs(z) <= 0.5) & np.isfinite(rvol)
        T, C = S & (rvol >= 2), S & (rvol < 2)
        S3 = (ext <= -1.5) & (np.abs(z3) <= 0.5) & np.isfinite(zv)
        T3, C3 = S3 & (zv >= 2), S3 & (zv < 2)
        out["shipped_mark"] = {k: cmp(d, T, C, k, rng) for k in ("fzd10", "fzd5", "fzd20", "fz10")}
        out["shipped_mark"]["fx10_pct"] = cmp(d, T, C, "fx10", rng, 100.0)
        out["v3_mark"] = {k: cmp(d, T3, C3, k, rng) for k in ("fzd10", "fzd5", "fzd20", "fz10")}
        out["v3_mark"]["fx10_pct"] = cmp(d, T3, C3, "fx10", rng, 100.0)
        out["counts"] = {"shipped": int(T.sum()), "v3": int(T3.sum()), "both": int((T & T3).sum()),
                         "per_stock_year_shipped": round(float(T.sum() / (len(d) / 252.0)), 3),
                         "per_stock_year_v3": round(float(T3.sum() / (len(d) / 252.0)), 3),
                         "share_zv_ge2": round(float(np.nanmean(zv >= 2)), 4), "share_rvol_ge2": round(float(np.nanmean(rvol >= 2)), 4),
                         "median_rvol_shipped": round(float(np.nanmedian(rvol)), 3)}
        # S1 generalisation
        small = (np.abs(z3) <= 0.5) & np.isfinite(zv)
        buckets = {"ext<=-1.5": ext <= -1.5, "between": (ext > -1.5) & (ext < 1.5), "ext>=1.5": ext >= 1.5}
        out["S1_no_move_by_extension"] = {
            b: {k: cmp(d, small & m & (zv >= 2), small & m & (zv < 2), k, rng) for k in ("fzd10", "fzd20")}
            for b, m in buckets.items()}
        out["S1_no_move_by_extension"]["all"] = {k: cmp(d, small & (zv >= 2), small & (zv < 2), k, rng)
                                                 for k in ("fzd10", "fzd20")}
        # S2 Gervais-Kaniel-Mingelgrin
        below = d["below"].to_numpy()
        hi, lo_, nm = below >= 45, below <= 4, (below > 4) & (below < 45)
        out["S2_gkm"] = {"high_minus_normal": {k: cmp(d, hi, nm, k, rng) for k in ("fzd10", "fzd20")},
                         "low_minus_normal": {k: cmp(d, lo_, nm, k, rng) for k in ("fzd10", "fzd20")}}
        out["S2_gkm"]["high_minus_normal"]["fx20_pct"] = cmp(d, hi, nm, "fx20", rng, 100.0)
        out["S2_gkm"]["low_minus_normal"]["fx20_pct"] = cmp(d, lo_, nm, "fx20", rng, 100.0)
        # S3 strong move on unusual volume: continuation or reversal
        sgn = np.sign(d["r"].to_numpy())
        for k in ("fzd5", "fzd10"):
            d["s_" + k] = sgn * d[k].to_numpy()
        strong = np.abs(z3) >= 1.5
        m = d["month"].to_numpy()
        out["S3_strong_move"] = {}
        for lab, msk in (("unusual_volume", strong & (zv >= 2)), ("ordinary_volume", strong & (zv < 1)),
                         ("unusual_up", strong & (zv >= 2) & (sgn > 0)), ("unusual_down", strong & (zv >= 2) & (sgn < 0))):
            out["S3_strong_move"][lab] = {k: e05.boot_mean(d["s_" + k].to_numpy()[msk], m[msk], rng) for k in ("fzd5", "fzd10")}
        out["S3_strong_move"]["unusual_minus_ordinary"] = {
            k: cmp(d, strong & (zv >= 2), strong & (zv < 1), "s_" + k, rng) for k in ("fzd5", "fzd10")}
        # S4 by period (EM only)
        if name == "EM":
            dt = d["date"].to_numpy()
            per = {"2018-02..2020-01": dt < np.datetime64("2020-02-01"),
                   "2020-02..2022-12": (dt >= np.datetime64("2020-02-01")) & (dt < np.datetime64("2023-01-01")),
                   "2023-01..2026-10": dt >= np.datetime64("2023-01-01")}
            out["S4_v3_mark_by_period"] = {k: cmp(d, T3 & pm, C3 & pm, "fzd10", rng) for k, pm in per.items()}
            out["S4_gkm_high_by_period_fzd20"] = {k: cmp(d, hi & pm, nm & pm, "fzd20", rng) for k, pm in per.items()}
    out["seconds"] = round(time.time() - t0)
    return out


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [None] * len(ps), 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, ps[i] * (len(ps) - rank)))
        adj[i] = round(run, 4)
    return adj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=DEFAULT_PANEL)
    ap.add_argument("--sets", nargs="+", default=list(SETS))
    a = ap.parse_args()
    res = {s: run_set(s, a.panel, 1800 + i) for i, s in enumerate(a.sets)}
    fam = [("P0 shipped mark on EM", res["EM"]["shipped_mark"]["fzd10"])] if "EM" in res else []
    fam += [(f"v3 mark on {s}", res[s]["v3_mark"]["fzd10"]) for s in a.sets]
    adj = holm([f[1]["p"] for f in fam])
    res["primary_family"] = [{"test": f[0], **f[1], "p_holm": adj[i]} for i, f in enumerate(fam)]
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e18_relvol_v3_confirmation.json"
    p.write_text(json.dumps(res, indent=1))

    def f(r):
        return "n/a" if r["diff"] is None else f"{r['diff']:+.3f} [{r['lo']:+.3f},{r['hi']:+.3f}] n={r['n']}"
    print("PRIMARY (fzd10)")
    for r in res["primary_family"]:
        print(f"  {r['test']:24s} {f(r)}  p={r['p']}  holm={r['p_holm']}")
    for s in a.sets:
        r = res[s]
        print(f"\n{s}: rows {r['eval_rows']}, {r['first']}..{r['last']}, counts {r['counts']}")
        print("  shipped mark:", {k: f(v) for k, v in r["shipped_mark"].items()})
        print("  v3 mark     :", {k: f(v) for k, v in r["v3_mark"].items()})
        print("  S1 no move  :", {b: f(v["fzd10"]) + " | fzd20 " + f(v["fzd20"]) for b, v in r["S1_no_move_by_extension"].items()})
        print("  S2 GKM high :", {k: f(v) for k, v in r["S2_gkm"]["high_minus_normal"].items()})
        print("  S2 GKM low  :", {k: f(v) for k, v in r["S2_gkm"]["low_minus_normal"].items()})
        g = r["S3_strong_move"]
        print("  S3 strong   :", {k: {kk: (vv["est"], vv["lo"], vv["hi"], vv["n"]) for kk, vv in g[k].items()} for k in ("unusual_volume", "ordinary_volume", "unusual_up", "unusual_down")})
        print("  S3 diff     :", {k: f(v) for k, v in g["unusual_minus_ordinary"].items()})
        if "S4_v3_mark_by_period" in r:
            print("  S4 v3 mark by period:", {k: f(v) for k, v in r["S4_v3_mark_by_period"].items()})
            print("  S4 GKM high fzd20 by period:", {k: f(v) for k, v in r["S4_gkm_high_by_period_fzd20"].items()})


if __name__ == "__main__":
    main()
