"""F03 - What to hold: momentum, 52-week high, trend quality (selection features).

Run:  cd swing-lab && python -m research.experiments.f03_momentum_selection [DEV] [CTX] [--pass1-only]

Development data only (protocol section 2):
    DEV  2011-01..2018-06, liquid US stocks alive in 2018 (252-bar features exist from 2012-01)
    CTX  1998-01..2010-12, survivors of 2026 only (strongly biased; two bear markets)
Every feature is known at the close of bar t and is computable in Pine from the chart's OHLCV plus
SPY through request.security. Every outcome is a total return from the OPEN of t+1 to the close of
t+h, h in 5, 10, 20, 40, 60 (Study.fwd). Inference is by date, Newey-West with 2h lags.

Two views per cell (same definitions as Study.event; the fast evaluator below is asserted equal
to Study.event on spot cells at the start of every run):
    XS  group mean minus the mean of the control (universe, or the stated base) on the same day
    TS  event-weighted group mean minus the universe's sample average (includes market timing)

Passes
    1  MAP      every feature: absolute-threshold buckets (single chart) and daily cross-sectional
                quintiles (needs screener), for ALL / liquidity below, above $50M / SPY above, below
                its 200-day average.
    2  DRILL    the features that looked alive in pass 1: long side versus avoid side, volatility
                and beta controls, combined scores, turnover and costs, momentum-crash behaviour.
    3  KILL     halves A/B, by year, neighbouring parameters, one-bar delay, permutation placebo,
                trade simulation against date-matched random entries.

Every cell is written to registry/trials_f03.jsonl. Nothing here is evidence (protocol section 3).
"""
from __future__ import annotations

import os

os.environ["SWINGLAB_REGISTRY_TAG"] = "f03"

import gc
import json
import sys
import time
from pathlib import Path

import bottleneck as bn
import numpy as np
import pandas as pd

from research.swinglab import engine as E
from research.swinglab import pinelike as ta
from research.swinglab import trades as TR
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

HS = (5, 10, 20, 40, 60)
FAMILY = "F03_momentum_selection"
INF = float("inf")
VARIANTS: dict[str, str] = {}          # distinct signal variants evaluated: id -> definition


