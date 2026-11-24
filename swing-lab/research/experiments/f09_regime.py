"""F09 - Market regime as an exposure dial.

Run:  cd swing-lab && python -m research.experiments.f09_regime            (DEV then CTX, one at a time)
      python -m research.experiments.f09_regime DEV                        (one sample)

Question. For a long-only swing trader the largest decision may be HOW MUCH to be invested. Which
market-level state variables, all known at the close of t and computable in Pine, change
  (1) the next 5/10/20-day RETURN of SPY and of the equal-weight liquid universe (from the next open),
  (2) the next-20-day RISK (realised volatility, probability of a loss worse than -5%),
and do exposure rules built on them beat buy-and-hold and the classic baselines (200-day, 10-month,
absolute/dual momentum) as PORTFOLIOS on daily data (switch at the next open, 5 bp per unit switched)?
Finally: do the single-stock effects of E01 (moderate dip, 3-sigma shock drift, up-move fade) differ
by regime, i.e. does a regime input belong in the stock-level indicator?

Samples: DEV 2011-01..2018-06 (no bear market), CTX 1998..2010 (two bear markets; the stock universe
is survivors only, so equal-weight LEVELS are inflated there: SPY is the honest series for levels).

Conventions
-----------
* A state on row t uses data up to the close of t. Market series (SPY, VIX, VIX3M, HYG, LQD, IEF, TLT,
  rates, IWM, XLY, XLP) are read with their FULL history before the sample and truncated at the
  sample's last day, so 200/252-bar lookbacks are warm on the first sample day (S.ctx() alone would
  start cold in 2011) and nothing after the sample is read.
* Portfolio arithmetic. w[t] is the target weight decided at the close of t. It is traded at the open
  of t+1: day d earns  w[d-2] x overnight(d)  +  w[d-1] x intraday(d)  +  (1 - w[d-1]) x T-bill,
  minus 5 bp x |w[d-1] - w[d-2]|.  Sharpe is on returns in excess of the 13-week bill (^IRX).
* "Adds return" vs "cuts risk" is read from the days the rule is OUT: if their mean excess return is
  below the IN days the state adds return; if only their variance is higher it cuts risk.
* Every number printed is written to registry/trials_f09.jsonl.
"""
from __future__ import annotations

import os

os.environ["SWINGLAB_REGISTRY_TAG"] = "f09"

import gc
import glob
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from research.swinglab import engine as E
from research.swinglab import pinelike as ta
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

YAHOO = "/home/user/data/yahoo_ctx/1d_*.parquet"
HS = (5, 10, 20)
COST_BP = 5.0
ANN = 252.0
VARIANTS: dict = {}          # id -> one-line definition; every distinct signal/rule variant evaluated
SAMPLE = "?"


# ============================================================================== small helpers
def LOG(hid, fam, definition, metric, value, t=None, n=None, params=None, note=""):
    v = float("nan") if value is None or not np.isfinite(value) else float(value)
    log_trial(f"F09.{hid}", f"F09_{fam}", definition, SAMPLE, metric, v, params=params or {},
              universe="market-level", tstat=None if t is None or not np.isfinite(t) else float(t), n=n, note=note)


def variant(vid: str, definition: str) -> str:
    VARIANTS.setdefault(vid, definition)
    return vid


def _c(x):
    return np.asarray(x, dtype=float)[:, None]


def sma(x, n): return ta.sma(_c(x), n)[:, 0]
def ema(x, n): return ta.ema(_c(x), n)[:, 0]
def stdev(x, n): return ta.stdev(_c(x), n)[:, 0]
def highest(x, n): return ta.highest(_c(x), n)[:, 0]
def lowest(x, n): return ta.lowest(_c(x), n)[:, 0]
def shift(x, k): return ta.shift(_c(x), k)[:, 0]
def rsi(x, n): return ta.rsi(_c(x), n)[:, 0]
def prank(x, n): return ta.percentrank(_c(x), n)[:, 0]


def ffill1(x):
    x = np.asarray(x, dtype=float)
    idx = np.where(np.isfinite(x), np.arange(len(x)), 0)
    np.maximum.accumulate(idx, out=idx)
    out = x[idx]
    first = np.argmax(np.isfinite(x)) if np.isfinite(x).any() else len(x)
    out[:first] = np.nan
    return out


def r1(x, nd=1):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def nw_se(u: np.ndarray, lags: int) -> float:
    """Newey-West standard error of the mean of u (Bartlett kernel)."""
    n = len(u)
    e = u - u.mean()
    var = (e @ e) / n
    for k in range(1, min(lags, n - 1) + 1):
        var += 2.0 * (1.0 - k / (lags + 1.0)) * (e[k:] @ e[:-k]) / n
    return float(np.sqrt(max(var, 1e-300) / n))


def cond_diff(y: np.ndarray, state: np.ndarray, lags: int):
    """Mean of y where state==1, where state==0, their difference and its Newey-West t (OLS of y on
    the state dummy with HAC errors). Returns None if either side has fewer than 20 days."""
    ok = np.isfinite(y) & np.isfinite(state)
    yy, x = y[ok], state[ok]
    n = len(yy)
    n1 = int(x.sum())
    if n < 100 or n1 < 20 or n - n1 < 20:
        return None
    p = x.mean()
    m1, m0 = yy[x == 1].mean(), yy[x == 0].mean()
    e = yy - (m0 + (m1 - m0) * x)
    u = (x - p) * e / (p * (1 - p))
    se = nw_se(u, lags)
    return {"in": float(m1), "out": float(m0), "diff": float(m1 - m0), "t": float((m1 - m0) / se), "p": float(p),
            "n": n, "n_in": n1}


def episodes(state: np.ndarray, rows: np.ndarray) -> int:
    s = np.where(np.isfinite(state), state, 0.0)[rows] > 0.5
    return int((s[1:] & ~s[:-1]).sum() + (1 if len(s) and s[0] else 0))


# ============================================================================== market context
class Market:
    """Market series on SPY's own trading calendar, full history, truncated at the sample end."""

    def __init__(self, S: Study):
        self.end = pd.Timestamp(S.dates[S.rows][-1])
        y = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(YAHOO))])
        self._y = y[y["date"] <= self.end]
        self.cal = self._raw("SPY").index
        self.pdates = pd.DatetimeIndex(S.dates)

    def _raw(self, sym, field="close"):
        d = self._y[self._y["symbol"] == sym].drop_duplicates("date").set_index("date")[field].sort_index()
        if d.empty:
            raise KeyError(sym)
        return d

    def s(self, sym, field="close") -> np.ndarray:
        return self._raw(sym, field).reindex(self.cal, method="ffill").to_numpy(dtype=float)

    def to_panel(self, x) -> np.ndarray:
        return pd.Series(np.asarray(x, dtype=float), index=self.cal).reindex(self.pdates, method="ffill").to_numpy()


def spy_vol_ewma(ret: np.ndarray, span: int = 20) -> np.ndarray:
    """S.vol's definition (engine.vol_ewma: robust EWMA of squared log returns) on a 1-D series."""
    return E.vol_ewma(SimpleNamespace(ret=_c(ret)), span)[:, 0]


# ============================================================================== state variables
def build_features(S: Study, M: Market) -> dict:
    """Continuous market features. Keys ending in '@cal' live on the SPY calendar, others on panel rows."""
    F = {}
    c = M.s("SPY")
    lc = np.log(c)
    r = lc - shift(lc, 1)
    F["c"], F["r"] = c, r
    for n in (20, 50, 100, 150, 200, 250, 300):
        F[f"sma{n}"] = sma(c, n)
    for k in (21, 63, 126, 189, 252):
        F[f"roc{k}"] = c / shift(c, k) - 1.0
    F["dd252"] = c / highest(c, 252) - 1.0
    F["ext200"] = c / F["sma200"] - 1.0
    vix, vix3m = M.s("^VIX"), M.s("^VIX3M")
    F["vix"], F["vts"] = vix, vix / vix3m
    F["vixpr"] = prank(vix, 252)
    F["dvix5"] = vix / shift(vix, 5) - 1.0
    F["vix_sma20"], F["vix_sma50"] = sma(vix, 20), sma(vix, 50)
    for n in (10, 20, 60):
        F[f"rv{n}"] = stdev(r, n) * np.sqrt(ANN)
    for sp in (10, 20, 60):
        F[f"volf{sp}"] = spy_vol_ewma(r, sp) * np.sqrt(ANN)          # annualised forecast, S.vol style
    F["vrp"] = vix / 100.0 - F["rv20"]
    hyg, lqd, ief, tlt = M.s("HYG"), M.s("LQD"), M.s("IEF"), M.s("TLT")
    F["hyg"], F["tlt"] = hyg, tlt
    F["hyg_lqd"], F["hyg_ief"] = hyg / lqd, hyg / ief
    tnx, irx = M.s("^TNX"), M.s("^IRX")
    F["yc"] = tnx - irx
    F["irx"] = irx
    F["iwm_spy"] = M.s("IWM") / c
    F["xly_xlp"] = M.s("XLY") / M.s("XLP")
    F["rsi2"] = rsi(c, 2)
    F["rsi14"] = rsi(c, 14)
    vd = spy_vol_ewma(r, 20)
    F["z5"] = (lc - shift(lc, 5)) / (shift(vd, 5) * np.sqrt(5))
    F["z10"] = (lc - shift(lc, 10)) / (shift(vd, 10) * np.sqrt(10))
    F["bb_low"] = F["sma20"] - 2.0 * stdev(c, 20)
    # month ends on the SPY calendar (the last bar of the truncated calendar is a true month end
    # in both samples: 2018-06-29 and 2010-12-31)
    mo = M.cal.month.to_numpy()
    me = np.r_[mo[1:] != mo[:-1], True]
    F["month_end"] = me
    return F


