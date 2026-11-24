"""Study: the one object experiments use to evaluate a signal.

It fixes, for every experiment, the things that must not vary by accident:

  * outcomes are total returns from the OPEN of the bar after the signal (protocol section 5);
  * the sample is DEV (2011-01..2018-06, biased universe) or CTX (1998..2010, survivors only);
    outcome arrays are blanked outside the chosen sample and near its end, so a script cannot
    read validation-period returns even by mistake. VAL needs an explicit token and every VAL
    evaluation is logged with partition="VAL";
  * inference is by date (Newey-West), in two views:
        XS  signal mean minus universe mean on the same day (stock-specific part)
        TS  event-weighted signal mean minus the universe's sample-average (includes market-wide
            timing; few independent episodes, so t-statistics are honest about that);
  * every evaluated cell is written to the trial registry.

Typical use
-----------
    from research.swinglab.study import Study
    from research.swinglab import pinelike as ta
    S = Study("DEV")                       # or "CTX"
    c = S.P.cf                             # forward-filled split-adjusted close  [T, N]
    sig = S.uni & (c > ta.sma(c, 200)) & (S.z(5) <= -1.5)
    tab = S.event("F1", "dip_in_uptrend", "z5<=-1.5 & c>sma200", sig, params={"z": -1.5})
    S.show(tab)
"""
from __future__ import annotations

import os

import numpy as np

from . import engine as E
from . import pinelike as ta
from .data import STOCK_TYPES, load_ctx, load_panel
from .registry import log_trial

HS = (1, 3, 5, 10, 20)
MAX_H = 60