# =============================================================================== features
# name: (definition at the close of t, Pine recipe, absolute bucket edges (lo, hi] )
SPEC: dict[str, tuple[str, str, tuple]] = {
    # ---- momentum
    "mom252_21": ("ln(C[21]/C[252]): 12-month return skipping the last month",
                  "math.log(close[21]/close[252])", (-INF, -0.4, -0.2, 0.0, 0.2, 0.4, 0.7, INF)),
    "mom126_21": ("ln(C[21]/C[126]): 6-month return skipping the last month",
                  "math.log(close[21]/close[126])", (-INF, -0.3, -0.15, 0.0, 0.15, 0.3, INF)),
    "mom63_5": ("ln(C[5]/C[63]): 3-month return skipping the last week",
                "math.log(close[5]/close[63])", (-INF, -0.2, -0.1, 0.0, 0.1, 0.2, INF)),
    "mom252_0": ("ln(C/C[252]): 12-month return, no skip (neighbour)",
                 "math.log(close/close[252])", (-INF, -0.4, -0.2, 0.0, 0.2, 0.4, 0.7, INF)),
    "mom252_126": ("ln(C[126]/C[252]): months 12 to 7 only (Novy-Marx 'intermediate' momentum)",
                   "math.log(close[126]/close[252])", (-INF, -0.3, -0.15, 0.0, 0.15, 0.3, INF)),
    "zmom252_21": ("mom252_21 / (stdev(daily log ret, 252) * sqrt(231)): volatility-scaled 12-1",
                   "math.log(close[21]/close[252]) / (ta.stdev(math.log(close/close[1]),252)*math.sqrt(231))",
                   (-INF, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, INF)),
    "resmom252_21": ("mom252_21 minus beta252 * SPY's mom252_21 (beta-adjusted, 'residual' momentum)",
                     "m - beta*mSpy, beta = ta.correlation(r, rSpy, 252)*ta.stdev(r,252)/ta.stdev(rSpy,252)",
                     (-INF, -0.4, -0.2, 0.0, 0.2, 0.4, INF)),
    "accel": ("mom126_21 minus ln(C[126]/C[252]): recent half-year minus the half-year before",
              "math.log(close[21]/close[126]) - math.log(close[126]/close[252])",
              (-INF, -0.3, -0.1, 0.0, 0.1, 0.3, INF)),
    "posmonths12": ("number of the last 12 21-bar blocks with a positive return (consistency)",
                    "sum over k=0..11 of (close[21*k] > close[21*(k+1)] ? 1 : 0)", (-1, 4, 5, 6, 7, 8, 12)),
    # ---- 52-week high
    "hi252": ("C / highest(H, 252): closeness to the 52-week high",
              "close / ta.highest(high, 252)", (0.0, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 1.0)),
    "hi126": ("C / highest(H, 126) (neighbour)", "close / ta.highest(high, 126)",
              (0.0, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 1.0)),
    "hi252c": ("C / highest(C, 252): closeness to the highest close (neighbour)",
               "close / ta.highest(close, 252)", (0.0, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 1.0)),
    "barshi252": ("bars since the highest high of 252 bars",
                  "-ta.highestbars(high, 252)", (-1, 5, 21, 63, 126, 189, 252)),
    "nh63": ("number of bars in the last 63 on which H made a new 252-bar high",
             "math.sum(high >= ta.highest(high, 252) ? 1 : 0, 63)", (-1, 0, 2, 5, 10, 63)),
    "lo252": ("C / lowest(L, 252): distance above the 52-week low",
              "close / ta.lowest(low, 252)", (0.0, 1.1, 1.3, 1.6, 2.0, INF)),
    # ---- trend position
    "d200": ("ln(C / sma(C,200)) / (vol * sqrt(200)), vol = Study.vol (robust EWMA, span 20)",
             "math.log(close/ta.sma(close,200)) / (vol*math.sqrt(200))",
             (-INF, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, INF)),
    "ma50_200": ("sma(C,50) / sma(C,200) - 1", "ta.sma(close,50)/ta.sma(close,200) - 1",
                 (-INF, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2, INF)),
    "stack": ("trend template count: (C>sma50) + (sma50>sma150) + (sma150>sma200), 0..3",
              "(close>ta.sma(close,50)?1:0)+(ta.sma(close,50)>ta.sma(close,150)?1:0)+(ta.sma(close,150)>ta.sma(close,200)?1:0)",
              (-1, 0, 1, 2, 3)),
    "minervini": ("1 if C>sma50>sma150>sma200 and sma200>sma200[21] and C>=1.3*lowest(L,252) and "
                  "C>=0.75*highest(H,252), else 0", "the eight-line trend template", (-1, 0, 1)),
    "above50_126": ("share of the last 126 bars with C > sma(C,50)",
                    "ta.sma(close > ta.sma(close,50) ? 1 : 0, 126)", (-0.01, 0.2, 0.4, 0.6, 0.8, 1.0)),
    # ---- trend quality / smoothness
    "r2s63": ("signed R-squared of ln(C) on time over 63 bars (sign of the slope). The slope's "
              "t-statistic is a monotone transform, so it has the same quantiles",
              "r = ta.correlation(math.log(close), bar_index, 63); math.sign(r)*r*r",
              (-1.0, -0.6, -0.3, 0.0, 0.3, 0.6, 0.8, 1.0)),
    "r2s126": ("signed R-squared of ln(C) on time over 126 bars",
               "r = ta.correlation(math.log(close), bar_index, 126); math.sign(r)*r*r",
               (-1.0, -0.6, -0.3, 0.0, 0.3, 0.6, 0.8, 1.0)),
    "tstat126": ("t-statistic of the 126-bar log-price regression slope: r*sqrt(124/(1-r^2))",
                 "r*math.sqrt(124/(1-r*r))", (-INF, -15.0, -5.0, 0.0, 5.0, 15.0, 25.0, INF)),
    "slopeR2_126": ("annualised 126-bar regression slope of ln(C) times its R-squared (Clenow)",
                    "252*ta.linreg slope of math.log(close) over 126 * r*r",
                    (-INF, -0.3, -0.1, 0.0, 0.1, 0.3, 0.6, INF)),
    "id252": ("information discreteness: sign(mom252_21) * (share of down days - share of up days) "
              "over bars t-252..t-21; negative = smooth trend (Da, Gurun, Warachka 2014)",
              "math.sign(m)*(ta.sma(r<0?1:0,231)[21] - ta.sma(r>0?1:0,231)[21])",
              (-INF, -0.12, -0.08, -0.04, 0.0, 0.04, INF)),
    "sharpe126": ("ln(C/C[126]) / (stdev(daily log ret,126)*sqrt(126)): return per unit of volatility",
                  "math.log(close/close[126]) / (ta.stdev(r,126)*math.sqrt(126))",
                  (-INF, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, INF)),
    "sharpe252_21": ("mom252_21 / (stdev(daily log ret,231)[21]*sqrt(231)): 12-1 return per unit of volatility",
                     "math.log(close[21]/close[252]) / (ta.stdev(r,231)[21]*math.sqrt(231))",
                     (-INF, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, INF)),
    "er126": ("signed efficiency ratio: ln(C/C[126]) / sum(|daily log ret|, 126) (Kaufman)",
              "math.log(close/close[126]) / math.sum(math.abs(r), 126)",
              (-INF, -0.1, -0.05, 0.0, 0.05, 0.1, 0.2, INF)),
    "upfrac126": ("share of up days over 126 bars", "ta.sma(close>close[1]?1:0,126)",
                  (0.0, 0.46, 0.49, 0.52, 0.55, 1.0)),
    # ---- relative strength versus SPY (the daily quintiles of rsN equal those of the raw N-bar return)
    "rs63": ("ln(C/C[63]) - ln(SPY/SPY[63])", "math.log(close/close[63]) - math.log(spy/spy[63])",
             (-INF, -0.2, -0.1, 0.0, 0.1, 0.2, INF)),
    "rs126": ("ln(C/C[126]) - ln(SPY/SPY[126])", "math.log(close/close[126]) - math.log(spy/spy[126])",
              (-INF, -0.3, -0.15, 0.0, 0.15, 0.3, INF)),
    "rsline252": ("(C/SPY) / highest(C/SPY, 252): closeness of the relative-strength line to its 52-week high",
                  "rs = close/spy; rs/ta.highest(rs,252)", (0.0, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 1.0)),
    # ---- control variable (not a candidate): the smoothness measures are close to "low volatility"
    "vol126": ("stdev(daily log ret, 126) (control: low-volatility effect)", "ta.stdev(r,126)",
               (0.0, 0.01, 0.015, 0.02, 0.03, INF)),
}