def build_breadth(S: Study, hi: int) -> dict:
    """Breadth of the panel universe on panel rows (NaN outside the sample)."""
    cf = S.P.cf[:hi]
    u = S.uni[:hi]
    real_day = np.isfinite(S.P.c[:hi, S.spy])           # phantom holiday rows exist in the DEV panel

    def share(cond, valid):
        m = u & valid
        n = m.sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            x = np.where(n >= 100, (cond & m).sum(axis=1) / np.maximum(n, 1), np.nan)
        x[~real_day] = np.nan
        return x

    B = {}
    s50, s200 = ta.sma(cf, 50), ta.sma(cf, 200)
    B["b50"] = 100.0 * share(cf > s50, np.isfinite(s50))
    B["b200"] = 100.0 * share(cf > s200, np.isfinite(s200))
    del s50, s200
    for n in (20, 252):
        hh, ll = ta.highest(cf, n), ta.lowest(cf, n)
        v = np.isfinite(hh)
        B[f"nhl{n}"] = 100.0 * (share(cf >= hh, v) - share(cf <= ll, v))
        del hh, ll
    ret = S.P.ret[:hi]
    v = np.isfinite(ret)
    adv, dec = share(ret > 0, v), share(ret < 0, v)
    with np.errstate(divide="ignore", invalid="ignore"):
        ad = (adv - dec) / (adv + dec)
    B["adv_share"] = adv / (adv + dec)
    B["ad"] = ad
    # rolling versions skip the phantom rows (computed on real days only, then put back)
    idx = np.flatnonzero(real_day)
    for k, src, fn in (("ad10", "ad", lambda x: sma(x, 10)), ("ad10ema", "adv_share", lambda x: ema(x, 10)),
                       ("nhl20_s10", "nhl20", lambda x: sma(x, 10)), ("nhl252_s10", "nhl252", lambda x: sma(x, 10)),
                       ("b50_chg10", "b50", lambda x: x - shift(x, 10))):
        full = np.full(hi, np.nan)
        full[idx] = fn(B[src][idx])
        B[k] = full
    return {k: ffill1(x) for k, x in B.items()}


def build_states(S: Study, M: Market, F: dict, B: dict, hi: int) -> dict:
    """Boolean states (1 = favourable by the conventional reading, 0 = not, NaN = undefined) on panel
    rows [0:hi]. Each: on, group, definition, pine."""
    ST = {}
    c = F["c"]

    def add(name, cond, valid, group, definition, pine, cal=True):
        x = np.where(valid, np.asarray(cond, dtype=float), np.nan)
        on = M.to_panel(x)[:hi] if cal else x[:hi]
        ST[name] = {"on": on, "group": group, "def": definition, "pine": pine}
        variant(f"S:{name}", definition)

    fin = np.isfinite
    # ---- trend of SPY
    for n in (50, 100, 150, 200, 250, 300):
        s = F[f"sma{n}"]
        add(f"T{n}", c > s, fin(s), "trend", f"SPY close > SMA{n}", f"close > ta.sma(close,{n})")
    add("GX", F["sma50"] > F["sma200"], fin(F["sma200"]), "trend", "SMA50 > SMA200 (golden cross state)",
        "ta.sma(close,50) > ta.sma(close,200)")
    s200 = F["sma200"]
    add("SL200", s200 > shift(s200, 20), fin(shift(s200, 20)), "trend", "SMA200 rising over 20 bars",
        "ta.sma(close,200) > ta.sma(close,200)[20]")
    s50 = F["sma50"]
    add("SL50", s50 > shift(s50, 10), fin(shift(s50, 10)), "trend", "SMA50 rising over 10 bars",
        "ta.sma(close,50) > ta.sma(close,50)[10]")
    add("T200_SL", (c > s200) & (s200 > shift(s200, 20)), fin(shift(s200, 20)), "trend",
        "close > SMA200 and SMA200 rising", "close > s200 and s200 > s200[20]")
    add("T200orSL", (c > s200) | (s200 > shift(s200, 20)), fin(shift(s200, 20)), "trend",
        "close > SMA200 OR SMA200 rising (out only when both fail)", "close > s200 or s200 > s200[20]")
    for k in (63, 126, 189, 252):
        x = F[f"roc{k}"]
        add(f"M{k}", x > 0, fin(x), "momentum", f"SPY {k}-bar price return > 0", f"close > close[{k}]")
    bill = sma(F["irx"], 252) / 100.0
    add("DM252", F["roc252"] > bill, fin(F["roc252"]) & fin(bill), "momentum",
        "SPY 252-bar return > average 13-week bill yield of the same year (absolute-momentum leg of dual momentum)",
        "close/close[252]-1 > ta.sma(request.security('TVC:US03MY','D',close),252)/100")
    for thr in (-0.05, -0.10, -0.15):
        add(f"DD{int(-thr * 100)}", F["dd252"] > thr, fin(F["dd252"]), "drawdown",
            f"SPY close within {int(-thr * 100)}% of its 252-bar closing high", f"close/ta.highest(close,252)-1 > {thr}")
    add("EXT8", F["ext200"] < 0.08, fin(F["ext200"]), "drawdown", "SPY less than 8% above SMA200 (not over-extended)",
        "close/ta.sma(close,200)-1 < 0.08")
    # ---- volatility
    vix = F["vix"]
    for thr in (15, 20, 25, 30):
        add(f"VIX<{thr}", vix < thr, fin(vix), "vol", f"VIX close < {thr}", f"request.security('CBOE:VIX','D',close) < {thr}")
    for thr in (50, 80, 90):
        add(f"VIXPR<{thr}", F["vixpr"] < thr, fin(F["vixpr"]), "vol", f"VIX percentrank over 252 bars < {thr}",
            f"ta.percentrank(vix,252) < {thr}")
    for thr in (0.90, 0.95, 1.00, 1.05):
        add(f"VTS<{thr:.2f}", F["vts"] < thr, fin(F["vts"]), "vol", f"VIX/VIX3M < {thr:.2f}",
            f"vix/request.security('CBOE:VIX3M','D',close) < {thr}")
    add("VIX<SMA50", vix < F["vix_sma50"], fin(F["vix_sma50"]), "vol", "VIX below its 50-bar SMA", "vix < ta.sma(vix,50)")
    add("VIXnoSpike", vix < 1.25 * F["vix_sma20"], fin(F["vix_sma20"]), "vol", "VIX < 1.25 x its 20-bar SMA (no spike)",
        "vix < 1.25*ta.sma(vix,20)")
    add("DVIX5<20", F["dvix5"] < 0.20, fin(F["dvix5"]), "vol", "VIX rose less than 20% in 5 bars", "vix/vix[5]-1 < 0.20")
    for thr in (0.15, 0.20, 0.25):
        add(f"RV20<{int(thr * 100)}", F["rv20"] < thr, fin(F["rv20"]), "vol",
            f"20-bar realised SPY volatility (annualised) < {int(thr * 100)}%",
            f"ta.stdev(math.log(close/close[1]),20)*math.sqrt(252) < {thr}")
    add("RV10<RV60", F["rv10"] < F["rv60"], fin(F["rv60"]), "vol", "10-bar realised vol below 60-bar (vol falling)",
        "ta.stdev(r,10) < ta.stdev(r,60)")
    add("VRP>0", F["vrp"] > 0, fin(F["vrp"]), "vol", "VIX above 20-bar realised vol (implied > realised)",
        "vix/100 > ta.stdev(r,20)*math.sqrt(252)")
    # ---- credit, rates, cross-asset
    for nm, key, sym in (("HYGLQD", "hyg_lqd", "HYG/LQD"), ("HYGIEF", "hyg_ief", "HYG/IEF")):
        for n in (50, 200):
            s = sma(F[key], n)
            add(f"{nm}>{n}", F[key] > s, fin(s), "credit", f"{sym} ratio above its SMA{n}",
                f"x = request.security('{sym.replace('/', '/AMEX:')}','D',close); x > ta.sma(x,{n})")
    s = sma(F["hyg"], 200)
    add("HYG>200", F["hyg"] > s, fin(s), "credit", "HYG price above its SMA200", "hyg > ta.sma(hyg,200)")
    s = sma(F["tlt"], 200)
    add("TLT>200", F["tlt"] > s, fin(s), "rates", "TLT price above its SMA200 (bond uptrend)", "tlt > ta.sma(tlt,200)")
    add("TLT<200", F["tlt"] < s, fin(s), "rates", "TLT price below its SMA200 (rates rising)", "tlt < ta.sma(tlt,200)")
    add("YC>0", F["yc"] > 0, fin(F["yc"]), "rates", "10-year minus 3-month yield > 0",
        "request.security('TVC:US10Y','D',close) > request.security('TVC:US03MY','D',close)")
    add("YC>1", F["yc"] > 1.0, fin(F["yc"]), "rates", "10-year minus 3-month yield > 1 point", "us10y - us03m > 1")
    for nm, key, sym in (("IWMSPY", "iwm_spy", "IWM/SPY"), ("XLYXLP", "xly_xlp", "XLY/XLP")):
        for n in (50, 200):
            s = sma(F[key], n)
            add(f"{nm}>{n}", F[key] > s, fin(s), "xasset", f"{sym} ratio above its SMA{n}", f"ratio > ta.sma(ratio,{n})")
    # ---- breadth of the panel universe (needs TradingView breadth tickers: see the report)
    def addb(name, cond, key, definition, pine):
        add(name, cond, np.isfinite(B[key]), "breadth", definition, pine, cal=False)
    for thr in (30, 40, 50, 60, 70):
        addb(f"B50>{thr}", B["b50"] > thr, "b50", f"share of universe above own SMA50 > {thr}%",
             f"request.security('INDEX:MMFI','D',close) > {thr}   // or S5FI")
    for thr in (40, 50, 60):
        addb(f"B200>{thr}", B["b200"] > thr, "b200", f"share of universe above own SMA200 > {thr}%",
             f"request.security('INDEX:MMTH','D',close) > {thr}   // or S5TH")
    addb("B50up", B["b50_chg10"] > 0, "b50_chg10", "share above SMA50 higher than 10 bars ago", "mmfi > mmfi[10]")
    addb("NHL20>0", B["nhl20_s10"] > 0, "nhl20_s10", "10-bar mean of (20-bar new highs - new lows)/N > 0",
         "needs screener / no direct ticker")
    addb("NHL252>0", B["nhl252_s10"] > 0, "nhl252_s10", "10-bar mean of (252-bar new highs - new lows)/N > 0",
         "ta.sma(request.security('INDEX:HIGN','D',close) - request.security('INDEX:LOWN','D',close),10) > 0")
    addb("AD10>0", B["ad10"] > 0, "ad10", "10-bar mean of (advancers - decliners)/(adv+dec) > 0",
         "ta.sma((advn-decn)/(advn+decn),10) > 0   // USI:ADVN.NY, USI:DECN.NY")
    # ---- short-term market states (1 = the "buy" reading)
    add("mZ5<-1.5", F["z5"] <= -1.5, fin(F["z5"]), "dip", "SPY 5-bar return <= -1.5 sigma (sigma = EWMA vol before the move)",
        "z5 <= -1.5")
    add("mZ5<-1", F["z5"] <= -1.0, fin(F["z5"]), "dip", "SPY 5-bar return <= -1 sigma", "z5 <= -1")
    add("mZ5>1", F["z5"] >= 1.0, fin(F["z5"]), "dip", "SPY 5-bar return >= +1 sigma", "z5 >= 1")
    add("mRSI2<10", F["rsi2"] < 10, fin(F["rsi2"]), "dip", "SPY RSI(2) < 10", "ta.rsi(close,2) < 10")
    add("mRSI2<10&T200", (F["rsi2"] < 10) & (c > s200), fin(F["rsi2"]) & fin(s200), "dip",
        "SPY RSI(2) < 10 and close > SMA200", "ta.rsi(close,2) < 10 and close > ta.sma(close,200)")
    add("mRSI2<10&notT200", (F["rsi2"] < 10) & (c <= s200), fin(F["rsi2"]) & fin(s200), "dip",
        "SPY RSI(2) < 10 and close <= SMA200", "ta.rsi(close,2) < 10 and close <= ta.sma(close,200)")
    add("mBBlow", c < F["bb_low"], fin(F["bb_low"]), "dip", "SPY close below lower Bollinger band (20, 2)",
        "close < ta.sma(close,20) - 2*ta.stdev(close,20)")
    r = F["r"]
    add("mDown3", (r < 0) & (shift(r, 1) < 0) & (shift(r, 2) < 0), fin(shift(r, 2)), "dip", "SPY down three closes in a row",
        "close<close[1] and close[1]<close[2] and close[2]<close[3]")
    add("mVIXspike", vix > 1.25 * F["vix_sma20"], fin(F["vix_sma20"]), "dip", "VIX > 1.25 x its 20-bar SMA (spike)",
        "vix > 1.25*ta.sma(vix,20)")
    add("mVIXPR>90", F["vixpr"] >= 90, fin(F["vixpr"]), "dip", "VIX percentrank(252) >= 90", "ta.percentrank(vix,252) >= 90")
    addb("mB50<20", B["b50"] < 20, "b50", "breadth washout: share above SMA50 < 20%", "mmfi < 20")
    addb("mB50<30", B["b50"] < 30, "b50", "breadth washout: share above SMA50 < 30%", "mmfi < 30")
    return ST


