"""E01 - Anatomy: what follows a k-day move, measured from the next open.

Descriptive map on DEVELOPMENT data only (protocol section 2):
    DEV   merged panel 2011-01..2018-06   (universe biased: alive in 2018)
    CTX   Yahoo survivors 1998-01..2010-12 (strongly biased; has two bear markets)

Signal at the close of t:   z_k = ln(C[t]/C[t-k]) / (sigma[t-k] * sqrt(k))
    sigma = robust EWMA volatility (span 20) known BEFORE the move started.
Buckets of z_k:  <=-3, (-3,-2], (-2,-1], (-1,0], (0,1], (1,2], (2,3], >3
Outcome: total return from the OPEN of t+1 to the close of t+h, h in 1,3,5,10,20.

Two views of every cell:
    XS  cross-sectional: bucket mean minus the universe mean on the same day (stock-specific part;
        a market-wide move cancels out)
    TS  time-series: event-weighted bucket mean minus the universe's average over the whole
        sample (what the trader keeps relative to "any day, any stock"; market-wide moves count)
Inference by date, Newey-West with 2h lags. Also reported: the overnight gap close(t)->open(t+1),
which a trader acting on a bar-close alert cannot capture.

Family "E01_anatomy": 9 lookbacks x 8 buckets x 5 horizons x 2 views x 2 samples = 1,440 cells.
Nothing here is evidence; it tells us where to aim pre-registered tests.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from research.swinglab import engine as E
from research.swinglab.data import load_ctx, load_panel
from research.swinglab.registry import log_trial

KS = (1, 2, 3, 5, 10, 21, 63, 126, 252)
HS = (1, 3, 5, 10, 20)
EDGES = (-np.inf, -3, -2, -1, 0, 1, 2, 3, np.inf)
LABELS = ("<=-3", "-3..-2", "-2..-1", "-1..0", "0..1", "1..2", "2..3", ">3")


def ts_effect(out: np.ndarray, sig: np.ndarray, uni: np.ndarray, rows: np.ndarray, h: int):
    """Event-weighted mean outcome of signals minus the universe's time-average, with a
    date-clustered t-statistic."""
    m_sig, n_sig = E.day_means(out, sig)
    m_uni, _ = E.day_means(out, uni, 20)
    ok = rows & np.isfinite(m_uni)
    ubar = np.nanmean(m_uni[ok])
    n = np.where(ok & np.isfinite(m_sig), n_sig, 0).astype(float)
    if n.sum() < 50:
        return np.nan, np.nan, int(n.sum())
    x = np.where(n > 0, n * (m_sig - ubar), 0.0)[ok] / (n[ok].mean())
    mean, t, _ = E.nw_mean(x, lags=2 * h)
    return mean, t, int(n.sum())


def run(sample: str) -> dict:
    if sample == "DEV":
        p = load_panel(); rows = p.rows("DEV"); adv = 20e6
    else:
        p = load_ctx(); rows = p.rows("CTX"); adv = 5e6
    P = E.prepare(p)
    uni = p.universe(adv_min=adv, px_min=5.0)
    vol = E.vol_ewma(P, 20)
    lc = np.log(P.cf)
    fwd = {h: E.fwd_ret_open(P, h) for h in HS}
    gap = E.overnight_gap(P)
    res = {"sample": sample, "dates": [str(p.dates[rows][0]), str(p.dates[rows][-1])],
           "universe_mean_names": float(uni[rows].sum(axis=1).mean()), "cells": []}
    for k in KS:
        with np.errstate(divide="ignore", invalid="ignore"):
            z = (lc - E.lag(lc, k)) / (E.lag(vol, k) * np.sqrt(k))
        for b in range(len(LABELS)):
            sig = uni & np.isfinite(z) & (z > EDGES[b]) & (z <= EDGES[b + 1])
            sig[~rows] = False
            n_events = int(sig.sum())
            # overnight gap, cross-sectional
            dg, ng = E.spread_series(gap, sig, uni)
            g_mean, g_t, _ = E.nw_mean(dg[rows], 2)
            for h in HS:
                d, ns = E.spread_series(fwd[h], sig, uni)
                xs_m, xs_t, xs_days = E.nw_mean(d[rows], 2 * h)
                ts_m, ts_t, ts_n = ts_effect(fwd[h], sig, uni, rows, h)
                cell = {"k": k, "bucket": LABELS[b], "h": h, "events": n_events,
                        "xs_bp": None if not np.isfinite(xs_m) else round(1e4 * xs_m, 1),
                        "xs_t": None if not np.isfinite(xs_t) else round(xs_t, 2), "xs_days": xs_days,
                        "ts_bp": None if not np.isfinite(ts_m) else round(1e4 * ts_m, 1),
                        "ts_t": None if not np.isfinite(ts_t) else round(ts_t, 2),
                        "gap_xs_bp": None if not np.isfinite(g_mean) else round(1e4 * g_mean, 1),
                        "gap_xs_t": None if not np.isfinite(g_t) else round(g_t, 2)}
                res["cells"].append(cell)
                for view in ("xs", "ts"):
                    log_trial("E01", "E01_anatomy", f"z_{k} in {LABELS[b]} -> fwd_open_{h} ({view})",
                              "DEV" if sample == "DEV" else "CTX", f"{view}_bp",
                              cell[f"{view}_bp"] if cell[f"{view}_bp"] is not None else float("nan"),
                              params={"k": k, "bucket": LABELS[b], "h": h}, universe=f"stocks adv>={adv:.0f} px>=5",
                              tstat=cell[f"{view}_t"], n=n_events)
    return res


def show(res: dict) -> None:
    print(f"\n===== {res['sample']} {res['dates'][0]}..{res['dates'][1]}  (avg {res['universe_mean_names']:.0f} names/day) =====")
    cells = {(c["k"], c["bucket"], c["h"]): c for c in res["cells"]}
    for view in ("xs", "ts"):
        print(f"\n--- view {view.upper()}: bp from next open (t-stat) ---")
        for k in KS:
            print(f"k={k:<3d} " + "".join(f"{'h=' + str(h):>16s}" for h in HS) + "   events   gapXS")
            for b in LABELS:
                row = f"  {b:>7s}"
                for h in HS:
                    c = cells[(k, b, h)]
                    v, t = c[f"{view}_bp"], c[f"{view}_t"]
                    row += f"{'' if v is None else f'{v:+7.1f} ({t:+5.1f})':>16s}"
                c = cells[(k, b, HS[0])]
                gv = "" if c["gap_xs_bp"] is None else f"{c['gap_xs_bp']:+6.1f} ({c['gap_xs_t']:+5.1f})"
                print(row + f"  {c['events']:>7d}  {gv}")


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "results"
    out.mkdir(exist_ok=True)
    for sample in (sys.argv[1:] or ["DEV", "CTX"]):
        r = run(sample)
        (out / f"e01_anatomy_{sample}.json").write_text(json.dumps(r, indent=0))
        show(r)