class _Store(dict):
    """Keeps only the sample rows [a:b] of each feature (float64), to bound memory."""

    def __init__(self, a: int, b: int):
        super().__init__()
        self.a, self.b = a, b

    def __setitem__(self, k, v):
        v = np.asarray(v, dtype=np.float64)[self.a:self.b]
        super().__setitem__(k, np.where(np.isfinite(v), v, np.nan))


def build_features(S: Study, a: int, b: int) -> dict[str, np.ndarray]:
    """All features, each [b-a, N]: rows a..b-1 of the panel (the sample). Computed on the whole
    panel history up to each bar (trailing windows only), then cut to the sample rows."""
    c = S.P.cf
    lc = np.log(c)
    hi = np.where(np.isfinite(S.P.h), S.P.h, c)
    lo = np.where(np.isfinite(S.P.l), S.P.l, c)
    r1 = lc - ta.shift(lc, 1)
    spy = lc[:, S.spy][:, None]
    rspy = r1[:, S.spy][:, None]
    f = _Store(a, b)
    with np.errstate(divide="ignore", invalid="ignore"):
        m12 = ta.shift(lc, 21) - ta.shift(lc, 252)
        m6 = ta.shift(lc, 21) - ta.shift(lc, 126)
        m12_7 = ta.shift(lc, 126) - ta.shift(lc, 252)
        f["mom252_21"] = m12
        f["mom126_21"] = m6
        f["mom63_5"] = ta.shift(lc, 5) - ta.shift(lc, 63)
        f["mom252_0"] = lc - ta.shift(lc, 252)
        f["mom252_126"] = m12_7
        s252 = ta.stdev(r1, 252)
        f["zmom252_21"] = m12 / (s252 * np.sqrt(231))
        # rolling beta to SPY over 252 bars
        mx, my = ta.sma(r1, 252), ta.sma(np.broadcast_to(rspy, r1.shape).copy(), 252)
        cov = ta.sma(r1 * rspy, 252) - mx * my
        var = ta.sma(np.broadcast_to(rspy * rspy, r1.shape).copy(), 252) - my * my
        beta = cov / var
        f["beta252"] = beta
        f["resmom252_21"] = m12 - beta * (ta.shift(spy, 21) - ta.shift(spy, 252))
        f["accel"] = m6 - m12_7
        pm = np.zeros(lc.shape)
        for k in range(12):
            d = ta.shift(lc, 21 * k) - ta.shift(lc, 21 * (k + 1))
            pm = pm + np.where(np.isfinite(d), (d > 0).astype(float), np.nan)
        f["posmonths12"] = pm
        hh252 = ta.highest(hi, 252)
        f["hi252"] = c / hh252
        f["hi126"] = c / ta.highest(hi, 126)
        f["hi252c"] = c / ta.highest(c, 252)
        f["barshi252"] = bn.move_argmax(hi, window=252, min_count=252, axis=0).astype(float)
        f["nh63"] = ta.rolling_sum(np.where(np.isfinite(hh252), (hi >= hh252).astype(float), np.nan), 63)
        ll252 = ta.lowest(lo, 252)
        f["lo252"] = c / ll252
        s50, s150, s200 = ta.sma(c, 50), ta.sma(c, 150), ta.sma(c, 200)
        f["d200"] = np.log(c / s200) / (S.vol * np.sqrt(200))
        f["ma50_200"] = s50 / s200 - 1.0
        f["stack"] = np.where(np.isfinite(s200), (c > s50).astype(float) + (s50 > s150) + (s150 > s200), np.nan)
        mnv = (c > s50) & (s50 > s150) & (s150 > s200) & (s200 > ta.shift(s200, 21)) & (c >= 1.3 * ll252) \
            & (c >= 0.75 * hh252)
        f["minervini"] = np.where(np.isfinite(ta.shift(s200, 21)) & np.isfinite(hh252), mnv.astype(float), np.nan)
        f["above50_126"] = ta.sma(np.where(np.isfinite(s50), (c > s50).astype(float), np.nan), 126)
        for n in (63, 126):
            sl = ta.linreg_slope(lc, n)
            sd = ta.stdev(lc, n)
            r = sl * np.sqrt((n * n - 1) / 12.0) / sd
            r = np.clip(r, -0.999999, 0.999999)
            f[f"r2s{n}"] = np.sign(r) * r * r
            if n == 126:
                f["tstat126"] = r * np.sqrt((n - 2) / (1 - r * r))
                f["slopeR2_126"] = 252.0 * sl * r * r
            # neighbours kept for pass 3
        for n in (42, 90, 189):
            sl = ta.linreg_slope(lc, n)
            r = np.clip(sl * np.sqrt((n * n - 1) / 12.0) / ta.stdev(lc, n), -0.999999, 0.999999)
            f[f"r2s{n}"] = np.sign(r) * r * r
        up = np.where(np.isfinite(r1), (r1 > 0).astype(float), np.nan)
        dn = np.where(np.isfinite(r1), (r1 < 0).astype(float), np.nan)
        f["id252"] = np.sign(m12) * (ta.shift(ta.sma(dn, 231), 21) - ta.shift(ta.sma(up, 231), 21))
        s126 = ta.stdev(r1, 126)
        f["sharpe126"] = (lc - ta.shift(lc, 126)) / (s126 * np.sqrt(126))
        f["sharpe252_21"] = m12 / (ta.shift(ta.stdev(r1, 231), 21) * np.sqrt(231))
        f["er126"] = (lc - ta.shift(lc, 126)) / ta.rolling_sum(np.abs(r1), 126)
        f["upfrac126"] = ta.sma(up, 126)
        f["rs63"] = (lc - ta.shift(lc, 63)) - (spy - ta.shift(spy, 63))
        f["rs126"] = (lc - ta.shift(lc, 126)) - (spy - ta.shift(spy, 126))
        ratio = c / c[:, S.spy][:, None]
        f["rsline252"] = ratio / ta.highest(ratio, 252)
        f["vol126"] = s126
        # neighbours for pass 3
        f["mom189_21"] = ta.shift(lc, 21) - ta.shift(lc, 189)
        f["mom315_21"] = ta.shift(lc, 21) - ta.shift(lc, 315)
        f["hi189"] = c / ta.highest(hi, 189)
        f["hi315"] = c / ta.highest(hi, 315)
        f["sharpe63"] = (lc - ta.shift(lc, 63)) / (ta.stdev(r1, 63) * np.sqrt(63))
        f["sharpe189"] = (lc - ta.shift(lc, 189)) / (ta.stdev(r1, 189) * np.sqrt(189))
    return f


