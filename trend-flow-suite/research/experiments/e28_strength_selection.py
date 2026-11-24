#!/usr/bin/env python3
"""E28 - Selection by strength, on every set: is a stock near its 52-week high, or strong over 12
months, followed by better returns than a weak one?

Added after E27 (2018-2026), where nearness to the 52-week high was the only price-side candidate
with a consistent sign. Exploratory: this checks whether the sign repeats on the five other sets.
PLAN (written before the numbers were computed)
  hi252   close / highest high of the last 252 bars
  mom12_1 ln(close[t-21] / close[t-252])
  Each day the stocks of the set are ranked into fifths. Top fifth minus bottom fifth, and top fifth
  minus the middle three: forward return over 20 and 60 bars, minus the set's mean that day, in
  risk units (sigma x sqrt(h)) and in percent. Month-block bootstrap, 2,000 resamples.
  Reading rule fixed in advance: worth a module only if top minus bottom over 60 bars is positive in
  at least five of the six sets and its interval excludes zero in at least three.
Survivors only: stocks that fell and were delisted are missing, which understates the weakness of
the bottom fifth.

  python3 -I experiments/e28_strength_selection.py [--panel DIR]      then, for the addendum at the end of this file:
  python3 -I experiments/e28_strength_selection.py --addendum
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json

import numpy as np
import pandas as pd

import experiments.e18_relvol_v3_confirmation as e18

SETS = ("A", "B", "LH", "MS", "EO", "EM")


def run_set(name, panel, rng):
    d = pd.read_parquet(pathlib.Path(panel) / f"panel_{name}.parquet", columns=["ticker", "date", "month", "eval", "high", "close", "sig0"])
    g = d.groupby("ticker", sort=False)
    lnc = np.log(d["close"])
    d["hi252"] = d["close"] / g["high"].transform(lambda x: x.rolling(252).max())
    d["mom12_1"] = g["close"].transform(lambda x: np.log(x.shift(21) / x.shift(252)))
    for h in (20, 60):
        f = g["close"].transform(lambda x: np.log(x.shift(-h) / x))
        d[f"x{h}"] = f - f.groupby(d["date"]).transform("mean")
        d[f"fx{h}"] = d[f"x{h}"] / (d["sig0"] * np.sqrt(h))
    e = d[d["eval"] & d["fx60"].notna()].copy()
    out = {"set": name, "rows": int(len(e)), "first": str(e["date"].min())[:10], "last": str(e["date"].max())[:10]}
    for col in ("hi252", "mom12_1"):
        q = e.groupby("date")[col].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False) if s.notna().sum() >= 50 else np.nan).to_numpy()
        top, bot, mid = q == 4, q == 0, (q >= 1) & (q <= 3)
        out[col] = {"top_minus_bottom_fx60": e18.cmp(e, top, bot, "fx60", rng), "top_minus_bottom_fx20": e18.cmp(e, top, bot, "fx20", rng),
                    "top_minus_middle_fx60": e18.cmp(e, top, mid, "fx60", rng), "bottom_minus_middle_fx60": e18.cmp(e, bot, mid, "fx60", rng),
                    "top_minus_bottom_pct_60_bars": e18.cmp(e, top, bot, "x60", rng, 100.0),
                    "top_minus_bottom_pct_20_bars": e18.cmp(e, top, bot, "x20", rng, 100.0)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=e18.DEFAULT_PANEL)
    a = ap.parse_args()
    rng = np.random.default_rng(28)
    res = {}
    f = lambda x: f"{x['diff']:+.3f} [{x['lo']:+.3f},{x['hi']:+.3f}]"
    for name in SETS:
        res[name] = r = run_set(name, a.panel, rng)
        print(name, r["first"], r["last"], r["rows"])
        for col in ("hi252", "mom12_1"):
            x = r[col]
            print(f"  {col:8s} T-B fx60 {f(x['top_minus_bottom_fx60'])}  fx20 {f(x['top_minus_bottom_fx20'])}  T-mid {f(x['top_minus_middle_fx60'])}  B-mid {f(x['bottom_minus_middle_fx60'])}"
                  f"  T-B % 60 bars {f(x['top_minus_bottom_pct_60_bars'])}  20 bars {f(x['top_minus_bottom_pct_20_bars'])}")
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e28_strength_selection.json"
    p.write_text(json.dumps(res, indent=1))


# ---- Addendum (after the first results): absolute bands and the market's own state --------------
# A single-symbol indicator cannot rank a universe, so the same question in absolute terms: forward
# 60-bar return relative to the set's mean, by band of close / 52-week high; and the top-minus-bottom
# contrast split by the market's own distance from its 52-week high (equal-weight index of the set),
# because momentum is known to fail in rebounds after market declines (Daniel and Moskowitz 2016).
def addendum(panel):
    rng = np.random.default_rng(281)
    res = {}
    for name in ("LH", "MS", "EM"):
        d = pd.read_parquet(pathlib.Path(panel) / f"panel_{name}.parquet", columns=["ticker", "date", "month", "eval", "high", "close", "sig0", "r"])
        g = d.groupby("ticker", sort=False)
        d["hi252"] = d["close"] / g["high"].transform(lambda x: x.rolling(252).max())
        f = g["close"].transform(lambda x: np.log(x.shift(-60) / x))
        d["x60"] = f - f.groupby(d["date"]).transform("mean")
        d["fx60"] = d["x60"] / (d["sig0"] * np.sqrt(60))
        f20 = g["close"].transform(lambda x: np.log(x.shift(-20) / x))
        d["x20"] = f20 - f20.groupby(d["date"]).transform("mean")
        d["fx20"] = d["x20"] / (d["sig0"] * np.sqrt(20))
        idx = np.exp(d.groupby("date")["r"].mean().sort_index().fillna(0.0).cumsum())
        mstate = (idx / idx.rolling(252).max())
        d["mkt_hi"] = d["date"].map(mstate)
        e = d[d["eval"] & d["fx60"].notna() & d["hi252"].notna() & d["mkt_hi"].notna()].copy()
        h = e["hi252"].to_numpy()
        bands = (("below 0.60", h < 0.60), ("0.60-0.75", (h >= 0.60) & (h < 0.75)), ("0.75-0.90", (h >= 0.75) & (h < 0.90)),
                 ("0.90-0.97", (h >= 0.90) & (h < 0.97)), ("0.97 and above", h >= 0.97))
        q = e.groupby("date")["hi252"].transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False) if len(s) >= 50 else np.nan).to_numpy()
        mk = e["mkt_hi"].to_numpy()
        r = {"share_of_bars_pct": {lab: round(100 * float(m.mean()), 1) for lab, m in bands},
             "mean_fx60_by_band": {lab: round(float(np.nanmean(e["fx60"].to_numpy()[m])), 3) for lab, m in bands},
             "mean_pct_60_bars_by_band": {lab: round(100 * float(np.nanmean(e["x60"].to_numpy()[m])), 2) for lab, m in bands},
             "median_fifth_boundaries": {"bottom_fifth_below": round(float(e.groupby("date")["hi252"].quantile(0.2).median()), 3),
                                         "top_fifth_above": round(float(e.groupby("date")["hi252"].quantile(0.8).median()), 3)},
             "below_0.75_minus_0.90_and_above_fx60": e18.cmp(e, h < 0.75, h >= 0.90, "fx60", rng),
             "top_minus_bottom_fifth_fx60_market_within_10pct_of_high": e18.cmp(e, (q == 4) & (mk >= 0.90), (q == 0) & (mk >= 0.90), "fx60", rng),
             "top_minus_bottom_fifth_fx60_market_more_than_10pct_below_high": e18.cmp(e, (q == 4) & (mk < 0.90), (q == 0) & (mk < 0.90), "fx60", rng),
             "share_of_days_market_more_than_10pct_below_high_pct": round(100 * float((mstate.reindex(np.sort(e["date"].unique())) < 0.90).mean()), 1)}
        # sensitivity to the market threshold, and the 20-bar horizon (percent, relative to the set's mean)
        r["sensitivity"] = {}
        for thr in (0.85, 0.90, 0.95):
            near, far = mk >= thr, mk < thr
            r["sensitivity"][str(thr)] = {
                "days_market_below_pct": round(100 * float((mstate.reindex(np.sort(e["date"].unique())) < thr).mean()), 1),
                "near_fx60": e18.cmp(e, (q == 4) & near, (q == 0) & near, "fx60", rng), "far_fx60": e18.cmp(e, (q == 4) & far, (q == 0) & far, "fx60", rng),
                "near_fx20": e18.cmp(e, (q == 4) & near, (q == 0) & near, "fx20", rng), "far_fx20": e18.cmp(e, (q == 4) & far, (q == 0) & far, "fx20", rng),
                "near_pct_20_bars": e18.cmp(e, (q == 4) & near, (q == 0) & near, "x20", rng, 100.0),
                "near_bottom_minus_middle_pct_20_bars": e18.cmp(e, (q == 0) & near, (q >= 1) & (q <= 3) & near, "x20", rng, 100.0),
                "near_top_minus_middle_pct_20_bars": e18.cmp(e, (q == 4) & near, (q >= 1) & (q <= 3) & near, "x20", rng, 100.0)}
        res[name] = r
        print(name, json.dumps({k: v for k, v in r.items() if k != "sensitivity"}))
        for thr, x in r["sensitivity"].items():
            ff = lambda y: f"{y['diff']:+.3f} [{y['lo']:+.3f},{y['hi']:+.3f}]"
            print(f"   thr {thr} below {x['days_market_below_pct']}% of days | fx60 near {ff(x['near_fx60'])} far {ff(x['far_fx60'])} | fx20 near {ff(x['near_fx20'])} far {ff(x['far_fx20'])} | 20-bar % near T-B {ff(x['near_pct_20_bars'])} B-mid {ff(x['near_bottom_minus_middle_pct_20_bars'])} T-mid {ff(x['near_top_minus_middle_pct_20_bars'])}")
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e28_strength_selection.json"
    old = json.loads(p.read_text())
    old["addendum_absolute_bands_and_market_state"] = res
    p.write_text(json.dumps(old, indent=1))


if __name__ == "__main__":
    if "--addendum" in sys.argv:
        addendum(e18.DEFAULT_PANEL)
    else:
        main()
