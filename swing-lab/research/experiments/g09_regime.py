"""G09 - Market regime as an exposure dial (compact main-loop version of family f09).

Part 1  Exposure rules on SPY, 1993-02 .. 2018-06 (Yahoo; nothing after the development cut-off).
        A small, pre-specified set; no optimisation. Signal at the close, switch at the NEXT OPEN,
        5 bp per unit of turnover, cash earns nothing. Reported by era so that one decade cannot
        carry the result. (E02 already gives the 200-day rule on the CRSP market, 1926-2022.)
Part 2  What the regime means for single stocks: forward return, realised volatility and the
        frequency of large losses for universe stocks, by market state (DEV and CTX).

Registry family "G09_regime".
"""
from __future__ import annotations

import gc
import glob
import json
import os
from pathlib import Path

os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "g09")

import numpy as np
import pandas as pd

from research.swinglab import engine as E
from research.swinglab import pinelike as ta
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

CUT = pd.Timestamp("2018-06-29")
ERAS = [("1993-02", "1999-12"), ("2000-01", "2009-12"), ("2010-01", "2018-06"), ("1993-02", "2018-06")]


def ctx(sym: str) -> pd.DataFrame:
    y = pd.concat([pd.read_parquet(f) for f in glob.glob("/home/user/data/yahoo_ctx/1d_*.parquet")])
    y = y[y["symbol"] == sym].drop_duplicates("date").set_index("date").sort_index()
    return y[y.index <= CUT]


def run_rule(spy: pd.DataFrame, w: pd.Series, cost_bp: float = 5.0) -> pd.Series:
    """w[t] = target weight decided at the close of t, in force from the open of t+1.
    Daily strategy return on day d = w[d-2]*(open d / close d-1 - 1) compounded with
    w[d-1]*(close d / open d - 1), plus dividends pro rata, minus costs on weight changes."""
    o, c = spy["open"], spy["close"]
    div = spy["dividend"].fillna(0.0)
    w_prev = w.shift(1).fillna(0.0)          # weight held during day d's session (decided at close d-1, traded at open d)
    w_prev2 = w.shift(2).fillna(0.0)         # weight held overnight into day d
    on = o / c.shift(1) - 1.0
    intr = c / o - 1.0
    r = (1 + w_prev2 * (on + div / c.shift(1))) * (1 + w_prev * intr) - 1
    turn = (w_prev - w_prev2).abs()
    return (r - turn * cost_bp / 1e4).fillna(0.0)


def perf(r: pd.Series) -> dict:
    g = (1 + r).cumprod()
    yrs = len(r) / 252
    sd = r.std()
    return {"cagr": round(100 * (g.iloc[-1] ** (1 / yrs) - 1), 1), "vol": round(100 * sd * np.sqrt(252), 1),
            "sharpe": round(float(r.mean() / sd * np.sqrt(252)), 2) if sd > 0 else 0.0,
            "maxdd": round(100 * float((g / g.cummax() - 1).min()), 1)}


