"""F06 - Breakouts, bases and volatility contraction, measured from the next open.

Run:   cd swing-lab && python -m research.experiments.f06_breakouts            (everything, DEV then CTX)
       python -m research.experiments.f06_breakouts DEV p1 p3                  (one sample, chosen passes)

Development data only (protocol section 2):  DEV 2011-01..2018-06 (biased to 2018 survivors),
CTX 1998..2010 (survivors of 2026). Outcomes are total returns from the OPEN of t+1 (Study.fwd).

Every event is known at the close of t and is written from Pine-faithful primitives (pinelike.py):

    ph_N      = ta.highest(close, N)[1]                 prior N-bar closing high
    nh_N      = close > ph_N                            new N-bar closing high
    first_N   = nh_N and no nh_N on any of the previous 10 bars      ("breakout")
    near_N    = close >= 0.97 * ph_N and not nh_N       control (ii): near the same high, no breakout today

Views (see Study): XS = equal-day mean of (signal mean - control mean) on the same day; the control is
the universe [U] or a named pool such as near_N [NH]. EW = the same difference weighted by the number
of signals per day, i.e. the expected result against date-matched random entries drawn from the pool.
TS = event-weighted signal mean minus the universe's whole-sample average (contains market timing).

Passes
    p1  broad map of every variant (horizons 1,3,5,10,20,40,60)
    p2  as trades (stop 2 ATR / base low, trail 3 ATR, time exit 20/40) against date-matched random entries
    p3  splits: market regime (SPY vs its 200-day average), liquidity, halves A/B, calendar years
    p4  attempts to kill what looks alive: one-bar delay, neighbouring parameters, further controls

Everything looked at is logged to registry/trials_f06.jsonl (S.event does it; the helpers here call
log_trial themselves).
"""
from __future__ import annotations

import os

os.environ["SWINGLAB_REGISTRY_TAG"] = "f06"          # before importing swinglab

import gc  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import bottleneck as bn  # noqa: E402
import numpy as np  # noqa: E402
from numba import njit  # noqa: E402

from research.swinglab import engine as E  # noqa: E402
from research.swinglab import pinelike as ta  # noqa: E402
from research.swinglab import trades as TR  # noqa: E402
from research.swinglab.registry import log_trial  # noqa: E402
from research.swinglab.study import Study  # noqa: E402

FAMILY = "F06_breakouts"
HS = (1, 3, 5, 10, 20, 40, 60)
HS3 = (5, 20, 60)
OUT = Path(__file__).resolve().parents[1] / "results" / "f06_breakouts.json"
RUN_NOTE = os.environ.get("F06_NOTE", "")


# ============================================================================== small helpers
def first_in(x: np.ndarray, k: int = 10) -> np.ndarray:
    """x is true today and was not true on any of the previous k bars (Pine: x and math.sum(x?1:0,k)[1]==0)."""
    prev = ta.rolling_sum(ta.shift(x.astype(float), 1), k)
    return x & (prev == 0)


def last_event(ev: np.ndarray):
    """Row index of the most recent event at or before each bar (-1 if none) and bars since it."""
    T = ev.shape[0]
    ar = np.arange(T)[:, None]
    last = np.maximum.accumulate(np.where(ev, ar, -1), axis=0)
    return last, ar - last


def at_last(x: np.ndarray, last: np.ndarray) -> np.ndarray:
    """Value of x on the bar of the most recent event (Pine: ta.valuewhen(ev, x, 0))."""
    out = np.take_along_axis(x, np.maximum(last, 0), axis=0).astype(float)
    out[last < 0] = np.nan
    return out


def count_since(cond: np.ndarray, last: np.ndarray) -> np.ndarray:
    """How many bars since the last event (excluding the event bar) had cond true, up to and including today."""
    cs = np.cumsum(cond, axis=0)
    return cs - np.take_along_axis(cs, np.maximum(last, 0), axis=0)


def lagb(x: np.ndarray, k: int = 1) -> np.ndarray:
    """Boolean signal delayed by k bars."""
    out = np.zeros_like(x)
    out[k:] = x[:-k]
    return out


