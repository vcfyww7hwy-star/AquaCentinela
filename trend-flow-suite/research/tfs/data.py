"""Data loading. Every loader returns a DataFrame indexed by timestamp with lower-case
columns: open, high, low, close, volume.

Sources
-------
- `load_bundled`: free sample data shipped inside PyPI packages (works offline):
    SPX     S&P 500 index, daily 1999-2018    (package `arch`, originally Yahoo Finance)
    NASDAQ  NASDAQ Composite, daily 1999-2018 (package `arch`)
    GOOG    Alphabet class C, daily 2004-2013 (package `backtesting`)
  Index "volume" is an aggregate figure, not the volume of a tradable instrument.
- `load_ohlcv_dir`: a folder of per-ticker CSVs (date, open, high, low, close, volume), the layout
  of the public Kaggle sets used in E05 (S&P 500 2013-2018; Dow 30 2006-2017). Not bundled.
- `load_csv`: any file in the standard schema (e.g. a vendor export).
- `load_tradingview_export`: TradingView "Export chart data" CSV.
- `fetch_financial_datasets`: REST API of financialdatasets.ai (needs an API key in
  FINANCIAL_DATASETS_API_KEY and network access to api.financialdatasets.ai).
  UNTESTED: the host was blocked by the network policy of the environment where this was written.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pandas as pd

COLS = ["open", "high", "low", "close", "volume"]


def _package_dir(name: str) -> Path:
    spec = importlib.util.find_spec(name)  # locates the package without importing it
    if spec is None or spec.origin is None:
        raise ImportError(f"Package '{name}' is not installed: pip install {name}")
    return Path(spec.origin).parent


def load_bundled(name: str) -> pd.DataFrame:
    name = name.upper()
    if name in ("SPX", "NASDAQ"):
        sub = {"SPX": "sp500/sp500.csv.gz", "NASDAQ": "nasdaq/nasdaq.csv.gz"}[name]
        d = pd.read_csv(_package_dir("arch") / "data" / sub)
        d["Date"] = pd.to_datetime(d["Date"], format="%m/%d/%Y")
        d = d.set_index("Date")
    elif name == "GOOG":
        d = pd.read_csv(_package_dir("backtesting") / "test" / "GOOG.csv", index_col=0, parse_dates=True)
    else:
        raise ValueError("bundled datasets: SPX, NASDAQ, GOOG")
    d.columns = [c.lower() for c in d.columns]
    return d[COLS].astype(float)


def load_csv(path: str | Path, date_col: str = "date") -> pd.DataFrame:
    d = pd.read_csv(path)
    d.columns = [c.strip().lower() for c in d.columns]
    d[date_col] = pd.to_datetime(d[date_col])
    return d.set_index(date_col)[COLS].astype(float)


def load_tradingview_export(path: str | Path) -> pd.DataFrame:
    """TradingView chart export: a 'time' column (UNIX seconds or ISO text) followed by OHLC,
    'Volume' and one column per plotted indicator series. Indicator columns are kept."""
    d = pd.read_csv(path)
    t = d["time"]
    d.index = pd.to_datetime(t, unit="s") if pd.api.types.is_numeric_dtype(t) else pd.to_datetime(t)
    d = d.drop(columns=["time"])
    d.columns = [c.strip().lower() if c.strip().lower() in COLS else c.strip() for c in d.columns]
    return d


def fetch_financial_datasets(ticker: str, start: str, end: str, interval: str = "day",
                             multiplier: int = 1) -> pd.DataFrame:
    """Download prices from financialdatasets.ai. UNTESTED here (host blocked by network policy)."""
    import requests

    key = os.environ.get("FINANCIAL_DATASETS_API_KEY")
    if not key:
        raise RuntimeError("Set FINANCIAL_DATASETS_API_KEY")
    resp = requests.get(
        "https://api.financialdatasets.ai/prices/",
        params={"ticker": ticker, "interval": interval, "interval_multiplier": multiplier,
                "start_date": start, "end_date": end},
        headers={"X-API-KEY": key}, timeout=60)
    resp.raise_for_status()
    d = pd.DataFrame(resp.json()["prices"])
    d.index = pd.to_datetime(d["time"])
    return d[COLS].astype(float)


def load_ohlcv_dir(path: str | Path, pattern: str = "*.csv", min_bars: int = 700,
                   start: str | None = None, end: str | None = None,
                   skip_prefixes: tuple[str, ...] = ("all_stocks",), tickers=None):
    """Load a folder of per-ticker daily CSVs. Returns ({ticker: frame}, audit dict).

    Cleaning: rows with a missing or non-positive OHLC value are dropped; missing volume becomes
    0; high/low are widened to contain open and close; duplicate dates keep the last row.
    Tickers with fewer than `min_bars` rows after the date filter are skipped.
    The ticker is the file name up to the first underscore ("AAPL_data.csv") or, without one, up
    to the first dot ("aapl.us.txt"), upper-cased. `tickers`: optional set of tickers to load."""
    out, audit = {}, {"files": 0, "kept": 0, "too_short": 0, "rows": 0, "rows_dropped": 0,
                      "rows_hl_repaired": 0, "zero_volume_rows": 0, "max_abs_log_return": {}}
    for f in sorted(Path(path).rglob(pattern)):
        if f.name.startswith(skip_prefixes) or f.name.startswith(".") or "__MACOSX" in f.parts:
            continue                                  # combined files, hidden files, macOS metadata
        tkr = (f.name.split("_")[0] if "_" in f.name else f.name.split(".")[0]).upper()
        if tickers is not None and tkr not in tickers:
            continue
        if f.stat().st_size == 0:
            continue
        audit["files"] += 1
        d = pd.read_csv(f)
        d.columns = [c.strip().lower() for c in d.columns]
        d["date"] = pd.to_datetime(d["date"])
        d = d.drop_duplicates("date", keep="last").set_index("date").sort_index()
        d = d[COLS].apply(pd.to_numeric, errors="coerce")
        n0 = len(d)
        d["volume"] = d["volume"].fillna(0.0)
        ok = d[["open", "high", "low", "close"]].notna().all(axis=1) & (d[["open", "high", "low", "close"]] > 0).all(axis=1)
        d = d[ok]
        hi = d[["open", "high", "close"]].max(axis=1)
        lo = d[["open", "low", "close"]].min(axis=1)
        audit["rows_hl_repaired"] += int(((hi > d["high"]) | (lo < d["low"])).sum())
        d["high"], d["low"] = hi, lo
        if start:
            d = d[d.index >= start]
        if end:
            d = d[d.index <= end]
        audit["rows_dropped"] += n0 - int(ok.sum())
        if len(d) < min_bars:
            audit["too_short"] += 1
            continue
        out[tkr] = d.astype(float)
        audit["kept"] += 1
        audit["rows"] += len(d)
        audit["zero_volume_rows"] += int((d["volume"] <= 0).sum())
        jump = float(np.abs(np.log(d["close"]).diff()).max())
        if jump > 0.4:
            audit["max_abs_log_return"][tkr] = round(jump, 3)
    return out, audit
