"""G12 - The risk engine: volatility forecasts, forward-range calibration, stop-out odds.

Compact main-loop version of family f12 (the delegated explorer was cut off by the account's
usage limit before it started). Development samples only: DEV 2011-01..2018-06, CTX 1998..2010.

A  Which Pine-computable estimate of daily volatility best forecasts the realised volatility of
   the next 5, 10, 20 bars?  Loss: QLIKE on variance (0 = perfect). Each estimate is also given a
   constant scale fitted on CTX and applied unchanged to DEV, so that a biased-but-informative
   estimate (ATR, range-based) is judged on information, not on units.
B  Calibration for the playbook: quantiles of the h-bar return from the next open divided by
   forecast*sqrt(h); and for stops placed k ATR(14) below the next open on RANDOM entries, the
   share stopped within h bars, the share of those that gapped through, and the average fill in R.
C  Does volatility contraction predict larger moves than the forecast already implies, or a
   direction?

Registry family "G12_risk".
"""
from __future__ import annotations

import gc
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "g12")

import numpy as np

from research.swinglab import engine as E
from research.swinglab import pinelike as ta
from research.swinglab import trades as TR
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

HS = (5, 10, 20)
LN2 = np.log(2.0)


def estimators(S: Study) -> dict:
    P = S.P
    r = P.ret
    r2 = r ** 2
    cf = P.cf
    o = np.where(np.isfinite(P.o), P.o, cf)
    h = np.where(np.isfinite(P.h), P.h, cf)
    l = np.where(np.isfinite(P.l), P.l, cf)
    pc = ta.shift(cf, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        on = np.log(o / pc) ** 2                      # overnight variance proxy
        hl = np.log(h / l) ** 2
        co = np.log(cf / o) ** 2
        rs = np.log(h / cf) * np.log(h / o) + np.log(l / cf) * np.log(l / o)     # Rogers-Satchell
    pk_d = hl / (4 * LN2) + on                        # Parkinson + overnight, daily variance
    gk_d = 0.5 * hl - (2 * LN2 - 1) * co + on         # Garman-Klass + overnight
    rs_d = rs + on
    est = {}
    est["stdev20"] = ta.stdev(r, 20)
    est["stdev60"] = ta.stdev(r, 60)
    for n in (10, 20, 40, 60):
        est[f"ewma{n}"] = np.sqrt(E.ewma(r2, 2.0 / (n + 1)))
    est["robust_ewma20"] = S.vol
    est["atr14/close"] = S.atr(14) / cf
    est["atr20/close"] = S.atr(20) / cf
    est["parkinson20+on"] = np.sqrt(ta.sma(pk_d, 20))
    est["garman_klass20+on"] = np.sqrt(ta.sma(gk_d, 20))
    est["rogers_satchell20+on"] = np.sqrt(ta.sma(rs_d, 20))
    # Yang-Zhang over 20 bars: sigma_on^2 + k*sigma_oc^2 + (1-k)*sigma_rs^2
    n = 20
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        lo_ = np.log(o / pc)
        lc_ = np.log(cf / o)
    est["yang_zhang20"] = np.sqrt(np.maximum(ta.stdev(lo_, n) ** 2 + k * ta.stdev(lc_, n) ** 2 + (1 - k) * ta.sma(rs, n), 0))
    est["har_r2(1,5,22)"] = np.sqrt((r2 + ta.sma(r2, 5) + ta.sma(r2, 22)) / 3)
    est["har_gk(1,5,22)"] = np.sqrt(np.maximum((gk_d + ta.sma(gk_d, 5) + ta.sma(gk_d, 22)) / 3, 0))
    est["ewma20_gk"] = np.sqrt(np.maximum(E.ewma(gk_d, 2.0 / 21), 0))
    est["ewma20_pk"] = np.sqrt(np.maximum(E.ewma(pk_d, 2.0 / 21), 0))
    # absolute-value (L1) family: robust to single shocks, like ATR
    tr = ta.true_range(h, l, cf) / pc                                   # true range as a fraction of the prior close
    absr = np.abs(r)
    for n in (10, 30, 50):
        est[f"atr{n}/close"] = S.atr(n) / cf
    est["blend atr14+atr50"] = 0.5 * S.atr(14) / cf + 0.5 * S.atr(50) / cf
    est["ewma20 of |r|"] = E.ewma(absr, 2.0 / 21)
    est["rma27 of |r|"] = ta.rma(np.where(np.isfinite(absr), absr, 0.0), 27)
    est["sma20 of TR%"] = ta.sma(tr, 20)
    est["median20 of TR%"] = ta.median(tr, 20)
    est["sqrt ewma27 of TR%^2"] = np.sqrt(E.ewma(tr ** 2, 2.0 / 28))
    est["har TR% (1,5,22)"] = (tr + ta.sma(tr, 5) + ta.sma(tr, 22)) / 3
    est["blend atr14 + ewma60(sd)"] = 0.5 * S.atr(14) / cf / 1.6 + 0.5 * est["ewma60"]
    est["blend ewma20/ewma60"] = np.sqrt(0.5 * est["ewma20"] ** 2 + 0.5 * est["ewma60"] ** 2)
    est["blend ewma20_gk/ewma60"] = np.sqrt(0.5 * est["ewma20_gk"] ** 2 + 0.5 * est["ewma60"] ** 2)
    # shrink the variance 20% toward the day's cross-sectional median (known at t)
    v = est["ewma20_gk"] ** 2
    med = np.nanmedian(np.where(S.uni, v, np.nan), axis=1)[:, None]
    est["ewma20_gk shrunk 20% to xs median"] = np.sqrt(0.8 * v + 0.2 * med)
    return est


def realised(S: Study, h: int) -> np.ndarray:
    """sqrt(mean squared daily log return) over bars t+1..t+h; NaN outside the sample."""
    r2 = S.P.ret ** 2
    fwd = np.full(r2.shape, np.nan)
    m = ta.sma(r2, h)                       # mean over t-h+1..t
    fwd[:-h] = m[h:]
    fwd[~S.rows] = np.nan
    last = np.flatnonzero(S.rows)[-1]
    fwd[last - h + 1:] = np.nan
    return np.sqrt(fwd)


def qlike(rv: np.ndarray, f: np.ndarray, mask: np.ndarray, scale: float = 1.0):
    ok = mask & np.isfinite(rv) & np.isfinite(f) & (f > 0) & (rv > 0)
    x = (rv[ok] / (f[ok] * scale)) ** 2
    return float(np.mean(x - np.log(x) - 1.0)), float(np.median(np.sqrt(x))), int(ok.sum())


def best_scale(rv, f, mask) -> float:
    """QLIKE-optimal constant: scale^2 = mean(rv^2 / f^2)."""
    ok = mask & np.isfinite(rv) & np.isfinite(f) & (f > 0) & (rv > 0)
    return float(np.sqrt(np.mean((rv[ok] / f[ok]) ** 2)))


def part_a(samples: dict) -> dict:
    res = {}
    scales = {}
    for smp in ("CTX", "DEV"):
        S = samples[smp]
        est = estimators(S)
        res[smp] = {}
        for h in HS:
            rv = realised(S, h)
            for name, f in est.items():
                raw, bias, n = qlike(rv, f, S.uni)
                if smp == "CTX":
                    scales[(name, h)] = best_scale(rv, f, S.uni)
                cal, _, _ = qlike(rv, f, S.uni, scales[(name, h)])
                res[smp].setdefault(name, {})[h] = {"qlike_raw": round(raw, 4), "bias": round(bias, 3),
                                                    "scale_from_ctx": round(scales[(name, h)], 3), "qlike_cal": round(cal, 4), "n": n}
                log_trial("G12", "G12_risk", f"A qlike {name} h={h}", smp, "qlike_cal", cal, note=f"raw {raw:.4f} bias {bias:.3f}", n=n)
        del est
        gc.collect()
    print("\nA. QLIKE of next-h-bar realised volatility (lower is better). 'cal' = scaled by a constant fitted on CTX.")
    print(f"{'estimate':<36s}" + "".join(f"  CTX h={h:<2d} cal  DEV h={h:<2d} raw/cal (bias)" for h in HS))
    names = sorted(res["DEV"], key=lambda k: res["DEV"][k][10]["qlike_cal"])
    for name in names:
        row = f"{name:<36s}"
        for h in HS:
            c, d = res["CTX"][name][h], res["DEV"][name][h]
            row += f"  {c['qlike_cal']:.3f}       {d['qlike_raw']:.3f}/{d['qlike_cal']:.3f} ({d['bias']:.2f})   "
        print(row)
    return res


def part_b(S: Study, smp: str, f: np.ndarray, fname: str) -> dict:
    res = {"forecast": fname}
    print(f"\nB[{smp}]. Return from the next open over h bars, divided by {fname}*sqrt(h): quantiles (normal: -2.33 -1.64 -1.28 -0.67 0 0.67 1.28 1.64 2.33)")
    qs = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
    for h in (5, 10, 20):
        x = np.log1p(S.fwd(h)) / (f * np.sqrt(h))
        x = x[S.uni & np.isfinite(x)]
        q = np.quantile(x, qs)
        res[f"q_h{h}"] = {str(a): round(float(b), 2) for a, b in zip(qs, q)}
        print(f"   h={h:<2d} " + " ".join(f"{b:+5.2f}" for b in q) + f"   share beyond +/-2: {np.mean(np.abs(x) > 2):.3f} (normal 0.046)  n={len(x):,}")
        log_trial("G12", "G12_risk", f"B quantiles h={h} of fwd/(f sqrt h)", smp, "q01", float(q[0]), note=json.dumps(res[f'q_h{h}']))
    # stop-out odds on random entries
    rng = np.random.default_rng(12)
    rnd = S.uni & (rng.random(S.uni.shape) < 0.02)
    c = S.P.cf
    spy_up = (c[:, S.spy] > ta.sma(c[:, [S.spy]], 200)[:, 0])
    atr = S.atr(14)
    print(f"B[{smp}]. Random entries at the next open, stop k x ATR(14) below entry: % stopped within h bars | of which gapped through | mean fill of stopped trades (R)")
    print("     k    " + "".join(f"h={h:<3d}               " for h in (3, 5, 10, 20)) + " | market below its 200-day average, h=10")
    res["stops"] = {}
    for k in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
        row = f"   {k:4.1f}  "
        for h in (3, 5, 10, 20):
            tr = TR.simulate(S.P, rnd, atr, rows=S.rows, stop_k=k, max_hold=h, cost_bp=0, stop_extra_bp=0)
            st = tr["reason"].isin(["stop", "gap_stop"])
            p = float(st.mean())
            g = float((tr["reason"] == "gap_stop").sum() / max(st.sum(), 1))
            fill = float(tr.loc[st, "R"].mean())
            res["stops"][f"k{k}_h{h}"] = {"p_stop": round(p, 3), "gap_share": round(g, 3), "mean_R_stopped": round(fill, 2), "n": int(len(tr)),
                                          "mean_ret_bp": round(1e4 * float(tr["ret"].mean()), 1)}
            row += f"{100 * p:4.1f}% | {100 * g:4.1f}% | {fill:5.2f}R  "
            log_trial("G12", "G12_risk", f"B stop-out k={k} h={h}", smp, "p_stop", p, n=int(len(tr)))
            if h == 10:
                dn = ~spy_up[tr["entry"].to_numpy() - 1]
                pd_ = float(st[dn].mean()) if dn.sum() > 50 else float("nan")
                tail = f" | {100 * pd_:4.1f}% (n={int(dn.sum())})"
                res["stops"][f"k{k}_h{h}"]["p_stop_market_down"] = round(pd_, 3) if np.isfinite(pd_) else None
        print(row + tail)
    # how often is the loss on a stopped trade worse than 1.5R / 2R (gap risk)
    tr = TR.simulate(S.P, rnd, atr, rows=S.rows, stop_k=2.0, max_hold=10, cost_bp=0, stop_extra_bp=0)
    res["tail_k2_h10"] = {"worse_than_-1.5R": round(float((tr["R"] < -1.5).mean()), 4), "worse_than_-2R": round(float((tr["R"] < -2).mean()), 4),
                          "worse_than_-3R": round(float((tr["R"] < -3).mean()), 4), "worst_R": round(float(tr["R"].min()), 1)}
    print(f"   2-ATR stop, 10 bars: trades worse than -1.5R {100 * res['tail_k2_h10']['worse_than_-1.5R']:.2f}%, worse than -2R {100 * res['tail_k2_h10']['worse_than_-2R']:.2f}%, worse than -3R {100 * res['tail_k2_h10']['worse_than_-3R']:.2f}%, worst {res['tail_k2_h10']['worst_R']}R")
    # overnight gap distribution in ATR units (risk a stop cannot remove)
    with np.errstate(divide="ignore", invalid="ignore"):
        g_atr = (E.lead(S.P.o, 1) - c) / atr
    ga = g_atr[S.uni & np.isfinite(g_atr)]
    res["overnight_gap_in_atr"] = {str(q): round(float(np.quantile(ga, q)), 2) for q in (0.001, 0.01, 0.05, 0.5, 0.95, 0.99, 0.999)}
    res["p_gap_below_-1atr"] = round(float(np.mean(ga < -1)), 5)
    res["p_gap_below_-2atr"] = round(float(np.mean(ga < -2)), 5)
    print(f"   overnight gap in ATR units: 0.1% {np.quantile(ga, 0.001):+.2f}, 1% {np.quantile(ga, 0.01):+.2f}, 5% {np.quantile(ga, 0.05):+.2f}; P(gap < -1 ATR) = {100 * np.mean(ga < -1):.2f}% of nights, P(gap < -2 ATR) = {100 * np.mean(ga < -2):.3f}%")
    return res


def part_c(S: Study, smp: str, f: np.ndarray) -> dict:
    res = {}
    r2 = S.P.ret ** 2
    ratio = np.sqrt(E.ewma(r2, 2.0 / 6)) / np.sqrt(E.ewma(r2, 2.0 / 61))          # 5-bar over 60-bar volatility
    cf = S.P.cf
    bbw = 4 * ta.stdev(cf, 20) / ta.sma(cf, 20)
    bbw_low = bbw <= ta.lowest(bbw, 126)                                           # band width at a 126-bar low
    tr_ = ta.true_range(np.where(np.isfinite(S.P.h), S.P.h, cf), np.where(np.isfinite(S.P.l), S.P.l, cf), cf)
    nr7 = tr_ <= ta.lowest(tr_, 7)
    print(f"\nC[{smp}]. Volatility contraction: realised |move| over the next h bars relative to the forecast (1.00 = as forecast), and direction (XS bp from next open)")
    for name, sig in (("vol ratio 5/60 <= 0.6", ratio <= 0.6), ("vol ratio 5/60 >= 1.6", ratio >= 1.6),
                      ("Bollinger width at 126-bar low", bbw_low), ("NR7 (narrowest range of 7)", nr7)):
        sig = sig & S.uni
        row = f"   {name:<32s} n={int(sig.sum()):>7d}"
        res[name] = {}
        for h in (5, 10):
            x = np.abs(np.log1p(S.fwd(h))) / (f * np.sqrt(h))
            a, b = np.nanmean(x[sig]), np.nanmean(x[S.uni & ~sig])
            ev = S.event("G12", "G12_risk", f"C {name}", sig, hs=(h,), params={"h": h})[h]
            res[name][h] = {"abs_move_ratio_vs_rest": round(float(a / b), 3), "xs_bp": ev["xs_bp"], "xs_t": ev["xs_t"]}
            row += f"   h={h}: |move| {a / b:.2f}x the rest; direction {ev['xs_bp']:+.1f} bp (t {ev['xs_t']:+.1f})"
        print(row)
    return res


if __name__ == "__main__":
    out = {}
    samples = {}
    # Part A needs both samples, but one Study at a time: run A per sample by building sequentially
    resA = {}
    scales = {}
    stash = {}
    for smp in ("CTX", "DEV"):
        S = Study(smp)
        stash[smp] = S
        samples[smp] = S
        if smp == "CTX":
            # run A for CTX immediately to fit scales, then free memory
            pass
    resA = part_a(samples)
    out["A"] = resA
    best = sorted(resA["DEV"], key=lambda k: resA["DEV"][k][10]["qlike_cal"])[0]
    print(f"\nbest calibrated estimate on DEV at h=10: {best}")
    for smp in ("DEV", "CTX"):
        S = samples[smp]
        est = estimators(S)
        sc = resA["CTX"]["atr14/close"][10]["scale_from_ctx"]
        f = est["atr14/close"] * sc
        out[f"B_{smp}"] = part_b(S, smp, f, f"(ATR14/close x {sc:.3f})")
        out[f"C_{smp}"] = part_c(S, smp, f)
        del est
        gc.collect()
    Path(__file__).resolve().parents[1].joinpath("results", "g12_risk_engine.json").write_text(json.dumps(out, indent=1, default=str))
