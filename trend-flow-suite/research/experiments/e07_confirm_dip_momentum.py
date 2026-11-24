#!/usr/bin/env python3
"""E07 - CONFIRMATION of the candidate found in E06 (plan: docs/06_validation_lite.md, section 2.3).

Rule D: context regime up and 5-bar return in risk units <= -1.5 on the first bar of the dip; buy
at that close; stop 2 ATR below (intrabar); exit at the close 10 bars later (primary) or by a
3-ATR chandelier (alternative); exit if the context turns down.
Tests C1-C4 are run once on set B (other stocks, same dates) and on DJ (other dates, incl. 2008).
Set A is printed for reference only; it is where the rule was found.
  python3 -I experiments/e07_confirm_dip_momentum.py --sp5 DIR --dj DIR
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json
from dataclasses import replace
from multiprocessing import Pool

import numpy as np
import pandas as pd

import experiments.e05_validation_lite as e05
from experiments.e06_explore_reversal_momentum import extra
from experiments.e06b_explore_dip_rule import ENGINE, sim
from tfs.data import load_bundled, load_ohlcv_dir

DIP_Z, STOP_ATR, N_RANDOM = -1.5, 2.0, 20
EXITS = {"time_10_bars": replace(ENGINE, trail_atr=1e6, max_bars=10), "chandelier_3_atr": ENGINE}


def diff(pan, s, c, key, rng):
    m = pan["month"].to_numpy()
    v = pan[key].to_numpy()
    return e05.boot_diff(v[s], m[s], v[c], m[c], rng)


def confirm_set(name, stocks, rng):
    """Frozen tests C1-C4 on one set of stocks. Prints a summary and returns the results."""
    with Pool(4) as pool:
        fp = pool.map(e05.features, sorted(stocks.items()), chunksize=4)
    exs = [extra(f[0]) for f in fp]
    pan = pd.concat([r[1] for r in fp], ignore_index=True).merge(
        pd.concat(exs, ignore_index=True), on=["ticker", "t"], how="left")
    up = (pan["ctx"] == 1).to_numpy()
    dip = pan["z5"].to_numpy() <= DIP_Z
    R = {"stocks": len(fp), "rows": int(len(pan)), "months": int(pan["month"].nunique())}
    R["C1_forward_returns"] = {k: diff(pan, up & dip, up & ~dip, k, rng) for k in ("f1", "f3", "f5", "f10", "f20", "fx5", "fx10")}
    R["C2_trades"] = {}
    for ename, eng in EXITS.items():
        t, sy, expo, rnd = sim(fp, exs, "ctx_up", "z5", DIP_Z, STOP_ATR, rng, N_RANDOM, engine=eng)
        r = t["r"].to_numpy()
        R["C2_trades"][ename] = {
            "trades": int(len(t)), "per_stock_year": round(len(t) / sy, 2),
            "win_pct": round(100 * float((r > 0).mean()), 1),
            "avg_r": e05.boot_mean(r, t["month"].to_numpy(), rng),
            "r_per_stock_year": e05.boot_mean(r, t["month"].to_numpy(), rng, denom=sy),
            "median_r": round(float(np.median(r)), 3), "avg_bars": round(float(t["bars"].mean()), 1),
            "r_per_100_bars_held": round(100 * float(r.sum() / t["bars"].sum()), 2),
            "worst_r": round(float(r.min()), 2), "pct_worse_than_minus_1_5r": round(100 * float((r < -1.5).mean()), 2),
            "exposure_pct": round(100 * expo, 1),
            "random_avg_r_mean": round(float(np.mean(rnd)), 4), "random_avg_r_sd": round(float(np.std(rnd)), 4),
            "p_vs_random": round((1 + sum(x >= r.mean() for x in rnd)) / (1 + len(rnd)), 3),
            "by_year": {str(int(y)): {"n": int(len(g)), "avg_r": round(float(g["r"].mean()), 3)}
                        for y, g in t.assign(year=t["month"] // 12).groupby("year")}}
    rs, mo = pan["rs12_1"].to_numpy(), pan["mom12_1"].to_numpy()
    has = np.isfinite(rs) & np.isfinite(mo)
    R["C3_momentum"] = {"rs>1_fx60": diff(pan, has & (rs > 1), has & ~(rs > 1), "fx60", rng),
                        "rs<=-1_fx60": diff(pan, has & (rs <= -1), has & ~(rs <= -1), "fx60", rng),
                        "mom>1_f60": diff(pan, has & (mo > 1), has & ~(mo > 1), "f60", rng),
                        "mom<=-1_f60": diff(pan, has & (mo <= -1), has & ~(mo <= -1), "f60", rng),
                        "rs>1_fx20": diff(pan, has & (rs > 1), has & ~(rs > 1), "fx20", rng),
                        "rs<=-1_fx20": diff(pan, has & (rs <= -1), has & ~(rs <= -1), "fx20", rng)}
    R["C4_dips_without_uptrend"] = {k: diff(pan, ~up & dip, ~up & ~dip, k, rng) for k in ("f5", "f10", "fx5", "fx10")}
    print(f"\n################ {name}: {R['stocks']} stocks, {R['rows']} rows, {R['months']} months")
    f = lambda r: f"{r['diff']:+.3f} [{r['lo']:+.3f},{r['hi']:+.3f}]" + ("*" if r["lo"] > 0 or r["hi"] < 0 else "") + f" n={r['n']}"
    print("C1 dip in uptrend vs uptrend without dip:"); [print(f"   {k:5s} {f(v)}") for k, v in R["C1_forward_returns"].items()]
    for en, v in R["C2_trades"].items():
        a_, y_ = v["avg_r"], v["r_per_stock_year"]
        print(f"C2 {en}: n={v['trades']} /stk-yr {v['per_stock_year']} win {v['win_pct']}% avgR {a_['est']:+.3f} [{a_['lo']:+.3f},{a_['hi']:+.3f}] "
              f"R/stk-yr {y_['est']:+.2f} [{y_['lo']:+.2f},{y_['hi']:+.2f}] medR {v['median_r']:+.2f} bars {v['avg_bars']} R/100bars {v['r_per_100_bars_held']} "
              f"worst {v['worst_r']} <-1.5R {v['pct_worse_than_minus_1_5r']}% expo {v['exposure_pct']}% | random {v['random_avg_r_mean']:+.3f} (sd {v['random_avg_r_sd']:.3f}) p={v['p_vs_random']}")
        print("     by year:", v["by_year"])
    print("C3 momentum:"); [print(f"   {k:12s} {f(v)}") for k, v in R["C3_momentum"].items()]
    print("C4 dips without uptrend:"); [print(f"   {k:5s} {f(v)}") for k, v in R["C4_dips_without_uptrend"].items()]
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sp5", required=True)
    ap.add_argument("--dj", required=True)
    ap.add_argument("--seed", type=int, default=707)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    e05._BENCH = load_bundled("SPX")["close"]
    sp5, _ = load_ohlcv_dir(a.sp5, "*_data.csv", min_bars=700)
    dj, _ = load_ohlcv_dir(a.dj, "*_2006-01-01_to_2018-01-01.csv", min_bars=700, end="2013-02-07")
    sets = {"A (development)": {k: v for k, v in sp5.items() if e05.half(k) == "A"},
            "B": {k: v for k, v in sp5.items() if e05.half(k) == "B"}, "DJ": dj}
    out = {name: confirm_set(name, stocks, rng) for name, stocks in sets.items()}
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e07_confirm_dip_momentum.json"
    p.write_text(json.dumps(out, indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main()
