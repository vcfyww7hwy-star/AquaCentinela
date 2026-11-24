#!/usr/bin/env python3
"""E26 - The intraday behaviour of the pane on a longer real sample (second external review,
objection 6; weakness "49 sessions" of the author's own report).

Data: the cleaned intraday sample of experiments/intraday_common.py (5-minute bars from public
1-minute Yahoo bars, 29 Aug 2025 - 5 Oct 2026, corrupted ticker-days removed) and the daily file of
the same stocks. One source, about one year: a first proper reading, still not several years.

PLAN (written before the numbers were computed)
 Q1  Flag rate of zV >= 2 and zV >= 3 on 60-minute bars and on 4-hour bars (09:30-13:30 and
     13:30-16:00) once a slot has at least 100 earlier sessions, by slot and by calendar quarter.
     Design rate on daily bars: about 4% and 1%.
 Q2  Centring: median relative volume by slot over the whole sample.
 Q3  Session pace: on how many stock-days does it reach 2x, at which bar, and how often does such a
     day end at 2x or more on the daily chart (relative volume of the official daily bar)?
 Q4  Half days (13:00 close): what the bars look like and what the pane shows.
 Q5  Expiry and index-rebalance days: share of 60-minute bars at zV >= 2 by slot, and the intraday
     sum over the daily volume, against ordinary days.
 Q6  Pine Screener (last 500 bars only): zV of the last session computed from the last 500
     60-minute bars against the full history; the same for daily bars.

  python3 -I experiments/e26_intraday_long_sample.py --bars DIR --daily FILE.parquet [--half-bars DIR]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import glob
import json

import numpy as np
import pandas as pd

from experiments.intraday_common import load_clean
from tfs.relvol import RelVolParams, log_level_lagged, mechanical_day, relative_volume

P = RelVolParams()
MATURE = 100


def rate(z):
    z = z[np.isfinite(z)]
    return {"n": int(len(z)), "ge2_pct": round(100 * float((z >= 2).mean()), 2), "ge3_pct": round(100 * float((z >= 3).mean()), 2)} if len(z) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", required=True)
    ap.add_argument("--daily", required=True)
    ap.add_argument("--half-bars", default=None, help="5-minute bars of the half days (the main harvest keeps full sessions only)")
    a = ap.parse_args()
    b, dly_all, clean = load_clean(a.bars, a.daily)
    if a.half_bars:
        hb = pd.concat([pd.read_parquet(f, columns=["ticker", "ts", "open", "high", "low", "close", "volume"])
                        for f in sorted(glob.glob(str(pathlib.Path(a.half_bars) / "bars5m_*.parquet")))], ignore_index=True)
        hb["ticker"] = hb["ticker"].astype(str)
        hb["day"] = hb["ts"].dt.normalize()
        hb["mins"] = (hb["ts"].dt.hour * 60 + hb["ts"].dt.minute) - 570
        hb = hb[(hb["mins"] >= 0) & (hb["mins"] < 390) & ~hb["day"].isin(b["day"].unique()) & hb["ticker"].isin(set(b["ticker"].unique()))]
        b = pd.concat([b, hb.drop_duplicates(["ticker", "ts"])], ignore_index=True)
    days = np.sort(b["day"].unique())
    out = {"sessions": int(len(days)), "first": str(days[0])[:10], "last": str(days[-1])[:10], "cleaning": clean}
    # half days: sessions whose latest bar starts before 13:00 for nearly every stock
    last_bar = b.groupby("day")["mins"].quantile(0.99)
    half_days = [d for d, m in last_bar.items() if m < 215]
    out["half_days"] = [str(d)[:10] for d in half_days]

    g = b.groupby(["ticker", "day"]).agg(n=("volume", "size"), vol=("volume", "sum"), px=("close", "last"))
    g["dv"] = g["vol"] * g["px"]
    t = g.groupby("ticker").agg(days=("n", "size"), full=("n", lambda x: (x >= 70).mean()), px=("px", "median"), dv=("dv", "median"))
    keep = t[(t["days"] >= 0.75 * len(days)) & (t["full"] >= 0.9) & (t["px"] >= 5) & (t["dv"] >= 5e6)].index
    b = b[b["ticker"].isin(keep)].copy()
    out["universe"] = int(len(keep))

    dly = dly_all[dly_all["ticker"].isin(set(keep))].rename(columns={"day": "date", "dvol": "volume"}).sort_values(["ticker", "date"]).reset_index(drop=True)
    zd, nd_, zd500 = [], [], []
    for _, d in dly.groupby("ticker", sort=False):
        v = d["volume"].to_numpy(dtype=float)
        k = np.zeros(len(v), dtype=np.int64)
        mu, s, n = log_level_lagged(v, k, P.span_daily, P.scale_span, P.clip, P.min_clip)
        with np.errstate(divide="ignore", invalid="ignore"):
            zd.append(np.where((n >= P.min_obs_daily) & (s > 0) & (v > 0), (np.log(np.where(v > 0, v, 1.0)) - mu) / s, np.nan))
            nd_.append(np.where(n >= P.min_obs_daily, v / np.exp(mu), np.nan))
        # Pine Screener on daily bars: only the last 500 bars
        z5 = np.full(len(v), np.nan)
        if len(v) > 600:
            m5, s5, n5 = log_level_lagged(v[-500:], k[-500:], P.span_daily, P.scale_span, P.clip, P.min_clip)
            with np.errstate(divide="ignore", invalid="ignore"):
                z5[-500:] = np.where((n5 >= P.min_obs_daily) & (s5 > 0) & (v[-500:] > 0), (np.log(np.where(v[-500:] > 0, v[-500:], 1.0)) - m5) / s5, np.nan)
        zd500.append(z5)
    dly["zv_d"], dly["rvol_d"], dly["zv_d500"] = np.concatenate(zd), np.concatenate(nd_), np.concatenate(zd500)
    last20 = dly.groupby("ticker", sort=False).tail(20)
    k = np.isfinite(last20["zv_d"]) & np.isfinite(last20["zv_d500"])
    out["Q6_screener_daily_500_bars"] = {
        "n": int(k.sum()), "median_abs_diff_zv": round(float((last20["zv_d"] - last20["zv_d500"]).abs()[k].median()), 4),
        "p95_abs_diff_zv": round(float((last20["zv_d"] - last20["zv_d500"]).abs()[k].quantile(0.95)), 4),
        "flag_agreement_pct": round(100 * float(((last20["zv_d"] >= 2) == (last20["zv_d500"] >= 2))[k].mean()), 2)}
    dly = dly[dly["date"].isin(days)].rename(columns={"date": "day", "volume": "dvol"})

    def bars(width, name):
        b["slot"] = b["mins"] // width
        h = b.groupby(["ticker", "day", "slot"]).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                                                     close=("close", "last"), volume=("volume", "sum"),
                                                     first=("mins", "min"), last=("mins", "max")).reset_index()
        h["len"] = np.minimum(width, 390 - h["slot"] * width)
        hd = h["day"].isin(half_days)
        h.loc[hd, "len"] = np.minimum(h.loc[hd, "len"], np.maximum(5, 210 - h.loc[hd, "slot"] * width))
        parts = []
        for tk, d in h.groupby("ticker", sort=False):
            d = d.sort_values(["day", "slot"])
            idx = pd.DatetimeIndex(d["day"] + pd.to_timedelta(570 + width * d["slot"], unit="m"))
            f = relative_volume(d[["open", "high", "low", "close", "volume"]].set_axis(idx), intraday=True, p=P, bar_minutes=d["len"].to_numpy())
            x = d[["ticker", "day", "slot", "len", "volume"]].copy()
            for c in ("rvol", "zv", "n", "pace", "pace_z"):
                x[c] = f[c].to_numpy()
            if name == "60m":                                          # Pine Screener: last 500 bars only
                z5 = np.full(len(d), np.nan)
                if len(d) > 600:
                    f5 = relative_volume(d[["open", "high", "low", "close", "volume"]].set_axis(idx).iloc[-500:], intraday=True, p=P,
                                         bar_minutes=d["len"].to_numpy()[-500:])
                    z5[-500:] = f5["zv"].to_numpy()
                x["zv500"] = z5
            parts.append(x)
        return pd.concat(parts, ignore_index=True)

    res = {}
    for width, name in ((60, "60m"), (240, "4h")):
        q = bars(width, name)
        q["mech"] = mechanical_day(pd.DatetimeIndex(q["day"]))
        q["half"] = q["day"].isin(half_days)
        full_len = np.minimum(width, 390 - q["slot"] * width)
        reg = q[(q["len"] == full_len) & ~q["half"]]
        mat = reg[(reg["n"] >= MATURE) & ~reg["mech"]]
        r = {"bars": int(len(q)), "Q1_mature_all": rate(mat["zv"].to_numpy()),
             "Q1_mature_by_slot": {int(s): rate(x["zv"].to_numpy()) for s, x in mat.groupby("slot")},
             "Q1_mature_by_quarter": {str(k): rate(x["zv"].to_numpy()) for k, x in mat.groupby(pd.PeriodIndex(mat["day"], freq="Q"))},
             "Q1_by_earlier_sessions": {lab: rate(reg.loc[(reg["n"] >= lo) & (reg["n"] <= hi) & ~reg["mech"], "zv"].to_numpy())
                                        for lab, lo, hi in (("10-19", 10, 19), ("20-49", 20, 49), ("50-99", 50, 99), ("100+", 100, 10 ** 6))},
             "Q2_median_rvol_by_slot": {int(s): round(float(x["rvol"].median()), 3) for s, x in reg[reg["n"] >= 20].groupby("slot")},
             "Q5_mechanical_days": {"days": sorted({str(d)[:10] for d in reg.loc[reg["mech"], "day"].unique()}),
                                    "ge2_pct_by_slot": {int(s): round(100 * float((x["zv"] >= 2).mean()), 1) for s, x in reg[reg["mech"] & reg["zv"].notna()].groupby("slot")},
                                    "ge2_pct_by_slot_other_days": {int(s): round(100 * float((x["zv"] >= 2).mean()), 1) for s, x in reg[~reg["mech"] & reg["zv"].notna()].groupby("slot")}}}
        hq = q[q["half"]]
        r["Q4_half_days"] = {"bars_by_slot_and_length": {f"slot{int(s)}_len{int(l)}": int(c) for (s, l), c in hq.groupby(["slot", "len"]).size().items()},
                             "median_rvol_by_slot": {int(s): (round(float(x["rvol"].median()), 3) if x["rvol"].notna().any() else None) for s, x in hq.groupby("slot")},
                             "share_of_short_last_bars_still_warming_up_pct": round(100 * float(hq.loc[hq["len"] < np.minimum(width, 390 - hq["slot"] * width), "rvol"].isna().mean()), 1)
                             if (hq["len"] < np.minimum(width, 390 - hq["slot"] * width)).any() else None}
        if name == "60m":
            # Q3 session pace: the alert as a fixed multiple and in units of the pace's own spread
            j = q.merge(dly[["ticker", "day", "rvol_d", "zv_d", "dvol"]], on=["ticker", "day"], how="inner")
            j = j[~j["half"] & ~j["mech"] & np.isfinite(j["pace"]) & np.isfinite(j["pace_z"]) & np.isfinite(j["zv_d"])]
            dayinfo = j.groupby(["ticker", "day"]).agg(rvol_d=("rvol_d", "first"), zv_d=("zv_d", "first"))
            r["Q3_session_pace"] = {"stock_days": int(len(dayinfo)), "daily_bar_unusual_pct": round(100 * float((dayinfo["zv_d"] >= 2).mean()), 2), "rules": {}}
            for lab, hit in (("pace >= 2x", j["pace"] >= 2.0), ("pace z >= 2", j["pace_z"] >= 2.0), ("pace z >= 2.5", j["pace_z"] >= 2.5),
                             ("pace z >= 2 and pace >= 1.5x", (j["pace_z"] >= 2.0) & (j["pace"] >= 1.5))):
                fc = dayinfo.join(j[hit].groupby(["ticker", "day"])["slot"].min().rename("cross"), how="left")
                got = fc["cross"].notna()
                un = fc["zv_d"] >= 2
                r["Q3_session_pace"]["rules"][lab] = {
                    "alerts_per_day_per_100_stocks": round(100 * float(got.mean()), 2),
                    "alert_days_ending_unusual_daily_pct": round(100 * float(un[got].mean()), 1),
                    "alert_days_median_daily_rvol": round(float(fc.loc[got, "rvol_d"].median()), 2),
                    "unusual_daily_bars_announced_pct": round(100 * float(got[un].mean()), 1),
                    "unusual_daily_bars_announced_by_11_30_pct": round(100 * float((fc.loc[un, "cross"] <= 1).mean()), 1),
                    "unusual_daily_bars_announced_by_13_30_pct": round(100 * float((fc.loc[un, "cross"] <= 3).mean()), 1),
                    "first_crossing_by_bar_pct": {int(k): round(100 * float(v), 1) for k, v in fc.loc[got, "cross"].value_counts(normalize=True).sort_index().items()},
                    "ending_unusual_by_bar_of_first_crossing_pct": {int(k): round(100 * float(x.mean()), 1) for k, x in un[got].groupby(fc.loc[got, "cross"])}}
            # Q5 intraday sum over daily volume
            iv = q.groupby(["ticker", "day"])["volume"].sum().rename("iv").reset_index().merge(dly[["ticker", "day", "dvol"]], on=["ticker", "day"])
            iv = iv[(iv["dvol"] > 0) & (iv["iv"] > 0)]
            iv["ratio"] = iv["iv"] / iv["dvol"]
            byd = iv.groupby("day")["ratio"].median()
            md = mechanical_day(pd.DatetimeIndex(byd.index))
            r["Q5_intraday_sum_over_daily"] = {"ordinary_days_median": round(float(byd[~md].median()), 3),
                                               "ordinary_days_p05_p95": [round(float(byd[~md].quantile(x)), 3) for x in (0.05, 0.95)],
                                               "mechanical_days": {str(d)[:10]: round(float(v), 3) for d, v in byd[md].items()},
                                               "share_of_stock_days_below_0.3_pct": round(100 * float((iv["ratio"] < 0.3).mean()), 2),
                                               "share_of_stock_days_below_0.5_pct": round(100 * float((iv["ratio"] < 0.5).mean()), 2)}
            # Q6 Pine Screener, 60-minute bars: the last session, 500 bars against the full history
            lastd = q[q["day"] == days[-1]]
            kk = np.isfinite(lastd["zv"]) & np.isfinite(lastd["zv500"])
            r["Q6_screener_500_bars"] = {"n": int(kk.sum()), "median_abs_diff_zv": round(float((lastd["zv"] - lastd["zv500"]).abs()[kk].median()), 4),
                                         "p95_abs_diff_zv": round(float((lastd["zv"] - lastd["zv500"]).abs()[kk].quantile(0.95)), 4),
                                         "flag_agreement_pct": round(100 * float(((lastd["zv"] >= 2) == (lastd["zv500"] >= 2))[kk].mean()), 2)}
        res[name] = r
    out.update(res)
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e26_intraday_long_sample.json"
    p.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
