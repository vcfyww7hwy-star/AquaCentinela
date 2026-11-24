"""F05 - Volume as information.

Development data only (protocol section 2):
    DEV  2011-01..2018-06  liquid US stocks (universe biased to names alive in 2018)
    CTX  1998-01..2010-12  Yahoo survivors (strongly biased; two bear markets)

Every outcome is a total return from the OPEN of the bar after the signal (Study.fwd). Every
feature uses bars <= t only and is written with the Pine-like primitives, so each has a one-line
Pine recipe (see FEATURES below and docs/_raw/exp_f05_volume.md).

Views per cell (same definitions as Study.event; `Ev` below is a faster, numerically identical
re-implementation that is checked against Study.event at start-up and logs every cell):
    XS  signal mean minus the mean of the control on the same day (control = universe, or `base`
        when the question is "what does volume add to a price state")
    TS  event-weighted signal mean minus the universe's sample average (includes market timing)

Run:   cd swing-lab && python -m research.experiments.f05_volume            (DEV then CTX, all passes)
       python -m research.experiments.f05_volume DEV p1                     (one sample, one pass)
Saves: research/results/f05_volume.json

TradingView caveat: volume on a default chart can be one exchange family (e.g. Cboe One) rather
than the consolidated tape. Only RELATIVE measures (volume over its own trailing median, ranks in
the stock's own history, shares of up-volume) are used; nothing here uses an absolute level.

FEATURES (Pine recipes; v=volume, c=close)
    rv20     v / ta.median(v,20)[1]                       rv60: same with 60
    dvz60    x=math.log(v*c); (x - ta.sma(x,60)[1]) / ta.stdev(x,60)[1]
    rv5      ta.sma(v,5) / ta.median(v,60)[5]
    vr50     ta.percentrank(v,49)                         (>=90: top 10% of the last 50 days)
    vt       ta.sma(v,20) / ta.sma(v,100)
    uvsN     math.sum(c>c[1] ? v : 0, N) / math.sum(v, N)
    obvs20   ta.linreg(ta.obv,20,0)-ta.linreg(ta.obv,20,1)  divided by ta.sma(v,20)
    accN     math.sum((c/c[1]-1>=0.002 and v>v[1]) ? 1 : 0, 25);  distN: same with <=-0.002
    pp       c>c[1] and v > ta.highest(c<c[1] ? v : 0, 10)[1]
    down3    mean volume of the last 3 down days / ta.sma(v,50)
    cmf20    math.sum(((c-l)-(h-c))/(h-l)*v,20)/math.sum(v,20)
    mfi14    ta.mfi(hlc3,14)
    vwg20    math.log( (math.sum(hlc3*v,20)/math.sum(v,20)) / ta.sma(hlc3,20) ) / sigma
    pvc20    ta.correlation(math.log(c/c[1]), math.log(v/ta.median(v,20)[1]), 20)
"""
from __future__ import annotations

import os

os.environ["SWINGLAB_REGISTRY_TAG"] = "f05"          # before importing swinglab

import gc
import json
import sys
import time
from pathlib import Path

import bottleneck as bn
import numpy as np

from research.swinglab import engine as E
from research.swinglab import pinelike as ta
from research.swinglab import trades as TR
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

FAM = "F05_volume"
HS = (1, 3, 5, 10, 20, 40)
INF = np.inf
RESULTS = Path(__file__).resolve().parents[1] / "results" / "f05_volume.json"


