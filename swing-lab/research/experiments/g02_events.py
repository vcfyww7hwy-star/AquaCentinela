"""G02 + G10 - One-day shocks and earnings announcements (compact main-loop version of f02, f10).

Shocks (DEV 2011-2018, CTX 1998-2010): z1 = one-day log return / volatility known the day before.
  What follows from the next open, stock-specific view (XS) and raw; split by volume, by gap versus
  intraday, by trend, by whether the market moved too; the "episodic pivot"; repeat shocks.
Earnings (DEV restricted to 2017-01..2018-06; dates start in 2017): drift after the reaction bar by
  surprise and by reaction; earnings versus non-earnings shocks; the size of reaction moves.

Registry families "G02_shocks", "G10_earnings".
"""
from __future__ import annotations

import gc
import json
import os
from pathlib import Path

os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "g02")

import numpy as np

from research.swinglab import earnings as EA
from research.swinglab import pinelike as ta
from research.swinglab.study import Study

HS = (1, 3, 5, 10, 20, 40)


def line(S, hid, fam, name, sig, control=None, hs=HS):
    t = S.event(hid, fam, name, sig, control=control, hs=hs)
    n = t[hs[0]]["events"]
    cells = "".join(f"  {t[h]['xs_bp'] if t[h]['xs_bp'] is not None else float('nan'):+7.1f}({t[h]['xs_t'] if t[h]['xs_t'] is not None else float('nan'):+5.1f})" for h in hs)
    raw = t[hs[3]]["raw_bp"] if len(hs) > 3 else None
    print(f"  {name:<58s} n={n:>6d}{cells}   raw10 {raw if raw is not None else float('nan'):+7.1f}")
    return t


