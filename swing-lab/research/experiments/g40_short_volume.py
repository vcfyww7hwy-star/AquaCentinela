"""G40 - FINRA daily short-sale volume (exploration sample DEV_S, 2018-08-01..2020-06-30).

Hypothesis from the literature, sign fixed before the look: heavy short selling is followed by
lower returns over the next days to weeks (Diether, Lee & Werner 2009; Boehmer, Jones & Zhang 2008;
Wang, Yan & Zheng 2020 on this same public FINRA file). Known complication: most off-exchange short
volume is market makers filling retail buy orders, so a high ratio may also measure retail buying.

Features on day d (FINRA values of day d):
    svr   short / FINRA total                      (needs FINRA total; availability on TradingView not verified)
    svc   short / consolidated volume              (Pine-safe: the chart's daily volume)
    rsv   short / median of the previous 20 bars' short volume     (Pine-safe: the series alone)
    svr5  5-bar sum of short / 5-bar sum of total
    zsvr  (svr - mean of the previous 20) / st.dev. of the previous 20
A signal at the close of t uses day t-L. L = 1 is the base case (the file for day t is published
after the close); L = 0 is the "evening" variant.

Registry family "G40_shortvol". Outcomes: total return from the next open, XS view.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "g40")

import numpy as np

from research.swinglab import pinelike as ta
from research.swinglab import shortvol as SV
from research.swinglab.study import Study

HS = (1, 5, 10, 20)


def features(S, sv):
    sh, to = sv["short"], sv["total"]
    with np.errstate(divide="ignore", invalid="ignore"):
        vraw = S.P.v * S.P.c / S.c_raw                 # consolidated volume in the shares of the day
        f = {
            "svr": sh / to,
            "svc": sh / vraw,
            "rsv": sh / ta.shift(ta.median_tol(sh, 20, 15), 1),
            "svr5": ta.rolling_sum(sh, 5) / ta.rolling_sum(to, 5),
        }
        m, s = ta.shift(ta.sma_tol(f["svr"], 20, 15), 1), ta.shift(ta.stdev(f["svr"], 20), 1)
        f["zsvr"] = (f["svr"] - m) / s
    return f


def xs_decile(x, uni, lo, hi):
    """Boolean masks of the bottom and top deciles of x among the universe on each day."""
    xx = np.where(uni, x, np.nan)
    ql = np.nanpercentile(xx, lo, axis=1, keepdims=True)
    qh = np.nanpercentile(xx, hi, axis=1, keepdims=True)
    return xx <= ql, xx >= qh


def main(sample="DEV_S"):
    S = Study(sample)
    sv = SV.load(S)
    F = features(S, sv)
    U = S.uni
    z5 = S.z(5)
    res = {}
    print(f"== G40 short volume [{sample}]  XS bp (t) from the next open; " + " ".join(f"h={h}" for h in HS))

    def line(name, sig, ctrl=None):
        t = S.event("G40", "G40_shortvol", name, sig, control=ctrl, hs=HS)
        res[name] = t
        cells = "".join(f" {t[h]['xs_bp'] if t[h]['xs_bp'] is not None else float('nan'):+7.1f}({t[h]['xs_t'] if t[h]['xs_t'] is not None else float('nan'):+5.1f})" for h in HS)
        print(f"  {name:<50s} n={t[HS[0]]['events']:>7d}{cells}")

    for L in (1, 0):
        f = {k: ta.shift(v, L) if L else v for k, v in F.items()}
        tag = f"L{L}"
        lo, hi = xs_decile(f["svr5"], U, 10, 90)
        line(f"{tag} svr5 top decile (not Pine)", U & hi)
        line(f"{tag} svr5 bottom decile (not Pine)", U & lo)
        lo, hi = xs_decile(f["svc"], U, 10, 90)
        line(f"{tag} svc top decile (not Pine)", U & hi)
        line(f"{tag} svc bottom decile (not Pine)", U & lo)
        line(f"{tag} svr >= 0.60", U & (f["svr"] >= 0.60))
        line(f"{tag} svr <= 0.30", U & (f["svr"] <= 0.30))
        line(f"{tag} svr5 >= 0.55", U & (f["svr5"] >= 0.55))
        line(f"{tag} svr5 <= 0.33", U & (f["svr5"] <= 0.33))
        line(f"{tag} svc >= 0.20", U & (f["svc"] >= 0.20))
        line(f"{tag} svc <= 0.05", U & (f["svc"] <= 0.05))
        line(f"{tag} rsv >= 3", U & (f["rsv"] >= 3))
        line(f"{tag} rsv >= 3 and 5-bar move up >= 1 sigma", U & (f["rsv"] >= 3) & (z5 >= 1))
        line(f"{tag} rsv >= 3 and 5-bar move down <= -1 sigma", U & (f["rsv"] >= 3) & (z5 <= -1))
        line(f"{tag} zsvr >= 2", U & (f["zsvr"] >= 2))
        line(f"{tag} zsvr <= -2", U & (f["zsvr"] <= -2))
        line(f"{tag} svr5 >= 0.55 and 5-bar move up >= 1 sigma", U & (f["svr5"] >= 0.55) & (z5 >= 1))
        line(f"{tag} svr5 >= 0.55 and 5-bar move down <= -1 sigma", U & (f["svr5"] >= 0.55) & (z5 <= -1))
    out = Path(__file__).resolve().parents[1] / "results" / f"g40_short_volume_{sample}.json"
    out.write_text(json.dumps(res, indent=0, default=str))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "DEV_S")