# ============================================================================= fast evaluator
class Ev:
    """Study.event on the sample's rows only, with the control means cached. Same numbers."""

    def __init__(self, S: Study, hs=HS):
        self.S, self.hs = S, tuple(hs)
        r = np.flatnonzero(S.rows)
        assert r[-1] - r[0] + 1 == len(r), "sample rows must be contiguous"
        self.sl = slice(int(r[0]), int(r[-1]) + 1)
        self.R = len(r)
        self.uni = S.uni[self.sl]
        self.dates = S.dates[self.sl]
        self.years = self.dates.astype("datetime64[Y]").astype(int) + 1970
        self.out0, self.fin, self.pos, self._ctrl, self._uni = {}, {}, {}, {}, {}
        for h in self.hs:
            f = S.fwd(h)[self.sl]
            fin = np.isfinite(f)
            self.fin[h] = fin
            self.out0[h] = np.where(fin, f, 0.0)
            self.pos[h] = fin & (f > 0)
            m, _ = self._means(self.uni, h, 20)
            ok = np.isfinite(m)
            self._uni[h] = (m, ok, float(np.nanmean(m[ok])) if ok.any() else np.nan)
        self.tables: dict = {}
        self.n_signals = 0

    def _means(self, mask, h, min_n):
        sf = mask & self.fin[h]
        cnt = np.count_nonzero(sf, axis=1)
        s = np.where(sf, self.out0[h], 0.0).sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(cnt >= min_n, s / cnt, np.nan), cnt

    def cell(self, sig, h, ctrl=None, ctrl_key=None, series=False):
        """sig must already be restricted to the universe (and to ctrl if given)."""
        ms, ns = self._means(sig, h, 1)
        if ctrl is None:
            mc = self._uni[h][0]
        else:
            k = (ctrl_key, h)
            if ctrl_key is None or k not in self._ctrl:
                mc, _ = self._means(ctrl, h, 20)
                if ctrl_key is not None:
                    self._ctrl[k] = mc
            else:
                mc = self._ctrl[k]
        d = ms - mc
        xs_m, xs_t, days = E.nw_mean(d, 2 * h)
        m_uni, ok, ubar = self._uni[h]
        ts_m = ts_t = np.nan
        if ok.sum() >= 60:
            n = np.where(ok & np.isfinite(ms), ns, 0).astype(float)
            if n.sum() >= 50:
                x = np.where(n > 0, n * (np.nan_to_num(ms) - ubar), 0.0)[ok] / n[ok].mean()
                ts_m, ts_t, _ = E.nw_mean(x, 2 * h)
        tot = int(ns.sum())
        raw = float(np.where(sig & self.fin[h], self.out0[h], 0.0).sum() / tot) if tot else np.nan
        hit = float(np.count_nonzero(sig & self.pos[h]) / tot) if tot else np.nan
        c = {"xs_bp": _r(1e4 * xs_m, 1), "xs_t": _r(xs_t, 2), "ts_bp": _r(1e4 * ts_m, 1), "ts_t": _r(ts_t, 2),
             "raw_bp": _r(1e4 * raw, 1), "hit": _r(hit, 3), "events": int(np.count_nonzero(sig)), "days": int(days)}
        return (c, d) if series else c

    def event(self, sec, label, defn, sig, *, base=None, base_key=None, params=None, hs=None, note="",
              store=True):
        """Evaluate one boolean signal [R, N]; log every cell; store in self.tables[sec][label]."""
        ctrl = None
        sig = sig & self.uni
        if base is not None:
            ctrl = base & self.uni
            sig = sig & ctrl
        row = {}
        hid = f"F05.{sec}"
        for h in (hs or self.hs):
            c = self.cell(sig, h, ctrl, base_key)
            row[h] = c
            for view in ("xs", "ts"):
                val = c[f"{view}_bp"]
                log_trial(hid, FAM, f"{defn} -> fwd_open_{h} ({view})", self.S.sample, f"{view}_bp",
                          float("nan") if val is None else val, params={**(params or {}), "h": h},
                          universe=f"adv>={self.S.adv_min:.0f}" + (f" base={base_key}" if base is not None else ""),
                          tstat=c[f"{view}_t"], n=c["events"], note=note)
        self.n_signals += 1
        if store:
            self.tables.setdefault(sec, {})[label] = {"def": defn, "base": base_key, **{str(h): v for h, v in row.items()}}
        return row

    def buckets(self, sec, name, feat, edges, *, base=None, base_key=None, defn=None, prefix=""):
        out = {}
        ok = np.isfinite(feat)
        for lo, hi in zip(edges[:-1], edges[1:]):
            lab = f"{prefix}{name} ({_f(lo)},{_f(hi)}]"
            sig = ok & (feat > lo) & (feat <= hi)
            out[lab] = self.event(sec, lab, f"{defn or name} in ({_f(lo)},{_f(hi)}]" + (f" | base {base_key}" if base is not None else ""),
                                  sig, base=base, base_key=base_key, params={"lo": _f(lo), "hi": _f(hi)})
        return out

    def quantiles(self, sec, name, feat, q=5, *, base=None, base_key=None, defn=None):
        b = self.uni if base is None else (base & self.uni)
        rk = E.xs_rank(feat, b)
        out = {}
        for i in range(q):
            lab = f"{name} xsQ{i + 1}/{q} [screener]"
            sig = b & (rk > i / q) & (rk <= (i + 1) / q)
            out[lab] = self.event(sec, lab, f"{defn or name} cross-sectional quantile {i + 1}/{q} (needs screener)"
                                  + (f" | base {base_key}" if base is not None else ""), sig, base=base,
                                  base_key=base_key, params={"q": i + 1, "of": q})
        return out

    def by_year(self, sec, label, defn, sig, h, *, base=None, base_key=None):
        """XS spread by calendar year (bp, t, events). Each year is a logged look."""
        ctrl = None
        sig = sig & self.uni
        if base is not None:
            ctrl = base & self.uni
            sig = sig & ctrl
        _, d = self.cell(sig, h, ctrl, base_key, series=True)
        ev = np.count_nonzero(sig & self.fin[h], axis=1)
        out = {}
        for y in np.unique(self.years):
            m = self.years == y
            x = d[m]
            x = x[np.isfinite(x)]
            if len(x) < 20:
                continue
            mean, t, n = E.nw_mean(x, 2 * h)
            out[int(y)] = {"xs_bp": _r(1e4 * mean, 1), "xs_t": _r(t, 2), "days": n, "events": int(ev[m].sum())}
            log_trial(f"F05.{sec}", FAM, f"{defn} -> fwd_open_{h} (xs) year={y}", self.S.sample, "xs_bp",
                      1e4 * mean, params={"h": h, "year": int(y)}, universe=f"adv>={self.S.adv_min:.0f}",
                      tstat=t, n=int(ev[m].sum()), note="by-year cut")
        # drop the best calendar month
        ym = self.dates.astype("datetime64[M]")
        fin = np.isfinite(d)
        tot = np.nansum(d)
        best, drop = None, None
        for mth in np.unique(ym[fin]):
            s = np.nansum(d[ym == mth])
            if best is None or abs(s) > abs(best):
                if np.sign(s) == np.sign(tot):
                    best, drop = s, mth
        if drop is not None:
            x = d[fin & (ym != drop)]
            mean, t, n = E.nw_mean(x, 2 * h)
            out["ex_best_month"] = {"xs_bp": _r(1e4 * mean, 1), "xs_t": _r(t, 2), "month": str(drop)}
            log_trial(f"F05.{sec}", FAM, f"{defn} -> fwd_open_{h} (xs) without best month", self.S.sample, "xs_bp",
                      1e4 * mean, params={"h": h, "dropped": str(drop)}, tstat=t, note="best month removed")
        self.tables.setdefault(sec + "_byyear", {})[f"{label} h={h}"] = out
        return out


def _r(x, nd):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def _f(x):
    return "-inf" if x == -INF else "inf" if x == INF else (int(x) if float(x).is_integer() else float(x))


def show(tab: dict, title: str, hs_xs=HS, hs_ts=(5, 20, 40)) -> None:
    print(f"\n### {title}")
    w = max([len(k) for k in tab] + [10])
    print(f"{'':<{w}s} | XS bp(t) " + " ".join(f"{'h=' + str(h):>12s}" for h in hs_xs)[9:]
          + " | TS bp(t) " + " ".join(f"{'h=' + str(h):>12s}" for h in hs_ts)[9:] + " |  events")
    for lab, row in tab.items():
        line = f"{lab:<{w}s} |"
        for h in hs_xs:
            c = row[h]
            line += f"{'' if c['xs_bp'] is None else f'{c['xs_bp']:+.0f}({c['xs_t']:+.1f})':>13s}"
        line += " |"
        for h in hs_ts:
            c = row[h]
            line += f"{'' if c['ts_bp'] is None else f'{c['ts_bp']:+.0f}({c['ts_t']:+.1f})':>13s}"
        print(line + f" | {row[hs_xs[0]]['events']:>8d}")


