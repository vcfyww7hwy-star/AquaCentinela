#!/usr/bin/env python3
"""E08 - Independent long-history set LH (added after the DJ result; docs/06, section 2.4).

Universe: the S&P 500 tickers of the SP5 set, traced back in the Kaggle "Huge Stock Market
Dataset" (daily, dividend- and split-adjusted). Period: 1999-01-02 .. 2013-02-07, which shares no
dates with SP5. Runs, unchanged: the frozen confirmation tests C1-C4 (E07) and the pre-registered
questions Q1-Q7 (E05).
  python3 -I experiments/e08_long_history.py --sp5 DIR --lh DIR/Stocks
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
from experiments.e07_confirm_dip_momentum import confirm_set
from tfs.data import load_bundled, load_ohlcv_dir

START, END = "1999-01-02", "2013-02-07"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sp5", required=True)
    ap.add_argument("--lh", required=True)
    ap.add_argument("--seed", type=int, default=808)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    e05._BENCH = load_bundled("SPX")["close"]
    names = {p.name.split("_")[0].upper().replace(".", "-") for p in pathlib.Path(a.sp5).rglob("*_data.csv")
             if not p.name.startswith(".")}
    t0 = time.time()
    lh, audit = load_ohlcv_dir(a.lh, "*.us.txt", min_bars=700, start=START, end=END, tickers=names)
    print(f"LH: {len(lh)} stocks loaded in {time.time() - t0:.0f}s; audit:",
          {k: v for k, v in audit.items() if k != "max_abs_log_return"}, "| big jumps:", len(audit["max_abs_log_return"]))
    out = {"period": [START, END], "data_audit": audit, "stocks": len(lh)}
    out["confirmation_C1_C4"] = confirm_set("LH", lh, rng)
    with Pool(4) as pool:
        res = pool.map(e05.features, sorted(lh.items()), chunksize=4)
    store = [r[0] for r in res]
    pan = pd.concat([r[1] for r in res], ignore_index=True)
    out["panel_rows"], out["months"] = int(len(pan)), int(pan["month"].nunique())
    out["mean_fz10_all_bars"] = round(float(pan["fz10"].mean()), 4)
    out["preregistered_Q1_Q7"] = e05.analyse(pan, store, rng)
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e08_long_history.json"
    p.write_text(json.dumps(out, indent=1))
    print(f"wrote {p} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
