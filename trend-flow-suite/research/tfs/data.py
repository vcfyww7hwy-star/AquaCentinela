"""Data loading. Every loader returns a DataFrame indexed by timestamp with lower-case
columns: open, high, low, close, volume.

Sources
-------
- `load_bundled`: free sample data shipped inside PyPI packages (works offline):
    SPX     S&P 500 index, daily 1999-2018    (package `arch`, originally Yahoo Finance)
    NASDAQ  NASDAQ Composite, daily 1999-2018 (package `arch`)
    GOOG    Alphabet class C, daily 2004-2013 (package `backtesting`)
  Index "volume" is an aggregate figure, not the volume of a tradable instrument.
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
