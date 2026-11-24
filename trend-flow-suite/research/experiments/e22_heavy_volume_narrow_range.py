#!/usr/bin/env python3
"""E22 - Second external review, objection 5: does the rule "use the ATR of the signal bar, add no
extra stop distance" fail on bars with unusual volume and a NARROW range?

PLAN (written before the numbers were computed)
E14 found that after unusual volume the ATR recomputed at that bar already reflects the higher
volatility that follows. The reviewer's point: that works when the bar's own range was large. On a
bar with heavy volume and a small range (true range <= previous ATR) the ATR does not rise, so the
volatility that follows could be under-stated exactly there.
Test, on evaluated bars with TR_t <= ATR_{t-1}:
  T = zV >= 2 (unusual volume)     C = zV < 1 (ordinary volume)
  C is re-weighted to T's distribution over four bins of TR_t / ATR_{t-1}, so the comparison is at
  equal bar range.
Outcomes over the next 10 bars, all relative to ATR_t (the ATR that includes the signal bar):
  vol_ratio   ln(mean true range of bars t+1..t+10 / ATR_t), reported as a percentage difference
  stop_any    a 2 x ATR_t stop on either side of the close is touched (difference in points)
  stop_long   low <= close - 2 x ATR_t           stop_short  high >= close + 2 x ATR_t
Also shown: the same contrast on wide bars (TR > ATR_{t-1}) and on all bars, and the subset of T
with a small close-to-close move (|z| <= 0.5).
Month-block bootstrap, 2,000 resamples, weights fixed. Sets EM (2018-2026), MS, LH. Survivors only.

  python3 -I experiments/e22_heavy_volume_narrow_range.py [--panel DIR]
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

import experiments.e18_relvol_v3_confirmation as e18

COLS = ["ticker", "date", "month", "eval", "high", "low", "close", "volume", "r", "atr"]
H = 10
N_BOOT = 2000
BINS = np.array([0.0, 0.5, 0.7, 0.85, 1.0000001])


def fwd(args):
    h, l, c, atr = args
    n = len(c)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    atr_prev = np.r_[np.nan, atr[:-1]]
    ftr, lo, hi = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
    if n > H:
        w = np.lib.stride_tricks.sliding_window_view
        ftr[:-H] = w(tr, H)[1:].mean(axis=1)
        lo[:-H] = w(l, H)[1:].min(axis=1)
        hi[:-H] = w(h, H)[1:].max(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = tr / atr_prev
        vr = np.log(ftr / atr)
        sl = (lo <= c - 2.0 * atr).astype(float)
        ss = (hi >= c + 2.0 * atr).astype(float)
        bad = ~(np.isfinite(lo) & (atr > 0))
        sl[bad] = np.nan
        ss[bad] = np.nan
    return rel.astype(np.float32), vr.astype(np.float32), sl.astype(np.float32), ss.astype(np.float32)


def boot_w(v, m, w, is_t, rng):
    """weighted mean of v over T minus weighted mean over C (weights w), month-block bootstrap."""
    ok = np.isfinite(v) & (w > 0)
    v, m, w, is_t = v[ok], m[ok], w[ok], is_t[ok]
    mc, inv = np.unique(m, return_inverse=True)
    k = len(mc)

    def agg(mask):
        return (np.bincount(inv[mask], weights=(v * w)[mask], minlength=k), np.bincount(inv[mask], weights=w[mask], minlength=k))
    st, nt = agg(is_t)
    sc, nc = agg(~is_t)
    est = st.sum() / nt.sum() - sc.sum() / nc.sum()
    idx = rng.integers(0, k, (N_BOOT, k))
    with np.errstate(divide="ignore", invalid="ignore"):
        bt = st[idx].sum(1) / nt[idx].sum(1) - sc[idx].sum(1) / nc[idx].sum(1)
    bt = bt[np.isfinite(bt)]
    lo, hi = np.percentile(bt, [2.5, 97.5])
    return {"diff": round(float(est), 4), "lo": round(float(lo), 4), "hi": round(float(hi), 4),
            "n_t": int(is_t.sum()), "n_c": int((~is_t).sum()),
            "level_t": round(float(st.sum() / nt.sum()), 4), "level_c": round(float(sc.sum() / nc.sum()), 4)}


def contrast(e, t, c, rng, reweight):
    sel = t | c
    is_t = t[sel]
    w = np.ones(int(sel.sum()))
    if reweight:
        b = np.digitize(e["rel"].to_numpy()[sel], BINS) - 1
        for k in range(len(BINS) - 1):
            nt, nc = (is_t & (b == k)).sum(), (~is_t & (b == k)).sum()
            w[~is_t & (b == k)] = nt / nc if nc > 0 else 0.0
    m = e["month"].to_numpy()[sel]
    out = {}
    for name, col in (("vol_ratio_ln", "vr"), ("stop_long", "sl"), ("stop_short", "ss"), ("stop_any", "sa")):
        out[name] = boot_w(e[col].to_numpy(dtype=float)[sel], m, w, is_t, rng)
    return out


def run_set(name, panel, seed):
    d = pd.read_parquet(pathlib.Path(panel) / f"panel_{name}.parquet", columns=COLS)
    gs = list(d.groupby("ticker", sort=False))
    with Pool(3) as pool:
        f1 = pool.map(e18.feats, [(g["volume"].to_numpy(dtype=float), g["r"].to_numpy(dtype=float)) for _, g in gs], chunksize=16)
        f2 = pool.map(fwd, [tuple(g[k].to_numpy(dtype=float) for k in ("high", "low", "close", "atr")) for _, g in gs], chunksize=16)
    d["zv"] = np.concatenate([x[0] for x in f1])
    d["z3"] = np.concatenate([x[1] for x in f1])
    for i, k in enumerate(("rel", "vr", "sl", "ss")):
        d[k] = np.concatenate([x[i] for x in f2])
    d["sa"] = np.fmax(d["sl"], d["ss"])
    e = d[d["eval"] & d["zv"].notna() & d["rel"].notna() & d["vr"].notna()].reset_index(drop=True)
    rng = np.random.default_rng(seed)
    zv, rel, z3 = e["zv"].to_numpy(), e["rel"].to_numpy(), np.abs(e["z3"].to_numpy())
    with np.errstate(invalid="ignore"):
        T, C = zv >= 2, zv < 1
        narrow, wide = rel <= 1.0, rel > 1.0
        out = {"set": name, "rows": int(len(e)),
               "share_of_unusual_bars_that_are_narrow": round(float((T & narrow).sum() / T.sum()), 4),
               "narrow_range_matched": contrast(e, T & narrow, C & narrow, rng, True),
               "narrow_range_small_move_matched": contrast(e, T & narrow & (z3 <= 0.5), C & narrow, rng, True),
               "wide_range_unmatched": contrast(e, T & wide, C & wide, rng, False),
               "all_bars_unmatched": contrast(e, T, C, rng, False)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=e18.DEFAULT_PANEL)
    a = ap.parse_args()
    res = {}
    for i, name in enumerate(("EM", "MS", "LH")):
        res[name] = run_set(name, a.panel, 220 + i)
        r = res[name]
        print(name, "rows", r["rows"], "narrow share of unusual bars", r["share_of_unusual_bars_that_are_narrow"])
        for grp in ("narrow_range_matched", "narrow_range_small_move_matched", "wide_range_unmatched", "all_bars_unmatched"):
            x = r[grp]
            v, s = x["vol_ratio_ln"], x["stop_any"]
            print(f"  {grp:32s} n_t={v['n_t']:6d} vol {100 * (np.exp(v['diff']) - 1):+.1f}% [{100 * (np.exp(v['lo']) - 1):+.1f}, {100 * (np.exp(v['hi']) - 1):+.1f}]"
                  f"  stop_any {100 * s['diff']:+.1f} pts [{100 * s['lo']:+.1f}, {100 * s['hi']:+.1f}] (T {100 * s['level_t']:.1f}%, C {100 * s['level_c']:.1f}%)"
                  f"  long {100 * x['stop_long']['diff']:+.1f} [{100 * x['stop_long']['lo']:+.1f}, {100 * x['stop_long']['hi']:+.1f}]"
                  f"  short {100 * x['stop_short']['diff']:+.1f} [{100 * x['stop_short']['lo']:+.1f}, {100 * x['stop_short']['hi']:+.1f}]")
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e22_heavy_volume_narrow_range.json"
    p.write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
