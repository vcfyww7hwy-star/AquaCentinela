"""Merge the two daily sources into one research set of securities.

    Yahoo     companies and funds that still trade: continuous, split- and spin-off-adjusted history
    DoltHub   everything as it traded, including names that stopped trading (cleaned by 02_entities)

Rule: a security that still trades is taken from Yahoo; a security that stopped trading is taken
from DoltHub. The overlap (survivors present in both) measures how good the DoltHub cleaning is,
which is the quality we get for the delisted names (written to merge_qa.json).

Two identity problems are resolved with Yahoo's continuous histories:

  Rename      FB stops, META starts: DoltHub shows a delisting and a new listing; Yahoo's META
              contains both. The DoltHub "FB" entity is a duplicate, not a delisting, and is dropped.
              Test: the ended entity's daily returns correlate > 0.95 with a Yahoo history.
  Take-over   Eldorado bought Caesars and took the ticker CZR: DoltHub's CZR is two companies glued
  of ticker   together; Yahoo's CZR is Eldorado throughout. The part of the DoltHub series before
              the break is a real company that stopped trading and is kept as an ended entity.
              Test: returns agree with Yahoo after some date and do not agree before it.

Output: merged_daily.parquet, merged_entities.parquet, merge_qa.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

START = pd.Timestamp("2011-01-03")
CORR_DUP = 0.95


def logret(x: pd.Series) -> pd.Series:
    return np.log(x).diff()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily", default="/home/user/data/daily")
    ap.add_argument("--yahoo", default="/home/user/data/yahoo_daily")
    ap.add_argument("--out", default="/home/user/data/merged")
    a = ap.parse_args()
    ddir, ydir, out = Path(a.daily), Path(a.yahoo), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    qa: dict = {}

    # ---------------------------------------------------------------- Yahoo
    ys = []
    for f in sorted(ydir.glob("1d_*.parquet")):
        ys.append(pd.read_parquet(f))
    Y = pd.concat(ys, ignore_index=True)
    del ys
    Y["sym"] = Y["symbol"].str.replace("-", ".", regex=False)
    for c in ("dividend", "split"):
        Y[c] = Y[c].fillna(0.0)
    Y = Y.dropna(subset=["open", "high", "low", "close"])
    Y = Y[(Y[["open", "high", "low", "close"]] > 0).all(axis=1)]
    Y = Y.drop_duplicates(["sym", "date"], keep="last").sort_values(["sym", "date"])
    # full history kept for long-context work (survivor-biased)
    Y.drop(columns=["symbol"]).to_parquet(out / "yahoo_full_history.parquet", index=False)
    ycount = Y.groupby("sym")["date"].agg(["size", "max"])
    last_day = Y["date"].max()
    y_ok = ycount.index[(ycount["size"] >= 250) & (ycount["max"] >= last_day - pd.Timedelta(days=10))]
    qa["yahoo_symbols_downloaded"] = int(len(ycount))
    qa["yahoo_symbols_usable"] = int(len(y_ok))
    Y = Y[Y["sym"].isin(y_ok)]
    ydict = {s: g.set_index("date") for s, g in Y.groupby("sym", sort=False)}
    del Y

    # ---------------------------------------------------------------- DoltHub
    ent = pd.read_parquet(ddir / "entities.parquet")
    D = pd.read_parquet(ddir / "daily.parquet")
    D = D.sort_values(["eid", "date"])
    didx = D.groupby("eid", sort=False).indices
    dates_all = D["date"].to_numpy()
    c_all = D["c"].to_numpy()

    def dser(eid: int) -> pd.Series:
        ix = didx[eid]
        return pd.Series(c_all[ix], index=pd.DatetimeIndex(dates_all[ix]))

    live = ent[~ent["ended"]]
    live_first = live.set_index("symbol")["first"].to_dict()
    live_eid = live.set_index("symbol")["eid"].to_dict()

    # ---------------------------------------------------------------- overlap quality + take-overs
    overlap_rows, prebreak = [], []
    for s in y_ok:
        if s not in live_eid:
            continue
        us, yy = dser(live_eid[s]), ydict[s]["close"]
        j = pd.concat([logret(us).rename("u"), logret(yy).rename("y")], axis=1, join="inner").dropna()
        if len(j) < 60:
            continue
        delta = (j["u"] - j["y"]).abs()
        dis = (delta > 0.01)
        # Identity is judged by whether MOST days disagree, never by one large disagreement:
        # a spin-off or a split missing from one source gives a single bad day in an otherwise
        # identical series (AT&T April 2022) and must not be read as a change of company.
        yr = j.index.year
        frac_by_year = dis.groupby(yr).mean()
        n_by_year = dis.groupby(yr).size()
        years = [int(k) for k in frac_by_year.index if n_by_year[k] >= 20]
        brk, status = None, "agree"

        def differs(k: int) -> bool:
            """Different security in year k: most days disagree AND returns are weakly related.
            (Sub-dollar stocks disagree by a cent, i.e. >1%, on most days yet correlate > 0.95.)"""
            if frac_by_year[k] <= 0.30:
                return False
            g = j[yr == k]
            lim = 0.5
            cu, cy = g["u"].clip(-lim, lim), g["y"].clip(-lim, lim)
            cc = cu.corr(cy) if cu.std() > 0 and cy.std() > 0 else 0.0
            return not (cc >= 0.5)

        if years:
            recent = years[-1] if n_by_year[years[-1]] >= 60 or len(years) == 1 else years[-2]
            if differs(recent):
                status = "conflict"             # the two sources disagree about the security today
            else:
                for k in reversed(years):
                    if differs(k):
                        g = dis[yr == k]
                        run = g.rolling(20, min_periods=10).mean()
                        cand = g.index[(run >= 0.5) & g]
                        brk = cand[-1] if len(cand) else g.index[g][-1]
                        # require agreement after the break
                        after = dis[j.index > brk]
                        if len(after) >= 60 and after.mean() < 0.05:
                            status = "takeover"
                        else:
                            status, brk = "conflict", None
                        break
        overlap_rows.append({"symbol": s, "n": int(len(j)), "bad2": int((delta > 0.02).sum()),
                             "bad25": int((delta > 0.25).sum()), "break": brk, "status": status,
                             "corr_all": float(j["u"].corr(j["y"]))})
        if status == "takeover":
            prebreak.append((s, live_eid[s], brk))
    ov = pd.DataFrame(overlap_rows)
    ov.to_parquet(out / "overlap_quality.parquet", index=False)
    qa["overlap_symbols"] = int(len(ov))
    qa["overlap_symbol_days"] = int(ov["n"].sum())
    clean = ov[ov["status"] == "agree"]
    qa["overlap_status"] = {k: int(v) for k, v in ov["status"].value_counts().items()}
    conflict = set(ov.loc[ov["status"] == "conflict", "symbol"])
    qa["overlap_days_diff_gt_2pct_frac"] = float(clean["bad2"].sum() / max(clean["n"].sum(), 1))
    qa["overlap_days_diff_gt_25pct_frac"] = float(clean["bad25"].sum() / max(clean["n"].sum(), 1))
    qa["overlap_symbols_with_zero_diff_days"] = int((clean["bad2"] == 0).sum())
    qa["ticker_takeovers_found"] = int(len(prebreak))

    # ---------------------------------------------------------------- renames (duplicates)
    ended = ent[ent["ended"] & (ent["bars"] >= 40)]
    # Yahoo symbols whose DoltHub live entity starts shortly after a given date
    starts = pd.Series(live_first).sort_values()
    start_syms = starts.index.to_numpy()
    start_vals = starts.to_numpy()
    dup_of = {}
    for row in ended.itertuples(index=False):
        us = dser(row.eid)
        cands = []
        if row.symbol in ydict:
            cands.append(row.symbol)
        lo = np.searchsorted(start_vals, np.datetime64(row.last), side="right")
        hi = np.searchsorted(start_vals, np.datetime64(row.last + pd.Timedelta(days=30)), side="right")
        cands += [s for s in start_syms[lo:hi] if s in ydict]
        lu = logret(us).dropna().iloc[-250:]
        for s in cands:
            j = pd.concat([lu.rename("u"), logret(ydict[s]["close"]).rename("y")], axis=1, join="inner").dropna()
            if len(j) >= 30 and j["u"].std() > 0 and j["y"].std() > 0 and j["u"].corr(j["y"]) > CORR_DUP:
                dup_of[row.eid] = s
                break
    qa["ended_entities_tested"] = int(len(ended))
    qa["ended_entities_dropped_as_rename_duplicates"] = int(len(dup_of))

    # ---------------------------------------------------------------- assemble
    frames, erows = [], []
    symtype = ent.drop_duplicates("symbol", keep="last").set_index("symbol")[["type", "security_name", "listing_exchange"]]

    # (1) Yahoo survivors
    for s in y_ok:
        g = ydict[s]
        g = g[g.index >= START - pd.Timedelta(days=0)]
        if len(g) < 2:
            continue
        # raw close = adjusted close x product of later split ratios
        sr = g["split"].where(g["split"] > 0, 1.0)
        later = sr[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
        mid = f"Y:{s}"
        frames.append(pd.DataFrame({
            "mid": mid, "date": g.index, "o": g["open"].to_numpy(), "h": g["high"].to_numpy(),
            "l": g["low"].to_numpy(), "c": g["close"].to_numpy(), "v": g["volume"].to_numpy(dtype="float64"),
            "c_raw": (g["close"] * later).to_numpy(), "div": g["dividend"].to_numpy(),
            "split_ratio": sr.to_numpy()}))
        t = symtype.loc[s] if s in symtype.index else None
        erows.append({"mid": mid, "symbol": s, "src": "yahoo", "first": g.index[0], "last": g.index[-1],
                      "bars": len(g), "ended": False, "suspect": s in conflict,
                      "type": t["type"] if t is not None else "unknown",
                      "name": t["security_name"] if t is not None else ""})

    # (2) DoltHub entities: ended and not a rename duplicate; live without usable Yahoo data;
    #     and the pre-break part of taken-over tickers
    cols = ["o", "h", "l", "c", "v", "c_raw", "div", "split_ratio"]
    arr = {c: D[c].to_numpy() for c in cols}
    pre_map = {eid: brk for _, eid, brk in prebreak}
    y_ok_set = set(y_ok)
    n_live_no_yahoo = 0
    for row in ent.itertuples(index=False):
        ix = didx[row.eid]
        dts = pd.DatetimeIndex(dates_all[ix])
        if row.ended:
            if row.eid in dup_of:
                continue
            sel = np.ones(len(ix), dtype=bool)
            tag, ended_flag = "", True
        elif row.symbol in y_ok_set:
            if row.eid not in pre_map:
                continue
            sel = np.asarray(dts < pre_map[row.eid])
            tag, ended_flag = "~pre", True
        else:
            sel = np.ones(len(ix), dtype=bool)
            tag, ended_flag = "", False
            n_live_no_yahoo += 1
        if sel.sum() < 2:
            continue
        mid = f"D:{row.entity}{tag}"
        ii = ix[sel]
        frames.append(pd.DataFrame({"mid": mid, "date": dts[sel], **{c: arr[c][ii] for c in cols}}))
        is_last = bool(row.is_last_entity_of_symbol) and tag == ""
        erows.append({"mid": mid, "symbol": row.symbol, "src": "dolthub", "first": dts[sel][0], "last": dts[sel][-1],
                      "bars": int(sel.sum()), "ended": ended_flag, "suspect": False,
                      "type": row.type if is_last else "prior_use",
                      "name": row.security_name if is_last else ""})
    qa["dolthub_live_entities_without_yahoo"] = n_live_no_yahoo

    M = pd.concat(frames, ignore_index=True)
    E = pd.DataFrame(erows)
    E["mid_code"] = np.arange(len(E), dtype=np.int32)
    M["mid"] = M["mid"].map(dict(zip(E["mid"], E["mid_code"]))).astype(np.int32)
    M = M.sort_values(["mid", "date"]).reset_index(drop=True)

    # bad ticks: a close that jumps more than 50% and comes straight back
    g = M.groupby("mid", sort=False)["c"]
    pc, nc = g.shift(1), g.shift(-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        M["bad"] = ((np.abs(np.log(M["c"] / pc)) > 0.5) & (np.abs(np.log(nc / pc)) < 0.12)).astype("int8")
    hi = M[["o", "h", "c"]].max(axis=1)
    lo = M[["o", "l", "c"]].min(axis=1)
    M["h"], M["l"] = hi, lo
    M.to_parquet(out / "merged_daily.parquet", index=False)
    E.to_parquet(out / "merged_entities.parquet", index=False)

    qa["merged_entities"] = int(len(E))
    qa["merged_rows"] = int(len(M))
    qa["merged_by_source"] = {k: int(v) for k, v in E["src"].value_counts().items()}
    qa["merged_ended_entities"] = int(E["ended"].sum())
    qa["ended_by_last_year"] = {int(k): int(v) for k, v in E[E["ended"]]["last"].dt.year.value_counts().sort_index().items()}
    qa["bad_tick_bars"] = int(M["bad"].sum())
    qa["date_min"], qa["date_max"] = str(M["date"].min().date()), str(M["date"].max().date())
    (out / "merge_qa.json").write_text(json.dumps(qa, indent=1, default=str))
    print(json.dumps(qa, indent=1, default=str))


if __name__ == "__main__":
    main()
