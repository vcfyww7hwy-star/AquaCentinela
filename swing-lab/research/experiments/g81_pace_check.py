"""G81 - How far can the intraday pace be trusted? (descriptive; RESEARCH_LOG entry 11)

Yahoo 1-hour bars, 12 Dec 2023 .. 31 Dec 2024 only (later data is sealed), full 7-bar days.
pace_k = cum volume through bar k / median(previous 20 sessions' cum volume through bar k)
final  = day volume / median(previous 20 sessions' day volume)
Run: cd swing-lab && python -m research.experiments.g81_pace_check
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from research.experiments.e03_intraday import BARS, load
from research.swinglab.registry import log_trial

N = 20


def main():
    d = load()
    d = d[d["volume"] > 0]
    piv = d.pivot_table(index=["symbol", "day"], columns="hm", values="volume", aggfunc="sum")[BARS].dropna()
    cum = piv.cumsum(axis=1)
    res = {"symbols": int(piv.index.get_level_values(0).nunique()), "days": int(piv.index.get_level_values(1).nunique())}
    out = {}
    g = cum.groupby(level=0)
    med = {hm: g[hm].transform(lambda s: s.shift(1).rolling(N, min_periods=N).median()) for hm in BARS}
    final = cum[BARS[-1]] / med[BARS[-1]]
    for k, hm in enumerate(BARS[:-1]):
        pace = cum[hm] / med[hm]
        ok = np.isfinite(pace) & np.isfinite(final) & (pace > 0) & (final > 0)
        p, f = pace[ok], final[ok]
        rho = float(pd.Series(p.values).rank().corr(pd.Series(f.values).rank()))
        err = float(np.median(np.abs(np.log(p.values / f.values))))
        hi_f, hi_p = f >= 2, p >= 2
        end_of_bar = BARS[k + 1] if k + 1 < len(BARS) else "16:00"
        out[end_of_bar] = {"n": int(ok.sum()), "spearman": rho, "median_abs_log_err": err,
                           "share_err_within_25pct": float(np.mean(np.abs(np.log(p.values / f.values)) <= np.log(1.25))),
                           "unusual_days_caught": float((hi_p & hi_f).sum() / max(hi_f.sum(), 1)),
                           "pace2_ends_ge2": float((hi_p & hi_f).sum() / max(hi_p.sum(), 1)),
                           "pace2_ends_ge1.5": float((hi_p & (f >= 1.5)).sum() / max(hi_p.sum(), 1)),
                           "unusual_days": int(hi_f.sum())}
        log_trial("G81", "G81_pace", f"pace at {end_of_bar} vs final", "INTRADAY_DEV", "spearman", rho, n=int(ok.sum()), note="descriptive")
    res["checkpoints"] = out
    print(json.dumps(res, indent=1))
    (Path(__file__).resolve().parents[1] / "results" / "g81_pace_check.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