# =============================================================================== fast evaluator
class Fast:
    """Row-sliced copies of what Study.event uses, so that a whole set of groups is evaluated in
    one pass per horizon (np.bincount) instead of one Study.event call (about 2 s) per group."""

    def __init__(self, S: Study):
        r = np.flatnonzero(S.rows)
        a, b = int(r[0]), int(r[-1]) + 1
        assert S.rows[a:b].all()
        self.S, self.a, self.b, self.hs = S, a, b, S.hs
        self.T, self.N = b - a, S.uni.shape[1]
        self.uni = S.uni[a:b]
        self.dates = S.dates[a:b]
        self.year = pd.DatetimeIndex(self.dates).year.to_numpy()
        self.month = (self.year * 100 + pd.DatetimeIndex(self.dates).month.to_numpy())
        self.out, self.fin, self.mu, self.ubar = {}, {}, {}, {}
        for h in self.hs:
            o = S.fwd(h)[a:b]
            self.out[h], self.fin[h] = o, np.isfinite(o)
            m_uni, _ = E.day_means(o, self.uni, 20)
            self.mu[h] = m_uni
            ok = np.isfinite(m_uni)
            self.ubar[h] = float(np.nanmean(m_uni[ok])) if ok.sum() >= 60 else np.nan
        self.rowix = np.arange(self.T, dtype=np.int64)[:, None]

    def sl(self, x: np.ndarray) -> np.ndarray:
        return x[self.a:self.b]

    def full(self, x: np.ndarray) -> np.ndarray:
        """Pad a row-sliced array back to the panel's length (for Study.event / Study.trades)."""
        out = np.full((len(self.S.dates), x.shape[1]), np.nan if x.dtype.kind == "f" else 0, dtype=x.dtype)
        out[self.a:self.b] = x
        return out