# ============================================================================== outcomes
def build_outcomes(S: Study, hi: int) -> dict:
    """Forward outcomes on panel rows [0:hi], NaN outside the sample or if the window leaves it."""
    O = {}
    rows = S.rows[:hi]
    for h in HS:
        f = S.fwd(h)[:hi]
        O[f"spy{h}"] = f[:, S.spy].copy()
        O[f"ew{h}"] = E.day_means(f, S.uni[:hi], 20)[0]
        O[f"ewA{h}"] = E.day_means(f, S.uni[:hi] & S.half_a[None, :], 20)[0]
        O[f"ewB{h}"] = E.day_means(f, S.uni[:hi] & ~S.half_a[None, :], 20)[0]
    # next-20-day realised volatility of SPY (close-to-close log returns t+1..t+20), annualised, and
    # the worst close inside the window relative to the entry open
    spy_c, spy_o = S.P.cf[:hi, S.spy], S.P.o[:hi, S.spy]
    lr = np.diff(np.log(spy_c), prepend=np.nan)
    T = hi
    rv = np.full(T, np.nan)
    worst = np.full(T, np.nan)
    last = S._last_row
    for t in np.flatnonzero(rows):
        if t + 20 > last or not np.isfinite(spy_o[t + 1]):
            continue
        rv[t] = np.std(lr[t + 1:t + 21]) * np.sqrt(ANN)
        worst[t] = spy_c[t + 1:t + 21].min() / spy_o[t + 1] - 1.0
    O["rv_next20"] = rv
    O["worst20"] = worst
    O["loss5"] = np.where(np.isfinite(O["spy20"]), (O["spy20"] < -0.05).astype(float), np.nan)
    O["path5"] = np.where(np.isfinite(worst), (worst <= -0.05).astype(float), np.nan)
    O["ewloss5"] = np.where(np.isfinite(O["ew20"]), (O["ew20"] < -0.05).astype(float), np.nan)
    return O


def daily_series(S: Study, M: Market, F: dict, hi: int) -> dict:
    """Daily overnight and intraday simple returns of SPY and of the equal-weight universe, and the
    daily bill return, on panel rows [0:hi]; zero outside the sample."""
    rows = S.rows[:hi]
    P = S.P
    with np.errstate(divide="ignore", invalid="ignore"):
        gross = P.tri[1:hi] / P.tri[:hi - 1]                     # close(d-1) -> close(d), total
        idr = P.c[1:hi] / P.o[1:hi]                              # open(d) -> close(d)
        on = gross / idr
    ok = np.isfinite(idr) & np.isfinite(on)
    D = {}
    s = S.spy
    D["spy_on"] = np.r_[0.0, np.where(ok[:, s], on[:, s] - 1.0, 0.0)]
    D["spy_id"] = np.r_[0.0, np.where(ok[:, s], idr[:, s] - 1.0, 0.0)]
    for nm, cols in (("ew", np.ones(P.c.shape[1], bool)), ("ewA", S.half_a), ("ewB", ~S.half_a)):
        mem = S.uni[:hi - 1] & ok & cols[None, :]                # member at the close of d-1, real bar on d
        n = mem.sum(axis=1)
        good = n >= 300 if SAMPLE == "DEV" else n >= 100
        with np.errstate(divide="ignore", invalid="ignore"):
            e_on = np.where(good, np.where(mem, on - 1.0, 0.0).sum(axis=1) / np.maximum(n, 1), 0.0)
            e_id = np.where(good, np.where(mem, idr - 1.0, 0.0).sum(axis=1) / np.maximum(n, 1), 0.0)
        D[f"{nm}_on"], D[f"{nm}_id"] = np.r_[0.0, e_on], np.r_[0.0, e_id]
    rf = M.to_panel(F["irx"])[:hi] / 100.0 / ANN
    D["rf"] = np.r_[0.0, rf[:-1]]                                # the yield known the day before
    for k in D:
        D[k] = np.where(rows, np.nan_to_num(D[k]), 0.0)
    D["rows"] = rows
    return D


