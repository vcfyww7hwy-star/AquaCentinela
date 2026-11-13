"""G11 - What exits do (compact main-loop version of family f11). DEV and CTX.

Two entry sets, both entered at the next open:
    RANDOM  a seeded 2% of universe names each day (no edge beyond the market's drift)
    TREND   close above the 200-day average and a new 20-bar closing high
For each, a small pre-specified exit menu. Costs: 5 bp per side, +10 bp on stop fills.
Read "bp/bar" (net return per bar held) to compare exits of different lengths, and the tail
columns to see what a stop buys.
"""
from __future__ import annotations

import gc
import json
import os
from pathlib import Path

os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "g11")

import numpy as np

from research.swinglab import pinelike as ta
from research.swinglab import trades as TR
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

BIG = 1e6


def menu(S):
    c = S.P.cf
    lo = np.where(np.isfinite(S.P.l), S.P.l, c)
    shock = S.z(1) <= -3
    below20 = c < ta.sma(c, 20)
    low10 = c < ta.shift(ta.lowest(lo, 10), 1)
    return [
        ("time 10, no stop", dict(stop_k=BIG, max_hold=10)),
        ("time 20, no stop", dict(stop_k=BIG, max_hold=20)),
        ("time 40, no stop", dict(stop_k=BIG, max_hold=40)),
        ("stop 1.5 ATR, time 20", dict(stop_k=1.5, max_hold=20)),
        ("stop 2 ATR, time 20", dict(stop_k=2.0, max_hold=20)),
        ("stop 3 ATR, time 20", dict(stop_k=3.0, max_hold=20)),
        ("stop 3 ATR, time 40", dict(stop_k=3.0, max_hold=40)),
        ("stop 2 ATR, trail 3 ATR, no time limit", dict(stop_k=2.0, trail_k=3.0, max_hold=250)),
        ("stop 3 ATR, trail 4 ATR, no time limit", dict(stop_k=3.0, trail_k=4.0, max_hold=250)),
        ("stop 2 ATR, target 2R, time 20", dict(stop_k=2.0, target_r=2.0, max_hold=20)),
        ("stop 2 ATR, target 3R, time 40", dict(stop_k=2.0, target_r=3.0, max_hold=40)),
        ("time 40, exit after a -3 sigma day", dict(stop_k=BIG, max_hold=40, exit_sig=shock)),
        ("time 40, exit on close under 20-day average", dict(stop_k=BIG, max_hold=40, exit_sig=below20)),
        ("time 40, exit on close under prior 10-day low", dict(stop_k=BIG, max_hold=40, exit_sig=low10)),
        ("stop 3 ATR, time 40, exit after a -3 sigma day", dict(stop_k=3.0, max_hold=40, exit_sig=shock)),
    ]


def main() -> None:
    out = {}
    for smp in ("DEV", "CTX"):
        S = Study(smp)
        c = S.P.cf
        rng = np.random.default_rng(11)
        rnd = S.uni & (rng.random(S.uni.shape) < 0.02)
        trend = S.uni & (c > ta.sma(c, 200)) & (c >= ta.highest(c, 20)) & (ta.shift(c, 1) < ta.shift(ta.highest(c, 20), 1))
        atr = S.atr(14)
        yrs = S.dates.astype("datetime64[Y]").astype(int) + 1970
        for ename, sig in (("RANDOM", rnd), ("TREND", trend)):
            print(f"\n[{smp}] entries: {ename}  ({int(sig.sum())} signals)")
            print(f"{'exit':<48s} trades   net bp   t    bars  bp/bar   meanR   win   sd%   P(R<-1.5)  worstR  bear-years bp")
            for name, kw in menu(S):
                tr = TR.simulate(S.P, sig, atr, rows=S.rows, **kw)
                s = TR.summarize(tr, len(S.dates))
                bear = tr[np.isin(yrs[tr["entry"].to_numpy()], (2001, 2002, 2008, 2011, 2015))]
                bb = 1e4 * bear["ret"].mean() if len(bear) > 50 else float("nan")
                sd = 100 * tr["ret"].std()
                # R is undefined without a stop: report it only when a stop exists
                has_stop = kw["stop_k"] < BIG
                out[f"{smp}|{ename}|{name}"] = {**s, "sd_pct": round(float(sd), 2), "bear_years_bp": None if not np.isfinite(bb) else round(float(bb), 1)}
                print(f"{name:<48s} {s['trades']:>6d}  {s['ret_bp']:+7.1f} {s['ret_t']:+5.1f}  {s['bars']:5.1f}  {s['ret_bp'] / s['bars']:+5.2f}  "
                      f"{(s['R'] if has_stop else float('nan')):+6.3f}  {s['win']:.3f} {sd:5.2f}   {(100 * s['share_below_-1.5R'] if has_stop else float('nan')):6.2f}%   {(s['worst_R'] if has_stop else float('nan')):6.1f}   {bb:+7.1f}")
                log_trial("G11", "G11_exits", f"{ename} | {name}", smp, "ret_bp", s["ret_bp"], tstat=s["ret_t"], n=s["trades"],
                          note=f"bars {s['bars']} sd {sd:.2f}")
        del S
        gc.collect()
    Path(__file__).resolve().parents[1].joinpath("results", "g11_exits.json").write_text(json.dumps(out, indent=0, default=str))


if __name__ == "__main__":
    main()