class DayTab:
    """Per-day sums and counts of the outcome for every group of an integer group-id array."""

    def __init__(self, F: Fast, gid: np.ndarray, labels: list[str], base: np.ndarray, outs: dict | None = None):
        self.F, self.labels, self.G = F, list(labels), len(labels)
        G = self.G
        flat = F.rowix * G + gid
        sig = base & (gid >= 0)
        self.ev = np.bincount(flat[sig], minlength=F.T * G).reshape(F.T, G)
        self.s, self.n, self.p, self.mc = {}, {}, {}, {}
        self.custom = outs is not None
        for h in F.hs:
            o = F.out[h] if outs is None else outs[h]
            fin = F.fin[h] if outs is None else np.isfinite(o)
            v = base & fin
            cn = v.sum(axis=1)
            cs = np.where(v, o, 0.0).sum(axis=1)
            self.mc[h] = np.where(cn >= 20, cs / np.maximum(cn, 1), np.nan)
            m = v & (gid >= 0)
            idx, w = flat[m], o[m]
            self.s[h] = np.bincount(idx, weights=w, minlength=F.T * G).reshape(F.T, G)
            self.n[h] = np.bincount(idx, minlength=F.T * G).reshape(F.T, G).astype(float)
            self.p[h] = np.bincount(idx, weights=(w > 0).astype(float), minlength=F.T * G).reshape(F.T, G)

    def ms(self, g: int, h: int) -> np.ndarray:
        n = self.n[h][:, g]
        return np.where(n >= 1, self.s[h][:, g] / np.maximum(n, 1), np.nan)

    def xs_series(self, g: int, h: int) -> np.ndarray:
        return self.ms(g, h) - self.mc[h]

    def cell(self, g: int, h: int, dm: np.ndarray | None = None) -> dict:
        F = self.F
        n = self.n[h][:, g]
        ms = self.ms(g, h)
        d = ms - self.mc[h]
        xs_m, xs_t, days = E.nw_mean(d if dm is None else d[dm], 2 * h)
        ts_m = ts_t = np.nan
        if not self.custom:
            ok = np.isfinite(F.mu[h])
            nn = np.where(ok & np.isfinite(ms), n, 0.0)
            if dm is not None:
                nn = np.where(dm, nn, 0.0)
            if ok.sum() >= 60 and nn.sum() >= 50:
                x = np.where(nn > 0, nn * (ms - F.ubar[h]), 0.0)[ok] / nn[ok].mean()
                ts_m, ts_t, _ = E.nw_mean(x, 2 * h)
        sel = slice(None) if dm is None else dm
        tot = n[sel].sum()
        return {"xs_bp": _r(1e4 * xs_m, 1), "xs_t": _r(xs_t, 2), "ts_bp": _r(1e4 * ts_m, 1), "ts_t": _r(ts_t, 2),
                "raw_bp": _r(1e4 * self.s[h][sel, g].sum() / tot, 1) if tot > 0 else None,
                "hit": _r(self.p[h][sel, g].sum() / tot, 3) if tot > 0 else None,
                "events": int(self.ev[sel, g].sum()), "days": int(days)}

    def spread(self, g1: int, g2: int, h: int, dm: np.ndarray | None = None) -> dict:
        d = self.ms(g1, h) - self.ms(g2, h)
        m, t, days = E.nw_mean(d if dm is None else d[dm], 2 * h)
        return {"xs_bp": _r(1e4 * m, 1), "xs_t": _r(t, 2), "days": int(days)}

    def by_year(self, g: int, h: int, g2: int | None = None) -> dict:
        d = self.xs_series(g, h) if g2 is None else self.ms(g, h) - self.ms(g2, h)
        res = {}
        for y in np.unique(self.F.year):
            v = d[self.F.year == y]
            v = v[np.isfinite(v)]
            res[int(y)] = _r(1e4 * v.mean(), 1) if len(v) >= 40 else None
        return res