@njit(cache=True)
def _pivots(hi, lo, c, left, right):
    """Swing highs as ta.pivothigh(high, left, right): bar p is a pivot high if its high is above the
    `left` bars before it and not exceeded on the `right` bars after it; it is KNOWN at bar p+right.

    Per bar t (all known at the close of t):
      brk  first close above the most recent confirmed pivot high since it was confirmed
      d0   depth of the pullback that followed that pivot: (pivot - lowest low since, up to t-1) / pivot
      d1   depth of the pullback that followed the previous pivot high (to the lowest low before the next pivot)
      d2   the one before that
    """
    T, N = c.shape
    brk = np.zeros((T, N), np.bool_)
    d0 = np.full((T, N), np.nan)
    d1 = np.full((T, N), np.nan)
    d2 = np.full((T, N), np.nan)
    for n in range(N):
        P = np.nan
        pbar = -1
        minlo = np.nan
        a1 = np.nan
        a2 = np.nan
        broken = True
        for t in range(T):
            if np.isnan(c[t, n]):
                continue
            p = t - right
            if p - left >= 0 and not np.isnan(hi[p - left, n]):
                x = hi[p, n]
                ok = True
                for j in range(p - left, p):
                    if hi[j, n] >= x:
                        ok = False
                        break
                if ok:
                    for j in range(p + 1, t + 1):
                        if hi[j, n] > x:
                            ok = False
                            break
                if ok:
                    if pbar >= 0:
                        m = lo[pbar, n]
                        for j in range(pbar, p + 1):
                            if lo[j, n] < m:
                                m = lo[j, n]
                        a2 = a1
                        a1 = (P - m) / P
                    P = x
                    pbar = p
                    minlo = lo[p, n]
                    for j in range(p, t):
                        if lo[j, n] < minlo:
                            minlo = lo[j, n]
                    broken = False
            if pbar >= 0:
                d0[t, n] = (P - minlo) / P
                d1[t, n] = a1
                d2[t, n] = a2
                if (not broken) and c[t, n] > P:
                    brk[t, n] = True
                    broken = True
                if lo[t, n] < minlo:
                    minlo = lo[t, n]
    return brk, d0, d1, d2


def _r(x, nd=1):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


