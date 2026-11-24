#!/usr/bin/env python3
"""E21 - Second external review, objections 1 and 2.

PLAN (written before the numbers were computed)
 A  Is the lost effect of mark H a decay, or was it always tied to stressed markets?  The first audit
    found the old mark worked on S&P names only in stressed markets (state known at t: trailing
    21-day volatility of the set's mean return above its past-only expanding median). The reviewer
    asks for the same split on the modern set EM. If H is "conditional on stress" it must reappear
    in the stressed part of 2018-2026; if it is absent there too, it decayed.
    Mark versus strict control exactly as in E11/E18 (shipped: rvol>=2; v3: zV>=2), fzd10,
    month-block bootstrap. For EM the expanding median uses the same source back to 2005 (set EO).
 B  How clustered are unusual-volume flags (zV>=2) by day, which days are they, and would a market
    reference help an alerts-only user?  Breadth = share of the set's stocks flagged on a day.
    Calendar classes: quarterly expiry (third Friday of Mar/Jun/Sep/Dec, or the previous trading
    day when that Friday is a holiday), other monthly expiries, Russell reconstitution (fourth
    Friday of June), MSCI review dates (last trading day of Feb/May/Aug/Nov), other month ends.
    Market references: zV of SPY (real SPY volume, sets up to 2017 only), zV of the set's total
    dollar volume, and the median zV of the set. Filter under test: keep a flag only if
    zV - market zV >= 1.5.
 C  How many flags come with a displacement of the bar (|move| >= 1, 1.5, 2 sigma)?
Descriptive except A. Survivors only, daily bars.

  python3 -I experiments/e21_stress_and_clustering.py [--panel DIR] [--spy FILE]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json
from multiprocessing import Pool

import numpy as np
import pandas as pd

import experiments.e18_relvol_v3_confirmation as e18
from tfs.relvol import RelVolParams, log_level_lagged

DEFAULT_PANEL = e18.DEFAULT_PANEL
DEFAULT_SPY = "/home/user/masaok/kaggle-boris-huge-stock-market-dataset/ETFs/spy.us.txt"
COLS = ["ticker", "date", "month", "eval", "volume", "dvol", "r", "r_mkt", "sig0", "ext", "rvol", "z", "fzd10"]
P = RelVolParams()


def load(name, panel):
    d = pd.read_parquet(pathlib.Path(panel) / f"panel_{name}.parquet", columns=COLS)
    groups = [(g["volume"].to_numpy(dtype=float), g["r"].to_numpy(dtype=float)) for _, g in d.groupby("ticker", sort=False)]
    with Pool(3) as pool:
        res = pool.map(e18.feats, groups, chunksize=16)
    d["zv"] = np.concatenate([x[0] for x in res])
    d["z3"] = np.concatenate([x[1] for x in res])
    return d


def series_zv(x: pd.Series) -> pd.Series:
    mu, s, n = log_level_lagged(x.to_numpy(dtype=float), np.zeros(len(x), dtype=np.int64), P.span_daily, P.scale_span, P.clip, P.min_clip)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where((n >= P.min_obs_daily) & (s > 0), (np.log(x.to_numpy(dtype=float)) - mu) / s, np.nan)
    return pd.Series(z, index=x.index)


def stress_state(mkt: pd.Series):
    vol = mkt.rolling(21).std()
    med = vol.expanding(min_periods=250).median().shift(1)
    return (vol > med).where(med.notna()), vol


def part_a(d, mkt_prior, rng):
    mkt = d.groupby("date")["r_mkt"].first().sort_index()
    if mkt_prior is not None:
        mkt = pd.concat([mkt_prior[mkt_prior.index < mkt.index[0]], mkt])
    stressed, vol = stress_state(mkt)
    e = d[d["eval"]]
    st = e["date"].map(stressed).to_numpy()
    vv = e["date"].map(vol).to_numpy()
    q1, q2 = np.nanquantile(vol.reindex(np.sort(e["date"].unique())).to_numpy(), [1 / 3, 2 / 3])
    ext, z, rvol, zv, z3 = (e[k].to_numpy() for k in ("ext", "z", "rvol", "zv", "z3"))
    with np.errstate(invalid="ignore"):
        S = (ext <= -1.5) & (np.abs(z) <= 0.5) & np.isfinite(rvol)
        T, C = S & (rvol >= 2), S & (rvol < 2)
        S3 = (ext <= -1.5) & (np.abs(z3) <= 0.5) & np.isfinite(zv)
        T3, C3 = S3 & (zv >= 2), S3 & (zv < 2)
    out = {"days_stressed_share": round(float(np.nanmean(stressed.reindex(np.sort(e["date"].unique())).astype(float))), 3)}
    for lab, m in (("all", np.ones(len(e), bool)), ("stressed", st == True), ("calm", st == False),  # noqa: E712
                   ("vol_tercile_low", vv <= q1), ("vol_tercile_mid", (vv > q1) & (vv <= q2)), ("vol_tercile_high", vv > q2)):
        out[lab] = {"shipped": e18.cmp(e, T & m, C & m, "fzd10", rng), "v3": e18.cmp(e, T3 & m, C3 & m, "fzd10", rng)}
    return out, mkt


def calendar_classes(days: pd.DatetimeIndex) -> pd.DataFrame:
    days = pd.DatetimeIndex(np.sort(days.unique()))
    dset = set(days)
    cls = pd.Series("other", index=days)
    nxt_month = pd.Series(days.month, index=days).shift(-1)
    last_of_month = (nxt_month != pd.Series(days.month, index=days)).to_numpy().copy()
    last_of_month[-1] = False
    for i, dd in enumerate(days):
        if last_of_month[i]:
            cls.iloc[i] = "msci_review_month_end" if dd.month in (2, 5, 8, 11) else "other_month_end"
    for y in sorted(set(days.year)):
        for mth in range(1, 13):
            fr = [pd.Timestamp(y, mth, k) for k in range(15, 22) if pd.Timestamp(y, mth, k).dayofweek == 4][0]
            dd = fr
            while dd not in dset and dd > fr - pd.Timedelta(days=4):
                dd -= pd.Timedelta(days=1)
            if dd in dset:
                cls[dd] = "quarterly_expiry" if mth % 3 == 0 else "monthly_expiry"
        rr = [pd.Timestamp(y, 6, k) for k in range(22, 29) if pd.Timestamp(y, 6, k).dayofweek == 4][0]
        if rr in dset:
            cls[rr] = "russell_reconstitution"
    return cls


def part_bc(d, spy: pd.Series | None):
    e = d[d["eval"] & d["zv"].notna()].copy()
    e["flag"] = e["zv"] >= 2
    cls = calendar_classes(pd.DatetimeIndex(e["date"]))
    by = e.groupby("date").agg(n=("flag", "size"), flags=("flag", "sum"), med_zv=("zv", "median"))
    by["breadth"] = by["flags"] / by["n"]
    by["cls"] = cls.reindex(by.index)
    tot = d.groupby("date")["dvol"].sum().sort_index()
    by["agg_zv"] = series_zv(tot).reindex(by.index)
    if spy is not None:
        by["spy_zv"] = series_zv(spy).reindex(by.index)
    out = {"days": int(len(by)), "flags": int(by["flags"].sum()), "flag_rate": round(float(by["flags"].sum() / by["n"].sum()), 4)}
    out["by_calendar_class"] = {k: {"days": int(len(g)), "mean_breadth": round(float(g["breadth"].mean()), 4),
                                    "share_of_all_flags": round(float(g["flags"].sum() / by["flags"].sum()), 4)}
                                for k, g in by.groupby("cls")}
    plain = by[by["cls"] != "quarterly_expiry"]
    srt = plain.sort_values("breadth", ascending=False)
    conc = {}
    for q in (0.01, 0.05, 0.10, 0.20):
        k = max(1, int(round(q * len(srt))))
        conc[f"top_{int(q * 100)}pct_days"] = {"share_of_flags": round(float(srt["flags"].iloc[:k].sum() / srt["flags"].sum()), 4),
                                               "min_breadth": round(float(srt["breadth"].iloc[k - 1]), 4)}
    out["concentration_excl_quarterly_expiry"] = conc
    out["breadth_quantiles"] = {str(q): round(float(plain["breadth"].quantile(q)), 4) for q in (0.5, 0.9, 0.95, 0.99, 1.0)}
    out["top_days"] = [{"date": str(i)[:10], "breadth": round(float(r_["breadth"]), 3), "class": r_["cls"],
                        "agg_zv": None if not np.isfinite(r_["agg_zv"]) else round(float(r_["agg_zv"]), 2)}
                       for i, r_ in srt.head(25).iterrows()]
    refs = ["agg_zv", "med_zv"] + (["spy_zv"] if spy is not None else [])
    out["market_reference"] = {}
    e = e[e["date"].map(by["cls"]) != "quarterly_expiry"]
    top5 = set(srt.index[: max(1, int(round(0.05 * len(srt))))])
    on_top = e["date"].isin(top5).to_numpy()
    fl = e["flag"].to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        idio = np.abs((e["r"] - e["r_mkt"]) / e["sig0"]).to_numpy() >= 2
    for ref in refs:
        m = e["date"].map(by[ref]).to_numpy()
        ok = np.isfinite(m)
        sp = plain[ref]
        res = {"rank_corr_with_breadth": round(float(plain[[ref, "breadth"]].corr(method="spearman").iloc[0, 1]), 3),
               "days_ref_ge2_share": round(float((sp >= 2).mean()), 4),
               "flags_on_days_ref_ge2_share": round(float((fl & ok & (m >= 2)).sum() / (fl & ok).sum()), 4),
               "top5pct_days_with_ref_ge2_share": round(float((plain.loc[list(top5), ref] >= 2).mean()), 3),
               "top5pct_days_with_ref_ge1_share": round(float((plain.loc[list(top5), ref] >= 1).mean()), 3)}
        keep = fl & ok & ((e["zv"].to_numpy() - m) >= 1.5)
        res["filter_excess_1p5"] = {
            "flags_kept_share": round(float(keep.sum() / (fl & ok).sum()), 4),
            "flags_kept_on_top5pct_days_share": round(float((keep & on_top).sum() / max(1, (fl & ok & on_top).sum())), 4),
            "flags_kept_on_other_days_share": round(float((keep & ~on_top).sum() / max(1, (fl & ok & ~on_top).sum())), 4),
            "idiosyncratic_jump_flags_kept_share": round(float((keep & idio).sum() / max(1, (fl & ok & idio).sum())), 4)}
        out["market_reference"][ref] = res
    out["share_of_flags_on_top5pct_days"] = round(float((fl & on_top).sum() / fl.sum()), 4)
    with np.errstate(invalid="ignore"):
        az = np.abs(e["z3"].to_numpy())
        out["displacement"] = {f"share_of_flags_with_move_ge_{k}": round(float((fl & (az >= k)).sum() / (fl & np.isfinite(az)).sum()), 4)
                               for k in (1.0, 1.5, 2.0)}
        out["displacement"]["flags_per_day_per_100_stocks"] = round(float(100 * fl.sum() / len(e)), 2)
        out["displacement"]["idiosyncratic_jump_share_of_flags"] = round(float((fl & idio).sum() / fl.sum()), 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=DEFAULT_PANEL)
    ap.add_argument("--spy", default=DEFAULT_SPY)
    a = ap.parse_args()
    spy = None
    if pathlib.Path(a.spy).exists():
        s = pd.read_csv(a.spy, parse_dates=["Date"]).set_index("Date")["Volume"].astype(float)
        spy = s[s > 0]
    res = {"A_stress": {}, "B_C_clustering": {}}
    rng = np.random.default_rng(21)
    eo_mkt = None
    for name in ("LH", "MS", "EO", "EM"):
        d = load(name, a.panel)
        res["A_stress"][name], mkt = part_a(d, eo_mkt if name == "EM" else None, rng)
        if name == "EO":
            eo_mkt = mkt
        if name in ("MS", "EM"):
            res["B_C_clustering"][name] = part_bc(d, spy if name == "MS" else None)
        x = res["A_stress"][name]
        print(name, "stressed days", x["days_stressed_share"])
        for lab in ("all", "stressed", "calm", "vol_tercile_low", "vol_tercile_mid", "vol_tercile_high"):
            s_, v_ = x[lab]["shipped"], x[lab]["v3"]
            print(f"  {lab:17s} shipped n={s_['n']:5d} {s_['diff']} [{s_['lo']}, {s_['hi']}]   v3 n={v_['n']:5d} {v_['diff']} [{v_['lo']}, {v_['hi']}]")
        del d
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e21_stress_and_clustering.json"
    p.write_text(json.dumps(res, indent=1))
    for name, x in res["B_C_clustering"].items():
        print(name, json.dumps({k: v for k, v in x.items() if k != "top_days"}, indent=1))
        print([(t["date"], t["breadth"], t["class"], t["agg_zv"]) for t in x["top_days"]])


if __name__ == "__main__":
    main()
