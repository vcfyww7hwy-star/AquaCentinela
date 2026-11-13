"""G50 - Calibration of the constants the scripts display (development AND validation data).

This is calibration, not a test: validation data have already been used for their two looks, and
the numbers frozen here are tested once on the lockbox.

  bands      y_h = ln(close[t+h] / close[t]) / (ATR14[t] / close[t] * sqrt(h)), chart prices
             (split-adjusted, no dividends; the final close if the security stops trading),
             quantiles 5 / 25 / 50 / 75 / 95 for h = 5, 10, 20
  stops      share of random entries (next open) stopped within h bars by a stop k ATR below the
             entry, k = 1, 1.5, 2, 2.5, 3, 4; h = 5, 10, 20
  earnings   opening gap on the reaction bar in ATR units: P(< -1), P(< -2), P(< -3), P(> +2)
  regime     SPY daily volatility with SPY above / below its 200-day average

    python -m research.experiments.g50_calibration
"""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "g50")
os.environ.setdefault("SWINGLAB_VAL_TOKEN", "PRE-REGISTERED")     # calibration use, declared in the log

import numpy as np

from research.swinglab import earnings as EA
from research.swinglab import pinelike as ta
from research.swinglab import trades as TR
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

QS = (0.05, 0.25, 0.50, 0.75, 0.95)
HS = (5, 10, 20)
KS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)


def band_y(S, h):
    c = S.P.cf
    atr = S.atr(14)
    T = c.shape[0]
    y = np.full(c.shape, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        y[:T - h] = np.log(c[h:] / c[:T - h]) / (atr[:T - h] / c[:T - h] * np.sqrt(h))
    ok = S.uni & np.isfinite(y)
    ok[~S.rows] = False
    ok[max(S._last_row - h + 1, 0):] = False          # the window must end inside the sample
    return y, ok


def one(sample):
    S = Study(sample)
    out = {"bands": {}, "stops": {}}
    for h in HS:
        y, ok = band_y(S, h)
        out["bands"][h] = {"q": [float(np.quantile(y[ok], q)) for q in QS], "n": int(ok.sum())}
        out[f"_y{h}"] = (y, ok)
    rng = np.random.default_rng(12)
    rnd = S.uni & (rng.random(S.uni.shape) < 0.02)
    atr = S.atr(14)
    for k in KS:
        for h in HS:
            tr = TR.simulate(S.P, rnd, atr, rows=S.rows, stop_k=k, max_hold=h, cost_bp=0, stop_extra_bp=0)
            stp = tr["reason"].isin(["stop", "gap_stop"])
            out["stops"][f"k{k}_h{h}"] = {"p": float(stp.mean()), "n": int(len(tr))}
    c = S.P.cf
    if sample != "CTX":
        ev = EA.load(S)
        react = ev["react"] & S.uni
        non = S.uni & ~(ev["react"] | ev["ann"])
        with np.errstate(divide="ignore", invalid="ignore"):
            g = (S.P.o - ta.shift(c, 1)) / ta.shift(atr, 1)
        ge, go = g[react & np.isfinite(g)], g[non & np.isfinite(g)]
        out["earnings"] = {"n": int(len(ge)), "lt-1": float(np.mean(ge < -1)), "lt-2": float(np.mean(ge < -2)), "lt-3": float(np.mean(ge < -3)),
                           "gt+1": float(np.mean(ge > 1)), "gt+2": float(np.mean(ge > 2)), "abs_gt2": float(np.mean(np.abs(ge) > 2)),
                           "ordinary_lt-1": float(np.mean(go < -1)), "ordinary_lt-2": float(np.mean(go < -2)), "ordinary_abs_gt2": float(np.mean(np.abs(go) > 2))}
    spy = c[:, [S.spy]]
    sma200 = ta.sma(spy, 200)[:, 0]
    above = spy[:, 0] > sma200
    r1d = S.P.ret[:, S.spy]
    st = np.r_[False, above[:-1]]
    known = np.r_[False, np.isfinite(sma200)[:-1]]
    rr = S.rows & np.isfinite(r1d) & known
    out["regime"] = {"vol_above": float(np.std(r1d[rr & st]) * np.sqrt(252)), "vol_below": float(np.std(r1d[rr & ~st]) * np.sqrt(252)),
                     "share_below": float((rr & ~st).sum() / rr.sum())}
    return S, out


def main():
    res, ys = {}, {}
    for smp in ("DEV", "VAL", "CTX"):
        S, o = one(smp)
        ys[smp] = {h: o.pop(f"_y{h}") for h in HS}
        res[smp] = o
        log_trial("G50", "G50_calibration", "bands, stop table, earnings gaps, regime", smp, "calibration", 0.0, note="calibration of displayed constants")
        del S
    # pooled DEV + VAL quantiles, and cross-coverage
    pooled = {}
    for h in HS:
        yy = np.concatenate([ys[s][h][0][ys[s][h][1]] for s in ("DEV", "VAL")])
        pooled[h] = [float(np.quantile(yy, q)) for q in QS]
    res["pooled_DEV_VAL_bands"] = pooled
    print("\nBANDS  y = ln(close[t+h]/close[t]) / (ATR/close*sqrt(h));  quantiles 5 25 50 75 95")
    for h in HS:
        for smp in ("DEV", "VAL", "CTX"):
            print(f"  h={h:<2d} {smp}: " + " ".join(f"{v:+.3f}" for v in res[smp]["bands"][h]["q"]) + f"   n={res[smp]['bands'][h]['n']}")
        print(f"  h={h:<2d} DEV+VAL: " + " ".join(f"{v:+.3f}" for v in pooled[h]))
    print("\nCOVERAGE of the pooled DEV+VAL bands, by sample  (90% band, 50% band)")
    cov = {}
    for h in HS:
        q = pooled[h]
        for smp in ("DEV", "VAL", "CTX"):
            y, ok = ys[smp][h]
            v = y[ok]
            c90, c50 = float(np.mean((v >= q[0]) & (v <= q[4]))), float(np.mean((v >= q[1]) & (v <= q[3])))
            cov[f"{smp}_h{h}"] = (c90, c50)
            print(f"  h={h:<2d} {smp}: {100 * c90:5.1f}%  {100 * c50:5.1f}%   below the 5% line {100 * float(np.mean(v < q[0])):.1f}%  above the 95% line {100 * float(np.mean(v > q[4])):.1f}%")
    res["coverage_of_pooled"] = cov
    print("\nSTOP TABLE  share stopped within h bars (DEV / VAL / CTX)")
    for k in KS:
        print(f"  k={k}: " + "   ".join(f"h={h}: " + " / ".join(f"{100 * res[s]['stops'][f'k{k}_h{h}']['p']:.1f}" for s in ("DEV", "VAL", "CTX")) for h in HS))
    print("\nEARNINGS", json.dumps({s: {k: round(v, 4) for k, v in res[s]["earnings"].items()} for s in ("DEV", "VAL")}, indent=0))
    print("\nREGIME", json.dumps({s: {k: round(v, 3) for k, v in res[s]["regime"].items()} for s in ("DEV", "VAL", "CTX")}))
    (Path(__file__).resolve().parents[1] / "results" / "g50_calibration.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