def shocks(smp: str) -> dict:
    S = Study(smp)
    P = S.P
    c = P.cf
    z1 = S.z(1)
    vol_prev = ta.shift(S.vol, 1)
    pc = ta.shift(c, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        gap_z = np.log(P.o / pc) / vol_prev
        intra_z = np.log(c / P.o) / vol_prev
        relvol = P.v / ta.shift(ta.median(np.where(np.isfinite(P.v), P.v, np.nan), 20), 1)
        loc = (c - P.l) / (P.h - P.l)
    up200 = c > ta.sma(c, 200)
    near_hi = c >= 0.90 * ta.highest(np.where(np.isfinite(P.h), P.h, c), 252)
    mz = z1[:, [S.spy]]
    out = {}
    hdr = "".join(f"  h={h:<3d} XS bp (t) " for h in HS)
    print(f"\n===== SHOCKS [{smp}] {hdr}")
    dn, up = z1 <= -3, z1 >= 3
    F = "G02_shocks"
    for lab, base in (("DOWN z1<=-3", dn), ("UP z1>=+3", up)):
        out[lab] = line(S, "G02", F, lab, base)
        line(S, "G02", F, f"{lab} | volume >= 3x median", base & (relvol >= 3))
        line(S, "G02", F, f"{lab} | volume < 1.5x median", base & (relvol < 1.5))
        g_dom = np.abs(gap_z) > np.abs(intra_z)
        line(S, "G02", F, f"{lab} | mostly overnight gap", base & g_dom)
        line(S, "G02", F, f"{lab} | mostly intraday", base & ~g_dom)
        line(S, "G02", F, f"{lab} | above 200-day average", base & up200)
        line(S, "G02", F, f"{lab} | below 200-day average", base & ~up200)
        line(S, "G02", F, f"{lab} | market moved same way (|SPY z1|>=1.5)", base & (np.sign(mz) == np.sign(z1)) & (np.abs(mz) >= 1.5))
        line(S, "G02", F, f"{lab} | market quiet (|SPY z1|<0.5)", base & (np.abs(mz) < 0.5))
    for thr in (2.0, 2.5, 4.0, 5.0):
        line(S, "G02", F, f"DOWN z1<=-{thr}", z1 <= -thr)
    for thr in (2.0, 4.0, 5.0):
        line(S, "G02", F, f"UP z1>=+{thr}", z1 >= thr)
    # episodic pivot and its mirror
    ep = (gap_z >= 3) & (relvol >= 3) & (loc >= 2 / 3)
    out["EP"] = line(S, "G02", F, "episodic pivot: gap>=3s, vol>=3x, close top third", ep)
    line(S, "G02", F, "  same, within 10% of 252-day high", ep & near_hi)
    line(S, "G02", F, "  same, not within 10% of high", ep & ~near_hi)
    line(S, "G02", F, "gap up >=3s that FADED (close bottom third)", (gap_z >= 3) & (loc <= 1 / 3))
    line(S, "G02", F, "gap down <=-3s, vol>=3x, close bottom third", (gap_z <= -3) & (relvol >= 3) & (loc <= 1 / 3))
    line(S, "G02", F, "gap down <=-3s that RECOVERED (close top third)", (gap_z <= -3) & (loc >= 2 / 3))
    # repeat shocks: a second shock in the same direction within 20 bars
    prior_dn = ta.rolling_sum(ta.shift(dn.astype(float), 1), 20) > 0
    prior_up = ta.rolling_sum(ta.shift(up.astype(float), 1), 20) > 0
    line(S, "G02", F, "second DOWN shock within 20 bars", dn & prior_dn)
    line(S, "G02", F, "second UP shock within 20 bars", up & prior_up)
    # value of an exit: what a holder avoids by selling at the next open after a down shock
    for h in (5, 10, 20):
        f = S.fwd(h)
        a = np.nanmean(f[dn & S.uni]); b = np.nanmean(f[S.uni])
        print(f"  holder's view, {h} bars after a down shock: shocked stocks {1e4 * a:+.1f} bp raw vs any stock {1e4 * b:+.1f} bp; P(< -10%): {100 * np.nanmean(f[dn & S.uni] < -0.10):.1f}% vs {100 * np.nanmean(f[S.uni] < -0.10):.1f}%")
    del S
    gc.collect()
    return out


def earnings() -> dict:
    os.environ["SWINGLAB_REGISTRY_TAG"] = "g10"
    S = Study("DEV")
    ev = EA.load(S)
    P = S.P
    c = P.cf
    yr = S.dates.astype("datetime64[D]")
    era = (yr >= np.datetime64("2017-01-01"))[:, None]
    react = ev["react"] & era & S.uni
    z1 = S.z(1)
    surp = ev["surp_react"]
    F = "G10_earnings"
    hs = (1, 3, 5, 10, 20, 40, 60)
    hdr = "".join(f"  h={h:<3d} XS bp (t) " for h in hs)
    print(f"\n===== EARNINGS [DEV 2017-01..2018-06] reaction bars in universe: {int(react.sum())} {hdr}")
    out = {}
    out["all"] = line(S, "G10", F, "all reaction bars", react, hs=hs)
    for lab, m in (("surprise <= -10%", surp <= -0.10), ("surprise -10%..0", (surp > -0.10) & (surp < 0)),
                   ("surprise 0..+10%", (surp >= 0) & (surp <= 0.10)), ("surprise > +10%", surp > 0.10)):
        out[lab] = line(S, "G10", F, lab, react & m, hs=hs)
    for lab, m in (("reaction z1 <= -3", z1 <= -3), ("reaction -3..-1", (z1 > -3) & (z1 <= -1)), ("reaction -1..+1", (z1 > -1) & (z1 < 1)),
                   ("reaction +1..+3", (z1 >= 1) & (z1 < 3)), ("reaction z1 >= +3", z1 >= 3)):
        out[lab] = line(S, "G10", F, lab, react & m, hs=hs)
    with np.errstate(divide="ignore", invalid="ignore"):
        loc = (c - P.l) / (P.h - P.l)
    line(S, "G10", F, "beat AND up >=1s AND close in top half", react & (surp > 0) & (z1 >= 1) & (loc >= 0.5), hs=hs)
    line(S, "G10", F, "miss AND down <=-1s AND close in bottom half", react & (surp < 0) & (z1 <= -1) & (loc <= 0.5), hs=hs)
    line(S, "G10", F, "beat BUT down <=-1s (sold on good news)", react & (surp > 0) & (z1 <= -1), hs=hs)
    line(S, "G10", F, "miss BUT up >=1s", react & (surp < 0) & (z1 >= 1), hs=hs)
    # the same 3-sigma moves on non-earnings days, same period
    near = ev["react"] | ta.shift(ev["react"].astype(float), 1).astype(bool) | ev["ann"]
    non = era & S.uni & ~near
    line(S, "G10", F, "NON-earnings z1 <= -3 (same period)", non & (z1 <= -3), hs=hs)
    line(S, "G10", F, "NON-earnings z1 >= +3 (same period)", non & (z1 >= 3), hs=hs)
    # risk table
    atr = S.atr(14)
    with np.errstate(divide="ignore", invalid="ignore"):
        gap_atr = (P.o - ta.shift(c, 1)) / ta.shift(atr, 1)
        day_atr = (c - ta.shift(c, 1)) / ta.shift(atr, 1)
    g_e, g_o = gap_atr[react & np.isfinite(gap_atr)], gap_atr[non & np.isfinite(gap_atr)]
    d_e, d_o = day_atr[react & np.isfinite(day_atr)], day_atr[non & np.isfinite(day_atr)]
    q = (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)
    print("  reaction-bar move in ATR units (close to close): quantiles " + " ".join(f"{np.quantile(d_e, x):+.2f}" for x in q) + "   | ordinary days: " + " ".join(f"{np.quantile(d_o, x):+.2f}" for x in q))
    print("  opening gap on the reaction bar in ATR units:    quantiles " + " ".join(f"{np.quantile(g_e, x):+.2f}" for x in q) + "   | ordinary days: " + " ".join(f"{np.quantile(g_o, x):+.2f}" for x in q))
    for k in (1, 2, 3, 4):
        print(f"  P(gap worse than -{k} ATR): earnings {100 * np.mean(g_e < -k):5.2f}%   ordinary night {100 * np.mean(g_o < -k):6.3f}%   ratio {np.mean(g_e < -k) / max(np.mean(g_o < -k), 1e-9):5.1f}x")
    big = (np.abs(z1) >= 3) & era & S.uni
    print(f"  share of all |z1|>=3 days that are earnings reaction bars: {100 * (big & react).sum() / big.sum():.1f}%  (reaction bars are {100 * react.sum() / (era & S.uni).sum():.2f}% of stock-days)")
    out["risk"] = {"p_gap_lt_-1atr_earn": float(np.mean(g_e < -1)), "p_gap_lt_-2atr_earn": float(np.mean(g_e < -2)),
                   "p_gap_lt_-1atr_ord": float(np.mean(g_o < -1)), "p_gap_lt_-2atr_ord": float(np.mean(g_o < -2)),
                   "share_big_moves_on_earnings": float((big & react).sum() / big.sum())}
    # ten bars before a scheduled announcement (dates are known in advance)
    pre = np.zeros_like(react)
    a = ev["ann"] & era
    for k in range(1, 11):
        pre[:-k] |= a[k:]
    f1 = S.fwd(1)
    print(f"  one-day return from the next open on the 10 bars before an announcement: {1e4 * np.nanmean(f1[pre & S.uni]):+.2f} bp vs other days {1e4 * np.nanmean(f1[~pre & S.uni & era]):+.2f} bp")
    return out


if __name__ == "__main__":
    res = {}
    for smp in ("DEV", "CTX"):
        res[f"shocks_{smp}"] = shocks(smp)
    res["earnings"] = earnings()
    Path(__file__).resolve().parents[1].joinpath("results", "g02_events.json").write_text(json.dumps(res, indent=1, default=str))