# ============================================================================== the forward map
def map_state(name: str, st: dict, O: dict, rows: np.ndarray, log=True) -> dict:
    on = st["on"]
    res = {"group": st["group"], "share_in": r1(np.nanmean(on[rows & np.isfinite(on)]), 3),
           "episodes": episodes(on, rows), "days": int((rows & np.isfinite(on)).sum())}
    for tgt in ("spy", "ew", "ewA", "ewB"):
        for h in HS:
            cd = cond_diff(O[f"{tgt}{h}"], on, 2 * h)
            if cd is None:
                continue
            res[f"{tgt}{h}"] = {"in_bp": r1(1e4 * cd["in"]), "out_bp": r1(1e4 * cd["out"]), "diff_bp": r1(1e4 * cd["diff"]),
                                "t": r1(cd["t"], 2)}
            if log:
                LOG(f"map.{name}", "map", f"[{st['def']}] in-state minus out-of-state fwd_open_{h} of {tgt}", "diff_bp",
                    1e4 * cd["diff"], t=cd["t"], n=cd["n_in"], params={"h": h, "target": tgt})
    for key in ("rv_next20", "loss5", "path5", "ewloss5"):
        cd = cond_diff(O[key], on, 40)
        if cd is None:
            continue
        sc = 100.0
        res[key] = {"in": r1(sc * cd["in"], 2), "out": r1(sc * cd["out"], 2), "t": r1(cd["t"], 2)}
        if log:
            LOG(f"map.{name}", "map", f"[{st['def']}] in-state minus out-of-state {key}", "diff_pct",
                sc * cd["diff"], t=cd["t"], n=cd["n_in"], params={"target": key})
    return res


def show_map(tab: dict, title: str) -> None:
    print(f"\n{title}")
    print(f"{'state':>18s} {'in%':>5s} {'epi':>4s} |" + "".join(f"{'SPY h=' + str(h) + ' in/out d(t)':>27s}" for h in HS)
          + " |" + "".join(f"{'EW h=' + str(h) + ' d(t)':>15s}" for h in HS) + " | vol20 in/out   P(<-5%) in/out  path in/out")
    for name, r in tab.items():
        line = f"{name:>18s} {100 * (r['share_in'] or 0):5.1f} {r['episodes']:4d} |"
        for h in HS:
            c = r.get(f"spy{h}")
            line += f"{'':>27s}" if c is None else f"{c['in_bp']:+7.0f}/{c['out_bp']:+5.0f} {c['diff_bp']:+5.0f}({c['t']:+4.1f})"
        line += " |"
        for h in HS:
            c = r.get(f"ew{h}")
            line += f"{'':>15s}" if c is None else f"{c['diff_bp']:+7.0f}({c['t']:+4.1f}) "
        v, l5, p5 = r.get("rv_next20"), r.get("loss5"), r.get("path5")
        line += " |" + ("" if v is None else f" {v['in']:5.1f}/{v['out']:5.1f}")
        line += "" if l5 is None else f"   {l5['in']:5.1f}/{l5['out']:5.1f}"
        line += "" if p5 is None else f"   {p5['in']:5.1f}/{p5['out']:5.1f}"
        print(line)


def bucket_map(name: str, x: np.ndarray, edges, O: dict, rows: np.ndarray) -> dict:
    """Mean outcomes by absolute bucket of a continuous feature (panel rows)."""
    out = {}
    for i in range(len(edges) - 1):
        lo, hi_ = edges[i], edges[i + 1]
        m = rows & np.isfinite(x) & (x > lo) & (x <= hi_)
        lab = f"({lo},{hi_}]"
        cell = {"days": int(m.sum())}
        if m.sum() >= 20:
            st = np.where(np.isfinite(x), m.astype(float), np.nan)
            for tgt in ("spy", "ew"):
                for h in HS:
                    y = O[f"{tgt}{h}"]
                    cd = cond_diff(y, st, 2 * h)
                    if cd is not None:
                        cell[f"{tgt}{h}"] = {"bp": r1(1e4 * cd["in"]), "t_vs_rest": r1(cd["t"], 2)}
                        LOG(f"bkt.{name}", "map", f"{name} in {lab}: mean fwd_open_{h} of {tgt} vs rest", "in_bp",
                            1e4 * cd["in"], t=cd["t"], n=cd["n_in"], params={"lo": lo, "hi": hi_, "h": h})
            for key in ("rv_next20", "loss5", "path5"):
                y = O[key]
                ok = m & np.isfinite(y)
                if ok.sum() >= 20:
                    cell[key] = r1(100.0 * y[ok].mean(), 2)
                    LOG(f"bkt.{name}", "map", f"{name} in {lab}: {key}", "pct", 100.0 * y[ok].mean(), n=int(ok.sum()))
        out[lab] = cell
    variant(f"BKT:{name}", f"absolute buckets of {name}: {list(edges)}")
    return out


def show_buckets(tab: dict, title: str) -> None:
    print(f"\n{title}")
    print(f"{'bucket':>16s} {'days':>5s}" + "".join(f"{'SPY' + str(h) + ' bp(t)':>15s}" for h in HS)
          + "".join(f"{'EW' + str(h) + ' bp(t)':>15s}" for h in HS) + "   vol20  P(<-5%)  path<-5%")
    for lab, c in tab.items():
        line = f"{lab:>16s} {c['days']:5d}"
        for tgt in ("spy", "ew"):
            for h in HS:
                x = c.get(f"{tgt}{h}")
                line += f"{'':>15s}" if x is None else f"{x['bp']:+8.0f}({x['t_vs_rest']:+4.1f}) "
        for key in ("rv_next20", "loss5", "path5"):
            line += f"{'' if c.get(key) is None else c[key]:>9}"
        print(line)


# ============================================================================== portfolios
def port_returns(w: np.ndarray, D: dict, asset: str = "spy", cost_bp: float = COST_BP, delay: int = 0):
    """Daily returns of 'hold `asset` with weight w' under the next-open convention.
    Returns (r, wd, mask) on panel rows: mask = sample rows from the first day the weight is defined."""
    wd = shift(w, 1 + delay)                    # weight during day d's session
    wo = shift(w, 2 + delay)                    # weight carried overnight into day d
    rows = D["rows"]
    defined = np.isfinite(wd)
    first = np.argmax(rows & defined) if (rows & defined).any() else len(w)
    mask = rows.copy()
    mask[:first] = False
    wd = np.where(np.isfinite(wd), wd, 0.0)
    wo = np.where(np.isfinite(wo), wo, wd)
    wo[first] = wd[first]                       # no switching cost at inception
    r = (1.0 + wo * D[f"{asset}_on"]) * (1.0 + wd * D[f"{asset}_id"]) - 1.0 + (1.0 - wd) * D["rf"] \
        - cost_bp / 1e4 * np.abs(wd - wo)
    return r, wd, wo, mask


def perf(r: np.ndarray, rf: np.ndarray) -> dict:
    n = len(r)
    if n < 60:
        return {}
    eq = np.cumprod(1.0 + r)
    ex = r - rf
    dd = eq / np.maximum.accumulate(eq) - 1.0
    sd = ex.std()
    return {"cagr": float(eq[-1] ** (ANN / n) - 1.0), "vol": float(r.std() * np.sqrt(ANN)),
            "sharpe": float(ex.mean() / sd * np.sqrt(ANN)) if sd > 0 else float("nan"), "maxdd": float(dd.min()),
            "years": n / ANN}


