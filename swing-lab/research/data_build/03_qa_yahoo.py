"""Cross-check the cleaned DoltHub series against Yahoo for companies that still trade.

Two independent community/vendor sources agreeing bar for bar is the best evidence available here
that a price series is right. Disagreement marks a symbol as unverified; reversal-type results are
re-run on the verified subset (protocol section 6.3).

Compares, per symbol, on common dates:
  - split-adjusted close-to-close returns (ours vs Yahoo "Close", which is split-adjusted);
  - split events (ours applied vs Yahoo's "Stock Splits").

Output: qa_yahoo.parquet (one row per symbol) and qa_yahoo.json (totals).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily", default="/home/user/data/daily")
    ap.add_argument("--yahoo", default="/home/user/data/yahoo_daily")
    ap.add_argument("--tol", type=float, default=0.02)
    a = ap.parse_args()
    ddir, ydir = Path(a.daily), Path(a.yahoo)

    ent = pd.read_parquet(ddir / "entities.parquet")
    live = ent[ent["is_last_entity_of_symbol"] & ~ent["ended"]].set_index("symbol")
    daily = pd.read_parquet(ddir / "daily.parquet", columns=["eid", "date", "c", "c_raw", "v", "split_ratio", "bad"])
    daily = daily[daily["eid"].isin(live["eid"])]
    eid_to_sym = dict(zip(live["eid"], live.index))
    daily["symbol"] = daily["eid"].map(eid_to_sym)

    rows, miss_splits, extra_splits = [], [], []
    for f in sorted(ydir.glob("1d_*.parquet")):
        y = pd.read_parquet(f)
        y["sym"] = y["symbol"].str.replace("-", ".", regex=False)
        for s, yy in y.groupby("sym"):
            if s not in live.index:
                continue
            us = daily[daily["symbol"] == s].set_index("date").sort_index()
            yy = yy.set_index("date").sort_index()
            yy = yy[~yy.index.duplicated(keep="last")]
            j = us.join(yy[["close", "split", "volume"]], how="inner", rsuffix="_y")
            if len(j) < 60:
                continue
            r_us = j["c"].pct_change()
            r_y = j["close"].pct_change()
            diff = (r_us - r_y).abs()
            n = int(diff.notna().sum())
            bad_days = diff > a.tol
            # level check: ratio of our adjusted close to Yahoo's should be constant
            lvl = np.log(j["c"] / j["close"])
            lvl_range = float(lvl.max() - lvl.min())
            # splits
            ours = j.index[(j["split_ratio"] != 1.0)]
            theirs = j.index[(j["split"].fillna(0) != 0)]
            our_r = j.loc[ours, "split_ratio"]
            their_r = j.loc[theirs, "split"]
            matched_ours = set()
            n_missed = 0
            for dt, ry in their_r.items():
                near = [d for d in ours if abs((d - dt).days) <= 5 and abs(np.log(our_r[d] / ry)) < 0.05]
                if near:
                    matched_ours.update(near)
                else:
                    n_missed += 1
                    miss_splits.append((s, dt, float(ry)))
            n_extra = 0
            for dt in ours:
                if dt not in matched_ours:
                    n_extra += 1
                    extra_splits.append((s, dt, float(our_r[dt])))
            rows.append({
                "symbol": s, "eid": int(live.at[s, "eid"]), "n": n,
                "bad_days": int(bad_days.sum()), "bad_frac": float(bad_days.mean()),
                "max_abs_diff": float(diff.max()), "level_range": lvl_range,
                "first": j.index[0], "last": j.index[-1],
                "splits_ours": int(len(ours)), "splits_yahoo": int(len(theirs)),
                "splits_missed": n_missed, "splits_extra": n_extra,
                "vol_ratio_median": float((j["v"] / j["volume"].replace(0, np.nan)).median()),
            })
    q = pd.DataFrame(rows)
    q["verified"] = (q["bad_days"] <= 2) & (q["level_range"] < 0.05)
    q.to_parquet(ddir / "qa_yahoo.parquet", index=False)
    pd.DataFrame(miss_splits, columns=["symbol", "date", "ratio"]).to_parquet(ddir / "qa_splits_missed.parquet", index=False)
    pd.DataFrame(extra_splits, columns=["symbol", "date", "ratio"]).to_parquet(ddir / "qa_splits_extra.parquet", index=False)
    tot = {
        "symbols_compared": int(len(q)),
        "symbol_days_compared": int(q["n"].sum()),
        "days_return_diff_gt_tol": int(q["bad_days"].sum()),
        "frac_days_diff": float(q["bad_days"].sum() / max(q["n"].sum(), 1)),
        "symbols_verified": int(q["verified"].sum()),
        "symbols_zero_bad_days": int((q["bad_days"] == 0).sum()),
        "yahoo_splits_total": int(q["splits_yahoo"].sum()),
        "yahoo_splits_we_missed": int(q["splits_missed"].sum()),
        "our_splits_total": int(q["splits_ours"].sum()),
        "our_splits_not_in_yahoo": int(q["splits_extra"].sum()),
        "tol": a.tol,
    }
    (ddir / "qa_yahoo.json").write_text(json.dumps(tot, indent=1))
    print(json.dumps(tot, indent=1))
    print("\nworst 15 symbols by bad days:")
    print(q.sort_values("bad_days", ascending=False).head(15)[
        ["symbol", "n", "bad_days", "max_abs_diff", "level_range", "splits_ours", "splits_yahoo",
         "splits_missed", "splits_extra"]].to_string(index=False))


if __name__ == "__main__":
    main()
