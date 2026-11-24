#!/usr/bin/env python3
"""E23 - Second external review, answer to question 2: would another scale estimator make the
unusual-volume flag (zV >= 2) less blunt after a volume spike?

PLAN (written before the numbers were computed)
The reviewer simulated that a median/MAD scale cuts the loss of flags in the 30 bars after a 5x day
from -25% to -6%, and proposes an L1 scale (average of |innovation|). E13 and its audit measured the
loss on real spikes, where it is confounded with what really happens after earnings. Here the
artefact is isolated by INJECTION into real series: on ordinary bars (zV < 1, at least 200 bars
apart) volume is multiplied by 5, everything else is left as it is, and the flags of the next 30
and 31-60 bars are counted with and without the injected bar. Any difference is caused by the
estimator alone.
Variants (level mu as shipped in all of them: clipped at 3 s, span 50):
  l2_clip3   shipped: s^2 = average of clipped squared innovations (clip 3 s)
  l1_clip3   s = sqrt(pi/2) x average of clipped |innovation|
  l2_clip2p5 squared innovations clipped at 2.5 s for the scale only
  l2_skip3   a bar beyond 3 s does not update the scale at all
  l1_skip3   the same with the L1 scale
Reported per variant: flag rate; spread of the per-stock flag rate (its 10th and 90th percentile
and the rate in the steadiest and most erratic fifth of stocks by sd of ln volume); flags lost
after an injected 5x bar (bars 1-30 and 31-60), and after an injected run of three bars at 5x, 3x,
2x (a spike with a tail, closer to an earnings week).
Decision rule fixed in advance: change the shipped scale only if a variant recovers at least half
of the injected loss without moving the flag rate outside 3.5-4.5% or widening the spread across
stocks. Sets EM and MS, every stock.

  python3 -I experiments/e23_scale_estimators_after_spike.py [--panel DIR]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json
import math
from multiprocessing import Pool

import numpy as np
import pandas as pd

import experiments.e18_relvol_v3_confirmation as e18

SPAN, SCALE_SPAN, MIN_CLIP, MIN_OBS = 50, 100, 20, 25
VARIANTS = {"l2_clip3": ("l2", 3.0, False), "l1_clip3": ("l1", 3.0, False), "l2_clip2p5": ("l2", 2.5, False),
            "l2_skip3": ("l2", 3.0, True), "l1_skip3": ("l1", 3.0, True)}
K1 = math.sqrt(math.pi / 2.0)


def zv_variant(v, mode, clip_s, skip):
    """zV with the level of tfs.relvol.log_level_lagged and a variant of the scale."""
    a, b = 2.0 / (SPAN + 1), 2.0 / (SCALE_SPAN + 1)
    n = len(v)
    out = np.full(n, np.nan)
    num = den = num2 = den2 = 0.0
    cnt = 0
    for i in range(n):
        x = v[i]
        mu = num / den if cnt > 0 else math.nan
        if den2 > 0.0 and num2 > 0.0:
            s = math.sqrt(num2 / den2) if mode == "l2" else K1 * num2 / den2
        else:
            s = math.nan
        if x > 0.0:
            lx = math.log(x)
            if cnt >= MIN_OBS and s == s and s > 0.0:
                out[i] = (lx - mu) / s
            if cnt == 0:
                num, den, cnt = a * lx, a, 1
            else:
                e = lx - mu
                es, upd = e, True
                if cnt >= MIN_CLIP and s == s and s > 0.0:
                    lim = 3.0 * s
                    lim_s = clip_s * s
                    if skip and abs(e) > lim_s:
                        upd = False
                    es = lim_s if e > lim_s else (-lim_s if e < -lim_s else e)
                    e = lim if e > lim else (-lim if e < -lim else e)
                num = (1.0 - a) * num + a * (mu + e)
                den = (1.0 - a) * den + a
                if upd:
                    num2 = (1.0 - b) * num2 + b * (es * es if mode == "l2" else abs(es))
                    den2 = (1.0 - b) * den2 + b
                cnt += 1
    return out


def one_stock(args):
    v, ev, seed = args
    n = len(v)
    rng = np.random.default_rng(seed)
    base = {k: zv_variant(v, *p) for k, p in VARIANTS.items()}
    z0 = base["l2_clip3"]
    # injection points: ordinary evaluated bars at least 200 bars apart, with 60 bars of room after
    pts, t = [], 300 + int(rng.integers(0, 200))
    while t < n - 61:
        if ev[t] and z0[t] == z0[t] and z0[t] < 1.0:
            pts.append(t)
            t += 200
        else:
            t += 1
    res = {}
    lv = np.log(np.where(v > 0, v, np.nan))
    sd = float(np.nanstd(np.diff(lv[ev]))) if ev.sum() > 50 else math.nan
    for k, p in VARIANTS.items():
        z = base[k]
        r = {"n": int((ev & np.isfinite(z)).sum()), "flags": int((ev & (z >= 2)).sum())}
        for tag, mult in (("one", (5.0,)), ("run", (5.0, 3.0, 2.0))):
            v2 = v.copy()
            for t in pts:
                for j, m in enumerate(mult):
                    v2[t + j] = v[t + j] * m
            z2 = zv_variant(v2, *p)
            o = len(mult)
            for lab, lo, hi in (("1_30", o, o + 30), ("31_60", o + 30, o + 60)):
                f0 = f1 = 0
                for t in pts:
                    f0 += int((z[t + lo:t + hi] >= 2).sum())
                    f1 += int((z2[t + lo:t + hi] >= 2).sum())
                r[f"{tag}_{lab}"] = (f0, f1)
        res[k] = r
    return res, sd, len(pts)


def run_set(name, panel):
    d = pd.read_parquet(pathlib.Path(panel) / f"panel_{name}.parquet", columns=["ticker", "volume", "eval"])
    jobs = [(g["volume"].to_numpy(dtype=float), g["eval"].to_numpy(), i) for i, (_, g) in enumerate(d.groupby("ticker", sort=False))]
    with Pool(4) as pool:
        out = pool.map(one_stock, jobs, chunksize=8)
    sds = np.array([o[1] for o in out])
    q = np.nanquantile(sds, [0.2, 0.8])
    res = {"set": name, "stocks": len(out), "injections": int(sum(o[2] for o in out))}
    for k in VARIANTS:
        n = np.array([o[0][k]["n"] for o in out], dtype=float)
        f = np.array([o[0][k]["flags"] for o in out], dtype=float)
        ok = n > 500
        rate = f[ok] / n[ok]
        r = {"flag_rate_pct": round(100 * f.sum() / n.sum(), 2),
             "per_stock_rate_p10_p90_pct": [round(100 * float(np.quantile(rate, x)), 2) for x in (0.1, 0.9)],
             "rate_steadiest_fifth_pct": round(100 * f[ok & (sds <= q[0])].sum() / n[ok & (sds <= q[0])].sum(), 2),
             "rate_most_erratic_fifth_pct": round(100 * f[ok & (sds >= q[1])].sum() / n[ok & (sds >= q[1])].sum(), 2)}
        for key in ("one_1_30", "one_31_60", "run_1_30", "run_31_60"):
            f0 = sum(o[0][k][key][0] for o in out)
            f1 = sum(o[0][k][key][1] for o in out)
            r[f"flags_lost_{key}_pct"] = round(100 * (f1 / f0 - 1), 1)
            r[f"flags_{key}"] = [int(f0), int(f1)]
        res[k] = r
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=e18.DEFAULT_PANEL)
    a = ap.parse_args()
    res = {}
    for name in ("EM", "MS"):
        res[name] = run_set(name, a.panel)
        print(name, "stocks", res[name]["stocks"], "injections", res[name]["injections"])
        for k in VARIANTS:
            r = res[name][k]
            print(f"  {k:11s} rate {r['flag_rate_pct']:.2f}%  p10-p90 {r['per_stock_rate_p10_p90_pct']}  steady {r['rate_steadiest_fifth_pct']:.2f}% erratic {r['rate_most_erratic_fifth_pct']:.2f}%"
                  f"  lost one 1-30 {r['flags_lost_one_1_30_pct']:+.1f}% 31-60 {r['flags_lost_one_31_60_pct']:+.1f}%  run 1-30 {r['flags_lost_run_1_30_pct']:+.1f}% 31-60 {r['flags_lost_run_31_60_pct']:+.1f}%")
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e23_scale_estimators_after_spike.json"
    p.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
