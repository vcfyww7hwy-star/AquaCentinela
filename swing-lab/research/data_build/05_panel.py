"""Build the research panel: date x security matrices for securities that were ever liquid.

Two physical copies are written:

    <out>/devval/                       dates up to 2022-12-30 only. Every experiment reads this.
    <out>/LOCKBOX_SEALED_do_not_open/   all dates. Read once, at the end, through
                                        swinglab.data.open_lockbox(), which records the opening.

Matrices are float32 [T, N], NaN where a security has no bar:
    o h l c      split-adjusted prices          v      split-adjusted share volume
    c_raw        price as traded (for the $-price filter)
    div          cash dividend on the ex-date (adjusted terms)
    adv60        median dollar volume of the previous 60 bars, known at the close of t
    bad          1 where the bar failed a quality test
Security metadata: ents.parquet (column order = matrix column order).

Inclusion: the security had adv60 >= ADV_MIN and c_raw >= PX_MIN on at least MIN_DAYS dates, and is
a common stock, ADR, ETF or an earlier use of a ticker (warrants, units, preferreds are excluded).
Inclusion uses the whole history, which is harmless: membership of the tradable universe on any
date is decided by adv60 and price on that date, both known then.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import bottleneck as bn
import numpy as np
import pandas as pd

ADV_MIN = 5e6
PX_MIN = 3.0
MIN_DAYS = 20
DEVVAL_END = np.datetime64("2022-12-30")
TYPES = {"common", "adr", "etf", "etf_levinv", "prior_use", "unknown"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merged", default="/home/user/data/merged")
    ap.add_argument("--out", default="/home/user/data/panel")
    a = ap.parse_args()
    mdir, out = Path(a.merged), Path(a.out)

    E = pd.read_parquet(mdir / "merged_entities.parquet")
    M = pd.read_parquet(mdir / "merged_daily.parquet")
    # Calendar = days on which the market was open, judged by SPY having a bar. The two sources
    # disagree on a few holidays (DoltHub carries stale bars on them); a row without the market
    # would be a hole for every Yahoo-sourced security and would disable 20- and 50-bar volume
    # windows for weeks (code audit B1, 12 Nov 2026).
    spy_mid = int(E.loc[E["mid"] == "Y:SPY", "mid_code"].iloc[0])
    open_days = np.sort(M.loc[M["mid"] == spy_mid, "date"].unique())
    n_before = M["date"].nunique()
    M = M[M["date"].isin(open_days)]
    dates = open_days
    print(f"calendar: {len(dates)} market days kept, {n_before - len(dates)} closed-market dates dropped")
    T, N0 = len(dates), len(E)
    r = np.searchsorted(dates, M["date"].to_numpy())
    k = M["mid"].to_numpy()

    def wide(col: str) -> np.ndarray:
        x = np.full((T, N0), np.nan, dtype=np.float32)
        x[r, k] = M[col].to_numpy(dtype=np.float32)
        return x

    c, v, c_raw = wide("c"), wide("v"), wide("c_raw")
    dv = c.astype(np.float64) * v
    # median of the last 60 available bars per security, in calendar alignment: gaps (NaN) are
    # skipped by the nan-aware moving median; at least 40 observations required
    adv60 = bn.move_median(dv, window=60, min_count=40, axis=0).astype(np.float32)
    del dv
    liquid = (adv60 >= ADV_MIN) & (c_raw >= PX_MIN)
    ok_type = E["type"].isin(TYPES).to_numpy().copy()
    if "suspect" in E.columns:                     # the two sources disagree about the security
        ok_type = ok_type & ~E["suspect"].fillna(False).to_numpy(dtype=bool)
    keep = (np.nansum(liquid, axis=0) >= MIN_DAYS) & ok_type
    cols = np.flatnonzero(keep)
    ents = E.iloc[cols].reset_index(drop=True)
    ents["col"] = np.arange(len(ents))
    print(f"securities in panel: {len(cols)} of {N0}; dates: {T}")

    fields = {"c": c[:, cols], "v": v[:, cols], "c_raw": c_raw[:, cols], "adv60": adv60[:, cols]}
    del c, v, c_raw, adv60, liquid
    for col in ("o", "h", "l", "div"):
        fields[col] = wide(col)[:, cols]
    bad = np.zeros((T, N0), dtype=np.int8)
    bad[r, k] = M["bad"].to_numpy()
    fields["bad"] = bad[:, cols]
    del bad, M

    t_end = int(np.searchsorted(dates, DEVVAL_END, side="right"))
    for name, tt in (("devval", t_end), ("LOCKBOX_SEALED_do_not_open", T)):
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        np.save(d / "dates.npy", dates[:tt])
        for f, x in fields.items():
            np.save(d / f"{f}.npy", x[:tt])
        ents.to_parquet(d / "ents.parquet", index=False)
    summary = {
        "securities": int(len(cols)), "dates_total": int(T), "dates_devval": int(t_end),
        "first_date": str(dates[0])[:10], "devval_last_date": str(dates[t_end - 1])[:10],
        "last_date": str(dates[-1])[:10],
        "by_type": {kk: int(vv) for kk, vv in ents["type"].value_counts().items()},
        "by_source": {kk: int(vv) for kk, vv in ents["src"].value_counts().items()},
        "ended": int(ents["ended"].sum()),
        "adv_min": ADV_MIN, "px_min": PX_MIN,
    }
    (out / "panel_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