def evaluate_rule(rid: str, definition: str, w: np.ndarray, D: dict, asset: str = "spy", delay: int = 0,
                  cost_bp: float = COST_BP, log: bool = True, placebo: int = 0, seed: int = 9) -> dict:
    """Portfolio metrics of a weight series against buy-and-hold on the SAME window."""
    r, wd, wo, mask = port_returns(w, D, asset, cost_bp, delay)
    if mask.sum() < 250:
        return {}
    rr, rf = r[mask], D["rf"][mask]
    bh = ((1.0 + D[f"{asset}_on"]) * (1.0 + D[f"{asset}_id"]) - 1.0)[mask]
    p, b = perf(rr, rf), perf(bh, rf)
    wdm, wom = wd[mask], wo[mask]
    exb = bh - rf
    tim = float(wdm.mean())
    # timing alpha: excess return of the rule minus a static mix with the same average exposure
    a = (rr - rf) - tim * exb
    alpha_t = a.mean() / nw_se(a, 10)
    out = {"asset": asset, "start": None, "cagr": r1(100 * p["cagr"], 2), "vol": r1(100 * p["vol"], 2),
           "sharpe": r1(p["sharpe"], 3), "maxdd": r1(100 * p["maxdd"], 1), "time_in": r1(100 * tim, 1),
           "switches": int((np.abs(wdm - wom) > 1e-9).sum()), "turnover": r1(float(np.abs(wdm - wom).sum()), 1),
           "bh_cagr": r1(100 * b["cagr"], 2), "bh_vol": r1(100 * b["vol"], 2), "bh_sharpe": r1(b["sharpe"], 3),
           "bh_maxdd": r1(100 * b["maxdd"], 1), "d_sharpe": r1(p["sharpe"] - b["sharpe"], 3),
           "alpha_ann": r1(100 * ANN * a.mean(), 2), "alpha_t": r1(alpha_t, 2), "years": r1(p["years"], 1)}
    # what the rule holds vs what it skips, on the segments it can actually trade (overnight segment
    # with the weight carried in, session with the weight set at the open). Per unit of exposure-time.
    on_m, id_m = D[f"{asset}_on"][mask], D[f"{asset}_id"][mask]
    wmax = float(np.nanmax(wdm))
    if 0.02 < tim < 0.98 and wmax <= 1.0 + 1e-9:
        held = wom * on_m + wdm * id_m - wdm * rf
        skipped = (1.0 - wom) * on_m + (1.0 - wdm) * id_m - (1.0 - wdm) * rf
        u = skipped / (1.0 - tim) - held / tim
        inn, outd = wdm > 0.5, wdm <= 0.5
        out.update({"in_ret_ann": r1(100 * ANN * held.mean() / tim, 1), "out_ret_ann": r1(100 * ANN * skipped.mean() / (1.0 - tim), 1),
                    "out_minus_in_t": r1(u.mean() / nw_se(u, 5), 2),
                    "in_vol": r1(100 * held[inn].std() * np.sqrt(ANN), 1) if inn.sum() > 20 else None,
                    "out_vol": r1(100 * skipped[outd].std() * np.sqrt(ANN), 1) if outd.sum() > 20 else None})
    if placebo:
        # circular-shift placebo: the same weight path moved in time (keeps time-in and run lengths)
        rng = np.random.default_rng(seed)
        idx = np.flatnonzero(mask)
        n = len(idx)
        w_in = np.where(np.isfinite(w), w, 0.0)[idx]
        sh, dd_, cg = [], [], []
        Dm = {k: D[k][idx] for k in (f"{asset}_on", f"{asset}_id", "rf")}
        Dm["rows"] = np.ones(n, bool)
        for k in rng.integers(63, n - 63, size=placebo):
            wr = np.roll(w_in, int(k))
            r2, _, _, m2 = port_returns(wr, Dm, asset, cost_bp, 0)
            q = perf(r2[m2], Dm["rf"][m2])
            sh.append(q["sharpe"]); dd_.append(q["maxdd"]); cg.append(q["cagr"])
        sh, dd_, cg = np.array(sh), np.array(dd_), np.array(cg)
        out["placebo"] = {"n": placebo, "sharpe_med": r1(np.median(sh), 3), "sharpe_pctile": r1(100 * (sh < p["sharpe"]).mean(), 1),
                          "cagr_med": r1(100 * np.median(cg), 2), "cagr_pctile": r1(100 * (cg < p["cagr"]).mean(), 1),
                          "maxdd_med": r1(100 * np.median(dd_), 1), "maxdd_pctile": r1(100 * (dd_ < p["maxdd"]).mean(), 1)}
    variant(f"R:{rid}", definition)
    if log:
        prm = {"asset": asset, "delay": delay, "cost_bp": cost_bp}
        LOG(f"port.{rid}", "port", f"{definition} | hold {asset}", "sharpe", p["sharpe"], n=int(mask.sum()), params=prm)
        LOG(f"port.{rid}", "port", f"{definition} | hold {asset}", "cagr_pct", 100 * p["cagr"], params=prm)
        LOG(f"port.{rid}", "port", f"{definition} | hold {asset}", "maxdd_pct", 100 * p["maxdd"], params=prm)
        LOG(f"port.{rid}", "port", f"{definition} | hold {asset}", "timing_alpha_ann_pct", 100 * ANN * a.mean(), t=alpha_t, params=prm)
    return out


def show_ports(tab: dict, title: str) -> None:
    print(f"\n{title}")
    print(f"{'rule':>22s} {'CAGR':>6s} {'vol':>5s} {'Shrp':>5s} {'maxDD':>6s} {'in%':>5s} {'sw':>4s} | {'BH: CAGR':>8s} {'Shrp':>5s} {'maxDD':>6s}"
          f" | {'dShrp':>6s} {'alpha%/y(t)':>12s} | {'ret in/out %/y (t)':>20s} {'vol in/out':>11s} {'yrs':>4s}")
    for name, p in tab.items():
        if not p:
            print(f"{name:>22s}  (window too short)")
            continue
        io = "" if "in_ret_ann" not in p else f"{p['in_ret_ann']:+6.1f}/{p['out_ret_ann']:+6.1f} ({(p['out_minus_in_t'] or 0):+4.1f})"
        vio = "" if p.get("in_vol") is None or p.get("out_vol") is None else f"{p['in_vol']:4.1f}/{p['out_vol']:4.1f}"
        print(f"{name:>22s} {p['cagr']:6.2f} {p['vol']:5.1f} {p['sharpe']:5.2f} {p['maxdd']:6.1f} {p['time_in']:5.1f} {p['switches']:4d} |"
              f" {p['bh_cagr']:8.2f} {p['bh_sharpe']:5.2f} {p['bh_maxdd']:6.1f} | {p['d_sharpe']:+6.2f} {p['alpha_ann']:+6.2f}({p['alpha_t']:+4.1f})"
              f" | {io:>20s} {vio:>11s} {p['years']:4.1f}")


# ============================================================================== rule builders
def monthly_hold(cond_cal: np.ndarray, valid: np.ndarray, month_end: np.ndarray) -> np.ndarray:
    """State sampled on the last bar of each month and held until the next month end (on the calendar)."""
    x = np.where(month_end & valid, cond_cal.astype(float), np.nan)
    return ffill1(x)


def hysteresis(x: np.ndarray, up: float, dn: float) -> np.ndarray:
    """1 after x > up, 0 after x < dn, previous state in between (x on any index; NaN keeps state)."""
    out = np.full(len(x), np.nan)
    s = np.nan
    for i, v in enumerate(x):
        if np.isfinite(v):
            if v > up:
                s = 1.0
            elif v < dn:
                s = 0.0
            elif not np.isfinite(s):
                s = 1.0 if v > 0.5 * (up + dn) else 0.0
        out[i] = s
    return out


def confirm(state: np.ndarray, n: int) -> np.ndarray:
    """Switch only after the raw state has held its new value for n consecutive bars."""
    out = np.full(len(state), np.nan)
    s, run, last = np.nan, 0, np.nan
    for i, v in enumerate(state):
        if not np.isfinite(v):
            out[i] = s
            continue
        run = run + 1 if v == last else 1
        last = v
        if not np.isfinite(s) or (v != s and run >= n):
            s = v
        out[i] = s
    return out


def vol_target(volf_ann: np.ndarray, target: float, cap: float, band: float = 0.10) -> np.ndarray:
    """w = min(cap, target / forecast); the held weight moves only when it is more than `band` away."""
    out = np.full(len(volf_ann), np.nan)
    cur = np.nan
    for i, v in enumerate(volf_ann):
        if np.isfinite(v) and v > 0:
            tgt = min(cap, target / v)
            if not np.isfinite(cur) or abs(tgt - cur) > band:
                cur = tgt
        out[i] = cur
    return out


def _and(a, b):
    return np.where(np.isfinite(a) & np.isfinite(b), ((a > 0.5) & (b > 0.5)).astype(float), np.nan)


def _or(a, b):
    return np.where(np.isfinite(a) & np.isfinite(b), ((a > 0.5) | (b > 0.5)).astype(float), np.nan)


def _not(a):
    return np.where(np.isfinite(a), 1.0 - a, np.nan)


def held_n(sig: np.ndarray, n: int) -> np.ndarray:
    """1 if the 0/1/NaN signal was 1 on any of the last n bars (a position opened at the next open
    after a signal and kept n sessions)."""
    return np.where(np.isfinite(sig), (highest(np.nan_to_num(sig), n) > 0.5).astype(float), np.nan) if n > 1 else sig


