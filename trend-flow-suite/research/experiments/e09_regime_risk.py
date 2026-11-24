#!/usr/bin/env python3
"""E09 - H1 (pre-registered in docs/04, section 5): does a trend filter improve the risk profile of
holding single stocks?

Rules (position decided at the close, held over the next bar, 5 bp per switch, cash earns 0):
  hold               buy and hold
  ctx_not_down       long unless the weekly context regime is down
  ctx_up             long only while the weekly context regime is up
  chart_not_down     long unless the daily regime is down
  market_not_down    long unless the benchmark's daily regime is down
  sma200             long while close > 200-day SMA (classic comparator)
Reported per stock (share of stocks improved, medians) and for an equal-weight portfolio.
  python3 -I experiments/e09_regime_risk.py --sp5 DIR --dj DIR --lh DIR/Stocks
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

from tfs.data import load_bundled, load_ohlcv_dir
from tfs.trend import regime, trend_score, weekly_context_dir

WARM, COST = 400, 5e-4
RULES = ("hold", "ctx_not_down", "ctx_up", "chart_not_down", "market_not_down", "sma200")
_BENCH = None


def one(item):
    tkr, df = item
    c = df["close"].to_numpy()
    r = np.r_[0.0, c[1:] / c[:-1] - 1.0]
    ctx = weekly_context_dir(df)
    d = regime(trend_score(np.log(c)), 1.0, 0.3)
    b = _BENCH.reindex(df.index).ffill().bfill().to_numpy()
    md = regime(trend_score(np.log(b)), 1.0, 0.3)
    sma = pd.Series(c).rolling(200).mean().to_numpy()
    pos = {"hold": np.ones(len(c)), "ctx_not_down": (ctx >= 0).astype(float), "ctx_up": (ctx == 1).astype(float),
           "chart_not_down": (d >= 0).astype(float), "market_not_down": (md >= 0).astype(float),
           "sma200": (c > sma).astype(float)}
    out = {}
    for k, p in pos.items():
        held = np.r_[0.0, p[:-1]]
        ret = held * r - np.abs(np.diff(np.r_[0.0, held])) * COST
        out[k] = pd.Series(ret[WARM:], index=df.index[WARM:])
    return tkr, out


def stats(ret: pd.Series) -> dict:
    x = ret.to_numpy()
    eq = np.cumprod(1 + x)
    yrs = len(x) / 252.0
    sd = x.std(ddof=1)
    return {"cagr_pct": round(100 * (eq[-1] ** (1 / yrs) - 1), 2), "vol_pct": round(100 * sd * np.sqrt(252), 1),
            "sharpe": round(float(x.mean() / sd * np.sqrt(252)) if sd > 0 else 0.0, 2),
            "max_dd_pct": round(100 * float((eq / np.maximum.accumulate(eq) - 1).min()), 1),
            "exposure_pct": round(100 * float((x != 0).mean()), 0)}


def run_set(name, stocks, periods):
    with Pool(4) as pool:
        res = pool.map(one, sorted(stocks.items()), chunksize=8)
    R = {"stocks": len(res)}
    per = {k: pd.DataFrame({t: stats(o[k]) for t, o in res}).T for k in RULES}
    R["per_stock"] = {}
    for k in RULES[1:]:
        R["per_stock"][k] = {
            "pct_stocks_higher_sharpe": round(100 * float((per[k]["sharpe"] > per["hold"]["sharpe"]).mean()), 1),
            "pct_stocks_smaller_max_dd": round(100 * float((per[k]["max_dd_pct"] > per["hold"]["max_dd_pct"]).mean()), 1),
            "median_sharpe": round(float(per[k]["sharpe"].median()), 2),
            "median_max_dd_pct": round(float(per[k]["max_dd_pct"].median()), 1),
            "median_cagr_pct": round(float(per[k]["cagr_pct"].median()), 2)}
    R["per_stock"]["hold"] = {"median_sharpe": round(float(per["hold"]["sharpe"].median()), 2),
                              "median_max_dd_pct": round(float(per["hold"]["max_dd_pct"].median()), 1),
                              "median_cagr_pct": round(float(per["hold"]["cagr_pct"].median()), 2)}
    port = {k: pd.DataFrame({t: o[k] for t, o in res}).mean(axis=1).dropna() for k in RULES}
    R["equal_weight_portfolio"] = {k: stats(v) for k, v in port.items()}
    R["portfolio_by_period"] = {}
    for lab, (a, b) in periods.items():
        R["portfolio_by_period"][lab] = {k: stats(v.loc[a:b]) for k, v in port.items() if len(v.loc[a:b]) > 200}
    print(f"\n################ {name}: {R['stocks']} stocks")
    print(pd.DataFrame(R["per_stock"]).T.to_string())
    print(pd.DataFrame(R["equal_weight_portfolio"]).T.to_string())
    for lab, v in R["portfolio_by_period"].items():
        print(f"  {lab}: " + " | ".join(f"{k} S={s['sharpe']} DD={s['max_dd_pct']}" for k, s in v.items()))
    return R


def main():
    global _BENCH
    ap = argparse.ArgumentParser()
    ap.add_argument("--sp5", required=True)
    ap.add_argument("--dj", required=True)
    ap.add_argument("--lh", required=True)
    a = ap.parse_args()
    _BENCH = load_bundled("SPX")["close"]
    sp5, _ = load_ohlcv_dir(a.sp5, "*_data.csv", min_bars=700)
    dj, _ = load_ohlcv_dir(a.dj, "*_2006-01-01_to_2018-01-01.csv", min_bars=700, end="2013-02-07")
    names = {t.replace(".", "-") for t in sp5}
    lh, _ = load_ohlcv_dir(a.lh, "*.us.txt", min_bars=700, start="1999-01-02", end="2013-02-07", tickers=names)
    out = {"LH_1999_2013": run_set("LH 1999-2013", lh, {"2000-2003": ("2000-08-01", "2003-12-31"), "2004-2007": ("2004-01-01", "2007-12-31"),
                                                         "2008-2009": ("2008-01-01", "2009-12-31"), "2010-2013": ("2010-01-01", "2013-02-07")}),
           "SP5_2013_2018": run_set("SP5 2013-2018", sp5, {"2014-2015": ("2014-09-01", "2015-12-31"), "2016-2018": ("2016-01-01", "2018-02-07")}),
           "DJ_2006_2013": run_set("DJ 2006-2013", dj, {"2007-2009": ("2007-08-01", "2009-12-31"), "2010-2013": ("2010-01-01", "2013-02-07")})}
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e09_regime_risk.json"
    p.write_text(json.dumps(out, indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main()