def _r(x, nd):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def bucket_gid(x: np.ndarray, edges) -> np.ndarray:
    """Group index of the interval (edges[i], edges[i+1]] containing x; -1 outside or NaN."""
    e = np.asarray(edges, dtype=float)
    g = np.searchsorted(e, x.astype(np.float64), side="left") - 1
    return np.where(np.isfinite(x) & (g >= 0) & (g < len(e) - 1), g, -1).astype(np.int64)


def bucket_labels(edges) -> list[str]:
    return [f"({_e(edges[i])},{_e(edges[i + 1])}]" for i in range(len(edges) - 1)]


def _e(v) -> str:
    return "-inf" if v == -INF else "inf" if v == INF else f"{v:g}"


def quant_gid(x: np.ndarray, base: np.ndarray, q: int = 5) -> np.ndarray:
    """Daily cross-sectional quantile index 0..q-1 within base (same cut rule as Study.quantiles)."""
    rk = E.xs_rank(x, base)
    g = np.full(x.shape, -1, dtype=np.int64)
    for i in range(q):
        g[(rk > i / q) & (rk <= (i + 1) / q)] = i
    return g


def log_cells(sample: str, hid: str, definition: str, base_name: str, cells: dict, adv_min: float,
              params: dict | None = None, note: str = "") -> None:
    """One registry line per (horizon, view), like Study.event."""
    VARIANTS.setdefault(f"{hid}|{definition}|{base_name}", definition)
    for h, c in cells.items():
        for view in ("xs", "ts"):
            if f"{view}_bp" not in c:
                continue
            log_trial(hid, FAMILY, f"{definition} [base {base_name}] -> fwd_open_{h} ({view})", sample,
                      f"{view}_bp", c[f"{view}_bp"], params={**(params or {}), "h": h, "base": base_name},
                      universe=f"adv>={adv_min:.0f}", tstat=c[f"{view}_t"], n=c.get("events"), note=note)


def fmt(c: dict, view: str = "xs") -> str:
    if c is None or c.get(f"{view}_bp") is None:
        return f"{'':>14s}"
    return f"{c[f'{view}_bp']:+7.1f}({c[f'{view}_t']:+5.1f})"