def build_rules(M: Market, F: dict, B: dict, ST: dict, hi: int) -> dict:
    """PASS 2 rules. Returns {group: {name: (weight on panel rows [0:hi], definition)}}."""
    Pn = lambda x: M.to_panel(x)[:hi]
    fin = np.isfinite
    c, s200 = F["c"], F["sma200"]
    T = lambda n: ST[n]["on"]
    R: dict = {}

    # ---- A. classic baselines (daily, weekly and monthly decision frequency)
    A = {}
    A["T200 daily"] = (T("T200"), "daily: close > SMA200")
    A["GX 50/200"] = (T("GX"), "daily: SMA50 > SMA200")

    def sampled(flag, cond, valid):
        idx = np.flatnonzero(flag)
        x = np.full(len(c), np.nan)
        x[idx] = np.where(valid, cond.astype(float), np.nan)
        return Pn(ffill1(x))

    me = F["month_end"]
    mi = np.flatnonzero(me)
    cm = c[mi]
    s10 = sma(cm, 10)
    A["T10M (Faber)"] = (sampled(me, cm > s10, fin(s10)), "month-end close > 10-month SMA of month-end closes; held one month")
    A["T200 @month-end"] = (sampled(me, cm > s200[mi], fin(s200[mi])), "daily SMA200 rule checked on the last bar of the month only")
    p12 = shift(cm, 12)
    A["M12 monthly"] = (sampled(me, cm > p12, fin(p12)), "month-end: 12-month price return > 0; held one month")
    bill12 = sma(F["irx"][mi], 12) / 100.0
    A["DualMom abs leg"] = (sampled(me, cm / p12 - 1.0 > bill12, fin(p12) & fin(bill12)),
                            "month-end: 12-month return > 12-month average 13-week bill yield (absolute leg of dual momentum); held one month")
    p6 = shift(cm, 6)
    A["M6 monthly"] = (sampled(me, cm > p6, fin(p6)), "month-end: 6-month price return > 0; held one month")
    iso = M.cal.isocalendar()
    wk = iso.week.to_numpy()
    we = np.r_[wk[1:] != wk[:-1], True]
    wi = np.flatnonzero(we)
    cw = c[wi]
    s40 = sma(cw, 40)
    A["W40 weekly"] = (sampled(we, cw > s40, fin(s40)), "week-end close > 40-week SMA of week-end closes; held one week")
    A["T200 @week-end"] = (sampled(we, cw > s200[wi], fin(s200[wi])), "daily SMA200 rule checked on the last bar of the week only")
    R["A_baselines"] = A

    # ---- B. hysteresis, confirmation, neighbours of the trend rule
    Bh = {}
    x = c / s200 - 1.0
    for b in (0.01, 0.02, 0.03, 0.05):
        Bh[f"T200 band {int(b * 100)}%"] = (Pn(hysteresis(x, b, -b)), f"in after close > SMA200*(1+{b}), out after close < SMA200*(1-{b})")
    Bh["T200 exit-3% in0"] = (Pn(hysteresis(x, 0.0, -0.03)), "in after close > SMA200, out only after close < 0.97*SMA200")
    Bh["T200 exit0 in+3%"] = (Pn(hysteresis(x, 0.03, 0.0)), "in only after close > 1.03*SMA200, out after close < SMA200")
    t200c = np.where(fin(s200), (c > s200).astype(float), np.nan)
    for n in (3, 5, 10):
        Bh[f"T200 confirm {n}d"] = (Pn(confirm(t200c, n)), f"close > SMA200, switch only after {n} consecutive bars on the new side")
    for n in (150, 250):
        xs_ = c / F[f"sma{n}"] - 1.0
        Bh[f"T{n} band 2%"] = (Pn(hysteresis(xs_, 0.02, -0.02)), f"SMA{n} with a +/-2% band")
    gx = F["sma50"] / s200 - 1.0
    Bh["GX band 1%"] = (Pn(hysteresis(gx, 0.01, -0.01)), "SMA50/SMA200 with a +/-1% band")
    for a_, b_ in ((20, 200), (50, 150), (100, 200), (50, 250)):
        v = F[f"sma{b_}"]
        Bh[f"GX {a_}/{b_}"] = (Pn(np.where(fin(v), (F[f"sma{a_}"] > v).astype(float), np.nan)), f"SMA{a_} > SMA{b_}")
    for k in (10, 40, 60):
        v = shift(s200, k)
        Bh[f"SL200 over {k}"] = (Pn(np.where(fin(v), (s200 > v).astype(float), np.nan)), f"SMA200 > SMA200[{k}]")
    R["B_trend_variants"] = Bh

    # ---- C. volatility-scaled exposure
    C = {}
    for tgt in (0.10, 0.12, 0.15):
        for cap in (1.0, 1.5, 2.0):
            C[f"VT {int(tgt * 100)}% cap{cap}"] = (Pn(vol_target(F["volf20"], tgt, cap)),
                                                 f"w = min({cap}, {tgt}/EWMA20 vol forecast), rebalance when off by > 0.10")
    for sp in (10, 60):
        for cap in (1.0, 1.5):
            C[f"VT 12% cap{cap} span{sp}"] = (Pn(vol_target(F[f"volf{sp}"], 0.12, cap)), f"same with EWMA span {sp}")
    for band in (0.0, 0.25):
        C[f"VT 12% cap1.0 band{band}"] = (Pn(vol_target(F["volf20"], 0.12, 1.0, band)), f"same, rebalance band {band}")
    C["VT 12% cap1.0 rv20"] = (Pn(vol_target(F["rv20"], 0.12, 1.0)), "w = min(1, 0.12 / 20-bar stdev)")
    C["VT 12% cap1.0 rv60"] = (Pn(vol_target(F["rv60"], 0.12, 1.0)), "w = min(1, 0.12 / 60-bar stdev)")
    for cap in (1.0, 1.5):
        C[f"VT VIX 15% cap{cap}"] = (Pn(vol_target(F["vix"] / 100.0, 0.15, cap)), f"w = min({cap}, 0.15 / (VIX/100))")
    C["VT var 12% cap1.0"] = (Pn(vol_target(F["volf20"] ** 2 / 0.12, 0.12, 1.0)), "w = min(1, (0.12/vol)^2)  (inverse variance)")
    C["VT var 12% cap1.5"] = (Pn(vol_target(F["volf20"] ** 2 / 0.12, 0.12, 1.5)), "w = min(1.5, (0.12/vol)^2)")
    R["C_vol_target"] = C

    # ---- D. combinations
    Dd = {}
    vt12 = C["VT 12% cap1.0"][0]
    Dd["T200 & VTS<1"] = (_and(T("T200"), T("VTS<1.00")), "close > SMA200 AND VIX < VIX3M")
    Dd["T200 | VTS<1"] = (_or(T("T200"), T("VTS<1.00")), "close > SMA200 OR VIX < VIX3M")
    Dd["out: <200 & VIX>=25"] = (_or(T("T200"), T("VIX<25")), "out only when close <= SMA200 AND VIX >= 25")
    Dd["out: <200 & VIX>=20"] = (_or(T("T200"), T("VIX<20")), "out only when close <= SMA200 AND VIX >= 20")
    Dd["out: <200 & RV20>=20"] = (_or(T("T200"), T("RV20<20")), "out only when close <= SMA200 AND 20-bar realised vol >= 20%")
    Dd["out: <200 & B50<40"] = (_or(T("T200"), _not(T("B50>40"))), "out only when close <= SMA200 AND breadth(50) >= 40 fails... see def")
    Dd["out: <200 & B50<40"] = (_or(T("T200"), T("B50>40")), "out only when close <= SMA200 AND share above SMA50 <= 40%")
    Dd["out: <200 & SL200dn"] = (T("T200orSL"), "out only when close <= SMA200 AND SMA200 falling over 20 bars")
    Dd["out: <200 & M252<0"] = (_or(T("T200"), T("M252")), "out only when close <= SMA200 AND 252-bar return <= 0")
    Dd["out: GXdn & SL200dn"] = (_or(T("GX"), T("SL200")), "out only when SMA50 <= SMA200 AND SMA200 falling")
    v3 = T("T200") + T("M252") + T("GX")
    Dd["vote2of3 T200/M252/GX"] = (np.where(fin(v3), (v3 >= 2).astype(float), np.nan), "at least two of: close>SMA200, 252-bar return>0, SMA50>SMA200")
    sc = (T("T200") + T("VIX<25") + T("B50>40")) / 3.0
    Dd["score T200+VIX25+B50"] = (sc, "w = share true of: close>SMA200, VIX<25, share above SMA50 > 40%")
    Dd["half T200"] = (0.5 + 0.5 * T("T200"), "w = 1 above SMA200, 0.5 below")
    Dd["half T200orSL"] = (0.5 + 0.5 * T("T200orSL"), "w = 0.5 only when close <= SMA200 and SMA200 falling, else 1")
    Dd["T200 x VT12"] = (T("T200") * vt12, "close > SMA200, sized min(1, 0.12/vol)")
    Dd["T200orSL x VT12"] = (T("T200orSL") * vt12, "(close > SMA200 or SMA200 rising), sized min(1, 0.12/vol)")
    Dd["GX x VT12"] = (T("GX") * vt12, "SMA50 > SMA200, sized min(1, 0.12/vol)")
    Dd["max(T200orSL, VT12/2)"] = (np.maximum(T("T200orSL"), 0.5 * vt12), "full size in the slow uptrend, otherwise half of the vol-target size")
    rs = np.where(fin(F["rsi2"]), (F["rsi2"] < 10).astype(float), np.nan)
    Dd["T200 or dip5"] = (_or(T("T200"), Pn(held_n(rs, 5))), "close > SMA200, OR within 5 bars of SPY RSI(2) < 10")
    Dd["T200orSL or dip5"] = (_or(T("T200orSL"), Pn(held_n(rs, 5))), "slow uptrend, OR within 5 bars of SPY RSI(2) < 10")
    R["D_combinations"] = Dd

    # ---- E. the market-dip dial: in for n sessions after a market-level dip signal
    Ee = {}
    sigs = {
        "mZ5<-1": (F["z5"] <= -1.0, fin(F["z5"]), "SPY 5-bar return <= -1 sigma"),
        "mZ5<-1.5": (F["z5"] <= -1.5, fin(F["z5"]), "SPY 5-bar return <= -1.5 sigma"),
        "mZ5<-2": (F["z5"] <= -2.0, fin(F["z5"]), "SPY 5-bar return <= -2 sigma"),
        "mZ10<-1": (F["z10"] <= -1.0, fin(F["z10"]), "SPY 10-bar return <= -1 sigma"),
        "mRSI2<10": (F["rsi2"] < 10, fin(F["rsi2"]), "SPY RSI(2) < 10"),
        "mRSI2<5": (F["rsi2"] < 5, fin(F["rsi2"]), "SPY RSI(2) < 5"),
        "mRSI2<20": (F["rsi2"] < 20, fin(F["rsi2"]), "SPY RSI(2) < 20"),
        "mDown3": ((F["r"] < 0) & (shift(F["r"], 1) < 0) & (shift(F["r"], 2) < 0), fin(shift(F["r"], 2)), "SPY down 3 closes in a row"),
        "mBBlow": (c < F["bb_low"], fin(F["bb_low"]), "SPY close < lower Bollinger(20,2)"),
        "mROC5<-3%": (c / shift(c, 5) - 1.0 <= -0.03, fin(shift(c, 5)), "SPY 5-bar return <= -3%"),
    }
    sig_cal = {}
    for nm, (cond, valid, d) in sigs.items():
        sg = np.where(valid, cond.astype(float), np.nan)
        sig_cal[nm] = sg
        for n in (1, 3, 5, 10):
            if nm not in ("mZ5<-1", "mRSI2<10", "mDown3") and n not in (5,):
                continue
            Ee[f"{nm} hold{n}"] = (Pn(held_n(sg, n)), f"in SPY for {n} session(s) after [{d}], else cash")
    R["E_dip_dial"] = Ee
    # overlays on buy and hold
    Ov = {}
    for nm in ("mZ5<-1", "mRSI2<10"):
        h5 = Pn(held_n(sig_cal[nm], 5))
        Ov[f"0.5 + 0.5 x {nm} hold5"] = (0.5 + 0.5 * h5, f"half invested, full for 5 sessions after [{sigs[nm][2]}]")
        Ov[f"1 + 0.5 x {nm} hold5"] = (1.0 + 0.5 * h5, f"fully invested, 150% for 5 sessions after [{sigs[nm][2]}] (leverage)")
        Ov[f"{nm} hold5 & T200"] = (_and(h5, T("T200")), f"5 sessions after [{sigs[nm][2]}], only if close > SMA200")
        Ov[f"{nm} hold5 & notT200"] = (_and(h5, _not(T("T200"))), f"5 sessions after [{sigs[nm][2]}], only if close <= SMA200")
    up = np.where(fin(F["z5"]), (F["z5"] >= 1.0).astype(float), np.nan)
    Ov["BH minus 1d after mZ5>1"] = (_not(Pn(up)), "invested except the session after SPY 5-bar return >= +1 sigma")
    Ov["BH minus 5d after mZ5>1"] = (_not(Pn(held_n(up, 5))), "invested except 5 sessions after SPY 5-bar return >= +1 sigma")
    R["F_dip_overlays"] = Ov
    return R