def part1() -> dict:
    spy = ctx("SPY")
    c = spy["close"]
    sma200 = c.rolling(200).mean()
    above = c > sma200
    rules: dict[str, pd.Series] = {"buy and hold": pd.Series(1.0, index=c.index)}
    rules["T200: above the 200-day average"] = above.astype(float)
    conf = above.rolling(3).sum()
    st = pd.Series(np.nan, index=c.index)
    st[conf == 3] = 1.0
    st[conf == 0] = 0.0
    rules["T200 confirmed 3 closes"] = st.ffill().fillna(0.0)
    band = pd.Series(np.nan, index=c.index)
    band[c > 1.02 * sma200] = 1.0
    band[c < 0.98 * sma200] = 0.0
    rules["T200 with a 2% band"] = band.ffill().fillna(0.0)
    me = c.groupby(c.index.to_period("M")).tail(1).index
    m10 = (c > c.rolling(210).mean())
    mrule = pd.Series(np.nan, index=c.index)
    mrule[me] = m10[me].astype(float)
    rules["10-month rule, decided at month-end"] = mrule.ffill().fillna(0.0)
    rules["half: 100% above, 50% below the 200-day"] = 0.5 + 0.5 * above.astype(float)
    # volatility target with the ATR-based forecast (G12): sigma_daily = 0.757 * ATR14 / close
    tr = pd.concat([spy["high"] - spy["low"], (spy["high"] - c.shift(1)).abs(), (spy["low"] - c.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    sig_ann = 0.757 * atr / c * np.sqrt(252)
    raw = (0.12 / sig_ann).clip(upper=1.0)
    vt = raw.copy()
    last = np.nan
    for i in range(len(vt)):                      # change the weight only when it moves by 0.10 or more
        x = raw.iloc[i]
        if np.isnan(x):
            continue
        if np.isnan(last) or abs(x - last) >= 0.10:
            last = x
        vt.iloc[i] = last
    rules["vol target 12% (ATR forecast), cap 1.0"] = vt.fillna(0.0)
    rules["T200 x vol target 12%"] = (above.astype(float) * vt).fillna(0.0)
    vix = ctx("^VIX")["close"].reindex(c.index).ffill()
    rules["out when below the 200-day AND VIX >= 25"] = 1.0 - ((~above) & (vix >= 25)).astype(float)
    dd = c / c.rolling(252).max() - 1
    rules["out when down 10%+ from the 252-day high and below the 200-day"] = 1.0 - ((dd <= -0.10) & (~above)).astype(float)
    res = {}
    print("Part 1. SPY exposure rules, next-open execution, 5 bp per switch")
    print(f"{'rule':<60s}" + "".join(f"  {a[:4]}-{b[:4]}: CAGR  Sh   DD " for a, b in ERAS) + "  in%  sw/yr")
    for name, w in rules.items():
        r = run_rule(spy, w)
        row, res[name] = f"{name:<60s}", {}
        for a, b in ERAS:
            p = perf(r.loc[a:b])
            res[name][f"{a[:4]}-{b[:4]}"] = p
            row += f"  {'':10s}{p['cagr']:5.1f} {p['sharpe']:4.2f} {p['maxdd']:5.0f}"
            log_trial("G09", "G09_regime", f"P1 {name} {a}..{b}", "SPY<=2018-06", "sharpe", p["sharpe"], note=json.dumps(p))
        sw = float(w.diff().abs().sum() / (len(w) / 252))
        res[name]["time_in"], res[name]["switches_per_year"] = round(float(w.mean()), 2), round(sw, 1)
        print(row + f"  {100 * w.mean():3.0f}  {sw:5.1f}")
    # volatility in and out of the trend state: the testable part of "risk switch"
    r1 = c.pct_change()
    st = above.shift(1).fillna(False).astype(bool)
    v_in, v_out = r1[st].std() * np.sqrt(252), r1[~st].std() * np.sqrt(252)
    res["vol_in_out"] = {"above": round(100 * float(v_in), 1), "below": round(100 * float(v_out), 1),
                         "mean_bp_above": round(1e4 * float(r1[st].mean()), 1), "mean_bp_below": round(1e4 * float(r1[~st].mean()), 1)}
    print(f"   SPY next-day volatility: {100 * v_in:.1f}% a year when above the 200-day, {100 * v_out:.1f}% when below; mean daily return {1e4 * r1[st].mean():+.1f} bp vs {1e4 * r1[~st].mean():+.1f} bp")
    return res


def part2(smp: str) -> dict:
    S = Study(smp)
    c = S.P.cf
    spy = c[:, [S.spy]]
    above = (spy > ta.sma(spy, 200))[:, 0]
    sma50 = (spy > ta.sma(spy, 50))[:, 0]
    dd = (spy / ta.highest(spy, 252) - 1)[:, 0]
    breadth = np.nanmean(np.where(S.uni, (c > ta.sma(c, 200)).astype(float), np.nan), axis=1)
    states = {
        "SPY above 200-day": above, "SPY below 200-day": ~above & np.isfinite(ta.sma(spy, 200)[:, 0]),
        "SPY below 200 and below 50": ~above & ~sma50 & np.isfinite(ta.sma(spy, 200)[:, 0]),
        "SPY below 200 but above 50": ~above & sma50 & np.isfinite(ta.sma(spy, 200)[:, 0]),
        "SPY drawdown worse than -10%": dd <= -0.10,
        "breadth: under 40% of stocks above own 200-day": breadth < 0.40,
        "breadth: over 70% of stocks above own 200-day": breadth > 0.70,
    }
    res = {}
    print(f"\nPart 2 [{smp}]. Universe stocks by market state at the close of t (from the next open)")
    print(f"{'state':<48s} days   mean 10d ret (bp)   mean 20d   P(20d < -10%)   P(20d > +10%)   10d vol/forecast")
    f10, f20 = S.fwd(10), S.fwd(20)
    fvol = 0.757 * S.atr(14) / c
    for name, st in states.items():
        m = S.uni & st[:, None]
        if m.sum() < 2000:
            continue
        a10 = np.nanmean(f10[m]); a20 = np.nanmean(f20[m])
        pl = np.nanmean(f20[m] < -0.10); pg = np.nanmean(f20[m] > 0.10)
        rel = np.nanmean(np.abs(np.log1p(f10[m])) / (fvol[m] * np.sqrt(10)))
        days = int(st[S.rows].sum())
        res[name] = {"days": days, "ret10_bp": round(1e4 * float(a10), 1), "ret20_bp": round(1e4 * float(a20), 1),
                     "p_loss10": round(float(pl), 4), "p_gain10": round(float(pg), 4), "abs_move_vs_forecast": round(float(rel), 3)}
        print(f"{name:<48s} {days:5d}   {1e4 * a10:+8.1f}          {1e4 * a20:+8.1f}    {100 * pl:6.2f}%        {100 * pg:6.2f}%        {rel:.2f}")
        log_trial("G09", "G09_regime", f"P2 {name}", smp, "ret10_bp", 1e4 * float(a10), note=json.dumps(res[name]), n=int(m.sum()))
    del S
    gc.collect()
    return res


if __name__ == "__main__":
    out = {"part1": part1()}
    for smp in ("DEV", "CTX"):
        out[f"part2_{smp}"] = part2(smp)
    Path(__file__).resolve().parents[1].joinpath("results", "g09_regime.json").write_text(json.dumps(out, indent=1, default=str))
