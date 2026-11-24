#!/usr/bin/env python3
"""E10b - Panel for a modern daily set "EM" (2018-02-08 .. 2026-11), same columns as E10.

Source: a public GitHub collection of daily bars for NASDAQ and NYSE tickers listed in Nov 2026
(split- and dividend-adjusted prices, consolidated volume rounded to 100 shares), packed into one
parquet file by the data search of 23 Nov 2026. Checked against the earlier S&P set on 127,188
common ticker-days: daily-return correlation 0.98, volume identical up to later splits; AAPL bars of
Nov 2026 equal the Financial Datasets connector to the cent.

Set EM: every ticker with >= 1000 bars since 2016-07-05, median close >= 5 and median dollar volume
>= 2e6. Rows are evaluated only from 2018-02-08, the day after the last date of sets A and B, so EM
shares no evaluated date with any earlier set. Survivors only (all tickers are still listed).
Benchmark for the fb/fzx columns: the equal-weight index of the set itself (the bundled SPX series
ends in 2018). spy_rvol is NaN.

  python3 -I experiments/e10b_build_em_panel.py --em FILE.parquet --out DIR
Source check "EO": the same source restricted to the period of set MS, to separate "the market changed"
from "the source or the universe is different":
  python3 -I experiments/e10b_build_em_panel.py --em FILE.parquet --out DIR --name EO \
      --start 2005-01-03 --end 2017-11-10 --eval-from 2006-08-04
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json

import numpy as np
import pandas as pd

import experiments.e10_build_volume_panel as e10

START, EVAL_FROM = "2016-07-05", "2018-02-08"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--em", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="EM")
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=None, help="last date kept (to rebuild an earlier period from the same source)")
    ap.add_argument("--eval-from", default=EVAL_FROM)
    a = ap.parse_args()
    d = pd.read_parquet(a.em, columns=["ticker", "date", "open", "high", "low", "close", "volume"])
    d["ticker"] = d["ticker"].astype(str)
    d = d[d["date"] >= a.start]
    if a.end:
        d = d[d["date"] <= a.end]
    px = d[["open", "high", "low", "close"]]
    d = d[px.notna().all(axis=1) & (px > 0).all(axis=1)].copy()
    d["volume"] = d["volume"].fillna(0.0).astype(float)
    d["high"] = d[["open", "high", "close"]].max(axis=1)
    d["low"] = d[["open", "low", "close"]].min(axis=1)
    d = d.drop_duplicates(["ticker", "date"], keep="last").sort_values(["ticker", "date"])
    stocks = {}
    for tkr, g in d.groupby("ticker", sort=True):
        if len(g) < 1000 or g["close"].median() < 5.0 or (g["close"] * g["volume"]).median() < 2e6:
            continue
        stocks[tkr] = g.set_index("date")[["open", "high", "low", "close", "volume"]].astype(float)
    # equal-weight index of the set as benchmark
    r = pd.concat({k: np.log(v["close"]).diff() for k, v in stocks.items()}, axis=1).mean(axis=1)
    e10._BENCH = np.exp(r.fillna(0.0).cumsum())
    e10._SPY = None
    info = e10.build(a.name, stocks, a.out, eval_from=a.eval_from)
    print(json.dumps(info))
    (pathlib.Path(a.out) / f"panel_info_{a.name}.json").write_text(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
