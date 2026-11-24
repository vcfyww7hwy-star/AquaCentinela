#!/usr/bin/env python3
"""E19 - First checks of the pane on REAL intraday data (earlier work had synthetic intraday only).

Data: 5-minute bars built from public 1-minute Yahoo bars (GitHub, MapleFrogStudio DATA-2026-09,
-10, -11): NYSE, NASDAQ and AMEX tickers, regular session, 31 Aug - 6 Nov 2026 (about 48 sessions).
Short history and one source: treat every number as a first reading, not as validation.

Questions
  Q1  Is the intraday volume consolidated (sum of the day against an independent daily file)?
  Q2  How is volume spread over the seven 60-minute bars of the session, and how often is a
      60-minute bar missing in liquid stocks?
  Q3  Does the per-slot reference of tfs.relvol put relative volume near 1 in every slot, where a
      reference that ignores the time of day does not?
  Q4  The live daily bar: how well can the day's final volume be projected from the volume traded
      so far? Compared: no projection (what the shipped pane shows), straight-line projection, a
      generic cumulative curve, the stock's own cumulative curve, and "relative volume at time".
  Q5  The live 60-minute bar: error of a straight-line projection after 15, 30, 45 minutes.

  python3 -I experiments/e19_intraday_real_data.py --bars DIR --daily FILE.parquet
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

from tfs.relvol import RelVolParams, log_level_lagged, relative_volume

CHECKS = [("10:00", 30), ("10:30", 60), ("11:30", 120), ("13:00", 210), ("14:30", 300), ("15:30", 360)]


def spearman(a, b):
    k = np.isfinite(a) & np.isfinite(b)
    if k.sum() < 30:
        return None
    return round(float(pd.Series(a[k]).rank().corr(pd.Series(b[k]).rank())), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", required=True)
    ap.add_argument("--daily", required=True)
    a = ap.parse_args()
    b = pd.concat([pd.read_parquet(f, columns=["ticker", "ts", "open", "high", "low", "close", "volume"])
                   for f in sorted(glob.glob(str(pathlib.Path(a.bars) / "bars5m_*.parquet")))], ignore_index=True)
    b["ticker"] = b["ticker"].astype(str)
    b["day"] = b["ts"].dt.normalize()
    b["mins"] = (b["ts"].dt.hour * 60 + b["ts"].dt.minute) - 570              # minutes after 09:30
    b = b[(b["mins"] >= 0) & (b["mins"] < 390)]
    out = {"source_rows_5m": int(len(b)), "sessions": int(b["day"].nunique()),
           "first": str(b["day"].min())[:10], "last": str(b["day"].max())[:10]}

    # universe: liquid, nearly complete days
    g = b.groupby(["ticker", "day"]).agg(n=("volume", "size"), vol=("volume", "sum"), px=("close", "last"))
    g["dv"] = g["vol"] * g["px"]
    t = g.groupby("ticker").agg(days=("n", "size"), full=("n", lambda x: (x >= 70).mean()), px=("px", "median"), dv=("dv", "median"))
    keep = t[(t["days"] >= 40) & (t["full"] >= 0.9) & (t["px"] >= 5) & (t["dv"] >= 5e6)].index
    b = b[b["ticker"].isin(keep)].copy()
    out["universe"] = {"tickers": int(len(keep)), "median_dollar_volume_musd": round(float(t.loc[keep, "dv"].median() / 1e6), 1)}

    # Q1 consolidated?
    dly = pd.read_parquet(a.daily, columns=["ticker", "date", "volume"])
    dly["ticker"] = dly["ticker"].astype(str)
    dsum = b.groupby(["ticker", "day"])["volume"].sum().rename("iv").reset_index().merge(
        dly.rename(columns={"date": "day", "volume": "dvol"}), on=["ticker", "day"])
    ratio = (dsum["iv"] / dsum["dvol"].replace(0, np.nan)).dropna()
    out["Q1_intraday_sum_over_daily_volume"] = {"n": int(len(ratio)), "p05": round(float(ratio.quantile(.05)), 3),
                                               "median": round(float(ratio.median()), 3), "p95": round(float(ratio.quantile(.95)), 3)}

    # 60-minute bars anchored at 09:30 (the last one is 30 minutes long), and 30-minute cumulative grid
    b["slot60"] = b["mins"] // 60
    h = b.groupby(["ticker", "day", "slot60"]).agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                                                   close=("close", "last"), volume=("volume", "sum")).reset_index()
    days = np.sort(b["day"].unique())
    nd = h.groupby("ticker")["day"].nunique()
    exp_bars = (nd * 7).sum()
    out["Q2_missing_60m_bars_share"] = round(float(1 - len(h) / exp_bars), 5)
    tot = h.groupby(["ticker", "day"])["volume"].transform("sum")
    h["share"] = h["volume"] / tot
    out["Q2_volume_share_by_60m_slot"] = {f"{9 + (30 + 60 * s) // 60:02d}:{(30 + 60 * s) % 60:02d}": round(float(v), 4)
                                         for s, v in h.groupby("slot60")["share"].mean().items()}

    # Q3 per-slot reference versus a reference blind to the time of day
    P = RelVolParams()
    rows = []
    for tkr, d in h.groupby("ticker", sort=False):
        d = d.sort_values(["day", "slot60"])
        idx = pd.DatetimeIndex(d["day"] + pd.to_timedelta(570 + 60 * d["slot60"], unit="m"))
        df = d[["open", "high", "low", "close", "volume"]].set_axis(idx)
        blen = np.where(d["slot60"].to_numpy() == 6, 30, 60)
        f = relative_volume(df, intraday=True, p=P, bar_minutes=blen)
        mu_b, s_b, n_b = log_level_lagged(d["volume"].to_numpy(float), np.zeros(len(d), dtype=np.int64), 140, 140, P.clip, P.min_clip)
        blind = np.where(n_b >= 70, d["volume"].to_numpy(float) / np.exp(mu_b), np.nan)
        rows.append(pd.DataFrame({"slot": d["slot60"].to_numpy(), "rvol": f["rvol"].to_numpy(), "zv": f["zv"].to_numpy(),
                                  "s": f["s"].to_numpy(), "blind": blind}))
    q = pd.concat(rows, ignore_index=True)
    q = q[np.isfinite(q["rvol"])]
    out["Q3_by_slot"] = {int(s): {"n": int(len(x)), "median_rvol_slot": round(float(x["rvol"].median()), 3),
                                  "median_rvol_blind": round(float(x["blind"].median()), 3) if x["blind"].notna().any() else None,
                                  "sd_zv": round(float(x["zv"].std()), 3), "share_zv_ge2": round(float((x["zv"] >= 2).mean()), 4),
                                  "median_s": round(float(x["s"].median()), 3)} for s, x in q.groupby("slot")}
    out["Q3_blind_flags_2x_by_slot"] = {int(s): round(float((x["blind"] >= 2).mean()), 4) for s, x in q.groupby("slot")}

    # Q4 projecting the day's volume from the volume so far
    b["cum"] = b.groupby(["ticker", "day"])["volume"].cumsum()
    piv = {}
    for lab, m in CHECKS:
        piv[lab] = b[b["mins"] < m].groupby(["ticker", "day"])["volume"].sum().unstack("day").reindex(columns=days)
    V = b.groupby(["ticker", "day"])["volume"].sum().unstack("day").reindex(columns=days)
    tick = V.index
    half = len(days) // 2
    test_days = days[half:]
    res4 = {}
    lnV = np.log(V.replace(0, np.nan))
    # the stock's own "normal day" and final daily relative volume, from previous sessions only
    def lagged_mean(df_log, span=20, need=10):
        vals = df_log.to_numpy()
        outm = np.full_like(vals, np.nan)
        a_ = 2.0 / (span + 1)
        for i in range(vals.shape[0]):
            num = den = 0.0
            cnt = 0
            for j in range(vals.shape[1]):
                if cnt >= need:
                    outm[i, j] = num / den
                x = vals[i, j]
                if np.isfinite(x):
                    num = (1 - a_) * num + a_ * x
                    den = (1 - a_) * den + a_
                    cnt += 1
        return pd.DataFrame(outm, index=df_log.index, columns=df_log.columns)
    normV = lagged_mean(lnV)
    final_rvol = (lnV - normV)
    for lab, m in CHECKS:
        C = piv[lab].reindex(tick)
        share = (C / V)
        gen = share[days[:half]].stack().mean()                         # generic curve from the first half of the sessions
        own = np.exp(lagged_mean(np.log(share.replace(0, np.nan))))      # the stock's own average share, previous sessions
        lnC = np.log(C.replace(0, np.nan))
        at_time = lnC - lagged_mean(lnC)                                 # relative volume at time (log)
        sel = (slice(None), test_days)
        def err(pred_ln):
            e = (pred_ln - lnV)[test_days].to_numpy().ravel()
            e = e[np.isfinite(e)]
            return {"bias_pct": round(float((np.exp(np.mean(e)) - 1) * 100), 1), "mae_ln": round(float(np.mean(np.abs(e))), 3)}
        fr = final_rvol[test_days].to_numpy().ravel()
        res4[lab] = {
            "share_of_day_done_generic": round(float(gen), 3),
            "no_projection": err(lnC),
            "straight_line": err(lnC + np.log(390.0 / m)),
            "generic_curve": err(lnC - np.log(gen)),
            "own_curve": err(lnC - np.log(own)),
            "spearman_with_final_rvol": {
                "generic_curve": spearman(((lnC - np.log(gen)) - normV)[test_days].to_numpy().ravel(), fr),
                "own_curve": spearman(((lnC - np.log(own)) - normV)[test_days].to_numpy().ravel(), fr),
                "rvol_at_time": spearman(at_time[test_days].to_numpy().ravel(), fr)},
        }
        # detection of days that end unusual (final relative volume >= 2x) with the generic curve
        proj = np.exp(((lnC - np.log(gen)) - normV)[test_days].to_numpy().ravel())
        fin = np.exp(fr)
        k = np.isfinite(proj) & np.isfinite(fin)
        hit = (fin[k] >= 2)
        res4[lab]["days_ending_2x_detected_share"] = round(float((proj[k][hit] >= 2).mean()), 3) if hit.sum() else None
        res4[lab]["flagged_2x_that_end_2x_share"] = round(float((fin[k][proj[k] >= 2] >= 2).mean()), 3) if (proj[k] >= 2).sum() else None
    out["Q4_daily_projection"] = res4
    out["Q4_note"] = {"test_sessions": int(len(test_days)), "generic_curve_from_sessions": int(half)}

    # Q5 the live 60-minute bar: straight-line projection after 15, 30, 45 minutes
    b["in_bar"] = b["mins"] - 60 * b["slot60"]
    tot60 = b.groupby(["ticker", "day", "slot60"])["volume"].transform("sum")
    res5 = {}
    for el in (15, 30, 45):
        part = b[b["in_bar"] < el].groupby(["ticker", "day", "slot60"])["volume"].sum()
        full = b.groupby(["ticker", "day", "slot60"])["volume"].sum()
        j = pd.concat([part.rename("p"), full.rename("f")], axis=1).dropna().reset_index()
        j = j[(j["slot60"] < 6) & (j["p"] > 0) & (j["f"] > 0)]
        j["e"] = np.log(j["p"] * 60.0 / el / j["f"])
        res5[f"{el}min"] = {int(s): {"bias_pct": round(float((np.exp(x["e"].mean()) - 1) * 100), 1),
                                     "mae_ln": round(float(x["e"].abs().mean()), 3)} for s, x in j.groupby("slot60")}
    out["Q5_60m_bar_straight_line"] = res5

    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e19_intraday_real_data.json"
    p.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
