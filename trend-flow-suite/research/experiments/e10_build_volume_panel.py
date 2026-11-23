#!/usr/bin/env python3
"""E10 - Shared daily panel for the volume experiments E11+ (review of the Relative Volume pane).

Builds one parquet file per data set with every series the volume experiments need, so that all of
them work from identical definitions. The definitions are the ones of the shipped indicator
(tfs.flow.volume_flow_v2 == pine/relative_volume.pine) and of E05 (risk-scaled forward returns).

Sets (all daily bars, survivors only):
  A, B  S&P 500 five-year set (Feb 2013 - Feb 2018), split by ticker hash exactly as in E05
  DJ    Dow-30 set, up to 2013-02-07, as in E05
  LH    the S&P names traced back in the "Huge Stock Market Dataset", 1999-01-02 .. 2013-02-07 (E08)
  MS    NEW: non-S&P stocks of the same Huge dataset, 2005-01-03 .. 2017-11-10, liquid enough to
        trade (median close >= 5, median dollar volume >= 2e6), at most 1200 names chosen by hash.
        Mostly mid and small caps. Listed in Nov 2017, so survivors only.

The data folders are public Kaggle sets and are NOT part of this repository.
  python3 -I experiments/e10_build_volume_panel.py --sp5 DIR --dj DIR --huge DIR --out DIR
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import hashlib
import json
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from tfs.data import load_bundled, load_ohlcv_dir
from tfs.flow import volume_flow_v2
from tfs.trend import robust_var_lagged

EVAL_START = 400
HORIZONS = (5, 10, 20)
_BENCH = None
_SPY = None


def half(ticker: str) -> str:
    return "A" if int(hashlib.md5(ticker.encode()).hexdigest(), 16) % 2 == 0 else "B"


def _fwd_sum(x: np.ndarray, h: int) -> np.ndarray:
    """sum of x[t+1 .. t+h]; NaN where the window is incomplete."""
    cs = np.cumsum(np.nan_to_num(x, nan=0.0))
    out = np.full(len(x), np.nan)
    out[:-h] = cs[h:] - cs[:-h]
    bad = np.isnan(x).astype(float)
    cb = np.cumsum(bad)
    nb = np.full(len(x), np.nan)
    nb[:-h] = cb[h:] - cb[:-h]
    out[nb > 0] = np.nan
    return out


def features(item):
    ticker, df = item
    o, h, l, c, v = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close", "volume"))
    n = len(c)
    fl = volume_flow_v2(df)
    lnc = np.log(c)
    r = np.r_[np.nan, np.diff(lnc)]
    sig0 = np.sqrt(robust_var_lagged(r, 100, 3.0))
    b = _BENCH.reindex(df.index).ffill().bfill().to_numpy()
    lnb = np.log(b)
    rng = h - l
    prev_c = np.r_[np.nan, c[:-1]]
    with np.errstate(divide="ignore", invalid="ignore"):
        clv = np.where(rng > 0, (c - l) / rng, 0.5)
        gap = np.log(o / prev_c)
        body = np.log(c / o)
        pk = np.log(h / l) ** 2 / (4.0 * np.log(2.0))          # Parkinson daily variance
    out = {
        "date": df.index.to_numpy(), "t": np.arange(n, dtype=np.int32),
        "month": (df.index.year * 12 + df.index.month - 1).to_numpy().astype(np.int32),
        "open": o, "high": h, "low": l, "close": c, "volume": v, "dvol": c * v,
        "r": r, "sigma": fl["sigma"].to_numpy(), "z": fl["z"].to_numpy(), "sig0": sig0,
        "ev": fl["ev"].to_numpy(), "rvol": fl["rvol"].to_numpy(),
        "atr": fl["atr"].to_numpy(), "ext": fl["ext"].to_numpy(),
        "clv": clv, "gap": gap, "body": body, "pk": pk,
        "asym_z": fl["asym_z"].to_numpy(),
    }
    for k in ("absorb_bottom", "absorb_top", "climax_up", "climax_dn", "dryup", "accumulation", "distribution"):
        out[k] = fl[k].to_numpy().astype(bool)
    for hz in HORIZONS:
        f = np.full(n, np.nan)
        f[:-hz] = lnc[hz:] - lnc[:-hz]
        fb = np.full(n, np.nan)
        fb[:-hz] = lnb[hz:] - lnb[:-hz]
        out[f"f{hz}"] = f                                       # raw forward log return, close to close
        out[f"fb{hz}"] = fb                                     # same for the SPX benchmark of E05
        out[f"fz{hz}"] = f / (sig0 * np.sqrt(hz))               # E05 metric
        out[f"fzx{hz}"] = (f - fb) / (sig0 * np.sqrt(hz))       # E05 market-adjusted metric
        out[f"rv_fwd{hz}"] = np.sqrt(_fwd_sum(r * r, hz) / hz)  # realised vol of the next hz bars
        out[f"pk_fwd{hz}"] = np.sqrt(_fwd_sum(pk, hz) / hz)
    pan = pd.DataFrame(out)
    pan["eval"] = ((np.arange(n) >= EVAL_START) & pan["fz20"].notna().to_numpy()
                   & np.isfinite(pan["fz10"].to_numpy()))
    if _SPY is not None:
        pan["spy_rvol"] = _SPY.reindex(df.index).to_numpy()
    else:
        pan["spy_rvol"] = np.nan
    pan.insert(0, "ticker", ticker)
    pan["half"] = half(ticker)
    return pan


def build(name, stocks, outdir):
    t0 = time.time()
    with Pool(4) as pool:
        frames = pool.map(features, sorted(stocks.items()), chunksize=8)
    pan = pd.concat(frames, ignore_index=True)
    # market participation and market move, measured inside the set on each date
    with np.errstate(divide="ignore", invalid="ignore"):
        pan["lrvol"] = np.log(pan["rvol"].where(pan["rvol"] > 0))
    g = pan.groupby("date")
    pan["mkt_lrvol"] = g["lrvol"].transform("median")
    pan["n_date"] = g["ticker"].transform("size").astype(np.int32)
    for hz in HORIZONS:
        pan[f"fx{hz}"] = pan[f"f{hz}"] - g[f"f{hz}"].transform("mean")      # date-demeaned forward return
        pan[f"fzd{hz}"] = pan[f"fx{hz}"] / (pan["sig0"] * np.sqrt(hz))
    pan["r_mkt"] = g["r"].transform("mean")
    for col in pan.columns:
        if pan[col].dtype == np.float64 and col not in ("open", "high", "low", "close", "volume", "dvol"):
            pan[col] = pan[col].astype(np.float32)
    pan["set"] = name
    path = pathlib.Path(outdir) / f"panel_{name}.parquet"
    pan.to_parquet(path, index=False)
    ev = pan[pan["eval"]]
    ab = ev["absorb_bottom"].to_numpy()
    ctl = (ev["ext"].to_numpy() <= -1.5) & ~ev["climax_dn"].to_numpy() & ~ab
    info = {"set": name, "stocks": int(pan["ticker"].nunique()), "rows": int(len(pan)),
            "eval_rows": int(len(ev)), "first_eval": str(ev["date"].min())[:10], "last": str(pan["date"].max())[:10],
            "absorb_bottom_eval": int(ab.sum()), "control_eval": int(ctl.sum()),
            "old_test_fz10_diff": round(float(np.nanmean(ev["fz10"].to_numpy()[ab])
                                              - np.nanmean(ev["fz10"].to_numpy()[ctl])), 4),
            "zero_volume_rows": int((pan["volume"] <= 0).sum()), "seconds": round(time.time() - t0)}
    print(json.dumps(info))
    return info


def main():
    global _BENCH, _SPY
    ap = argparse.ArgumentParser()
    ap.add_argument("--sp5", required=True)
    ap.add_argument("--dj", required=True)
    ap.add_argument("--huge", required=True, help="folder holding Stocks/ and ETFs/")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ms-max", type=int, default=1200)
    a = ap.parse_args()
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    _BENCH = load_bundled("SPX")["close"]
    spy, _ = load_ohlcv_dir(pathlib.Path(a.huge) / "ETFs", "spy.us.txt", min_bars=700)
    _SPY = volume_flow_v2(spy["SPY"])["rvol"]
    infos = []

    sp5, _ = load_ohlcv_dir(a.sp5, "*_data.csv", min_bars=700)
    infos.append(build("A", {k: v for k, v in sp5.items() if half(k) == "A"}, a.out))
    infos.append(build("B", {k: v for k, v in sp5.items() if half(k) == "B"}, a.out))
    dj, _ = load_ohlcv_dir(a.dj, "*_2006-01-01_to_2018-01-01.csv", min_bars=700, end="2013-02-07")
    infos.append(build("DJ", dj, a.out))

    names = {p.name.split("_")[0].upper().replace(".", "-") for p in pathlib.Path(a.sp5).rglob("*_data.csv")
             if not p.name.startswith(".")}
    stocks_dir = pathlib.Path(a.huge) / "Stocks"
    lh, _ = load_ohlcv_dir(stocks_dir, "*.us.txt", min_bars=700, start="1999-01-02", end="2013-02-07", tickers=names)
    infos.append(build("LH", lh, a.out))
    del lh

    allst, audit = load_ohlcv_dir(stocks_dir, "*.us.txt", min_bars=1000, start="2005-01-03", end="2017-11-10")
    cand = {}
    for k, d in allst.items():
        if k in names:
            continue
        if d["close"].median() >= 5.0 and (d["close"] * d["volume"]).median() >= 2e6:
            cand[k] = d
    keys = sorted(cand, key=lambda s: hashlib.md5(s.encode()).hexdigest())[: a.ms_max]
    print(f"MS: {len(allst)} loaded, {len(cand)} pass the price and liquidity filter, {len(keys)} used")
    del allst
    info = build("MS", {k: cand[k] for k in keys}, a.out)
    info["candidates"] = len(cand)
    infos.append(info)
    (pathlib.Path(a.out) / "panel_info.json").write_text(json.dumps(infos, indent=1))


if __name__ == "__main__":
    main()
