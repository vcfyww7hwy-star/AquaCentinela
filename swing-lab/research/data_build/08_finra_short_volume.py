"""FINRA daily short-sale volume (consolidated NMS file, "CNMSshvol"), 2018-08-01 onward.

One row per symbol and day: ShortVolume, ShortExemptVolume, TotalVolume of trades reported to
FINRA facilities (off-exchange). TradingView exposes the same series as FINRA:<TICKER>_SHORT_VOLUME
(daily, first bar 2018-08-01), so anything built on it is reachable from Pine.

Only dates up to 2022-12-30 are downloaded here; the lockbox period is fetched when it is opened.
Because the series starts inside the validation window, this family has its own split, declared in
docs/00_protocol.md (amendment 1): explore 2018-08-01..2020-06-30, confirm 2020-07-01..2022-12-30.

Usage: python -m research.data_build.08_finra_short_volume download | build
"""
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("/home/user/data_raw/finra_cnms")
OUT = Path("/home/user/data/finra")
URL = "https://cdn.finra.org/equity/regsho/daily/CNMSshvol{d}.txt"


def download() -> None:
    dates = np.load("/home/user/data/panel/devval/dates.npy").astype("datetime64[D]")
    dates = dates[dates >= np.datetime64("2018-08-01")]
    RAW.mkdir(parents=True, exist_ok=True)
    got = miss = 0
    for d in dates:
        s = str(d).replace("-", "")
        f = RAW / f"{s}.txt"
        if f.exists() and f.stat().st_size > 1000:
            got += 1
            continue
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(URL.format(d=s), headers={"User-Agent": "research-client"}), timeout=60) as r:
                    f.write_bytes(r.read())
                got += 1
                break
            except urllib.error.HTTPError as e:
                if e.code in (403, 404):
                    miss += 1
                    break
                time.sleep(3 * (attempt + 1))
            except Exception:  # noqa: BLE001
                time.sleep(3 * (attempt + 1))
        time.sleep(0.15)
    print(f"files present: {got}, not published: {miss}, of {len(dates)} trading days")


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for f in sorted(RAW.glob("[0-9]*.txt")):          # the download log lives in the same folder
        try:
            d = pd.read_csv(f, sep="|", dtype={"Symbol": object}, keep_default_na=False, on_bad_lines="skip")
        except Exception:  # noqa: BLE001
            continue
        if "Date" not in d.columns:
            continue
        d = d[d["Date"].astype(str).str.fullmatch(r"\d{8}")]
        if d.empty:
            continue
        d = d[["Date", "Symbol", "ShortVolume", "TotalVolume"]].copy()
        d["Date"] = pd.to_datetime(d["Date"].astype(str), format="%Y%m%d")
        for c in ("ShortVolume", "TotalVolume"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        frames.append(d)
    x = pd.concat(frames, ignore_index=True).rename(columns={"Date": "date", "Symbol": "symbol", "ShortVolume": "short", "TotalVolume": "total"})
    x.to_parquet(OUT / "short_volume_devval.parquet", index=False)
    print(f"rows {len(x):,}, days {x['date'].nunique()}, symbols {x['symbol'].nunique()}, {x['date'].min().date()}..{x['date'].max().date()}")
    print("median short share of FINRA-reported volume:", round(float((x['short'] / x['total']).median()), 3))


if __name__ == "__main__":
    {"download": download, "build": build}[sys.argv[1] if len(sys.argv) > 1 else "download"]()