def by_year(w: np.ndarray, D: dict, dates: np.ndarray, asset: str = "spy", delay: int = 0) -> dict:
    r, wd, wo, mask = port_returns(w, D, asset, COST_BP, delay)
    bh = (1.0 + D[f"{asset}_on"]) * (1.0 + D[f"{asset}_id"]) - 1.0
    yrs = dates.astype("datetime64[Y]").astype(int) + 1970
    out = {}
    for y in np.unique(yrs[mask]):
        m = mask & (yrs == y)
        if m.sum() < 60:
            continue
        e1, e0 = np.cumprod(1 + r[m]), np.cumprod(1 + bh[m])
        out[int(y)] = {"rule": r1(100 * (e1[-1] - 1), 1), "bh": r1(100 * (e0[-1] - 1), 1),
                       "rule_dd": r1(100 * (e1 / np.maximum.accumulate(e1) - 1).min(), 1),
                       "bh_dd": r1(100 * (e0 / np.maximum.accumulate(e0) - 1).min(), 1), "in": r1(100 * wd[m].mean(), 0)}
    return out


# ============================================================================== stock level
def stock_by_regime(S: Study, M: Market, F: dict, B: dict, ST: dict, hi: int) -> dict:
    """Do the E01 single-stock effects (moderate dip, 3-sigma shock, up-move) differ by market regime?
    XS = signal minus the universe on the same day (stock-specific part); raw = plain mean of signals."""
    Tn = S.P.c.shape[0]

    def full(x):
        out = np.full(Tn, np.nan)
        out[:hi] = x
        return out

    Pn = lambda k: full(M.to_panel(F[k])[:hi])
    t200, vix, b50, z5m, vts, dd = full(ST["T200"]["on"]), Pn("vix"), full(B["b50"]), Pn("z5"), Pn("vts"), Pn("dd252")
    rv = Pn("rv20")
    reg = {
        "ALL": np.ones(Tn, bool),
        "SPY>SMA200": t200 == 1, "SPY<=SMA200": t200 == 0,
        "VIX<15": vix < 15, "VIX 15-20": (vix >= 15) & (vix < 20), "VIX 20-30": (vix >= 20) & (vix < 30), "VIX>=30": vix >= 30,
        "B50<40": b50 < 40, "B50 40-60": (b50 >= 40) & (b50 < 60), "B50>=60": b50 >= 60,
        "mkt z5<=-1": z5m <= -1, "mkt z5 -1..1": (z5m > -1) & (z5m < 1), "mkt z5>=1": z5m >= 1,
        "VTS<1": vts < 1, "VTS>=1": vts >= 1,
        "DD<5%": dd > -0.05, "DD>=10%": dd <= -0.10,
        "RV20<15%": rv < 0.15, "RV20>=25%": rv >= 0.25,
    }
    z1, z3, z5 = S.z(1), S.z(3), S.z(5)
    eff = {
        "dip3": ((z3 > -2) & (z3 <= -1), "stock 3-bar return in (-2,-1] sigma"),
        "dip5": ((z5 > -2) & (z5 <= -1), "stock 5-bar return in (-2,-1] sigma"),
        "shock1": (z1 <= -3, "stock 1-bar return <= -3 sigma"),
        "up3": ((z3 > 1) & (z3 <= 2), "stock 3-bar return in (1,2] sigma"),
        "up5": ((z5 > 1) & (z5 <= 2), "stock 5-bar return in (1,2] sigma"),
    }
    out = {}
    for e, (sig, d) in eff.items():
        out[e] = {}
        variant(f"X:{e}", f"{d}, by 19 market regimes")
        for rn, rm in reg.items():
            s = sig & rm[:, None]
            if (s & S.uni).sum() < 300:
                continue
            out[e][rn] = S.event(f"F09.stock.{e}", "F09_stock", f"{d} | market regime {rn}", s, hs=HS, params={"regime": rn})
    return out, reg


def show_stock(tab: dict, title: str) -> None:
    print(f"\n{title}")
    print(f"{'regime':>14s}" + "".join(f"{'h=' + str(h) + ': XS bp(t)  raw bp':>28s}" for h in HS) + "    events")
    for rn, row in tab.items():
        line = f"{rn:>14s}"
        for h in HS:
            c = row[h]
            xs = "" if c["xs_bp"] is None else f"{c['xs_bp']:+7.1f}({c['xs_t']:+5.1f})"
            raw = "" if c["raw_bp"] is None else f"{c['raw_bp']:+8.1f}"
            line += f"{xs:>18s}{raw:>10s}"
        print(line + f"  {row[HS[0]]['events']:>8d}")