# ============================================================================== the lab
class Lab:
    """Holds one Study, the shared features, and the result tables of one sample."""

    def __init__(self, sample: str):
        t0 = time.time()
        self.S = S = Study(sample)
        self.sample = sample
        self.res: dict = {}
        self.variants: dict = {}                       # key -> definition (the count of distinct signals)
        P = S.P
        c = P.cf
        self.c = c
        self.hi = np.where(np.isfinite(P.h), P.h, c)
        self.lo = np.where(np.isfinite(P.l), P.l, c)
        self.op = np.where(np.isfinite(P.o), P.o, c)
        self.atr = S.atr(14)
        self.T, self.N = c.shape
        # market regime from Yahoo's long SPY history (the DEV panel itself starts in 2011)
        spy = S.ctx("SPY", "close")
        self.reg_up = spy > ta.sma(spy[:, None], 200)[:, 0]
        self.reg_dn = np.isfinite(spy) & ~self.reg_up
        self.years = S.dates.astype("datetime64[Y]").astype(int) + 1970
        self._ph: dict = {}
        self._cache: dict = {}
        print(f"[{sample}] study built in {time.time() - t0:.1f}s  shape={c.shape}  "
              f"sample {S.dates[S.rows][0]}..{S.dates[S.rows][-1]}  names/day={S.uni[S.rows].sum(axis=1).mean():.0f}  "
              f"SPY>SMA200 on {self.reg_up[S.rows].mean():.0%} of sample days")

    # ---------------------------------------------------------------- features (all causal)
    def ph(self, n: int) -> np.ndarray:
        if n not in self._ph:
            self._ph[n] = ta.shift(ta.highest(self.c, n), 1)
        return self._ph[n]

    def nh(self, n: int) -> np.ndarray:
        return self.c > self.ph(n)

    def first(self, n: int, k: int = 10) -> np.ndarray:
        key = ("first", n, k)
        if key not in self._cache:
            self._cache[key] = first_in(self.nh(n), k)
        return self._cache[key]

    def near(self, n: int, pct: float = 0.03) -> np.ndarray:
        key = ("near", n, pct)
        if key not in self._cache:
            self._cache[key] = (self.c >= (1 - pct) * self.ph(n)) & ~self.nh(n)
        return self._cache[key]

    def get(self, name: str):
        """Lazily built named features."""
        if name in self._cache:
            return self._cache[name]
        c, hi, lo, atr = self.c, self.hi, self.lo, self.atr
        if name == "rv":                       # volume / its average over the previous 50 bars
            v = self.S.P.v
            with np.errstate(divide="ignore", invalid="ignore"):
                x = v / ta.shift(bn.move_mean(v, window=50, min_count=40, axis=0), 1)
        elif name == "clv":                    # close location in the bar's range
            with np.errstate(divide="ignore", invalid="ignore"):
                x = (c - lo) / (hi - lo)
        elif name == "up200":
            x = c > ta.sma(c, 200)
        elif name == "dist252":                # close / highest close of 252 bars (incl. today)
            x = c / ta.highest(c, 252)
        elif name == "atr_ratio":              # ATR(5)/ATR(50)
            x = ta.atr(hi, lo, c, 5) / ta.atr(hi, lo, c, 50)
        elif name == "bb_sq":                  # Bollinger width (20,2) at its 126-bar low
            w = 4.0 * ta.stdev(c, 20) / ta.sma(c, 20)
            x = w <= ta.lowest(w, 126)
        elif name == "bb_up":                  # close above the upper band
            x = c > ta.sma(c, 20) + 2.0 * ta.stdev(c, 20)
        elif name.startswith("rng"):           # rng15 / rng25: highest high - lowest low of the last L bars
            L = int(name[3:])
            x = ta.highest(hi, L) - ta.lowest(lo, L)
        elif name.startswith("hh"):            # hh20: prior L-bar highest HIGH
            L = int(name[2:])
            x = ta.shift(ta.highest(hi, L), 1)
        elif name.startswith("ll"):            # ll10: prior L-bar lowest LOW
            L = int(name[2:])
            x = ta.shift(ta.lowest(lo, L), 1)
        elif name.startswith("rq"):            # rq15: percentrank over 252 bars of (L-bar range / close)
            L = int(name[2:])
            x = ta.percentrank(self.get(f"rng{L}") / c, 252)
        elif name == "pivots":
            x = _pivots(hi, lo, c, 5, 5)
        elif name == "bars":                   # number of bars of history so far
            x = np.cumsum(np.isfinite(c), axis=0)
        elif name == "ath_prev":               # highest close of all previous bars
            x = ta.shift(np.fmax.accumulate(c, axis=0), 1)
        else:
            raise KeyError(name)
        self._cache[name] = x
        return x

    def tight(self, L: int, k: float) -> np.ndarray:
        """The L bars BEFORE today spanned less than k ATR(14): (highest(high,L)-lowest(low,L))[1] < k*atr[1]."""
        return ta.shift(self.get(f"rng{L}"), 1) < k * ta.shift(self.atr, 1)

    def tightq(self, L: int, q: float = 20.0) -> np.ndarray:
        """Range/price of the previous L bars in the lowest quintile of the stock's own last 252 values."""
        return ta.shift(self.get(f"rq{L}"), 1) <= q

    # ---------------------------------------------------------------- evaluation
    def ev(self, key: str, definition: str, sig: np.ndarray, controls=(("U", None),), hs=HS, ew_hs=(),
           table: str = "p1", quiet: bool = False) -> dict:
        """Evaluate one signal against each control; store and print one line per control."""
        S = self.S
        self.variants.setdefault(key, definition)
        out = {}
        for cname, ctrl in controls:
            tab = S.event(f"F06.{key}", FAMILY, f"{definition} | control={cname}", sig, control=ctrl, hs=hs,
                          params={"control": cname}, note=RUN_NOTE)
            for h in ew_hs:
                m, t = self.ew(sig, ctrl, h)
                tab[h]["ew_bp"], tab[h]["ew_t"] = _r(1e4 * m), _r(t, 2)
                log_trial(f"F06.{key}", FAMILY, f"{definition} | control={cname} -> fwd_open_{h} (ew)", S.sample,
                          "ew_bp", 1e4 * m if np.isfinite(m) else float("nan"), params={"control": cname, "h": h},
                          universe=f"adv>={S.adv_min:.0f}", tstat=t if np.isfinite(t) else None,
                          n=int((sig & S.uni).sum()), note=RUN_NOTE)
            out[cname] = {str(h): v for h, v in tab.items()}
            if not quiet:
                self.line(key, cname, tab)
        self.res.setdefault(table, {})[key] = {"def": definition, "ctrl": out}
        return out

    def ew(self, sig: np.ndarray, ctrl: np.ndarray | None, h: int):
        """Signal-count-weighted mean of (signal mean - control mean) by day: what date-matched random
        entries from the control pool would be beaten by, in expectation. Newey-West t over all days."""
        S = self.S
        out = S.fwd(h)
        sig = sig & S.uni
        ctrl = S.uni if ctrl is None else (ctrl & S.uni)
        ms, ns = E.day_means(out, sig)
        mc, _ = E.day_means(out, ctrl, 20)
        ok = S.rows & np.isfinite(mc)
        n = np.where(ok & np.isfinite(ms), ns, 0).astype(float)
        if n.sum() < 50:
            return np.nan, np.nan
        x = np.where(n > 0, n * (ms - mc), 0.0)[ok] / n[ok].mean()
        m, t, _ = E.nw_mean(x, lags=2 * h)
        return m, t

    @staticmethod
    def header(title: str, hs=HS, ts_hs=HS3) -> None:
        print(f"\n--- {title}")
        print(f"{'variant':<30s}{'ctl':<8s}{'events':>8s} |" + "".join(f"{'XS h=' + str(h):>13s}" for h in hs)
              + " |" + "".join(f"{'TS h=' + str(h):>13s}" for h in ts_hs if h in hs))

    @staticmethod
    def line(key: str, cname: str, tab: dict, ts_hs=HS3) -> None:
        hs = list(tab.keys())
        s = f"{key:<30s}{cname:<8s}{tab[hs[0]]['events']:>8d} |"
        for h in hs:
            cell = tab[h]
            s += f"{'' if cell['xs_bp'] is None else f'{cell['xs_bp']:+6.1f}({cell['xs_t']:+4.1f})':>13s}"
        s += " |"
        for h in ts_hs:
            if h in tab:
                cell = tab[h]
                s += f"{'' if cell['ts_bp'] is None else f'{cell['ts_bp']:+6.1f}({cell['ts_t']:+4.1f})':>13s}"
        ew = [f"h{h}:{tab[h]['ew_bp']:+.1f}({tab[h]['ew_t']:+.1f})" for h in hs if tab[h].get("ew_bp") is not None]
        if ew:
            s += "  EW " + " ".join(ew)
        print(s)