# ============================================================================= rolling helpers
def _mc(n):
    return max(1, int(0.8 * n))


def rmed(x, n):
    return bn.move_median(x, window=n, min_count=_mc(n), axis=0)


def rmean(x, n):
    return bn.move_mean(x, window=n, min_count=_mc(n), axis=0)


def rsum(x, n):
    return bn.move_sum(x, window=n, min_count=_mc(n), axis=0)


def rstd(x, n):
    return bn.move_std(x, window=n, min_count=_mc(n), axis=0, ddof=0)


def rmax(x, n):
    return bn.move_max(x, window=n, min_count=_mc(n), axis=0)


def rmin(x, n):
    return bn.move_min(x, window=n, min_count=_mc(n), axis=0)


def ratio(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        x = a / b
    return np.where(np.isfinite(x), x, np.nan)


def rcorr(x, y, n):
    ok = np.isfinite(x) & np.isfinite(y)
    x = np.where(ok, x, np.nan)
    y = np.where(ok, y, np.nan)
    mx, my = rmean(x, n), rmean(y, n)
    cov = rmean(x * y, n) - mx * my
    return ratio(cov, rstd(x, n) * rstd(y, n))


def last3_down_mean(v, dn):
    """Mean volume of the three most recent down days up to and including t."""
    T, N = v.shape
    buf = np.full((3, N), np.nan)
    out = np.full((T, N), np.nan)
    for t in range(T):
        d = dn[t] & np.isfinite(v[t])
        if d.any():
            buf[0, d] = buf[1, d]
            buf[1, d] = buf[2, d]
            buf[2, d] = v[t, d]
        out[t] = buf.mean(axis=0)
    return out


# ============================================================================= features
class Feats:
    """All inputs known at the close of t, sliced to the sample's rows as float32 / bool."""

    def __init__(self, S: Study, sl: slice):
        t0 = time.time()
        P = S.P
        c, v = P.cf, P.v
        hi = np.where(np.isfinite(P.h), P.h, c)
        lo = np.where(np.isfinite(P.l), P.l, c)
        pc = ta.shift(c, 1)
        r1 = ratio(c, pc) - 1.0
        up, dn = r1 > 0, r1 < 0
        f32 = lambda x: np.asarray(x[sl], dtype=np.float32)            # noqa: E731
        self.N = c.shape[1]
        self.sl = sl
        # --- price states (for interactions and controls)
        self.z1, self.z3, self.z5, self.z10, self.z20 = (f32(S.z(k)) for k in (1, 3, 5, 10, 20))
        self.r1 = f32(r1)
        self.up, self.dn = up[sl], dn[sl]
        sma10, sma20, sma50, sma200 = (ta.sma(c, n) for n in (10, 20, 50, 200))
        self.above50 = (c > sma50)[sl]
        self.above200 = (c > sma200)[sl]
        self.up_trend = ((c > sma50) & (sma50 > sma200))[sl]
        self.below10 = (c < sma10)[sl]
        self.near10 = (np.abs(ratio(c, sma10) - 1.0) <= 0.02)[sl]
        self.near50 = (np.abs(ratio(c, sma50) - 1.0) <= 0.03)[sl]
        hh20, hh50, ll20, ll50 = ta.highest(c, 20), ta.highest(c, 50), ta.lowest(c, 20), ta.lowest(c, 50)
        self.hi20, self.hi50 = (c >= hh20)[sl], (c >= hh50)[sl]
        self.lo20, self.lo50 = (c <= ll20)[sl], (c <= ll50)[sl]
        self.since_hi50 = f32(ta.barssince(c >= hh50))
        new_hi50 = (c >= hh50) & ~(ta.shift((ta.rolling_sum((c >= hh50).astype(float), 10)), 1) > 0)
        new_lo50 = (c <= ll50) & ~(ta.shift((ta.rolling_sum((c <= ll50).astype(float), 10)), 1) > 0)
        self.brk50, self.bdn50 = new_hi50[sl], new_lo50[sl]
        dn5 = rsum(dn.astype(float), 5)
        self.dn3of5 = (dn5 >= 3)[sl]
        del sma10, sma20, hh20, ll20, ll50
        # --- relative volume
        med20, med60 = ta.shift(rmed(v, 20), 1), ta.shift(rmed(v, 60), 1)
        rv20 = ratio(v, med20)
        self.rv20 = f32(rv20)
        self.rv60 = f32(ratio(v, med60))
        with np.errstate(divide="ignore", invalid="ignore"):
            ldv = np.log(v * c)
        ldv = np.where(np.isfinite(ldv), ldv, np.nan)
        self.dvz60 = f32(ratio(ldv - ta.shift(rmean(ldv, 60), 1), ta.shift(rstd(ldv, 60), 1)))
        self.rv5 = f32(ratio(rmean(v, 5), ta.shift(rmed(v, 60), 5)))
        self.rv3 = f32(ratio(rmean(v, 3), ta.shift(rmed(v, 60), 3)))
        self.vr50 = f32(ta.percentrank(v, 49))
        self.vr20 = f32(ta.percentrank(v, 19))
        self.vr100 = f32(ta.percentrank(v, 99))
        self.vhi250 = (v >= rmax(v, 250))[sl]
        # consecutive-day patterns
        lowv = (rv20 < 0.7).astype(float)
        highv = (rv20 > 1.5).astype(float)
        self.low3 = (rsum(lowv, 3) >= 3)[sl]
        self.high3 = (rsum(highv, 3) >= 3)[sl]
        self.high3up = ((rsum(highv * up, 3) >= 3))[sl]
        self.high3dn = ((rsum(highv * dn, 3) >= 3))[sl]
        # market-wide volume (SPY on the chart via request.security; xs median needs a screener)
        spy = S.spy
        self.spy_rv20 = rv20[sl, spy].astype(np.float32)
        self.rv20_rel_spy = f32(ratio(rv20, rv20[:, [spy]]))
        uni = S.uni[sl]
        medx = np.array([np.nanmedian(row[m]) if m.sum() > 20 else np.nan for row, m in zip(self.rv20, uni)])
        self.xs_med_rv20 = medx
        self.rv20_adj = (self.rv20 / medx[:, None]).astype(np.float32)
        self.breadth_rv2 = np.array([np.nanmean(row[m] >= 2.0) if m.sum() > 20 else np.nan
                                     for row, m in zip(self.rv20, uni)])
        del med20, med60, ldv, lowv, highv
        # --- volume trend, up-volume share
        self.vt = f32(ratio(rmean(v, 20), rmean(v, 100)))
        self.vt_10_50 = f32(ratio(rmean(v, 10), rmean(v, 50)))
        upv = np.where(up, v, np.where(np.isfinite(v), 0.0, np.nan))
        dnv = np.where(dn, v, np.where(np.isfinite(v), 0.0, np.nan))
        self.uvs20 = f32(ratio(rsum(upv, 20), rsum(v, 20)))
        self.uvs50 = f32(ratio(rsum(upv, 50), rsum(v, 50)))
        self.udr50 = f32(ratio(rsum(upv, 50), rsum(dnv, 50)))
        # --- OBV
        sgn = np.sign(np.nan_to_num(c - pc))
        obv = np.cumsum(sgn * np.nan_to_num(v), axis=0)
        has = np.isfinite(c)
        mv20 = rmean(v, 20)
        self.obvs20 = f32(np.where(has, ratio(ta.linreg_slope(obv, 20), mv20), np.nan))
        self.obvs50 = f32(np.where(has, ratio(ta.linreg_slope(obv, 50), rmean(v, 50)), np.nan))
        obv_n = np.where(has, obv, np.nan)
        self.obv_hi50 = (obv_n >= ta.highest(obv_n, 50))[sl]
        self.obv_hi100 = (obv_n >= ta.highest(obv_n, 100))[sl]
        self.obv_lo50 = (obv_n <= ta.lowest(obv_n, 50))[sl]
        self.px_hi100 = (c >= ta.highest(c, 100))[sl]
        self.since_hi100 = f32(ta.barssince(c >= ta.highest(c, 100)))
        self.since_lo50 = f32(ta.barssince(c <= ta.lowest(c, 50)))
        del obv, obv_n, sgn
        # --- accumulation / distribution day counts (25 bars)
        pv = ta.shift(v, 1)
        acc = ((r1 >= 0.002) & (v > pv)).astype(float)
        dist = ((r1 <= -0.002) & (v > pv)).astype(float)
        self.acc25 = f32(rsum(acc, 25))
        self.dist25 = f32(rsum(dist, 25))
        self.spy_dist25 = self.dist25[:, spy].copy()
        self.spy_acc25 = self.acc25[:, spy].copy()
        self.spy_z1 = self.z1[:, spy].copy()
        self.spy_uvs20 = self.uvs20[:, spy].copy()
        self.spy_above200 = self.above200[:, spy].copy()
        del acc, dist
        # --- pocket pivot
        maxdn10 = ta.shift(rmax(np.nan_to_num(dnv), 10), 1)
        self.pp = (up & (v > maxdn10) & np.isfinite(maxdn10))[sl]
        maxdn5 = ta.shift(rmax(np.nan_to_num(dnv), 5), 1)
        self.pp5 = (up & (v > maxdn5) & np.isfinite(maxdn5))[sl]
        maxdn20 = ta.shift(rmax(np.nan_to_num(dnv), 20), 1)
        self.pp20 = (up & (v > maxdn20) & np.isfinite(maxdn20))[sl]
        del maxdn10, maxdn5, maxdn20
        # --- dry-up
        mv50 = rmean(v, 50)
        self.down3 = f32(ratio(last3_down_mean(v, dn), mv50))
        self.last3 = f32(ratio(rmean(v, 3), mv50))
        # --- money flow style
        rng = hi - lo
        mfm = np.where(rng > 0, ((c - lo) - (hi - c)) / np.where(rng > 0, rng, 1.0), 0.0)
        mfm = np.where(np.isfinite(v), mfm, np.nan)
        self.cmf20 = f32(ratio(rsum(mfm * v, 20), rsum(v, 20)))
        tp = (hi + lo + c) / 3.0
        ptp = ta.shift(tp, 1)
        posf = np.where(tp > ptp, tp * v, np.where(np.isfinite(tp * v), 0.0, np.nan))
        negf = np.where(tp < ptp, tp * v, np.where(np.isfinite(tp * v), 0.0, np.nan))
        with np.errstate(divide="ignore", invalid="ignore"):
            mfi = 100.0 - 100.0 / (1.0 + rsum(posf, 14) / rsum(negf, 14))
        self.mfi14 = f32(mfi)
        vw20 = ratio(rsum(tp * v, 20), rsum(v, 20))
        with np.errstate(divide="ignore", invalid="ignore"):
            self.vwg20 = f32(ratio(np.log(vw20 / rmean(tp, 20)), S.vol))
        del mfm, posf, negf, vw20, tp, ptp
        # --- price-volume correlation
        with np.errstate(divide="ignore", invalid="ignore"):
            lr = np.log(ratio(c, pc))
            lrv = np.log(rv20)
        lrv = np.where(np.isfinite(lrv), lrv, np.nan)
        self.pvc20 = f32(rcorr(lr, lrv, 20))
        self.pvc50 = f32(rcorr(lr, lrv, 50))
        # --- Amihud illiquidity, 5 bars over 60
        il = ratio(np.abs(lr), v * c)
        self.amr = f32(ratio(rmean(il, 5), ta.shift(rmean(il, 60), 5)))
        del il, lr, lrv
        # --- liquidity level (needs screener; proxy only, no shares outstanding in the data)
        self.adv_rank = E.xs_rank(np.asarray(S.adv60[sl], dtype=np.float64), uni).astype(np.float32)
        self.half_a = np.broadcast_to(S.half_a[None, :], uni.shape)
        print(f"  features built in {time.time() - t0:.0f}s")


# ============================================================================= pass 1: broad map
def pass1(X: Ev, F: Feats) -> None:
    uni = X.uni
    T = X.tables
    # ---------- 1. relative volume, unconditional
    sec = "RV"
    X.buckets(sec, "rv20", F.rv20, (0, 0.5, 0.75, 1, 1.5, 2, 3, 5, INF), defn="rv20 = v/median(v,20)[1]")
    X.buckets(sec, "rv60", F.rv60, (0, 0.5, 0.75, 1, 1.5, 2, 3, 5, INF), defn="rv60 = v/median(v,60)[1]")
    X.buckets(sec, "dvz60", F.dvz60, (-INF, -2, -1, 0, 1, 2, 3, INF), defn="dvz60 = z-score of log dollar volume vs previous 60 bars")
    X.buckets(sec, "rv5", F.rv5, (0, 0.6, 0.8, 1.2, 1.8, 2.5, INF), defn="rv5 = sma(v,5)/median(v,60)[5]")
    X.buckets(sec, "rv20/SPY", F.rv20_rel_spy, (0, 0.5, 0.75, 1.33, 2, 3, INF), defn="rv20 of stock / rv20 of SPY")
    X.buckets(sec, "rv20/xsmed", F.rv20_adj, (0, 0.5, 0.75, 1.33, 2, 3, INF), defn="rv20 / cross-sectional median rv20 (needs screener)")
    X.quantiles(sec, "rv20", F.rv20)
    X.quantiles(sec, "dvz60", F.dvz60)
    show(_rows(T[sec]), "1. Relative volume today (control: universe)")

    # ---------- 2. Gervais-Kaniel-Mingelgrin high-volume premium
    sec = "GKM"
    small = np.abs(F.z1) < 0.5
    hi, lo, mid = F.vr50 >= 90, F.vr50 <= 10, (F.vr50 > 10) & (F.vr50 < 90)
    X.event(sec, "vr50 top10%", "volume in top 10% of own last 50 days (percentrank(v,49)>=90)", hi)
    X.event(sec, "vr50 mid", "volume in middle 80% of own last 50 days", mid)
    X.event(sec, "vr50 bottom10%", "volume in bottom 10% of own last 50 days (percentrank(v,49)<=10)", lo)
    X.event(sec, "top10% & |z1|<0.5", "vr50 top 10% and |z1|<0.5 | base |z1|<0.5", hi, base=small, base_key="|z1|<0.5")
    X.event(sec, "bottom10% & |z1|<0.5", "vr50 bottom 10% and |z1|<0.5 | base |z1|<0.5", lo, base=small, base_key="|z1|<0.5")
    upb, dnb = (F.z1 >= 0.5) & (F.z1 < 2), (F.z1 <= -0.5) & (F.z1 > -2)
    X.event(sec, "top10% & z1 in [0.5,2)", "vr50 top 10% | base z1 in [0.5,2)", hi, base=upb, base_key="z1[0.5,2)")
    X.event(sec, "top10% & z1 in (-2,-0.5]", "vr50 top 10% | base z1 in (-2,-0.5]", hi, base=dnb, base_key="z1(-2,-0.5]")
    X.event(sec, "bottom10% & z1 in [0.5,2)", "vr50 bottom 10% | base z1 in [0.5,2)", lo, base=upb, base_key="z1[0.5,2)")
    X.event(sec, "bottom10% & z1 in (-2,-0.5]", "vr50 bottom 10% | base z1 in (-2,-0.5]", lo, base=dnb, base_key="z1(-2,-0.5]")
    small5 = np.abs(F.z5) < 0.5
    X.event(sec, "week rv5>=1.5 & |z5|<0.5", "rv5>=1.5 | base |z5|<0.5", F.rv5 >= 1.5, base=small5, base_key="|z5|<0.5")
    X.event(sec, "week rv5<=0.7 & |z5|<0.5", "rv5<=0.7 | base |z5|<0.5", F.rv5 <= 0.7, base=small5, base_key="|z5|<0.5")
    X.event(sec, "vr20 top10%", "volume top 10% of own last 20 days (percentrank(v,19)>=90)", F.vr20 >= 90)
    X.event(sec, "vr100 top10%", "volume top 10% of own last 100 days (percentrank(v,99)>=90)", F.vr100 >= 90)
    X.event(sec, "vr100 bottom10%", "volume bottom 10% of own last 100 days", F.vr100 <= 10)
    show(_rows(T[sec]), "2. High-volume premium (Gervais, Kaniel, Mingelgrin) and low-volume days")

    # ---------- 3. return sign x relative volume (control: same price bucket)
    sec = "Z1xRV"
    zed = (-INF, -3, -2, -1, 0, 1, 2, 3, INF)
    rve = (0, 0.7, 1.0, 1.5, 2.5, INF)
    for a, b in zip(zed[:-1], zed[1:]):
        base = np.isfinite(F.z1) & (F.z1 > a) & (F.z1 <= b)
        key = f"z1({_f(a)},{_f(b)}]"
        X.buckets(sec, "rv20", F.rv20, rve, base=base, base_key=key, prefix=f"{key} ")
    show(_rows(T[sec]), "3. One-day return x relative volume (control: same z1 bucket, any volume)")

    sec = "Z5xRV5"
    zed5 = (-INF, -2, -1, 0, 1, 2, INF)
    for a, b in zip(zed5[:-1], zed5[1:]):
        base = np.isfinite(F.z5) & (F.z5 > a) & (F.z5 <= b)
        key = f"z5({_f(a)},{_f(b)}]"
        X.buckets(sec, "rv5", F.rv5, (0, 0.8, 1.2, 1.8, INF), base=base, base_key=key, prefix=f"{key} ")
    show(_rows(T[sec]), "4. Five-day return x five-day relative volume (control: same z5 bucket)")

    # ---------- 5. Medhat-Schmeling analogue: 20-bar return x volume state
    sec = "Z20xVOL"
    for a, b in zip(zed5[:-1], zed5[1:]):
        base = np.isfinite(F.z20) & (F.z20 > a) & (F.z20 <= b)
        key = f"z20({_f(a)},{_f(b)}]"
        X.buckets(sec, "vt", F.vt, (0, 0.8, 1.25, INF), base=base, base_key=key, prefix=f"{key} ")
    for a, b in zip(zed5[:-1], zed5[1:]):
        base = np.isfinite(F.z20) & (F.z20 > a) & (F.z20 <= b)
        key = f"z20({_f(a)},{_f(b)}]"
        X.buckets(sec, "advRank[screener]", F.adv_rank, (0, 1 / 3, 2 / 3, 1), base=base, base_key=key, prefix=f"{key} ",
                  defn="cross-sectional rank of 60-bar median dollar volume (liquidity level; needs screener)")
    show(_rows(T[sec]), "5. 20-bar return x volume state (vt = sma20/sma100 of volume; adv rank terciles) (control: same z20 bucket)")

    # ---------- 6. volume trend
    sec = "VT"
    X.buckets(sec, "vt", F.vt, (0, 0.6, 0.8, 1.0, 1.25, 1.6, INF), defn="vt = sma(v,20)/sma(v,100)")
    X.buckets(sec, "vt10/50", F.vt_10_50, (0, 0.6, 0.8, 1.0, 1.25, 1.6, INF), defn="sma(v,10)/sma(v,50)")
    X.quantiles(sec, "vt", F.vt)
    show(_rows(T[sec]), "6. Volume trend")

    # ---------- 7. up-volume share
    sec = "UVS"
    X.buckets(sec, "uvs20", F.uvs20, (0, 0.35, 0.45, 0.55, 0.65, 1.0), defn="up-volume share, 20 bars")
    X.buckets(sec, "uvs50", F.uvs50, (0, 0.40, 0.45, 0.50, 0.55, 0.60, 1.0), defn="up-volume share, 50 bars")
    X.quantiles(sec, "uvs20", F.uvs20)
    X.quantiles(sec, "uvs50", F.uvs50)
    for nm, base in (("z20>0.5", F.z20 > 0.5), ("z20<-0.5", F.z20 < -0.5), ("|z20|<=0.5", np.abs(F.z20) <= 0.5)):
        X.buckets(sec, "uvs20", F.uvs20, (0, 0.40, 0.60, 1.0), base=base, base_key=nm, prefix=f"{nm} ")
    show(_rows(T[sec]), "7. Up-volume share (last block: control = same 20-bar return state)")

    # ---------- 8. OBV
    sec = "OBV"
    X.buckets(sec, "obvs20", F.obvs20, (-INF, -0.3, -0.1, 0.1, 0.3, INF), defn="OBV 20-bar regression slope / sma(v,20)")
    X.buckets(sec, "obvs50", F.obvs50, (-INF, -0.2, -0.07, 0.07, 0.2, INF), defn="OBV 50-bar regression slope / sma(v,50)")
    not_hi = ~F.hi50 & (F.since_hi50 >= 5)
    X.event(sec, "OBV hi50, price not (>=5 bars)", "OBV at 50-bar high, close below its 50-bar high for >=5 bars | base price not at 50-bar high >=5 bars",
            F.obv_hi50, base=not_hi, base_key="px_not_hi50_5")
    X.event(sec, "OBV hi50 first, price not", "first bar OBV at 50-bar high (not in previous 5), price not at 50-bar high >=5 bars | same base",
            F.obv_hi50 & ~_any_prev(F.obv_hi50, 5), base=not_hi, base_key="px_not_hi50_5")
    not_hi100 = ~F.px_hi100 & (F.since_hi100 >= 5)
    X.event(sec, "OBV hi100, price not", "OBV at 100-bar high, close below 100-bar high >=5 bars | base price not at 100-bar high",
            F.obv_hi100, base=not_hi100, base_key="px_not_hi100_5")
    X.event(sec, "OBV hi50, price not, c>sma50", "OBV at 50-bar high, price not, close>sma50 | base price not at 50-bar high & close>sma50",
            F.obv_hi50, base=not_hi & F.above50, base_key="px_not_hi50_5&above50")
    X.event(sec, "price hi50, OBV not", "close at 50-bar high, OBV not at its 50-bar high | base close at 50-bar high",
            ~F.obv_hi50, base=F.hi50, base_key="px_hi50")
    not_lo = ~F.lo50 & (F.since_lo50 >= 5)
    X.event(sec, "OBV lo50, price not", "OBV at 50-bar low, close above its 50-bar low >=5 bars | base price not at 50-bar low",
            F.obv_lo50, base=not_lo, base_key="px_not_lo50_5")
    X.event(sec, "price lo50, OBV not", "close at 50-bar low, OBV not at its 50-bar low | base close at 50-bar low",
            ~F.obv_lo50, base=F.lo50, base_key="px_lo50")
    show(_rows(T[sec]), "8. OBV slope and OBV/price divergences")

    # ---------- 9. accumulation / distribution day counts
    sec = "AD"
    X.buckets(sec, "dist25", F.dist25, (-1, 2, 4, 6, 25), defn="distribution days in 25 bars (close<=-0.2% on higher volume)")
    X.buckets(sec, "acc25", F.acc25, (-1, 2, 4, 6, 25), defn="accumulation days in 25 bars (close>=+0.2% on higher volume)")
    net = F.acc25 - F.dist25
    X.buckets(sec, "net25", net, (-26, -4, -2, 1, 3, 25), defn="accumulation minus distribution days, 25 bars")
    X.quantiles(sec, "net25", net + 1e-3 * F.uvs20)
    show(_rows(T[sec]), "9. Accumulation / distribution day counts (25 bars)")

    # ---------- 10. pocket pivot
    sec = "PP"
    X.event(sec, "pp10", "pocket pivot: up day, v > max down-day volume of prior 10 bars", F.pp)
    X.event(sec, "pp10 | up day", "pocket pivot | base up day", F.pp, base=F.up, base_key="up")
    X.event(sec, "pp10 & uptrend | up & uptrend", "pocket pivot in uptrend (c>sma50>sma200) | base up day in uptrend",
            F.pp, base=F.up & F.up_trend, base_key="up&uptrend")
    X.event(sec, "pp10 & near sma10 | same w/o vol", "pocket pivot within 2% of sma10 in uptrend | base up day within 2% of sma10 in uptrend",
            F.pp, base=F.up & F.up_trend & F.near10, base_key="up&uptrend&near10")
    X.event(sec, "pp10 & near sma50 | same w/o vol", "pocket pivot within 3% of sma50, c>sma200 | base up day within 3% of sma50, c>sma200",
            F.pp, base=F.up & F.above200 & F.near50, base_key="up&above200&near50")
    X.event(sec, "pp5 | up day", "pocket pivot (5-bar lookback) | base up day", F.pp5, base=F.up, base_key="up")
    X.event(sec, "pp20 | up day", "pocket pivot (20-bar lookback) | base up day", F.pp20, base=F.up, base_key="up")
    X.event(sec, "pp10 & uptrend (vs universe)", "pocket pivot in uptrend (c>sma50>sma200), control universe", F.pp & F.up_trend)
    show(_rows(T[sec]), "10. Pocket pivot")

    # ---------- 11. volume dry-up on a pullback inside an uptrend
    sec = "DRY"
    pbA = F.above200 & (F.z5 <= -1)
    pbB = F.up_trend & F.below10 & F.dn3of5
    for nm, base in (("uptrend200 & z5<=-1", pbA), ("c>sma50>sma200 & c<sma10 & 3of5 down", pbB)):
        X.buckets(sec, "down3", F.down3, (0, 0.5, 0.7, 1.0, 1.3, INF), base=base, base_key=nm, prefix=f"[{nm}] ",
                  defn="mean volume of last 3 down days / sma(v,50)")
    X.event(sec, "pbA vs universe", "pullback A: close>sma200 and z5<=-1 (no volume condition)", pbA)
    X.event(sec, "pbA & down3<0.5 vs universe", "pullback A with dry-up: last 3 down days' volume < 0.5 x sma50", pbA & (F.down3 < 0.5))
    X.event(sec, "pbA & down3<0.7 vs universe", "pullback A with dry-up < 0.7", pbA & (F.down3 < 0.7))
    X.event(sec, "pbB & last3<0.7 | pbB", "pullback B with last 3 bars' mean volume < 0.7 x sma50 | base pullback B",
            F.last3 < 0.7, base=pbB, base_key="pbB")
    show(_rows(T[sec]), "11. Dry-up during a pullback in an uptrend (control: same pullback, any volume)")

    # ---------- 12. price-volume divergence
    sec = "DIV"
    X.buckets(sec, "pvc20", F.pvc20, (-1, -0.4, -0.15, 0.15, 0.4, 1), defn="20-bar correlation of daily return and log relative volume")
    X.buckets(sec, "pvc50", F.pvc50, (-1, -0.3, -0.1, 0.1, 0.3, 1), defn="50-bar correlation of daily return and log relative volume")
    X.buckets(sec, "vt", F.vt, (0, 0.8, 1.25, INF), base=F.hi20, base_key="close at 20-bar high", prefix="[20-bar high] ")
    X.buckets(sec, "vt", F.vt, (0, 0.8, 1.25, INF), base=F.lo20, base_key="close at 20-bar low", prefix="[20-bar low] ")
    X.buckets(sec, "obvs20", F.obvs20, (-INF, 0, INF), base=F.z20 > 1, base_key="z20>1", prefix="[z20>1] ")
    X.buckets(sec, "obvs20", F.obvs20, (-INF, 0, INF), base=F.z20 < -1, base_key="z20<-1", prefix="[z20<-1] ")
    show(_rows(T[sec]), "12. Price-volume divergence")

    # ---------- 13. classic money-flow indicators
    sec = "CLS"
    X.buckets(sec, "cmf20", F.cmf20, (-1, -0.2, -0.05, 0.05, 0.2, 1), defn="Chaikin money flow 20")
    X.buckets(sec, "mfi14", F.mfi14, (0, 20, 35, 65, 80, 100), defn="money flow index 14")
    X.buckets(sec, "vwg20", F.vwg20, (-INF, -1, -0.3, 0.3, 1, INF), defn="ln(20-bar VWAP / 20-bar SMA of hlc3) / sigma")
    show(_rows(T[sec]), "13. Chaikin money flow, MFI, VWAP-minus-SMA gap")

    # ---------- 14. climax volume
    sec = "CLX"
    for nm, cond in (("z1<=-1", F.z1 <= -1), ("|z1|<1", np.abs(F.z1) < 1), ("z1>=1", F.z1 >= 1)):
        X.event(sec, f"v 250-bar high & {nm}", f"volume at 250-bar high | base {nm}", F.vhi250, base=cond, base_key=nm)
    for nm, cond in (("z1<=-2", F.z1 <= -2), ("z1>=2", F.z1 >= 2)):
        X.event(sec, f"rv20>=5 & {nm}", f"rv20>=5 | base {nm}", F.rv20 >= 5, base=cond, base_key=nm)
        X.event(sec, f"rv20<1.5 & {nm}", f"rv20<1.5 | base {nm}", F.rv20 < 1.5, base=cond, base_key=nm)
    show(_rows(T[sec]), "14. Climax volume (control: same price move)")

    # ---------- 15. volume-confirmed breakouts / breakdowns
    sec = "BRK"
    X.buckets(sec, "rv20", F.rv20, (0, 1.0, 1.5, 2.5, INF), base=F.brk50, base_key="new 50-bar closing high (first in 10)", prefix="[brk50] ")
    X.buckets(sec, "rv20", F.rv20, (0, 1.0, 1.5, 2.5, INF), base=F.bdn50, base_key="new 50-bar closing low (first in 10)", prefix="[bdn50] ")
    X.event(sec, "brk50 vs universe", "new 50-bar closing high, first in 10 bars (no volume condition)", F.brk50)
    X.event(sec, "brk50 & rv20>=1.5 vs universe", "new 50-bar closing high with rv20>=1.5", F.brk50 & (F.rv20 >= 1.5))
    X.event(sec, "bdn50 & rv20>=1.5 vs universe", "new 50-bar closing low with rv20>=1.5", F.bdn50 & (F.rv20 >= 1.5))
    show(_rows(T[sec]), "15. Breakouts and breakdowns by volume (control: same breakout)")

    # ---------- 16. Amihud ratio, quiet / persistent patterns
    sec = "MISC"
    X.buckets(sec, "amr", F.amr, (0, 0.5, 1, 2, INF), defn="Amihud |ret|/dollar volume, 5-bar mean over prior 60-bar mean")
    X.event(sec, "3 bars rv20<0.7", "three consecutive bars with rv20<0.7", F.low3)
    X.event(sec, "3 bars rv20>1.5", "three consecutive bars with rv20>1.5", F.high3)
    X.event(sec, "3 up bars rv20>1.5", "three consecutive up bars with rv20>1.5", F.high3up)
    X.event(sec, "3 down bars rv20>1.5", "three consecutive down bars with rv20>1.5", F.high3dn)
    show(_rows(T[sec]), "16. Amihud ratio; quiet and persistent volume")

    # ---------- 17. market-level volume states (TS view is the one that matters)
    sec = "MKT"
    b = lambda x: uni & x[:, None]                                     # noqa: E731
    X.event(sec, "SPY dist25>=5", "SPY distribution days in 25 bars >= 5 (all universe names)", b(F.spy_dist25 >= 5))
    X.event(sec, "SPY dist25>=7", "SPY distribution days in 25 bars >= 7", b(F.spy_dist25 >= 7))
    X.event(sec, "SPY dist25<=2", "SPY distribution days in 25 bars <= 2", b(F.spy_dist25 <= 2))
    X.event(sec, "SPY acc25>=7", "SPY accumulation days in 25 bars >= 7", b(F.spy_acc25 >= 7))
    X.event(sec, "SPY rv20>=1.5 & z1<=-1", "SPY rv20>=1.5 and SPY z1<=-1", b((F.spy_rv20 >= 1.5) & (F.spy_z1 <= -1)))
    X.event(sec, "SPY rv20<1.5 & z1<=-1", "SPY rv20<1.5 and SPY z1<=-1", b((F.spy_rv20 < 1.5) & (F.spy_z1 <= -1)))
    X.event(sec, "SPY rv20>=1.5 & z1>=1", "SPY rv20>=1.5 and SPY z1>=1", b((F.spy_rv20 >= 1.5) & (F.spy_z1 >= 1)))
    X.event(sec, "SPY rv20<=0.7", "SPY rv20<=0.7", b(F.spy_rv20 <= 0.7))
    X.event(sec, "SPY uvs20<=0.4", "SPY up-volume share 20 <= 0.40", b(F.spy_uvs20 <= 0.40))
    X.event(sec, "SPY uvs20>=0.6", "SPY up-volume share 20 >= 0.60", b(F.spy_uvs20 >= 0.60))
    X.event(sec, "breadth rv20>=2 above 15%", "share of universe with rv20>=2 above 15% (needs screener)", b(F.breadth_rv2 > 0.15))
    X.event(sec, "xs median rv20>=1.3", "cross-sectional median rv20 >= 1.3 (needs screener)", b(F.xs_med_rv20 >= 1.3))
    X.event(sec, "xs median rv20<=0.8", "cross-sectional median rv20 <= 0.8 (needs screener)", b(F.xs_med_rv20 <= 0.8))
    show(_rows(T[sec]), "17. Market-level volume states (signal = every universe name on those days; read TS)")


def _any_prev(x: np.ndarray, n: int) -> np.ndarray:
    """True if x was true on any of the previous n bars (excluding the current one)."""
    s = bn.move_sum(x.astype(float), window=n, min_count=1, axis=0)
    out = np.zeros_like(x)
    out[1:] = s[:-1] > 0
    return out


def _rows(sec_tab: dict) -> dict:
    return {lab: {int(h): c for h, c in row.items() if h not in ("def", "base")} for lab, row in sec_tab.items()}


# ============================================================================= self-check
def selfcheck(S: Study, X: Ev, F: Feats) -> None:
    """Ev must reproduce Study.event. The Study.event numbers are logged too (same values)."""
    full = lambda a: _full(S, X, a)                                    # noqa: E731
    sig = F.rv20 > 2.0
    base = F.z1 <= -1.0
    for name, s, b in (("rv20>2", sig, None), ("rv20>2 | z1<=-1", sig, base)):
        a = S.event("F05.CHECK", FAM, f"self-check {name}", full(s) if b is None else full(s & b),
                    control=None if b is None else full(b), hs=X.hs, note="Ev vs Study.event equality check")
        r = X.event("CHECK", name, f"self-check {name}", s, base=b, base_key=None if b is None else "z1<=-1",
                    note="Ev vs Study.event equality check", store=False)
        for h in X.hs:
            for k in ("xs_bp", "xs_t", "ts_bp", "ts_t", "raw_bp", "hit", "events"):
                x, y = a[h][k], r[h][k]
                assert (x is None and y is None) or abs(x - y) <= 0.051, (name, h, k, x, y)
    print("  self-check passed: Ev == Study.event")


def _full(S: Study, X: Ev, a: np.ndarray) -> np.ndarray:
    out = np.zeros(S.uni.shape, dtype=bool)
    out[X.sl] = a
    return out


# ============================================================================= main
PASSES = {"p1": pass1}


def run(sample: str, passes) -> dict:
    t0 = time.time()
    S = Study(sample, hs=HS)
    X = Ev(S)
    F = Feats(S, X.sl)
    print(f"\n================ {sample}: {X.dates[0]}..{X.dates[-1]}  {X.R} days, "
          f"{X.uni.sum(1).mean():.0f} names/day ================")
    selfcheck(S, X, F)
    for p in passes:
        PASSES[p](X, F)
        print(f"  [{sample} {p}] done at {time.time() - t0:.0f}s, signals so far {X.n_signals}")
    res = {"sample": sample, "dates": [str(X.dates[0]), str(X.dates[-1])], "names_per_day": float(X.uni.sum(1).mean()),
           "signals_evaluated": X.n_signals, "tables": X.tables}
    del S, X, F
    gc.collect()
    return res


if __name__ == "__main__":
    args = sys.argv[1:]
    samples = [a for a in args if a in ("DEV", "CTX")] or ["DEV", "CTX"]
    passes = [a for a in args if a in PASSES] or list(PASSES)
    allres = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    for s in samples:
        r = run(s, passes)
        prev = allres.get(s, {"tables": {}})
        prev_tabs = prev.get("tables", {})
        prev_tabs.update(r["tables"])
        r["tables"] = prev_tabs
        allres[s] = r
        RESULTS.write_text(json.dumps(allres, indent=0))
    print(f"\nsaved {RESULTS}")
