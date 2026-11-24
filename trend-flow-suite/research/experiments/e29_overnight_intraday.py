#!/usr/bin/env python3
"""E29 - When during the day is the return earned? Overnight (previous close to open) against
intraday (open to close), equal-weight average of the set per day, on the sets LH, MS and EM.

Descriptive. Relevant to execution: a setup that fires at the close can be bought at that close or
at the next open, and a position can be sold at an open or at a close. Bars with an overnight or
intraday move beyond 20% are dropped as data errors. Survivors only; no costs; the opening print is
not always a price at which size can be traded.

  python3 -I experiments/e29_overnight_intraday.py [--panel DIR]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=e18.DEFAULT_PANEL)
    a = ap.parse_args()
    res = {}
    for name in ("LH", "MS", "EM"):
        d = pd.read_parquet(pathlib.Path(a.panel) / f"panel_{name}.parquet", columns=["date", "gap", "body", "eval"])
        d = d[d["eval"] & np.isfinite(d["gap"]) & np.isfinite(d["body"]) & (d["gap"].abs() < 0.2) & (d["body"].abs() < 0.2)]
        g = d.groupby("date").agg(on=("gap", "mean"), intr=("body", "mean"))

        def st(x):
            return {"bp_per_day": round(1e4 * float(x.mean()), 1), "pct_per_year": round(252 * 100 * float(x.mean()), 1),
                    "t": round(float(x.mean() / x.std() * np.sqrt(len(x))), 1)}
        y = g.groupby(g.index.year).mean() * 1e4
        res[name] = {"days": int(len(g)), "first": str(g.index.min())[:10], "last": str(g.index.max())[:10],
                     "overnight": st(g["on"]), "intraday": st(g["intr"]),
                     "years_overnight_positive": f"{int((y['on'] > 0).sum())} of {len(y)}",
                     "years_intraday_positive": f"{int((y['intr'] > 0).sum())} of {len(y)}",
                     "by_year_bp_overnight": {int(k): round(float(v), 1) for k, v in y["on"].items()},
                     "by_year_bp_intraday": {int(k): round(float(v), 1) for k, v in y["intr"].items()}}
        print(name, json.dumps({k: v for k, v in res[name].items() if not k.startswith("by_year")}))
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e29_overnight_intraday.json"
    p.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