# ============================================================================== pass 1: the broad map
def p1(L: Lab) -> None:
    S, c, hi, lo, atr = L.S, L.c, L.hi, L.lo, L.atr
    U = ("U", None)
    rv, clv = L.get("rv"), L.get("clv")

    # ---- A. plain new closing highs
    L.header("A. new N-bar closing high; 'first' = no such close on the previous 10 bars.  NH = within 3% below the "
             "same prior high, no new high today")
    for n in (20, 55, 126, 252):
        NH = ("NH", L.near(n))
        L.ev(f"first_{n}", f"close > highest(close,{n})[1], first in 10 bars", L.first(n), (U, NH), ew_hs=HS3)
    for n in (20, 55, 126, 252):
        L.ev(f"near_{n}", f"close within 3% below highest(close,{n})[1], not a new high today", L.near(n), (U,),
             ew_hs=HS3)
    for n in (20, 55, 252):
        L.ev(f"anynh_{n}", f"close > highest(close,{n})[1] (any day, also inside a run)", L.nh(n),
             (U, ("NH", L.near(n))))
    for n in (20, 55, 252):
        L.ev(f"runnh_{n}", f"close > highest(close,{n})[1] and a new high also on one of the previous 10 bars",
             L.nh(n) & ~L.first(n), (U,))

    # ---- B. volume on the breakout bar
    L.header("B. breakout volume vs its 50-bar average (rv)")
    for n in (20, 55, 252):
        NH = ("NH", L.near(n))
        f = L.first(n)
        L.ev(f"first_{n}_rv1.5", f"first_{n} and volume >= 1.5 x sma(volume,50)[1]", f & (rv >= 1.5), (U, NH))
        L.ev(f"first_{n}_rv2", f"first_{n} and volume >= 2 x sma(volume,50)[1]", f & (rv >= 2.0), (U, NH))
        L.ev(f"first_{n}_rvlow", f"first_{n} and volume < 1 x sma(volume,50)[1]", f & (rv < 1.0), (U, NH))
    L.ev("first_55_rv3", "first_55 and volume >= 3 x sma(volume,50)[1]", L.first(55) & (rv >= 3.0),
         (U, ("NH", L.near(55))))

    # ---- C. tight bases
    L.header("C. tight base then close above the base's highest high.  TB = names in the same kind of base that did "
             "not break out today")
    for Lb in (15, 25):
        up = c > L.get(f"hh{Lb}")
        for k in (2.5, 4.0):
            t = L.tight(Lb, k)
            L.ev(f"base{Lb}_{k:g}atr", f"(highest(high,{Lb})-lowest(low,{Lb}))[1] < {k:g}*atr(14)[1] and close > "
                 f"highest(high,{Lb})[1]", t & up, (U, ("TB", t & ~up)))
        tq = L.tightq(Lb)
        L.ev(f"base{Lb}_q20", f"percentrank((highest(high,{Lb})-lowest(low,{Lb}))/close,252)[1] <= 20 and close > "
             f"highest(high,{Lb})[1]", tq & up, (U, ("TB", tq & ~up)))
    for n in (55, 252):
        NH = ("NH", L.near(n))
        L.ev(f"first_{n}_tight15_4", f"first_{n} and previous 15 bars spanned < 4 ATR", L.first(n) & L.tight(15, 4.0),
             (U, NH))
        L.ev(f"first_{n}_tight25_4", f"first_{n} and previous 25 bars spanned < 4 ATR", L.first(n) & L.tight(25, 4.0),
             (U, NH))
        L.ev(f"first_{n}_tightq15", f"first_{n} and 15-bar range/price in its lowest quintile of 252 bars",
             L.first(n) & L.tightq(15), (U, NH))
    # tight base in an uptrend, the textbook setup
    t = L.tight(15, 4.0) & L.get("up200") & (L.get("dist252") >= 0.85)
    up = c > L.get("hh15")
    L.ev("base15_4atr_uptrend", "base15_4atr and close > sma(200) and close >= 0.85*highest(close,252)", t & up,
         (U, ("TB", t & ~up)))

    # ---- D. volatility-contraction proxies
    L.header("D. volatility contraction then breakout")
    for W, n in ((20, 20), (20, 55), (10, 20)):
        d = (ta.highest(hi, W) - ta.lowest(lo, W)) / ta.highest(hi, W)
        vc = (ta.shift(d, 1 + 2 * W) > ta.shift(d, 1 + W)) & (ta.shift(d, 1 + W) > ta.shift(d, 1))
        L.ev(f"vcpw{W}_first_{n}", f"range%({W}) of three consecutive {W}-bar windows before today strictly shrinking, "
             f"then first_{n}", vc & L.first(n), (U, ("NH", L.near(n))))
    brk, d0, d1, d2 = L.get("pivots")
    below_piv = ~brk
    L.ev("pivot_brk", "first close above the last confirmed swing high (pivothigh 5/5)", brk, (U,))
    c2 = d1 > d0
    c3 = (d2 > d1) & (d1 > d0)
    L.ev("vcp_piv_2c", "pivot_brk and last two pullback depths shrinking (d1 > d0)", brk & c2, (U,))
    L.ev("vcp_piv_3c", "pivot_brk and last three pullback depths shrinking (d2 > d1 > d0)", brk & c3,
         (U, ("VC", c3 & below_piv)))
    L.ev("vcp_piv_3c_near", "vcp_piv_3c and close >= 0.85*highest(close,252) and close > sma(200)",
         brk & c3 & (L.get("dist252") >= 0.85) & L.get("up200"), (U,))
    L.ev("vcp_piv_3c_tight", "vcp_piv_3c and final pullback shallower than 8%", brk & c3 & (d0 < 0.08), (U,))
    L.ev("vcp_piv_expand", "pivot_brk and pullback depths growing (d2 < d1 < d0), the opposite of a VCP",
         brk & (d2 < d1) & (d1 < d0), (U,))
    ar = ta.shift(L.get("atr_ratio"), 1)
    for n in (20, 55):
        NH = ("NH", L.near(n))
        L.ev(f"first_{n}_atrc", f"first_{n} and (atr(5)/atr(50))[1] < 0.75", L.first(n) & (ar < 0.75), (U, NH))
        L.ev(f"first_{n}_atrx", f"first_{n} and (atr(5)/atr(50))[1] > 1.25", L.first(n) & (ar > 1.25), (U, NH))
    sq = ta.rolling_sum(ta.shift(L.get("bb_sq").astype(float), 1), 10) > 0
    for n in (20, 55):
        L.ev(f"first_{n}_bbsq", f"first_{n} and Bollinger width(20,2) made a 126-bar low within the previous 10 bars",
             L.first(n) & sq, (U, ("NH", L.near(n))))
    bbx = first_in(L.get("bb_up"), 10)
    L.ev("bbsq_bandbreak", "close > upper Bollinger band (first in 10 bars) and width at a 126-bar low within the "
         "previous 10 bars", bbx & sq, (U, ("SQ", sq & ~L.get("bb_up"))))
    L.ev("squeeze_only", "Bollinger width(20,2) at a 126-bar low today (no breakout required)", L.get("bb_sq"), (U,))
    L.ev("atrc_only", "atr(5)/atr(50) < 0.75 today (no breakout required)", L.get("atr_ratio") < 0.75, (U,))

    # ---- E. where the breakout happens relative to the 252-bar high
    L.header("E. breakout near the 252-bar high versus from a deep base.  DB = all names in the same distance band")
    dist = L.get("dist252")
    bands = (("near5", dist >= 0.95), ("mid", (dist >= 0.80) & (dist < 0.95)), ("deep", dist < 0.80))
    for n in (20, 55):
        for bn_, m in bands:
            L.ev(f"first_{n}_{bn_}", f"first_{n} and close/highest(close,252) in band {bn_} "
                 "(near5 >= 0.95, mid 0.80-0.95, deep < 0.80)", L.first(n) & m, (U, ("DB", m)))
    for bn_, m in bands:
        L.ev(f"band_{bn_}", f"close/highest(close,252) in band {bn_} (no breakout required)", m, (U,))

    # ---- F. where the bar closes
    L.header("F. close location on the breakout bar")
    for n in (20, 55, 252):
        NH = ("NH", L.near(n))
        L.ev(f"first_{n}_clvtop", f"first_{n} and (close-low)/(high-low) >= 0.75", L.first(n) & (clv >= 0.75), (U, NH))
        L.ev(f"first_{n}_clvweak", f"first_{n} and (close-low)/(high-low) < 0.5", L.first(n) & (clv < 0.5), (U, NH))

    # ---- G. Donchian channels (turtle entries)
    L.header("G. Donchian: close (or high) above the prior N-bar highest high")
    for n in (20, 55):
        hh = L.get(f"hh{n}")
        L.ev(f"don{n}_close", f"close > highest(high,{n})[1], first in 10 bars", first_in(c > hh, 10),
             (U, ("NH", L.near(n))))
        L.ev(f"don{n}_touch", f"high > highest(high,{n})[1], first in 10 bars (intraday turtle trigger seen at the "
             "close)", first_in(hi > hh, 10), (U, ("NH", L.near(n))))
    hh = L.get("hh20")
    L.ev("don20_touch_fail", "high > highest(high,20)[1] but close <= it (intraday breakout that did not hold)",
         (hi > hh) & (c <= hh), (U, ("NH", L.near(20))))

    # ---- H. inside bars and NR7
    L.header("H. inside-bar and NR7 breakouts.  SET = same setup yesterday, close inside yesterday's range today")
    h1, l1 = ta.shift(hi, 1), ta.shift(lo, 1)
    ib = (h1 <= ta.shift(hi, 2)) & (l1 >= ta.shift(lo, 2))
    rng = hi - lo
    nr7 = ta.shift(rng, 1) <= ta.shift(ta.lowest(rng, 7), 1)
    nr7 &= np.isfinite(ta.shift(ta.lowest(rng, 7), 1))
    inside_today = (c <= h1) & (c >= l1)
    for nm, st in (("ib", ib), ("nr7", nr7), ("nr7ib", nr7 & ib)):
        L.ev(f"{nm}_up", f"yesterday was {nm}; close > yesterday's high", st & (c > h1), (U, ("SET", st & inside_today)))
        L.ev(f"{nm}_dn", f"yesterday was {nm}; close < yesterday's low", st & (c < l1), (U, ("SET", st & inside_today)))
    up200 = L.get("up200")
    L.ev("ib_up_trend", "ib_up and close > sma(200)", ib & (c > h1) & up200, (U,))
    L.ev("nr7_up_trend", "nr7_up and close > sma(200)", nr7 & (c > h1) & up200, (U,))
    L.ev("nr7_up_near20", "nr7_up and close within 3% of / above highest(close,20)[1]",
         nr7 & (c > h1) & (c >= 0.97 * L.ph(20)), (U,))
    L.ev("nr7_today", "today's range is the narrowest of 7 (no breakout)", rng <= ta.lowest(rng, 7), (U,))

    # ---- I. all-time highs within the available history
    L.header("I. all-time-high closes within the panel's history (Wilcox & Crittenden style)")
    ath = c > L.get("ath_prev")
    bars = L.get("bars")
    NH = ("NH", L.near(252))
    L.ev("ath_first_252", "close > highest close of ALL previous bars (>= 252 bars of history), first in 10 bars",
         first_in(ath, 10) & (bars > 252), (U, NH))
    L.ev("ath_first_500", "same, with >= 500 bars of history", first_in(ath, 10) & (bars > 500), (U, NH))
    L.ev("ath_any_500", "any all-time-high close with >= 500 bars of history", ath & (bars > 500), (U, NH))
    L.ev("first_252_notath", "first_252 that is NOT an all-time high (>= 500 bars of history)",
         L.first(252) & ~ath & (bars > 500), (U, NH))

    # ---- J. failed breakouts (for holders) and breakouts that held
    L.header("J. after the breakout: failed (first close back below the breakout level within k bars) vs held")
    for n in (20, 55, 252):
        last, bs = last_event(L.first(n))
        lvl = at_last(L.ph(n), last)
        below = (c < lvl) & (bs >= 1)
        cnt = count_since(below, last)
        NH = ("NH", L.near(n))
        for k in (3, 5):
            L.ev(f"fail_{n}_k{k}", f"first close below the first_{n} breakout level within {k} bars of the breakout",
                 below & (cnt == 1) & (bs <= k), (U, NH))
            L.ev(f"held_{n}_k{k}", f"bar {k} after a first_{n} breakout with no close below the level since",
                 (bs == k) & (cnt == 0) & (last >= 0), (U, NH))
        L.ev(f"fail_{n}_k10", f"first close below the first_{n} breakout level within 10 bars", below & (cnt == 1)
             & (bs <= 10), (U, NH))
        L.ev(f"fail_{n}_late", f"first close below the first_{n} breakout level 11-40 bars after the breakout",
             below & (cnt == 1) & (bs > 10) & (bs <= 40), (U,))
        # retest that holds: low comes back to within 0.5 ATR of the level, close stays above it
        touch = (lo <= lvl + 0.5 * atr) & (c > lvl) & (bs >= 1) & (bs <= 10) & (cnt == 0)
        L.ev(f"retest_{n}", f"within 10 bars of first_{n}: low <= level + 0.5 ATR, close > level, no close below "
             "the level since the breakout (first such bar)", touch & (count_since(touch, last) == 1), (U, NH))

    # ---- K. the mirror: breakdowns to new closing lows
    L.header("K. new N-bar closing LOW, first in 10 bars.  NL = within 3% above the same prior low, no new low today")
    for n in (20, 55, 252):
        pl = ta.shift(ta.lowest(c, n), 1)
        nl = c < pl
        L.ev(f"low_first_{n}", f"close < lowest(close,{n})[1], first in 10 bars", first_in(nl, 10),
             (U, ("NL", (c <= 1.03 * pl) & ~nl)))
    pl = ta.shift(ta.lowest(c, 20), 1)
    L.ev("low_first_20_up200", "close < lowest(close,20)[1], first in 10 bars, close > sma(200)",
         first_in(c < pl, 10) & up200, (U,))

    # ---- L. size and shape of the breakout bar
    L.header("L. size of the breakout bar.  Z = all names with the same 1-day z bucket (isolates new-high from up-day)")
    z1 = S.z(1)
    ext = (c - L.ph(55)) / atr
    f55 = L.first(55)
    for nm, m in (("z<=1", z1 <= 1), ("z1-2", (z1 > 1) & (z1 <= 2)), ("z2-3", (z1 > 2) & (z1 <= 3)), ("z>3", z1 > 3)):
        L.ev(f"first_55_{nm}", f"first_55 and 1-day z in bucket {nm}", f55 & m, (U, ("Z", m), ("NH", L.near(55))))
    for nm, m in (("ext<.25", ext < 0.25), ("ext.25-1", (ext >= 0.25) & (ext < 1)), ("ext>1", ext >= 1)):
        L.ev(f"first_55_{nm}", f"first_55 and (close - prior high)/ATR in bucket {nm}", f55 & m, (U, ("NH", L.near(55))))
    gapup = L.op > L.ph(55)
    L.ev("first_55_gap", "first_55 and the OPEN was already above the prior 55-bar closing high", f55 & gapup,
         (U, ("NH", L.near(55))))
    L.ev("first_55_nogap", "first_55 and the open was at or below the prior high (intraday breakout)", f55 & ~gapup,
         (U, ("NH", L.near(55))))

    # ---- M. how much of the breakout day's strength continues into the next open (not capturable)
    g = S.gap()
    print("\n--- M. overnight gap close(t)->open(t+1), XS vs universe, bp (t): what the bar-close trader misses or pays")
    gaps = {}
    for key, sig in (("first_20", L.first(20)), ("first_55", L.first(55)), ("first_252", L.first(252)),
                     ("first_55_rv2", L.first(55) & (rv >= 2.0)), ("near_55", L.near(55))):
        d, _ = E.spread_series(g, sig & S.uni, S.uni)
        m, t, n = E.nw_mean(d[S.rows], 2)
        gaps[key] = {"gap_xs_bp": _r(1e4 * m), "gap_t": _r(t, 2)}
        log_trial(f"F06.{key}", FAMILY, f"{key}: overnight gap close(t)->open(t+1) (xs)", S.sample, "gap_xs_bp",
                  1e4 * m, tstat=t, n=int((sig & S.uni).sum()), note=RUN_NOTE)
        print(f"{key:<30s}{1e4 * m:+7.1f} ({t:+5.1f})")
    L.res["p1_gap"] = gaps


# ============================================================================== driver
PASSES = {"p1": p1}


def run(sample: str, passes) -> dict:
    L = Lab(sample)
    for name in passes:
        t0 = time.time()
        print(f"\n================ {sample} / {name} ================")
        PASSES[name](L)
        print(f"[{sample}/{name}] {time.time() - t0:.0f}s")
    res = L.res
    res["_variants"] = L.variants
    del L
    gc.collect()
    return res


def main(argv) -> None:
    samples = [a for a in argv if a in ("DEV", "CTX")] or ["DEV", "CTX"]
    passes = [a for a in argv if a in PASSES] or list(PASSES)
    saved = json.loads(OUT.read_text()) if OUT.exists() else {}
    for sample in samples:
        res = run(sample, passes)
        cur = saved.setdefault(sample, {})
        variants = {**cur.get("_variants", {}), **res.pop("_variants")}
        cur.update(res)
        cur["_variants"] = variants
        OUT.write_text(json.dumps(saved, indent=0))
        print(f"\n[{sample}] distinct signal definitions so far: {len(variants)}  -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1:])
