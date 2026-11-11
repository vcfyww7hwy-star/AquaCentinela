"""G41 - Does short-term reversal survive in the less liquid bucket ($5-20M median dollar volume)?

Context: in Kenneth French's survivorship-free portfolios the one-month reversal is still about
+10% a year in SMALL stocks after 2010 (E02). The protocol's cost for this bucket is 25 bp a side.
Development data only (DEV 2011-2018 is survivor-biased, which FLATTERS dip buying; CTX likewise).
A dip rule must clear 50 bp per round trip here before it is worth a validation look.

Registry family "G41_small_dips". XS view against the same liquidity bucket, from the next open.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "g41")

import numpy as np

from research.swinglab import pinelike as ta
from research.swinglab.study import Study

HS = (3, 5, 10)


def main():
    res = {}
    for smp in ("DEV", "CTX"):
        S = Study(smp, adv_min=5e6)
        c = S.P.cf
        small = S.uni & (S.adv60 >= 5e6) & (S.adv60 < 20e6)
        up = c > ta.sma(c, 200)
        z1, z3, z5 = S.z(1), S.z(3), S.z(5)
        rsi2 = ta.rsi(c, 2)
        d = c < ta.shift(c, 1)
        three_down = d & ta.shift(d, 1) & ta.shift(d, 2)
        sigs = {
            "5-bar fall <= -2 sigma": z5 <= -2,
            "5-bar fall <= -3 sigma": z5 <= -3,
            "3-bar fall <= -2 sigma": z3 <= -2,
            "1-bar fall <= -3 sigma": z1 <= -3,
            "RSI(2) < 10, above the 200-day": (rsi2 < 10) & up,
            "three down closes, above the 200-day": three_down & up,
            "5-bar fall <= -2 sigma, above the 200-day": (z5 <= -2) & up,
            "5-bar rise >= +2 sigma (the other side)": z5 >= 2,
        }
        print(f"\n== G41 small-bucket dips [{smp}]  XS bp (t) vs the bucket; " + " ".join(f"h={h}" for h in HS) + f"   names/day {small[S.rows].sum(axis=1).mean():.0f}")
        for name, s in sigs.items():
            t = S.event("G41", "G41_small_dips", name, small & s, control=small, hs=HS)
            res.setdefault(name, {})[smp] = t
            cells = "".join(f" {t[h]['xs_bp'] if t[h]['xs_bp'] is not None else float('nan'):+7.1f}({t[h]['xs_t'] if t[h]['xs_t'] is not None else float('nan'):+5.1f})" for h in HS)
            print(f"  {name:<46s} n={t[HS[0]]['events']:>7d}{cells}")
        del S
    (Path(__file__).resolve().parents[1] / "results" / "g41_small_dips.json").write_text(json.dumps(res, indent=0, default=str))


if __name__ == "__main__":
    main()
