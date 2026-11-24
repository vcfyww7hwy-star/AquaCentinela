"""FINRA consolidated daily short-sale volume aligned to a Study.

    sv = load(S) -> dict of [T, N] float arrays: short, total  (NaN where FINRA has no row)

Source: cdn.finra.org/equity/regsho/daily/CNMSshvolYYYYMMDD.txt, built by
data_build/08_finra_short_volume.py; only rows up to 2022-12-30 are in the file this reads.
`short` and `total` are the short-sale and total share volumes of trades reported to FINRA's
facilities (off-exchange trades), not consolidated volume.

Timing. FINRA publishes the file for day t in the evening of day t, after the close. A daily-bar
script that decides at the close of t therefore knows the value of t-1 at best. Features are built
with an explicit lag L: L = 1 is the base case (Pine-safe), L = 0 is the "evening" variant that
would need the trader to look after the file is published.

TradingView exposes the short volume as FINRA:<TICKER>_SHORT_VOLUME (daily, from 2018-08-01).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

FILE = Path("/home/user/data/finra/short_volume_devval.parquet")


def load(S) -> dict:
    d = pd.read_parquet(FILE)
    d["symbol"] = d["symbol"].astype(str).str.replace("/", ".", regex=False)
    ents = S.ents[["symbol", "first", "last"]].copy()
    ents["col"] = np.arange(len(ents))
    ents["first"] = pd.to_datetime(ents["first"]).astype("datetime64[ns]")
    ents["last"] = pd.to_datetime(ents["last"]).astype("datetime64[ns]")
    d["date"] = d["date"].astype("datetime64[ns]")
    m = d.merge(ents, on="symbol", how="inner")
    m = m[(m["date"] >= m["first"]) & (m["date"] <= m["last"])]
    dates = pd.DatetimeIndex(S.dates)
    row = dates.get_indexer(m["date"])
    ok = row >= 0
    T, N = S.P.c.shape
    short = np.full((T, N), np.nan)
    total = np.full((T, N), np.nan)
    short[row[ok], m["col"].to_numpy()[ok]] = m["short"].to_numpy(dtype=float)[ok]
    total[row[ok], m["col"].to_numpy()[ok]] = m["total"].to_numpy(dtype=float)[ok]
    return {"short": short, "total": total}
