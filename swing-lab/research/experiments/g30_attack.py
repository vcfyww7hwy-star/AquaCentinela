"""G30 - Attack the candidates on development data before any validation look (protocol section 6).

For each frozen candidate (swinglab/candidates.py), at its own horizon:
    base      XS effect in DEV and CTX
    halves    cross-section halves A and B (DEV)
    liquidity median dollar volume above / below $50M (DEV)
    years     number of calendar years with the predicted sign (DEV + CTX, years with >= 200 events)
    delay     the same signal entered one bar later (must not get better)
    no-best   DEV without its best calendar month for the candidate
    clean     excluding signal bars whose own daily return is beyond 6 sigma (bad ticks)
    gap       how much of the effect sits in the overnight gap the trader cannot capture
    cost      the effect net of a 10 bp round trip when the candidate is used as a long entry
A candidate goes to validation only if it keeps its sign through all of these.
Registry family "G30_attack".
"""
from __future__ import annotations

import gc
import json
import os
from pathlib import Path

os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "g30")

import numpy as np

from research.swinglab import candidates as C
from research.swinglab import engine as E
from research.swinglab import pinelike as ta
from research.swinglab.registry import log_trial
from research.swinglab.study import Study


def xs(S, sig, ctrl, h, rows=None, cols=None):
    """XS bp and t for a signal, optionally restricted to a subset of dates or securities."""
    out = S.fwd(h)
    u = S.uni if ctrl is None else ctrl
    sig = sig & S.uni
    if cols is not None:
        sig, u = sig & cols[None, :], u & cols[None, :]
    d, ns = E.spread_series(out, sig, u)
    r = S.rows if rows is None else (S.rows & rows)
    m, t, n = E.nw_mean(d[r], 2 * h)
    return (1e4 * m if np.isfinite(m) else np.nan), t, int(ns[r][np.isfinite(d[r])].sum())


def main() -> None:
    res: dict = {}
    year_hits: dict = {}
    for smp in ("DEV", "CTX"):
        S = Study(smp)
        F = C.Feat(S)
        yrs = S.dates.astype("datetime64[Y]").astype(int) + 1970
        months = S.dates.astype("datetime64[M]").astype(int)
        liq = S.adv60 >= 50e6
        gap = S.gap()
        for name, spec in C.SPEC.items():
            sig, ctrl = spec["fn"](F)
            h, sgn = spec["h"], spec["sign"]
            r = res.setdefault(name, {"h": h, "sign": sgn, "use": spec["use"]})
            b, t, n = xs(S, sig, ctrl, h)
            r[smp] = {"bp": round(b, 1), "t": round(t, 2), "n": n}
            log_trial("G30", "G30_attack", f"{name} base", smp, "xs_bp", b, tstat=t, n=n, params={"h": h})
            # years with the predicted sign
            good = tot = 0
            for y in np.unique(yrs[S.rows]):
                by, _, ny = xs(S, sig, ctrl, h, rows=(yrs == y))
                if ny >= 200 and np.isfinite(by):
                    tot += 1
                    good += int(np.sign(by) == sgn)
            hits = year_hits.setdefault(name, [0, 0])
            hits[0] += good
            hits[1] += tot
            if smp == "DEV":
                a = xs(S, sig, ctrl, h, cols=S.half_a)
                bb = xs(S, sig, ctrl, h, cols=~S.half_a)
                # liquidity split is a split of signal-days, not of securities
                hi = xs(S, sig & liq, ctrl if ctrl is None else ctrl, h)
                lo = xs(S, sig & ~liq, ctrl, h)
                d1 = xs(S, ta.shift(sig.astype(float), 1).astype(bool), None if ctrl is None else ta.shift(ctrl.astype(float), 1).astype(bool), h)
                # without the best month: drop the calendar month that contributes most in the predicted direction
                out = S.fwd(h)
                dser, _ = E.spread_series(out, sig & S.uni, S.uni if ctrl is None else ctrl)
                contrib = {}
                for mth in np.unique(months[S.rows]):
                    x = dser[(months == mth) & S.rows]
                    contrib[mth] = np.nansum(x) * sgn
                best = max(contrib, key=contrib.get)
                nb = xs(S, sig, ctrl, h, rows=(months != best))
                clean = xs(S, sig & (np.abs(F.z1) < 6), ctrl, h)
                gx, gt, _ = (lambda dd: E.nw_mean(dd[0][S.rows], 2))(E.spread_series(gap, sig & S.uni, S.uni if ctrl is None else ctrl))
                r["attacks"] = {
                    "half_A": round(a[0], 1), "half_B": round(bb[0], 1), "liq>=50M": round(hi[0], 1), "liq<50M": round(lo[0], 1),
                    "delay_1_bar": round(d1[0], 1), "delay_t": round(d1[1], 2), "without_best_month": round(nb[0], 1), "nb_t": round(nb[1], 2),
                    "excl_6sigma_bars": round(clean[0], 1), "overnight_gap_bp": round(1e4 * gx, 1), "gap_t": round(gt, 2),
                }
                for k, v in r["attacks"].items():
                    log_trial("G30", "G30_attack", f"{name} {k}", "DEV", "xs_bp", v, params={"h": h})
        del S, F
        gc.collect()
    print(f"{'candidate':<26s} h  sign |   DEV bp (t)      n  |   CTX bp (t)      n  | halfA halfB | liq>=50M <50M | delay1 (t) | no-best-month (t) | clean | o/n gap (t) | years ok")
    for name, r in res.items():
        a = r["attacks"]
        yh = year_hits[name]
        print(f"{name:<26s} {r['h']:>2d}  {r['sign']:+d}  | {r['DEV']['bp']:+7.1f} ({r['DEV']['t']:+5.2f}) {r['DEV']['n']:>6d} | {r['CTX']['bp']:+7.1f} ({r['CTX']['t']:+5.2f}) {r['CTX']['n']:>6d} |"
              f" {a['half_A']:+6.1f} {a['half_B']:+6.1f} | {a['liq>=50M']:+7.1f} {a['liq<50M']:+7.1f} | {a['delay_1_bar']:+6.1f} ({a['delay_t']:+4.1f}) | {a['without_best_month']:+7.1f} ({a['nb_t']:+4.1f}) |"
              f" {a['excl_6sigma_bars']:+6.1f} | {a['overnight_gap_bp']:+5.1f} ({a['gap_t']:+4.1f}) | {yh[0]}/{yh[1]}")
        r["years_with_predicted_sign"] = f"{yh[0]}/{yh[1]}"
    Path(__file__).resolve().parents[1].joinpath("results", "g30_attack.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