def trades_by_regime(S: Study, reg: dict, hi: int) -> dict:
    """A generic long swing trade (2-ATR stop, 10-bar time exit, 5 bp per side) by the regime on the
    signal day: (a) random entries (2% of universe-days, fixed seed), (b) moderate 3-bar dips."""
    from research.swinglab import trades as TR
    atr = S.atr(14)
    rng = np.random.default_rng(909)
    rnd = S.uni & (rng.random(S.uni.shape) < 0.02)
    z3 = S.z(3)
    dip = S.uni & (z3 > -2) & (z3 <= -1)
    out = {}
    for nm, sig, d in (("random", rnd, "random 2% of universe-days"), ("dip3", dip, "stock 3-bar return in (-2,-1] sigma")):
        tr = S.trades(sig, atr=atr, stop_k=2.0, max_hold=10, cost_bp=5.0)
        variant(f"TR:{nm}", f"trades: {d}; stop 2 ATR, 10-bar time exit; by regime of the signal day")
        out[nm] = {}
        sday = tr["entry"].to_numpy() - 1
        for rn, rm in reg.items():
            sub = tr[rm[sday]]
            sm = TR.summarize(sub, len(S.dates))
            if "ret_bp" not in sm:
                continue
            sm["stop_share"] = round(sm["exit_mix"].get("stop", 0) + sm["exit_mix"].get("gap_stop", 0), 3)
            out[nm][rn] = sm
            LOG(f"trade.{nm}", "stock", f"{d}; stop 2 ATR, hold<=10 | regime {rn}", "net_ret_bp", sm["ret_bp"], t=sm["ret_t"],
                n=sm["trades"], params={"regime": rn})
            LOG(f"trade.{nm}", "stock", f"{d}; stop 2 ATR, hold<=10 | regime {rn}", "R", sm["R"], t=sm["R_t"], n=sm["trades"],
                params={"regime": rn})
    return out


def show_trades(tab: dict, title: str) -> None:
    print(f"\n{title}")
    print(f"{'regime':>14s} {'trades':>8s} {'net bp (t)':>16s} {'R (t)':>16s} {'win':>6s} {'stopped':>8s} {'bars':>5s}")
    for rn, s in tab.items():
        print(f"{rn:>14s} {s['trades']:8d} {s['ret_bp']:+8.1f}({s['ret_t']:+5.1f}) {s['R']:+8.3f}({s['R_t']:+5.1f}) {s['win']:6.3f} "
              f"{s['stop_share']:8.3f} {s['bars']:5.1f}")


# ============================================================================== one sample
def run(sample: str) -> dict:
    global SAMPLE
    SAMPLE = sample
    t0 = time.time()
    S = Study(sample)
    hi = S._last_row + 1                       # nothing at or after this row index + 0 is read below
    rows = S.rows[:hi]
    M = Market(S)
    F = build_features(S, M)
    B = build_breadth(S, hi)
    ST = build_states(S, M, F, B, hi)
    O = build_outcomes(S, hi)
    D = daily_series(S, M, F, hi)
    res = {"sample": sample, "dates": [str(S.dates[:hi][rows][0]), str(S.dates[:hi][rows][-1])]}
    print(f"\n{'=' * 150}\n{sample} {res['dates'][0]}..{res['dates'][1]}   ({len(ST)} boolean states)   build {time.time() - t0:.0f}s")

    # ---------------- unconditional
    base = {}
    for k in [f"{t}{h}" for t in ("spy", "ew") for h in HS] + ["rv_next20", "loss5", "path5", "ewloss5"]:
        y = O[k]
        base[k] = r1((1e4 if k[-1].isdigit() and k[:2] in ("sp", "ew") and "loss" not in k else 100.0) * np.nanmean(y), 2)
    res["unconditional"] = base
    print("unconditional: " + "  ".join(f"{k}={v}" for k, v in base.items()))

    # ---------------- PASS 1a: forward map of every boolean state
    res["map"] = {name: map_state(name, st, O, rows) for name, st in ST.items()}
    for g in ("trend", "momentum", "drawdown", "vol", "credit", "rates", "xasset", "breadth", "dip"):
        show_map({k: v for k, v in res["map"].items() if v["group"] == g}, f"[{sample}] MAP {g}: in-state vs out-of-state, bp from next open (NW t)")

    # ---------------- PASS 1b: bucket maps of continuous features
    P = lambda k: M.to_panel(F[k])[:hi]
    bk = {
        "vix": (P("vix"), (0, 12, 15, 20, 25, 30, 40, 100)),
        "vix_pctrank252": (P("vixpr"), (-1, 20, 40, 60, 80, 90, 100)),
        "vix/vix3m": (P("vts"), (0, 0.85, 0.90, 0.95, 1.0, 1.05, 2)),
        "vix_5d_change": (P("dvix5"), (-1, -0.2, -0.1, 0, 0.1, 0.2, 0.4, 5)),
        "rv20": (P("rv20"), (0, 0.08, 0.12, 0.16, 0.20, 0.30, 2)),
        "dd_from_252d_high": (P("dd252"), (-1, -0.20, -0.10, -0.05, -0.02, -0.0001, 0.01)),
        "close/sma200-1": (P("ext200"), (-1, -0.10, -0.05, 0, 0.05, 0.10, 1)),
        "roc252": (P("roc252"), (-1, -0.10, 0, 0.10, 0.20, 2)),
        "spy_z5": (P("z5"), (-50, -2, -1, 0, 1, 2, 50)),
        "spy_rsi2": (P("rsi2"), (-1, 5, 10, 30, 70, 90, 95, 101)),
        "breadth_above50": (B["b50"], (-1, 20, 30, 40, 50, 60, 70, 80, 101)),
        "breadth_above200": (B["b200"], (-1, 30, 40, 50, 60, 70, 101)),
        "yield_curve_10y-3m": (P("yc"), (-5, 0, 1, 2, 3, 6)),
    }
    res["buckets"] = {}
    for name, (x, edges) in bk.items():
        res["buckets"][name] = bucket_map(name, x, edges, O, rows)
        show_buckets(res["buckets"][name], f"[{sample}] BUCKETS {name}")

    # ---------------- PASS 1c: every boolean state as an exposure rule on SPY (and EW)
    res["ports_spy"], res["ports_ew"] = {}, {}
    ones = np.ones(hi)
    res["ports_spy"]["BUY&HOLD"] = evaluate_rule("BH", "always invested", ones, D, "spy")
    res["ports_ew"]["BUY&HOLD"] = evaluate_rule("BH", "always invested", ones, D, "ew")
    for name, st in ST.items():
        res["ports_spy"][name] = evaluate_rule(f"S.{name}", f"invested when [{st['def']}]", st["on"], D, "spy")
        res["ports_ew"][name] = evaluate_rule(f"S.{name}", f"invested when [{st['def']}]", st["on"], D, "ew")
    show_ports(res["ports_spy"], f"[{sample}] PORTFOLIOS on SPY: invested only when the state is 1 (next open, 5 bp/switch, cash earns T-bill)")
    show_ports(res["ports_ew"], f"[{sample}] PORTFOLIOS on the EQUAL-WEIGHT universe (levels survivor-inflated in CTX)")

    # ---------------- PASS 2: baselines, hysteresis, vol targeting, combinations, the dip dial
    RULES = build_rules(M, F, B, ST, hi)
    res["rules_spy"], res["rules_ew"] = {}, {}
    for grp, rules in RULES.items():
        res["rules_spy"][grp] = {"BUY&HOLD": res["ports_spy"]["BUY&HOLD"]}
        res["rules_ew"][grp] = {"BUY&HOLD": res["ports_ew"]["BUY&HOLD"]}
        for name, (w, d) in rules.items():
            res["rules_spy"][grp][name] = evaluate_rule(f"{grp[0]}.{name}", d, w, D, "spy")
            res["rules_ew"][grp][name] = evaluate_rule(f"{grp[0]}.{name}", d, w, D, "ew")
        show_ports(res["rules_spy"][grp], f"[{sample}] PASS 2 {grp} on SPY")
        show_ports(res["rules_ew"][grp], f"[{sample}] PASS 2 {grp} on the EQUAL-WEIGHT universe")

    # ---------------- PASS 2b: do the E01 stock-level effects differ by regime?
    res["stock"], reg = stock_by_regime(S, M, F, B, ST, hi)
    for e, tab in res["stock"].items():
        show_stock(tab, f"[{sample}] STOCK-LEVEL effect '{e}' by market regime (XS = vs universe same day; raw = plain mean)")
    res["trades"] = trades_by_regime(S, reg, hi)
    for nm, tab in res["trades"].items():
        show_trades(tab, f"[{sample}] GENERIC SWING TRADE '{nm}' (2-ATR stop, 10-bar exit, net of 10 bp) by regime on the signal day")

    res["variants"] = dict(VARIANTS)
    del S
    gc.collect()
    print(f"[{sample}] done in {time.time() - t0:.0f}s")
    return res, (M, F, B, ST, O, D)


def main(argv):
    out = Path(__file__).resolve().parents[1] / "results"
    out.mkdir(exist_ok=True)
    allres = {}
    for sample in (argv or ["DEV", "CTX"]):
        res, keep = run(sample)
        allres[sample] = res
        del keep
        gc.collect()
    allres["n_variants"] = len(VARIANTS)
    allres["variants"] = dict(VARIANTS)
    name = "f09_regime.json" if not argv or len(argv) == 2 else f"f09_regime_{argv[0]}.json"
    (out / name).write_text(json.dumps(allres, indent=0))
    print(f"\n{len(VARIANTS)} distinct variants evaluated; results -> {out / name}")


if __name__ == "__main__":
    main(sys.argv[1:])
