"""Download Yahoo daily history (split-adjusted OHLC, dividend-adjusted close, split and dividend
events) for a list of symbols. Survivors only: Yahoo drops delisted companies.

Used for three things:
  1. an independent cross-check of the DoltHub prices and of our split detection;
  2. long pre-2011 history of today's listed companies, ETFs and indices (survivor-biased context);
  3. market-state series (SPY, sector ETFs, ^VIX, ^VIX3M ...).

Usage:
    python -m research.data_build.00_yahoo_daily --symbols-file liquid_survivors.txt --out /home/user/data/yahoo_daily
    python -m research.data_build.00_yahoo_daily --symbols SPY QQQ ^VIX --out /home/user/data/yahoo_daily

Writes one parquet per batch plus a manifest. Safe to re-run: finished batches are skipped.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")


def fetch_batch(symbols: list[str], period: str, interval: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(symbols, period=period, interval=interval, auto_adjust=False, actions=True,
                      group_by="ticker", threads=True, progress=False)
    frames = []
    if raw is None or len(raw) == 0:
        return pd.DataFrame()
    for s in symbols:
        try:
            d = raw[s] if isinstance(raw.columns, pd.MultiIndex) else raw
        except KeyError:
            continue
        d = d.dropna(how="all")
        if d.empty or "Close" not in d:
            continue
        d = d.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close",
                              "Adj Close": "adj_close", "Volume": "volume",
                              "Dividends": "dividend", "Stock Splits": "split"})
        d = d.dropna(subset=["close"])
        d.index = pd.to_datetime(d.index).tz_localize(None) if getattr(d.index, "tz", None) is None \
            else pd.to_datetime(d.index).tz_convert("America/New_York").tz_localize(None)
        d.index.name = "date"
        d = d.reset_index()
        d.insert(0, "symbol", s)
        keep = [c for c in ["symbol", "date", "open", "high", "low", "close", "adj_close", "volume",
                            "dividend", "split"] if c in d.columns]
        frames.append(d[keep])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", default=[])
    ap.add_argument("--symbols-file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--period", default="max")
    ap.add_argument("--interval", default="1d")
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--pause", type=float, default=2.0)
    a = ap.parse_args()

    syms = list(a.symbols)
    if a.symbols_file:
        syms += [x.strip() for x in Path(a.symbols_file).read_text().split() if x.strip()]
    syms = sorted(set(syms))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"batches": {}}

    n_batches = (len(syms) + a.batch - 1) // a.batch
    for b in range(n_batches):
        chunk = syms[b * a.batch:(b + 1) * a.batch]
        key = f"{a.interval}_{b:04d}"
        f = out / f"{key}.parquet"
        if key in manifest["batches"] and f.exists() and manifest["batches"][key]["symbols"] == chunk:
            continue
        df = pd.DataFrame()
        for attempt in range(4):
            try:
                df = fetch_batch(chunk, a.period, a.interval)
                if len(df):
                    break
            except Exception as exc:  # noqa: BLE001 - network errors of many kinds
                print(f"batch {b} attempt {attempt}: {type(exc).__name__}: {str(exc)[:120]}", flush=True)
            time.sleep(a.pause * 4 * (attempt + 1))
        got = sorted(df["symbol"].unique()) if len(df) else []
        if len(df):
            df.to_parquet(f, index=False)
        manifest["batches"][key] = {"symbols": chunk, "got": got, "rows": int(len(df))}
        manifest_path.write_text(json.dumps(manifest))
        print(f"[{b + 1}/{n_batches}] {len(got)}/{len(chunk)} symbols, {len(df)} rows", flush=True)
        time.sleep(a.pause)
    total_got = sum(len(v["got"]) for v in manifest["batches"].values())
    print(f"done: {total_got}/{len(syms)} symbols with data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