# =============================================================================== pass 1: the map
def evaluate_groups(F: Fast, sample: str, name: str, kind: str, gid: np.ndarray, labels: list[str],
                    base: np.ndarray, base_name: str, day_masks: dict[str, np.ndarray] | None = None,
                    definition: str = "", spread: tuple[int, int] | None = None) -> dict:
    """Evaluate all groups of `gid` within `base`. Returns {split: {label: {h: cell}}}; the splits
    are base_name itself and one per entry of day_masks (subsets of DATES, e.g. market state)."""
    tab = DayTab(F, gid, labels, base)
    adv = F.S.adv_min
    res = {}
    splits = {base_name: None, **(day_masks or {})}
    for sp, dm in splits.items():
        bn_ = base_name if dm is None else f"{base_name}&{sp}"
        out = {}
        for g, lab in enumerate(labels):
            cells = {h: tab.cell(g, h, dm) for h in F.hs}
            out[lab] = cells
            log_cells(sample, f"F03.{name}", f"{name} {kind} {lab}: {definition}", bn_, cells, adv)
        if spread is not None:
            g1, g2 = spread
            cells = {h: tab.spread(g1, g2, h, dm) for h in F.hs}
            lab = f"{labels[g1]}-{labels[g2]}"
            out[lab] = cells
            log_cells(sample, f"F03.{name}", f"{name} {kind} spread {lab}: {definition}", bn_, cells, adv)
        res[bn_] = out
    res["_by_year"] = {lab: {h: tab.by_year(g, h) for h in (20, 60)} for g, lab in enumerate(labels)}
    if spread is not None:
        res["_by_year"][f"{labels[spread[0]]}-{labels[spread[1]]}"] = {
            h: tab.by_year(spread[0], h, spread[1]) for h in (20, 60)}
    return res


def show_feature(name: str, res: dict, hs=HS) -> None:
    definition = SPEC[name][0] if name in SPEC else name
    print(f"\n--- {name}: {definition}")
    print(f"{'ALL':>22s}" + "".join(f"{'XS h=' + str(h):>15s}" for h in hs) + f"{'TS h=20':>15s}{'TS h=60':>15s}   events")
    for kind in ("bucket", "quintile"):
        tab = res[kind]["ALL"]
        for lab, row in tab.items():
            line = f"{lab:>22s}" + "".join(f"{fmt(row[h]):>15s}" for h in hs)
            line += f"{fmt(row[20], 'ts'):>15s}{fmt(row[60], 'ts'):>15s}"
            print(line + (f"  {row[hs[0]]['events']:>8d}" if "events" in row[hs[0]] else ""))
    print(f"{'splits (XS)':>22s}" + "".join(f"{s + ' h=' + str(h):>17s}" for s in ("liqLo", "liqHi", "mktUp", "mktDn")
                                           for h in (20, 60)))
    for kind in ("bucket", "quintile"):
        labs = list(res[kind]["ALL"].keys())
        pick = [labs[0], labs[-2], labs[-1]] if kind == "quintile" else [labs[0], labs[-2], labs[-1]]
        for lab in pick:
            line = f"{lab:>22s}"
            for sp in ("liqLo", "liqHi", "ALL&mktUp", "ALL&mktDn"):
                row = res[kind].get(sp, {}).get(lab)
                for h in (20, 60):
                    line += f"{fmt(row[h]) if row else '':>17s}"
            print(line)


def pass1(S: Study, F: Fast, feats: dict, ctxv: dict) -> dict:
    sample = S.sample
    out = {}
    bases = {"ALL": F.uni, "liqLo": F.uni & ctxv["liq_lo"], "liqHi": F.uni & ctxv["liq_hi"]}
    days = {"mktUp": ctxv["mkt_up"], "mktDn": ctxv["mkt_dn"]}
    for name, (definition, pine, edges) in SPEC.items():
        x = feats[name]
        blabs = bucket_labels(edges)
        bg = bucket_gid(x, edges)
        res = {"bucket": {}, "quintile": {}, "definition": definition, "pine": pine}
        qlabs = [f"Q{i + 1}" for i in range(5)]
        for bname, base in bases.items():
            dm = days if bname == "ALL" else None
            r = evaluate_groups(F, sample, name, "bucket", bg, blabs, base, bname, dm, definition,
                                spread=(len(blabs) - 1, 0))
            by = r.pop("_by_year")
            res["bucket"].update(r)
            if bname == "ALL":
                res["bucket_by_year"] = by
            qg = quant_gid(x, base)
            r = evaluate_groups(F, sample, name, "xs-quintile(needs screener)", qg, qlabs, base, bname, dm,
                                definition, spread=(4, 0))
            by = r.pop("_by_year")
            res["quintile"].update(r)
            if bname == "ALL":
                res["quintile_by_year"] = by
        out[name] = res
        show_feature(name, res)
    return out


