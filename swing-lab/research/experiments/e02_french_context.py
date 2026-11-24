"""E02 - Long-run, survivorship-free context from the Kenneth French data library.

The library's portfolios are built from CRSP, which includes delisted companies. They cannot test
a chart rule, but they answer, with up to 96 years of data and no survivor bias:

  A  short-term reversal (sorted on last month's return): alive? by era, big versus small stocks
  B  momentum (12-2): alive? by era, big versus small stocks
  C  turn of the month on the market
  D  market trend filter (price above its 200-day average), next-day execution
  E  volatility-managed market exposure (target a constant volatility with a trailing estimate)

Data are cut at 2022-12-30 like every other source until the lockbox opens (protocol section 2.2).
Family "E02_french"; every printed cell is logged.
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from research.swinglab import engine as E
from research.swinglab.registry import log_trial

SRC = Path("/home/user/data/french/x")
CUT = pd.Timestamp("2022-12-30")
ERAS = [("1926-07", "1962-12"), ("1963-01", "1989-12"), ("1990-01", "1999-12"), ("2000-01", "2009-12"),
        ("2010-01", "2022-12")]


def read_french(name: str, section: int = 0) -> pd.DataFrame:
    """Daily file -> DataFrame of percent returns. Sections are separated by blank lines; section 0
    is value-weighted, 1 equal-weighted where present."""
    txt = (SRC / name).read_text(errors="replace")
    blocks, cur = [], []
    for line in txt.splitlines():
        if re.match(r"^\s*\d{8}\s*,", line):
            cur.append(line)
        else:
            if cur:
                blocks.append(cur)
                cur = []
            if "," in line and not re.match(r"^\s*\d", line):
                header = line
                blocks.append(("H", header))
    if cur:
        blocks.append(cur)
    # pair each data block with the header that precedes it
    out, hdr = [], None
    for b in blocks:
        if isinstance(b, tuple):
            hdr = b[1]
        else:
            out.append((hdr, b))
    hdr, rows = out[section]
    cols = ["date"] + [c.strip() for c in hdr.split(",")[1:]]
    d = pd.read_csv(io.StringIO("\n".join(rows)), header=None, names=cols)
    d["date"] = pd.to_datetime(d["date"].astype(str), format="%Y%m%d")
    d = d.set_index("date").apply(pd.to_numeric, errors="coerce")
    d = d.where(d > -99)
    return d[d.index <= CUT]


def ann(x: pd.Series, lags: int = 5) -> tuple[float, float]:
    """Annualised mean (percent) and Newey-West t of a daily percent series."""
    m, t, _ = E.nw_mean(x.to_numpy(), lags)
    return 252 * m, t


def by_era(x: pd.Series, label: str, res: dict) -> None:
    row = {}
    for a, b in ERAS:
        s = x.loc[a:b].dropna()
        if len(s) < 500:
            continue
        m, t = ann(s)
        row[f"{a[:4]}-{b[:4]}"] = (round(m, 1), round(t, 1))
        log_trial("E02", "E02_french", f"{label} {a}..{b}", "FRENCH<=2022", "ann_pct", m, tstat=t, n=len(s))
    res[label] = row
    print(f"{label:<52s}" + "  ".join(f"{k}: {v[0]:+6.1f}% (t {v[1]:+5.1f})" for k, v in row.items()))


def perf(r: pd.Series) -> dict:
    """Daily percent returns -> CAGR, vol, Sharpe (excess of nothing), max drawdown."""
    g = (1 + r / 100).cumprod()
    yrs = len(r) / 252
    return {"cagr": round(100 * (g.iloc[-1] ** (1 / yrs) - 1), 1), "vol": round(r.std() * np.sqrt(252), 1),
            "sharpe": round(r.mean() / r.std() * np.sqrt(252), 2), "maxdd": round(100 * (g / g.cummax() - 1).min(), 0)}


def main() -> None:
    res: dict = {}
    ff = read_french("F-F_Research_Data_Factors_daily.csv")
    mkt = ff["Mkt-RF"] + ff["RF"]
    rf = ff["RF"]

    print("\nA. Short-term reversal: last month's losers minus winners (value-weighted, percent per year)")
    r6 = read_french("6_Portfolios_ME_Prior_1_0_Daily.csv")
    by_era(r6["BIG LoPRIOR"] - r6["BIG HiPRIOR"], "A reversal, BIG stocks (losers - winners)", res)
    by_era(r6["SMALL LoPRIOR"] - r6["SMALL HiPRIOR"], "A reversal, SMALL stocks (losers - winners)", res)
    by_era(r6["BIG LoPRIOR"] - mkt, "A reversal, BIG losers minus market (long side)", res)

    print("\nB. Momentum 12-2: winners minus losers (value-weighted, percent per year)")
    m6 = read_french("6_Portfolios_ME_Prior_12_2_Daily.csv")
    by_era(m6["BIG HiPRIOR"] - m6["BIG LoPRIOR"], "B momentum, BIG stocks (winners - losers)", res)
    by_era(m6["SMALL HiPRIOR"] - m6["SMALL LoPRIOR"], "B momentum, SMALL stocks (winners - losers)", res)
    by_era(m6["BIG HiPRIOR"] - mkt, "B momentum, BIG winners minus market (long side)", res)
    by_era(m6["BIG LoPRIOR"] - mkt, "B momentum, BIG losers minus market (avoid side)", res)
    m10 = read_french("10_Portfolios_Prior_12_2_Daily.csv")
    by_era(m10.iloc[:, -1] - mkt, "B momentum, top decile minus market", res)
    by_era(m10.iloc[:, 0] - mkt, "B momentum, bottom decile minus market", res)

    print("\nC. Turn of the month on the market (last trading day + first three), percent per DAY in bp")
    d = mkt.to_frame("r")
    ym = d.index.to_period("M")
    pos_in_month = d.groupby(ym).cumcount()
    rev_pos = d.groupby(ym).cumcount(ascending=False)
    tom = (pos_in_month <= 2) | (rev_pos == 0)
    row = {}
    for a, b in ERAS:
        s = d.loc[a:b]
        k = tom.loc[a:b]
        x = (s["r"][k].mean() - s["r"][~k].mean()) * 100
        # date-level t: difference of means with unequal variances
        se = np.sqrt(s["r"][k].var() / k.sum() + s["r"][~k].var() / (~k).sum()) * 100
        row[f"{a[:4]}-{b[:4]}"] = (round(s["r"][k].mean() * 100, 1), round(s["r"][~k].mean() * 100, 1), round(x / se, 1))
        log_trial("E02", "E02_french", f"C turn-of-month minus other days {a}..{b}", "FRENCH<=2022", "bp_per_day", x, tstat=x / se, n=int(k.sum()))
    res["C turn of month (bp/day TOM, other, t of difference)"] = row
    print("   " + "  ".join(f"{k}: TOM {v[0]:+5.1f} other {v[1]:+5.1f} (t {v[2]:+4.1f})" for k, v in row.items()))

    print("\nD. Market trend filter: hold the market when its total-return index closed above its 200-day average")
    idx = (1 + mkt / 100).cumprod()
    above = (idx > idx.rolling(200).mean()).shift(2).fillna(False)   # decided at close t, traded at the next close-to-close day after one day's delay
    strat = np.where(above, mkt, rf)
    strat = pd.Series(strat, index=mkt.index) - 0.05 * above.astype(int).diff().abs().fillna(0)   # 5 bp per switch
    row = {}
    for a, b in ERAS + [("1926-07", "2022-12")]:
        p1, p2 = perf(mkt.loc[a:b]), perf(strat.loc[a:b])
        row[f"{a[:4]}-{b[:4]}"] = {"hold": p1, "filter": p2, "time_in": round(float(above.loc[a:b].mean()), 2)}
        log_trial("E02", "E02_french", f"D 200-day filter sharpe {a}..{b}", "FRENCH<=2022", "sharpe", p2["sharpe"], note=f"hold {p1['sharpe']}")
        print(f"   {a[:4]}-{b[:4]}  hold: CAGR {p1['cagr']:5.1f} Sharpe {p1['sharpe']:.2f} maxDD {p1['maxdd']:4.0f}% | filter: CAGR {p2['cagr']:5.1f} Sharpe {p2['sharpe']:.2f} maxDD {p2['maxdd']:4.0f}%  in market {above.loc[a:b].mean():.0%}")
    res["D trend filter"] = row

    print("\nE. Volatility-managed market: weight = min(1.5, 15% / trailing 20-day annualised vol), decided one day earlier")
    vol20 = mkt.rolling(20).std() * np.sqrt(252)
    w = (15.0 / vol20).clip(upper=1.5).shift(2)
    vm = w * (mkt - rf) + rf
    vm = vm - 0.05 * w.diff().abs().fillna(0)
    row = {}
    for a, b in ERAS + [("1926-07", "2022-12")]:
        p1, p2 = perf(mkt.loc[a:b]), perf(vm.loc[a:b].dropna())
        row[f"{a[:4]}-{b[:4]}"] = {"hold": p1, "managed": p2, "avg_weight": round(float(w.loc[a:b].mean()), 2)}
        log_trial("E02", "E02_french", f"E vol-managed sharpe {a}..{b}", "FRENCH<=2022", "sharpe", p2["sharpe"], note=f"hold {p1['sharpe']}")
        print(f"   {a[:4]}-{b[:4]}  hold: CAGR {p1['cagr']:5.1f} Sharpe {p1['sharpe']:.2f} maxDD {p1['maxdd']:4.0f}% | managed: CAGR {p2['cagr']:5.1f} Sharpe {p2['sharpe']:.2f} maxDD {p2['maxdd']:4.0f}%  avg weight {w.loc[a:b].mean():.2f}")
    res["E vol managed"] = row

    out = Path(__file__).resolve().parents[1] / "results" / "e02_french_context.json"
    out.write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
