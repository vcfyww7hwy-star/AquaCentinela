#!/usr/bin/env python3
"""E06 - EXPLORATORY (not pre-registered): where, if anywhere, is there a directional edge?

E05 found no edge in the v1 signals and a consistent hint of short-term mean reversion. This script
looks at a short menu of effects documented in the literature, on the DEVELOPMENT half (A) only:
  X1 short-term reversal: forward returns by the recent k-bar return in sigma units (k = 3, 5),
     split by the weekly context regime
  X2 extension from the baseline (ATR units), same split
  X3 the bar that confirms a swing high in an uptrend (a >= 2 ATR pullback by close)
  X4 long-horizon momentum (12-1 months), absolute and relative to the benchmark
  X5 nearness to the 252-bar high
Anything promising must then be confirmed ONCE on set B and on DJ (see docs/06, Part 2).
  python3 -I experiments/e06_explore_reversal_momentum.py --sp5 DIR --dj DIR [--sets A]
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

import experiments.e05_validation_lite as e05
from tfs.data import load_bundled, load_ohlcv_dir

FWD = (1, 3, 5, 10, 20, 60)


def extra(feat):
    c, b, s0, n = feat["c"], feat["bench"], feat["sig0"], feat["n"]
    lnc, lnb = np.log(c), np.log(b)
    out = {"t": np.arange(n)}
    for k in (3, 5, 10):
        z = np.full(n, np.nan)
        z[k:] = (lnc[k:] - lnc[:-k]) / (s0[k:] * np.sqrt(k))
        out[f"z{k}"] = z
    mom = np.full(n, np.nan)
    mom[252:] = lnc[231:-21] - lnc[:-252]
    momb = np.full(n, np.nan)
    momb[252:] = lnb[231:-21] - lnb[:-252]
    out["mom12_1"] = mom / (s0 * np.sqrt(231))
    out["rs12_1"] = (mom - momb) / (s0 * np.sqrt(231))
    out["hi252"] = c / pd.Series(feat["h"]).rolling(252).max().to_numpy()
    out["new_sh"] = feat["new_sh"]
    for h in FWD:
        f, fb = np.full(n, np.nan), np.full(n, np.nan)
        f[:-h] = lnc[h:] - lnc[:-h]
        fb[:-h] = lnb[h:] - lnb[:-h]
        out[f"f{h}"] = f / (s0 * np.sqrt(h))
        out[f"fx{h}"] = (f - fb) / (s0 * np.sqrt(h))
    d = pd.DataFrame(out)
    d["ticker"] = feat["ticker"]
    return d


def table(pan, rng, rows, metrics):
    m = pan["month"].to_numpy()
    out = []
    for name, s_mask, c_mask in rows:
        r = {"rule": name, "n": int(s_mask.sum())}
        for k in metrics:
            v = pan[k].to_numpy()
            res = e05.boot_diff(v[s_mask], m[s_mask], v[c_mask], m[c_mask], rng)
            r[k] = None if res["diff"] is None else f"{res['diff']:+.3f} [{res['lo']:+.3f},{res['hi']:+.3f}]" + ("*" if res["lo"] > 0 or res["hi"] < 0 else "")
        out.append(r)
    return out


def bucket_rows(x, edges, labels, cond, name):
    rows = []
    for (lo, hi), lab in zip(edges, labels):
        s = cond & (x > lo) & (x <= hi)
        rows.append((f"{name} {lab}", s, cond & ~s))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sp5", required=True)
    ap.add_argument("--dj", required=True)
    ap.add_argument("--sets", default="A")
    ap.add_argument("--seed", type=int, default=606)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    e05._BENCH = load_bundled("SPX")["close"]
    sp5, _ = load_ohlcv_dir(a.sp5, "*_data.csv", min_bars=700)
    dj, _ = load_ohlcv_dir(a.dj, "*_2006-01-01_to_2018-01-01.csv", min_bars=700, end="2013-02-07")
    sets = {"A": {k: v for k, v in sp5.items() if e05.half(k) == "A"},
            "B": {k: v for k, v in sp5.items() if e05.half(k) == "B"}, "DJ": dj}
    res = {}
    for name in a.sets.split(","):
        with Pool(4) as pool:
            fp = pool.map(e05.features, sorted(sets[name].items()), chunksize=4)
        pan = pd.concat([r[1] for r in fp], ignore_index=True)
        ex = pd.concat([extra(r[0]) for r in fp], ignore_index=True)
        pan = pan.merge(ex, on=["ticker", "t"], how="left")
        ctx_up, dr = (pan["ctx"] == 1).to_numpy(), pan["dir"].to_numpy()
        every = np.ones(len(pan), dtype=bool)
        inf, R = np.inf, {}
        zb = [(-inf, -2), (-2, -1), (-1, 0), (0, 1), (1, 2), (2, inf)]
        zl = ["<=-2", "-2..-1", "-1..0", "0..1", "1..2", ">2"]
        short = ("f1", "f3", "f5", "f10", "fx5")
        for k in ("z3", "z5"):
            x = pan[k].to_numpy()
            R[f"X1_{k}_all"] = table(pan, rng, bucket_rows(x, zb, zl, every, k), short)
            R[f"X1_{k}_context_up"] = table(pan, rng, bucket_rows(x, zb, zl, ctx_up, k + "|ctx up"), short)
            R[f"X1_{k}_context_not_up"] = table(pan, rng, bucket_rows(x, zb, zl, ~ctx_up, k + "|ctx not up"), short)
        x = pan["ext"].to_numpy()
        R["X2_ext_context_up"] = table(pan, rng, bucket_rows(x, zb, zl, ctx_up, "ext|ctx up"), short)
        R["X2_ext_context_not_up"] = table(pan, rng, bucket_rows(x, zb, zl, ~ctx_up, "ext|ctx not up"), short)
        sh = pan["new_sh"].to_numpy().astype(bool)
        R["X3_swing_high_confirmed"] = table(pan, rng, [
            ("new_sh & chart up vs chart up", sh & (dr == 1), (dr == 1) & ~sh),
            ("new_sh & ctx up vs ctx up", sh & ctx_up, ctx_up & ~sh),
            ("new_sh (any) vs all", sh, ~sh)], short)
        mb = [(-inf, -1), (-1, 0), (0, 1), (1, 2), (2, inf)]
        ml = ["<=-1", "-1..0", "0..1", "1..2", ">2"]
        longm = ("f5", "f20", "f60", "fx20", "fx60")
        has = pan["mom12_1"].notna().to_numpy()
        R["X4_mom12_1"] = table(pan, rng, bucket_rows(pan["mom12_1"].to_numpy(), mb, ml, has, "mom12-1"), longm)
        R["X4_rs12_1"] = table(pan, rng, bucket_rows(pan["rs12_1"].to_numpy(), mb, ml, has, "rs12-1"), longm)
        hb = [(0, 0.8), (0.8, 0.9), (0.9, 0.98), (0.98, 2)]
        hl = ["<0.80", "0.80-0.90", "0.90-0.98", ">=0.98"]
        hh = pan["hi252"].notna().to_numpy()
        R["X5_hi252"] = table(pan, rng, bucket_rows(pan["hi252"].to_numpy(), hb, hl, hh, "close/252-high"), longm)
        res[name] = {"rows": int(len(pan)), "tables": R}
        print(f"\n################ SET {name}: {len(pan)} rows")
        for tn, rows in R.items():
            print(f"--- {tn}")
            print(pd.DataFrame(rows).to_string(index=False))
    out = pathlib.Path(__file__).resolve().parents[1] / "results" / f"e06_explore_{a.sets.replace(',', '_')}.json"
    out.write_text(json.dumps(res, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
