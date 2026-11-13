#!/usr/bin/env python3
"""Write daily bars of a few symbols as JSON for the Pine runtime harness (see README.md).

Source: the Yahoo daily files used by the research (split-adjusted OHLC, not dividend-adjusted,
which is what a TradingView chart shows by default). Output: bars/<SYMBOL>.json, a list of
{openTime, closeTime, open, high, low, close, volume}, times in epoch milliseconds (09:30 and
16:00 New York time).

    python tools/pinets_harness/export_bars.py AAPL NVDA GE KO SPY
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import pandas as pd

SRC = "/home/user/data/yahoo_daily/1d_*.parquet"
OUT = Path(__file__).resolve().parent / "bars"


def main(symbols: list[str]) -> None:
    OUT.mkdir(exist_ok=True)
    want = set(symbols)
    frames = []
    for f in sorted(glob.glob(SRC)):
        d = pd.read_parquet(f)
        d = d[d["symbol"].isin(want)]
        if len(d):
            frames.append(d)
    d = pd.concat(frames).drop_duplicates(["symbol", "date"]).sort_values(["symbol", "date"])
    for sym, g in d.groupby("symbol"):
        g = g.dropna(subset=["open", "high", "low", "close"])
        day = pd.DatetimeIndex(g["date"])
        o = (day + pd.Timedelta(hours=9, minutes=30)).tz_localize("America/New_York").tz_convert("UTC")
        c = (day + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC")
        rows = [{"openTime": int(a.value // 10**6), "closeTime": int(b.value // 10**6), "open": float(r.open), "high": float(r.high),
                 "low": float(r.low), "close": float(r.close), "volume": float(r.volume)}
                for a, b, r in zip(o, c, g.itertuples())]
        (OUT / f"{sym}.json").write_text(json.dumps(rows))
        print(sym, len(rows), g["date"].iloc[0].date(), g["date"].iloc[-1].date())


if __name__ == "__main__":
    main(sys.argv[1:] or ["AAPL", "NVDA", "GE", "KO", "SPY"])
