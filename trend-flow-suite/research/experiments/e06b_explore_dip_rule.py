#!/usr/bin/env python3
"""E06b - EXPLORATORY, development half (A) only: shape of the "dip in an uptrend" effect.

1. Grid: long-term condition x dip depth -> forward returns vs the same condition without a dip
   (looking for a plateau, not a peak).
2. Trade rule: buy at the close of the first bar of a dip while the long-term condition holds;
   initial stop = close - 2 ATR; chandelier trail 3 ATR; intrabar stops; exit if the weekly
   context turns down. Compared with random entries under the same condition.
  python3 -I experiments/e06b_explore_dip_rule.py --sp5 DIR --dj DIR [--sets A]
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
from experiments.e06_explore_reversal_momentum import extra
from tfs.data import load_bundled, load_ohlcv_dir
from tfs.trend import TrendParams, simulate_trades

ENGINE = TrendParams(stop_mode="intrabar", exit_mode="chandelier", trail_atr=3.0)
START = e05.EVAL_START
N_RANDOM = 20


def conditions(ex, ctx):
    m, r = ex["mom12_1"].to_numpy(), ex["rs12_1"].to_numpy()
    return {"ctx_up": ctx == 1, "mom>0": m > 0, "mom>1": m > 1, "rs>0": r > 0,
            "ctx_up&mom>0": (ctx == 1) & (m > 0), "any": np.ones(len(ctx), dtype=bool)}


def sim(fp, exs, cond_name, zkey, thr, stop_atr, rng, random_runs=0, engine=None):
    """Returns (trades frame, stock_years, exposure) and optionally the random-entry avg R list."""
    def run(pick_random):
        rows, sy, expo = [], 0.0, 0.0
        for (feat, _), ex in zip(fp, exs):
            n, c, atr, ctx = feat["n"], feat["c"], feat["atr"], feat["ctx"]
            cond = conditions(ex, ctx)[cond_name]
            z = ex[zkey].to_numpy()
            dip = (z <= thr) & np.r_[True, ~(z[:-1] <= thr)]            # first bar of a dip episode
            ok = cond & (np.arange(n) >= START) & (np.arange(n) < n - 1) & np.isfinite(atr)
            ent = dip & ok
            if pick_random:
                k, pool = int(ent.sum()), np.flatnonzero(ok)
                ent = np.zeros(n, dtype=bool)
                if k and len(pool):
                    ent[rng.choice(pool, size=min(k, len(pool)), replace=False)] = True
            sig = ent.astype(int)
            st = np.where(ent, c - stop_atr * atr, np.nan)
            cols, trades = simulate_trades(feat["o"], feat["h"], feat["l"], c, atr, ctx, feat["last_sl"], sig, st, engine or ENGINE)
            sy += (n - START) / 252.0
            expo += cols["in_trade"][START:].sum()
            for tr in trades:
                ts_ = pd.Timestamp(feat["dates"][tr["entry_bar"]])
                rows.append((feat["ticker"], ts_.year * 12 + ts_.month - 1, tr["r"], tr["bars"], tr["reason"]))
        return pd.DataFrame(rows, columns=["ticker", "month", "r", "bars", "reason"]), sy, expo / max(sy * 252, 1)
    t, sy, expo = run(False)
    rnd = [float(run(True)[0]["r"].mean()) for _ in range(random_runs)]
    return t, sy, expo, rnd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sp5", required=True)
    ap.add_argument("--dj", required=True)
    ap.add_argument("--sets", default="A")
    ap.add_argument("--seed", type=int, default=607)
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
        exs = [extra(f[0]) for f in fp]
        pan = pd.concat([r[1] for r in fp], ignore_index=True).merge(
            pd.concat(exs, ignore_index=True), on=["ticker", "t"], how="left")
        m = pan["month"].to_numpy()
        cond = conditions(pan, pan["ctx"].to_numpy())
        grid = []
        for cn, cm in cond.items():
            for zk, thr in (("z5", -1.0), ("z5", -1.5), ("z5", -2.0), ("z3", -1.5), ("z10", -1.5)):
                s = cm & (pan[zk].to_numpy() <= thr)
                row = {"condition": cn, "dip": f"{zk}<={thr}", "n": int(s.sum())}
                for k in ("f3", "f5", "f10", "fx5", "fx10" if "fx10" in pan else "fx5"):
                    r = e05.boot_diff(pan[k].to_numpy()[s], m[s], pan[k].to_numpy()[cm & ~s], m[cm & ~s], rng)
                    row[k] = f"{r['diff']:+.3f} [{r['lo']:+.3f},{r['hi']:+.3f}]" + ("*" if r["lo"] > 0 or r["hi"] < 0 else "")
                grid.append(row)
        print(f"\n################ SET {name}  grid: dip vs same condition without dip")
        print(pd.DataFrame(grid).to_string(index=False))
        trades = []
        for cn, zk, thr, sa in (("ctx_up", "z5", -1.0, 2.0), ("ctx_up", "z5", -1.5, 2.0), ("ctx_up", "z5", -2.0, 2.0),
                                ("ctx_up&mom>0", "z5", -1.5, 2.0), ("mom>0", "z5", -1.5, 2.0), ("any", "z5", -1.5, 2.0),
                                ("ctx_up", "z5", -1.5, 1.5), ("ctx_up", "z5", -1.5, 3.0)):
            t, sy, expo, rnd = sim(fp, exs, cn, zk, thr, sa, rng, N_RANDOM)
            r = t["r"].to_numpy()
            am = e05.boot_mean(r, t["month"].to_numpy(), rng)
            ry = e05.boot_mean(r, t["month"].to_numpy(), rng, denom=sy)
            trades.append({"condition": cn, "dip": f"{zk}<={thr}", "stop_atr": sa, "trades": len(t),
                           "per_stock_yr": round(len(t) / sy, 2), "win%": round(100 * float((r > 0).mean()), 1),
                           "avgR": f"{am['est']:+.3f} [{am['lo']:+.3f},{am['hi']:+.3f}]",
                           "R/stock-yr": f"{ry['est']:+.2f} [{ry['lo']:+.2f},{ry['hi']:+.2f}]",
                           "medR": round(float(np.median(r)), 2), "bars": round(float(t['bars'].mean()), 1),
                           "worstR": round(float(r.min()), 1), "expo%": round(100 * expo, 1),
                           "random avgR": f"{np.mean(rnd):+.3f} (sd {np.std(rnd):.3f})",
                           "p_vs_random": round((1 + sum(x >= r.mean() for x in rnd)) / (1 + len(rnd)), 3)})
        print(f"\n################ SET {name}  trade rule (entry at dip close, chandelier 3 ATR, intrabar stops)")
        print(pd.DataFrame(trades).to_string(index=False))
        res[name] = {"grid": grid, "trades": trades}
    out = pathlib.Path(__file__).resolve().parents[1] / "results" / f"e06b_explore_dip_{a.sets.replace(',', '_')}.json"
    out.write_text(json.dumps(res, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