class Study:
    def __init__(self, sample: str = "DEV", adv_min: float | None = None, px_min: float = 5.0,
                 types=STOCK_TYPES, hs=HS, panel=None):
        sample = sample.upper()
        if sample == "LOCKBOX":
            # only research/confirm/run_lockbox.py builds this, with the panel that
            # data.open_lockbox() returned (which records the opening in registry/lockbox.json)
            if panel is None or getattr(panel, "name", "") != "full":
                raise PermissionError("LOCKBOX needs the panel returned by data.open_lockbox() (protocol section 2).")
            p = panel
        elif sample in ("VAL", "VAL_S"):
            if os.environ.get("SWINGLAB_VAL_TOKEN") != "PRE-REGISTERED":
                raise PermissionError("VAL is for pre-registered confirmations only (protocol section 3). "
                                      "Register the hypothesis in docs/RESEARCH_LOG.md first.")
            p = load_panel()
        elif sample in ("DEV", "DEV_S"):
            p = load_panel()
        elif sample == "CTX":
            p = load_ctx()
        else:
            raise ValueError("sample must be DEV, CTX, DEV_S, VAL, VAL_S or LOCKBOX")
        self.sample, self.p, self.hs = sample, p, tuple(hs)
        self.adv_min = adv_min if adv_min is not None else (5e6 if sample == "CTX" else 20e6)
        self.rows = p.rows(sample)
        # keep only securities of the requested types that are ever in the widest universe, plus
        # SPY as the market reference (its column index is self.spy)
        wide = p.universe(adv_min=min(self.adv_min, 5e6), px_min=3.0, types=types)
        keep = wide[self.rows].any(axis=0)
        spy_col = p.col("SPY")
        keep[spy_col] = True
        self.cols = np.flatnonzero(keep)
        self.spy = int(np.searchsorted(self.cols, spy_col))
        self.ents = p.ents.iloc[self.cols].reset_index(drop=True)
        self.dates = p.dates
        sub = _SubPanel(p, self.cols)
        self.P = E.prepare(sub)
        uni = sub.universe(adv_min=self.adv_min, px_min=px_min, types=types)
        uni[:, self.spy] = False
        uni[~self.rows] = False
        self.uni = uni
        self.adv60 = np.asarray(sub.adv60, dtype=np.float64)
        self.c_raw = np.asarray(sub.c_raw, dtype=np.float64)
        self.vol = E.vol_ewma(self.P, 20)                  # daily sigma known at the close of t
        self._fwd: dict = {}
        self._z: dict = {}
        r_idx = np.flatnonzero(self.rows)
        self._last_row = int(r_idx[-1])
        self.half_a = np.array([_md5_even(s) for s in self.ents["symbol"]])

    def truncated(self, t_cut: int) -> "Study":
        """A copy of this Study that has never seen rows >= t_cut. Used to prove that a signal
        does not depend on the future: build it on the copy and compare with the full one."""
        import copy
        T = copy.copy(self)
        P = copy.copy(self.P)
        for k in ("o", "h", "l", "c", "cf", "v", "ret", "tri"):
            setattr(P, k, getattr(self.P, k)[:t_cut].copy())
        T.P = P
        T.uni = self.uni[:t_cut].copy()
        T.adv60, T.c_raw = self.adv60[:t_cut], self.c_raw[:t_cut]
        T.dates, T.rows = self.dates[:t_cut], self.rows[:t_cut]
        T.vol = E.vol_ewma(P, 20)
        T._fwd, T._z = {}, {}
        return T

    # ------------------------------------------------------------------ building blocks
    def z(self, k: int) -> np.ndarray:
        """k-day log return in units of the volatility known before the move started."""
        if k not in self._z:
            lc = np.log(self.P.cf)
            with np.errstate(divide="ignore", invalid="ignore"):
                z = (lc - ta.shift(lc, k)) / (ta.shift(self.vol, k) * np.sqrt(k))
            self._z[k] = np.where(np.isfinite(z), z, np.nan)
        return self._z[k]

    def fwd(self, h: int) -> np.ndarray:
        """Total return open(t+1) -> close(t+h); NaN outside the sample or if t+h leaves it."""
        if h not in self._fwd:
            f = E.fwd_ret_open(self.P, h)
            f[~self.rows] = np.nan
            f[max(self._last_row - h + 1, 0):] = np.nan
            self._fwd[h] = f
        return self._fwd[h]

    def mkt(self, h: int) -> np.ndarray:
        """SPY's forward return over the same window, [T]."""
        return self.fwd(h)[:, self.spy]

    def ctx(self, symbol: str, field: str = "close") -> np.ndarray:
        """A market-context series from Yahoo (e.g. '^VIX', '^VIX3M', 'HYG', 'XLK'), aligned to
        self.dates; the value on row t is that day's close, so it is known at the close of t.
        Forward-filled over holidays of that series. Use only as a SIGNAL input."""
        import glob
        import pandas as pd
        frames = [pd.read_parquet(f) for f in glob.glob("/home/user/data/yahoo_ctx/1d_*.parquet")]
        y = pd.concat(frames)
        y = y[y["symbol"] == symbol].drop_duplicates("date").set_index("date")[field].sort_index()
        if y.empty:
            raise KeyError(symbol)
        return y.reindex(pd.DatetimeIndex(self.dates), method="ffill").to_numpy(dtype=float)

    def atr(self, n: int = 14) -> np.ndarray:
        """ta.atr(n) on forward-filled bars."""
        cf = self.P.cf
        h = np.where(np.isfinite(self.P.h), self.P.h, cf)
        l = np.where(np.isfinite(self.P.l), self.P.l, cf)
        return ta.atr(h, l, cf, n)

    def trades(self, sig: np.ndarray, **kw):
        """Simulate entries at the next open with stops/exits (see swinglab.trades.simulate)."""
        from . import trades as TR
        kw.setdefault("atr", self.atr(14))
        atr = kw.pop("atr")
        return TR.simulate(self.P, sig & self.uni, atr, rows=self.rows, **kw)

    def gap(self) -> np.ndarray:
        g = E.overnight_gap(self.P)
        g[~self.rows] = np.nan
        g[self._last_row] = np.nan            # its open belongs to the next sample
        return g

    # ------------------------------------------------------------------ evaluation
    def _ts(self, out, sig, h):
        m_sig, n_sig = E.day_means(out, sig)
        m_uni, _ = E.day_means(out, self.uni, 20)
        ok = self.rows & np.isfinite(m_uni)
        if ok.sum() < 60:
            return np.nan, np.nan
        ubar = np.nanmean(m_uni[ok])
        n = np.where(ok & np.isfinite(m_sig), n_sig, 0).astype(float)
        if n.sum() < 50:
            return np.nan, np.nan
        x = np.where(n > 0, n * (m_sig - ubar), 0.0)[ok] / n[ok].mean()
        m, t, _ = E.nw_mean(x, lags=2 * h)
        return m, t

    def event(self, hid: str, family: str, definition: str, sig: np.ndarray, *, params: dict | None = None,
              control: np.ndarray | None = None, hs=None, log: bool = True, note: str = "") -> dict:
        """Evaluate a boolean signal [T, N]. `control` defaults to the whole universe on the same day.

        Returns {h: {...}} with, per horizon: xs_bp, xs_t (vs control, same day), ts_bp, ts_t
        (vs the universe's sample average), raw_bp (plain mean outcome of signals, event-weighted),
        hit (share of signal outcomes > 0), events, days.
        """
        sig = sig & self.uni
        ctrl = self.uni if control is None else (control & self.uni)
        res = {}
        n_events = int(sig.sum())
        for h in (hs or self.hs):
            out = self.fwd(h)
            d, ns = E.spread_series(out, sig, ctrl)
            xs_m, xs_t, days = E.nw_mean(d[self.rows], 2 * h)
            ts_m, ts_t = self._ts(out, sig, h)
            vals = out[sig]
            vals = vals[np.isfinite(vals)]
            cell = {
                "xs_bp": _r(1e4 * xs_m, 1), "xs_t": _r(xs_t, 2), "ts_bp": _r(1e4 * ts_m, 1), "ts_t": _r(ts_t, 2),
                "raw_bp": _r(1e4 * vals.mean(), 1) if len(vals) else None,
                "hit": _r(float((vals > 0).mean()), 3) if len(vals) else None,
                "events": n_events, "days": int(days),
            }
            res[h] = cell
            if log:
                for view in ("xs", "ts"):
                    log_trial(hid, family, f"{definition} -> fwd_open_{h} ({view})", self.sample, f"{view}_bp",
                              cell[f"{view}_bp"] if cell[f"{view}_bp"] is not None else float("nan"),
                              params={**(params or {}), "h": h}, universe=f"adv>={self.adv_min:.0f}",
                              tstat=cell[f"{view}_t"], n=n_events, note=note)
        return res

    def buckets(self, hid: str, family: str, name: str, feature: np.ndarray, edges, *, base: np.ndarray | None = None,
                params: dict | None = None, hs=None, log: bool = True) -> dict:
        """Evaluate each interval (edges[i], edges[i+1]] of a feature. `base` restricts the signal
        AND the control to a sub-universe (e.g. names in an uptrend)."""
        base = self.uni if base is None else (base & self.uni)
        out = {}
        for i in range(len(edges) - 1):
            lo, hi = edges[i], edges[i + 1]
            sig = base & np.isfinite(feature) & (feature > lo) & (feature <= hi)
            lab = f"({lo},{hi}]"
            out[lab] = self.event(hid, family, f"{name} in {lab}", sig, params={**(params or {}), "lo": lo, "hi": hi},
                                  control=base, hs=hs, log=log)
        return out

    def quantiles(self, hid: str, family: str, name: str, feature: np.ndarray, q: int = 5, *,
                  base: np.ndarray | None = None, params: dict | None = None, hs=None, log: bool = True) -> dict:
        """Cross-sectional quantile sort each day within `base` (default: universe). NOT computable
        on a single chart; relevant for screener-style ranking."""
        base = self.uni if base is None else (base & self.uni)
        rk = E.xs_rank(feature, base)
        out = {}
        for i in range(q):
            sig = base & (rk > i / q) & (rk <= (i + 1) / q)
            out[f"Q{i + 1}"] = self.event(hid, family, f"{name} xs-quantile {i + 1}/{q}", sig,
                                          params={**(params or {}), "q": i + 1, "of": q}, control=base, hs=hs, log=log)
        return out

    @staticmethod
    def show(tab: dict, title: str = "") -> None:
        if title:
            print(f"\n{title}")
        first = next(iter(tab.values()))
        if "xs_bp" in first:                 # single event table {h: cell}
            tab = {"": tab}
        hs = list(next(iter(tab.values())).keys())
        print(f"{'':>16s}" + "".join(f"{'h=' + str(h):>30s}" for h in hs) + "    events")
        print(f"{'':>16s}" + "".join(f"{'XS bp (t)   TS bp (t)':>30s}" for _ in hs))
        for lab, row in tab.items():
            line = f"{lab:>16s}"
            for h in hs:
                c = row[h]
                xs = "" if c["xs_bp"] is None else f"{c['xs_bp']:+6.1f}({c['xs_t']:+4.1f})"
                ts = "" if c["ts_bp"] is None else f"{c['ts_bp']:+6.1f}({c['ts_t']:+4.1f})"
                line += f"{xs:>15s}{ts:>15s}"
            print(line + f"  {row[hs[0]]['events']:>8d}")


def _r(x, nd):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def _md5_even(s: str) -> bool:
    import hashlib
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % 2 == 0


class _SubPanel:
    """A column subset of a Panel that quacks like one for engine.prepare and universe()."""

    def __init__(self, p, cols):
        self._p, self._cols = p, cols
        self.dates = p.dates
        self.ents = p.ents.iloc[cols].reset_index(drop=True)

    def __getattr__(self, item):
        return np.asarray(getattr(self._p, item))[:, self._cols]

    def universe(self, adv_min=20e6, px_min=5.0, types=STOCK_TYPES):
        u = (self.adv60 >= adv_min) & (self.c_raw >= px_min)
        u &= self.ents["type"].isin(types).to_numpy()[None, :]
        u &= np.isfinite(self.c)
        return u
