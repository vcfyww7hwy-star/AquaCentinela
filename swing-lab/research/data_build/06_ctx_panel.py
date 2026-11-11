"""Context panel: Yahoo daily history of today's survivors, 1997-2010.

Purpose: a second development sample that contains the 2000-02 and 2008 bear markets.
Bias: STRONG. Only companies that still trade in 2026 are here. Dip-buying and trend rules look
better than they were. Nothing is promoted on this sample; it is used to see whether an effect
found in 2011-2018 behaves the same way in bear markets, before spending a validation look.

Same layout as the main panel (see 05_panel.py), written to <out>/ctx/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import bottleneck as bn
import numpy as np
import pandas as pd

START, END = np.datetime64("1997-01-02"), np.datetime64("2010-12-31")
ADV_MIN, PX_MIN, MIN_DAYS = 5e6, 3.0, 20
TYPES = {"common", "adr", "etf", "etf_levinv", "prior_use", "unknown"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merged", default="/home/user/data/merged")
    ap.add_argument("--out", default="/home/user/data/panel")
    a = ap.parse_args()
    mdir, out = Path(a.merged), Path(a.out) / "ctx"
    out.mkdir(parents=True, exist_ok=True)

    Y = pd.read_parquet(mdir / "yahoo_full_history.parquet")
    Y = Y.sort_values(["sym", "date"])
    # raw price = split-adjusted close x product of all LATER split ratios (over the full history)
    sr = Y["split"].where(Y["split"] > 0, 1.0)
    later = sr[::-1].groupby(Y["sym"][::-1], sort=False).cumprod()[::-1]
    later = later.groupby(Y["sym"], sort=False).shift(-1).fillna(1.0)
    Y["c_raw"] = Y["close"] * later
    Y = Y[(Y["date"] >= START) & (Y["date"] <= END)]
    E = pd.read_parquet(mdir / "merged_entities.parquet")
    E = E[E["src"] == "yahoo"].set_index("symbol")
    Y = Y[Y["sym"].isin(E.index)]

    dates = np.sort(Y["date"].unique())
    syms = np.sort(Y["sym"].unique())
    r = np.searchsorted(dates, Y["date"].to_numpy())
    k = np.searchsorted(syms, Y["sym"].to_numpy())
    T, N0 = len(dates), len(syms)

    def wide(col: str) -> np.ndarray:
        x = np.full((T, N0), np.nan, dtype=np.float32)
        x[r, k] = Y[col].to_numpy(dtype=np.float32)
        return x

    c, v, c_raw = wide("close"), wide("volume"), wide("c_raw")
    adv60 = bn.move_median(c.astype(np.float64) * v, window=60, min_count=40, axis=0).astype(np.float32)
    liquid = (adv60 >= ADV_MIN) & (c_raw >= PX_MIN)
    types = E["type"].reindex(syms).fillna("unknown")
    suspect = E["suspect"].reindex(syms).fillna(False).to_numpy(dtype=bool) if "suspect" in E else np.zeros(N0, bool)
    keep = (np.nansum(liquid, axis=0) >= MIN_DAYS) & types.isin(TYPES).to_numpy() & ~suspect
    cols = np.flatnonzero(keep)
    ents = pd.DataFrame({"mid": ["Y:" + s for s in syms[cols]], "symbol": syms[cols], "src": "yahoo",
                         "ended": False, "type": types.to_numpy()[cols], "col": np.arange(len(cols))})
    fields = {"c": c[:, cols], "v": v[:, cols], "c_raw": c_raw[:, cols], "adv60": adv60[:, cols],
              "o": wide("open")[:, cols], "h": wide("high")[:, cols], "l": wide("low")[:, cols],
              "div": np.nan_to_num(wide("dividend")[:, cols]).astype(np.float32)}
    # bad ticks
    cc = fields["c"].astype(np.float64)
    prev = np.vstack([np.full((1, cc.shape[1]), np.nan), cc[:-1]])
    nxt = np.vstack([cc[1:], np.full((1, cc.shape[1]), np.nan)])
    with np.errstate(divide="ignore", invalid="ignore"):
        bad = (np.abs(np.log(cc / prev)) > 0.5) & (np.abs(np.log(nxt / prev)) < 0.12)
    fields["bad"] = bad.astype(np.int8)
    np.save(out / "dates.npy", dates)
    for f, x in fields.items():
        np.save(out / f"{f}.npy", x)
    ents.to_parquet(out / "ents.parquet", index=False)
    summary = {"securities": int(len(cols)), "dates": int(T), "first": str(dates[0])[:10], "last": str(dates[-1])[:10],
               "by_type": {kk: int(vv) for kk, vv in ents["type"].value_counts().items()},
               "bad_tick_bars": int(bad.sum())}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