def summary_table(p1: dict, hs=(20, 40, 60)) -> None:
    print("\n=== PASS 1 SUMMARY: daily cross-sectional quintiles, XS bp (t) versus the universe ===")
    print(f"{'feature':>14s}" + "".join(f"{lab + ' h=' + str(h):>16s}" for h in hs for lab in ("Q5-uni", "Q1-uni", "Q5-Q1")))
    for name, res in p1.items():
        q = res["quintile"]["ALL"]
        line = f"{name:>14s}"
        for h in hs:
            line += f"{fmt(q['Q5'][h]):>16s}{fmt(q['Q1'][h]):>16s}{fmt(q['Q5-Q1'][h]):>16s}"
        print(line)


# =============================================================================== driver
def context(S: Study, F: Fast) -> dict:
    c = S.P.cf
    spy = c[:, S.spy]
    s200 = ta.sma(spy[:, None], 200)[:, 0]
    up = F.sl(spy > s200) & np.isfinite(F.sl(s200))
    dn = F.sl(spy <= s200) & np.isfinite(F.sl(s200))
    adv = F.sl(S.adv60)
    return {"mkt_up": up, "mkt_dn": dn, "liq_hi": adv >= 50e6, "liq_lo": adv < 50e6,
            "spy": spy, "spy200": s200}


def check_against_study(S: Study, F: Fast, feats: dict) -> None:
    """The fast evaluator must reproduce Study.event / Study.buckets to the rounding shown."""
    x = F.full(feats["hi252"])
    sig = S.uni & np.isfinite(x) & (x > 0.95) & (x <= 0.98)
    ref = S.event("F03.check", FAMILY, "hi252 bucket (0.95,0.98] (evaluator check, duplicate of the map cell)", sig,
                  note="evaluator check")
    gid = bucket_gid(feats["hi252"], SPEC["hi252"][2])
    tab = DayTab(F, gid, bucket_labels(SPEC["hi252"][2]), F.uni)
    for h in HS:
        mine = tab.cell(5, h)
        for k in ("xs_bp", "xs_t", "ts_bp", "ts_t", "raw_bp", "hit", "events", "days"):
            assert mine[k] == ref[h][k] or abs(mine[k] - ref[h][k]) <= 0.11, (h, k, mine[k], ref[h][k])
    refq = S.quantiles("F03.check", FAMILY, "mom252_21 (evaluator check)", F.full(feats["mom252_21"]), hs=(20,))
    qg = quant_gid(feats["mom252_21"], F.uni)
    tq = DayTab(F, qg, [f"Q{i + 1}" for i in range(5)], F.uni)
    for i in range(5):
        mine = tq.cell(i, 20)
        for k in ("xs_bp", "xs_t", "ts_bp", "ts_t", "events"):
            assert abs(mine[k] - refq[f"Q{i + 1}"][20][k]) <= 0.11, (i, k, mine[k], refq[f"Q{i + 1}"][20][k])
    print("evaluator check against Study.event / Study.quantiles: OK")


def run(sample: str, only_pass1: bool = False) -> dict:
    t0 = time.time()
    S = Study(sample, hs=HS)
    F = Fast(S)
    feats = build_features(S, F.a, F.b)
    ctxv = context(S, F)
    print(f"\n{'=' * 110}\n{sample}: {F.dates[0]}..{F.dates[-1]}  days {F.T}  names/day {F.uni.sum(1).mean():.0f}  "
          f"SPY<=sma200 on {ctxv['mkt_dn'].mean():.1%} of days  liquid(>=50M) share {(ctxv['liq_hi'] & F.uni).sum() / F.uni.sum():.1%}"
          f"   [{time.time() - t0:.0f}s]")
    check_against_study(S, F, feats)
    res = {"sample": sample, "dates": [str(F.dates[0]), str(F.dates[-1])], "names_per_day": float(F.uni.sum(1).mean())}
    res["pass1"] = pass1(S, F, feats, ctxv)
    summary_table(res["pass1"])
    print(f"[{sample} pass 1 done {time.time() - t0:.0f}s]")
    del S, F, feats
    gc.collect()
    return res


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only1 = "--pass1-only" in sys.argv
    out_dir = Path(__file__).resolve().parents[1] / "results"
    out_dir.mkdir(exist_ok=True)
    allres = {}
    for smp in (args or ["DEV", "CTX"]):
        allres[smp] = run(smp, only1)
        gc.collect()
    allres["variants_evaluated"] = len(VARIANTS)
    print(f"\ndistinct signal variants evaluated in this run: {len(VARIANTS)}")
    (out_dir / "f03_momentum_selection.json").write_text(json.dumps(allres))
