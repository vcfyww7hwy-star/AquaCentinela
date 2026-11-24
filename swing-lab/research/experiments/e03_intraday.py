"""E03 - What one-hour bars can tell us without touching a P&L question (protocol section 2.3).

Data: Yahoo 1-hour bars, regular session, survivors that were liquid at the end of 2022,
12 Dec 2023 .. 31 Dec 2024 ONLY (the later part of the download is sealed with the lockbox).
Seven bars per day: 09:30, 10:30, ..., 14:30 (60 minutes each) and 15:30 (30 minutes).

  A  Time-of-day volume profile: share of the day's volume in each bar, for a relative-volume
     normaliser on 1h charts.
  B  Deciding before the close: how often does a daily-bar state computed at 15:30 (the close of
     the 14:30 bar) agree with the same state computed at the 16:00 close? If agreement is high,
     an alert on the 1h chart at 15:30 can stand in for the daily close and leave 20 minutes to
     place a market-on-close order.
  C  Does realised variance from 1h bars (plus the overnight gap) forecast the next days'
     volatility better than daily closes alone?  (QLIKE; well-posed, no P&L.)
  D  Where in the day the day's range is made (share of days whose high or low falls in each bar):
     relevant to stop placement on entry days.

Limits: one year, survivors only, a single market phase. Everything here is "suggestive" at best.
Family "E03_intraday".
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.swinglab.registry import log_trial

SRC = "/home/user/data/yahoo_1h/1h_*.parquet"
START, END = pd.Timestamp("2023-12-12"), pd.Timestamp("2024-12-31 23:59")
BARS = ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]


def load() -> pd.DataFrame:
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(SRC))], ignore_index=True)
    d = d[(d["date"] >= START) & (d["date"] <= END)]
    d["day"] = d["date"].dt.normalize()
    d["hm"] = d["date"].dt.strftime("%H:%M")
    d = d[d["hm"].isin(BARS)]
    # keep full days only (7 bars), which also drops half-days
    n = d.groupby(["symbol", "day"])["hm"].transform("size")
    return d[n == 7].sort_values(["symbol", "date"]).reset_index(drop=True)


def main() -> None:
    res: dict = {}
    d = load()
    res["rows"], res["symbols"], res["days"] = int(len(d)), int(d["symbol"].nunique()), int(d["day"].nunique())
    print(f"1h bars: {len(d):,} rows, {res['symbols']} symbols, {res['days']} full days, {d['day'].min().date()}..{d['day'].max().date()}")

    # ---------------------------------------------------------------- A volume profile
    day_vol = d.groupby(["symbol", "day"])["volume"].transform("sum")
    d["vshare"] = d["volume"] / day_vol.replace(0, np.nan)
    prof = d.groupby("hm")["vshare"].agg(["median", "mean", lambda x: x.quantile(0.1), lambda x: x.quantile(0.9)])
    prof.columns = ["median", "mean", "p10", "p90"]
    res["A_volume_profile"] = prof.round(4).to_dict("index")
    print("\nA. Share of the day's volume by bar (median across symbol-days; 10th-90th percentile)")
    for hm, r in prof.iterrows():
        print(f"   {hm}  {100 * r['median']:5.1f}%   ({100 * r['p10']:.1f}-{100 * r['p90']:.1f}%)")
        log_trial("E03", "E03_intraday", f"A volume share bar {hm}", "INTRADAY_DEV", "median_share", float(r["median"]))
    cum = prof["median"].cumsum() / prof["median"].sum()
    res["A_cumulative_by_bar_end"] = cum.round(3).to_dict()

    # ---------------------------------------------------------------- daily frame with the 15:30 price
    g = d.groupby(["symbol", "day"])
    daily = g.agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"), v=("volume", "sum"))
    p1530 = d[d["hm"] == "14:30"].set_index(["symbol", "day"])["close"].rename("c1530")     # close of the 14:30-15:30 bar
    upto = d[d["hm"] != "15:30"].groupby(["symbol", "day"]).agg(h1530=("high", "max"), l1530=("low", "min"), v1530=("volume", "sum"))
    daily = daily.join(p1530).join(upto).reset_index().sort_values(["symbol", "day"])
    gs = daily.groupby("symbol")
    daily["pc"] = gs["c"].shift(1)
    daily["r"] = np.log(daily["c"] / daily["pc"])
    daily["r1530"] = np.log(daily["c1530"] / daily["pc"])
    # volatility known before today: EWMA(20) of squared daily log returns, shifted one day
    daily["vol"] = gs["r"].transform(lambda x: np.sqrt((x ** 2).ewm(span=20, min_periods=20).mean()).shift(1))

    # ---------------------------------------------------------------- B agreement at 15:30
    print("\nB. Daily state decided at 15:30 versus at the 16:00 close (precision = 15:30 alarms that were still true at the close; recall = close signals already visible at 15:30)")
    c5 = gs["c"].shift(5)
    sma20_prev = gs["c"].transform(lambda x: x.rolling(19).sum().shift(1))        # sum of the previous 19 closes
    hi20_prev = gs["c"].transform(lambda x: x.rolling(20).max().shift(1))
    sma50_prev = gs["c"].transform(lambda x: x.rolling(49).sum().shift(1))
    vol5 = daily["vol"] * np.sqrt(5)
    states = {
        "z1 <= -3 (crash day)": (daily["r"] / daily["vol"] <= -3, daily["r1530"] / daily["vol"] <= -3),
        "z1 >= +3 (surge day)": (daily["r"] / daily["vol"] >= 3, daily["r1530"] / daily["vol"] >= 3),
        "z5 <= -1.5 (5-day dip)": (np.log(daily["c"] / c5) / vol5 <= -1.5, np.log(daily["c1530"] / c5) / vol5 <= -1.5),
        "close above 20-day average": (daily["c"] > (sma20_prev + daily["c"]) / 20, daily["c1530"] > (sma20_prev + daily["c1530"]) / 20),
        "cross above 50-day average today": ((daily["c"] > (sma50_prev + daily["c"]) / 50) & (daily["pc"] <= gs["c"].transform(lambda x: x.rolling(50).mean().shift(1))),
                                             (daily["c1530"] > (sma50_prev + daily["c1530"]) / 50) & (daily["pc"] <= gs["c"].transform(lambda x: x.rolling(50).mean().shift(1)))),
        "new 20-day closing high": (daily["c"] > hi20_prev, daily["c1530"] > hi20_prev),
    }
    res["B_agreement"] = {}
    for name, (at_close, at_1530) in states.items():
        ok = at_close.notna() & at_1530.notna() & daily["vol"].notna()
        a, b = at_close[ok].astype(bool), at_1530[ok].astype(bool)
        tp = int((a & b).sum())
        prec = tp / max(int(b.sum()), 1)
        rec = tp / max(int(a.sum()), 1)
        res["B_agreement"][name] = {"signals_at_close": int(a.sum()), "signals_at_1530": int(b.sum()),
                                    "precision": round(prec, 3), "recall": round(rec, 3)}
        print(f"   {name:<34s} at close {int(a.sum()):>7d}   at 15:30 {int(b.sum()):>7d}   precision {prec:.1%}   recall {rec:.1%}")
        log_trial("E03", "E03_intraday", f"B agreement {name}", "INTRADAY_DEV", "precision", prec, note=f"recall {rec:.3f}", n=int(a.sum()))
    move = (daily["r"] - daily["r1530"]).abs() / daily["vol"]
    res["B_last_half_hour_move_in_sigma"] = {q: round(float(move.quantile(q)), 3) for q in (0.5, 0.9, 0.99)}
    print(f"   size of the last half hour: |move| / daily sigma  median {move.quantile(0.5):.2f}, 90th pct {move.quantile(0.9):.2f}, 99th pct {move.quantile(0.99):.2f}")

    # ---------------------------------------------------------------- C realised variance forecast
    print("\nC. Forecasting the next 5 days' volatility (QLIKE, lower is better)")
    d["lr"] = np.log(d["close"] / d["open"])
    d["first"] = d["hm"] == "09:30"
    prev_close = d.groupby("symbol")["close"].shift(1)
    d["lr_bar"] = np.where(d["first"], np.log(d["open"] / prev_close), 0.0) ** 2 + d["lr"] ** 2     # overnight^2 + bar^2
    rv = d.groupby(["symbol", "day"])["lr_bar"].sum().rename("rv").reset_index()
    daily = daily.merge(rv, on=["symbol", "day"], how="left")
    gs = daily.groupby("symbol")
    r2 = daily["r"] ** 2
    target = gs["r"].transform(lambda x: (x ** 2).rolling(5).mean().shift(-5))              # next 5 days, close-to-close
    f = {
        "EWMA(20) of squared daily returns": gs["r"].transform(lambda x: (x ** 2).ewm(span=20, min_periods=20).mean()),
        "EWMA(20) of 1h realised variance": gs["rv"].transform(lambda x: x.ewm(span=20, min_periods=20).mean()),
        "HAR-style mean of 1/5/22-day realised variance": (daily["rv"] + gs["rv"].transform(lambda x: x.rolling(5).mean()) + gs["rv"].transform(lambda x: x.rolling(22).mean())) / 3,
        "HAR-style mean of 1/5/22-day squared daily returns": (r2 + gs["r"].transform(lambda x: (x ** 2).rolling(5).mean()) + gs["r"].transform(lambda x: (x ** 2).rolling(22).mean())) / 3,
    }
    res["C_qlike"] = {}
    okc = target.notna() & (target > 0)
    for k_, v_ in f.items():
        okc &= v_.notna() & (v_ > 0)
    for name, fc in f.items():
        x = target[okc] / fc[okc]
        q = float((x - np.log(x) - 1).mean())
        bias = float(x.median())
        res["C_qlike"][name] = {"qlike": round(q, 4), "median_ratio": round(bias, 3), "n": int(okc.sum())}
        print(f"   {name:<52s} QLIKE {q:.4f}   median(target/forecast) {bias:.2f}")
        log_trial("E03", "E03_intraday", f"C qlike {name}", "INTRADAY_DEV", "qlike", q, n=int(okc.sum()))

    # ---------------------------------------------------------------- D when the day's extremes are made
    print("\nD. Share of days whose high / low is made in each bar")
    idx_hi = d.loc[d.groupby(["symbol", "day"])["high"].idxmax(), "hm"].value_counts(normalize=True).reindex(BARS)
    idx_lo = d.loc[d.groupby(["symbol", "day"])["low"].idxmin(), "hm"].value_counts(normalize=True).reindex(BARS)
    res["D_extremes"] = {"high": idx_hi.round(3).to_dict(), "low": idx_lo.round(3).to_dict()}
    for hm in BARS:
        print(f"   {hm}  high {idx_hi[hm]:.1%}   low {idx_lo[hm]:.1%}")
    out = Path(__file__).resolve().parents[1] / "results" / "e03_intraday.json"
    out.write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
