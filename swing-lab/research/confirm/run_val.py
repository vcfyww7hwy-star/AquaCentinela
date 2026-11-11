"""The single pre-registered validation run (protocol sections 2, 3; docs/03_preregistration_val.md).

Sample: VAL, 2018-07-02 .. 2022-12-30, survivorship-free universe.
Runs ONCE. It refuses to run if results/val_confirmation.json already exists.

Part D  directional candidates (swinglab/candidates.py), each at its frozen horizon with its
        frozen predicted sign. Statistic: mean over days of (signal mean - control mean) from the
        next open; Newey-West t with 2h lags; one-sided p-value; Holm correction across the list.
        Secondary (reported, not used for the verdict): event-weighted estimate.
Part R  risk-engine claims with pass/fail criteria fixed in the pre-registration.

    SWINGLAB_VAL_TOKEN=PRE-REGISTERED python -m research.confirm.run_val
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "val")

import numpy as np

from research.confirm.prereg_val import DIRECTIONAL, DEV_STOP_TABLE, RISK_CRITERIA
from research.experiments import g12_risk_engine as G12
from research.swinglab import candidates as C
from research.swinglab import earnings as EA
from research.swinglab import engine as E
from research.swinglab import pinelike as ta
from research.swinglab import trades as TR
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

OUT = Path(__file__).resolve().parents[1] / "results" / "val_confirmation.json"


def norm_sf(x: float) -> float:
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def directional(S) -> dict:
    F = C.Feat(S)
    res = {}
    for name in DIRECTIONAL:
        spec = C.SPEC[name]
        sig, ctrl = spec["fn"](F)
        h, sgn = spec["h"], spec["sign"]
        tab = S.event("VAL", "VAL_directional", name, sig, control=ctrl, hs=(h,), params={"h": h}, note="pre-registered")[h]
        # event-weighted secondary: each event weighs the same, against the same-day control mean
        out = S.fwd(h)
        u = S.uni if ctrl is None else (ctrl & S.uni)
        m_ctl, _ = E.day_means(out, u, 20)
        s = sig & S.uni
        ex = np.where(s, out - m_ctl[:, None], np.nan)
        day_sum = np.nansum(ex, axis=1)
        n_day = np.isfinite(ex).sum(axis=1)
        r = S.rows
        ew_mean = float(np.nansum(day_sum[r]) / max(n_day[r].sum(), 1))
        x = np.where(n_day > 0, day_sum, 0.0)[r] / max(n_day[r].mean(), 1e-12)
        _, ew_t, _ = E.nw_mean(x, 2 * h)
        t = tab["xs_t"] if tab["xs_t"] is not None else float("nan")
        p = norm_sf(sgn * t) if np.isfinite(t) else 1.0
        res[name] = {"h": h, "predicted_sign": sgn, "use": spec["use"], "xs_bp": tab["xs_bp"], "xs_t": tab["xs_t"],
                     "p_one_sided": round(p, 5), "events": tab["events"], "days": tab["days"],
                     "event_weighted_bp": round(1e4 * ew_mean, 1), "event_weighted_t": round(float(ew_t), 2)}
    # Holm step-down across the list
    order = sorted(res, key=lambda k: res[k]["p_one_sided"])
    m = len(order)
    still = True
    for i, k in enumerate(order):
        thr = 0.05 / (m - i)
        ok = still and res[k]["p_one_sided"] <= thr
        still = ok
        res[k]["holm_threshold"] = round(thr, 5)
        res[k]["verdict"] = ("CONFIRMED" if ok else ("right sign, not significant after correction" if res[k]["xs_bp"] is not None and np.sign(res[k]["xs_bp"]) == res[k]["predicted_sign"] else "WRONG SIGN"))
    return res


def risk(S) -> dict:
    res = {}
    c = S.P.cf
    est = G12.estimators(S)
    sc = RISK_CRITERIA["scale_from_ctx"]
    # R1 forecast ranking
    r1 = {}
    for h in (5, 10, 20):
        rv = G12.realised(S, h)
        r1[h] = {k: round(G12.qlike(rv, est[k], S.uni, sc[k][str(h)])[0], 4) for k in ("atr14/close", "ewma20", "yang_zhang20", "robust_ewma20")}
    res["R1_qlike"] = r1
    res["R1_pass"] = all(r1[h]["atr14/close"] < min(r1[h]["ewma20"], r1[h]["yang_zhang20"]) for h in r1)
    # R2 calibration
    f = est["atr14/close"] * sc["atr14/close"]["10"]
    x = np.log1p(S.fwd(10)) / (f * np.sqrt(10))
    x = x[S.uni & np.isfinite(x)]
    q05, q95, beyond = float(np.quantile(x, 0.05)), float(np.quantile(x, 0.95)), float(np.mean(np.abs(x) > 2))
    res["R2_calibration"] = {"q05": round(q05, 3), "q95": round(q95, 3), "share_beyond_2": round(beyond, 4), "n": int(len(x))}
    lo5, hi5 = RISK_CRITERIA["q05_range"]
    lo95, hi95 = RISK_CRITERIA["q95_range"]
    res["R2_pass"] = bool(lo5 <= q05 <= hi5 and lo95 <= q95 <= hi95)
    # R3 stop-out table
    rng = np.random.default_rng(12)
    rnd = S.uni & (rng.random(S.uni.shape) < 0.02)
    atr = S.atr(14)
    tabl, worst = {}, 0.0
    for k in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
        for h in (5, 10, 20):
            tr = TR.simulate(S.P, rnd, atr, rows=S.rows, stop_k=k, max_hold=h, cost_bp=0, stop_extra_bp=0)
            p = float(tr["reason"].isin(["stop", "gap_stop"]).mean())
            dev = DEV_STOP_TABLE[f"k{k}_h{h}"]
            tabl[f"k{k}_h{h}"] = {"val": round(p, 3), "dev": dev, "diff": round(p - dev, 3)}
            worst = max(worst, abs(p - dev))
    res["R3_stop_table"] = tabl
    res["R3_max_abs_diff"] = round(worst, 3)
    res["R3_pass"] = bool(worst <= RISK_CRITERIA["stop_table_tolerance"])
    # R4 earnings gap risk
    ev = EA.load(S)
    react = ev["react"] & S.uni
    near = ev["react"] | ev["ann"]
    non = S.uni & ~near
    with np.errstate(divide="ignore", invalid="ignore"):
        gap_atr = (S.P.o - ta.shift(c, 1)) / ta.shift(atr, 1)
    ge, go = gap_atr[react & np.isfinite(gap_atr)], gap_atr[non & np.isfinite(gap_atr)]
    pe, po = float(np.mean(ge < -2)), float(np.mean(go < -2))
    res["R4_earnings_gap"] = {"p_gap_lt_-2atr_reaction": round(pe, 4), "p_gap_lt_-2atr_ordinary": round(po, 5), "ratio": round(pe / max(po, 1e-9), 1),
                              "p_gap_lt_-1atr_reaction": round(float(np.mean(ge < -1)), 4), "reaction_bars": int(len(ge))}
    res["R4_pass"] = bool(pe / max(po, 1e-9) >= RISK_CRITERIA["earnings_gap_ratio_min"])
    # R5 exits on random entries
    def bpbar(**kw):
        tr = TR.simulate(S.P, rnd, atr, rows=S.rows, **kw)
        return 1e4 * float(tr["ret"].mean()) / float(tr["bars"].mean()), int(len(tr))
    below20 = c < ta.sma(c, 20)
    a = bpbar(stop_k=1e6, max_hold=20)
    b = bpbar(stop_k=2.0, max_hold=20)
    d = bpbar(stop_k=1e6, max_hold=40, exit_sig=below20)
    e3 = bpbar(stop_k=3.0, max_hold=20)
    res["R5_exits_bp_per_bar"] = {"hold20_no_stop": round(a[0], 2), "stop2atr_hold20": round(b[0], 2), "stop3atr_hold20": round(e3[0], 2), "exit_under_20d_avg": round(d[0], 2)}
    res["R5_pass"] = bool(a[0] > b[0] and a[0] > d[0])
    # R6 regime: SPY volatility below / above its 200-day average, and single-stock tail
    spy = c[:, [S.spy]]
    sma200 = ta.sma(spy, 200)[:, 0]
    above = spy[:, 0] > sma200
    r1d = S.P.ret[:, S.spy]
    st = np.r_[False, above[:-1]]
    known = np.r_[False, np.isfinite(sma200)[:-1]]
    rr = S.rows & np.isfinite(r1d) & known
    v_in, v_out = float(np.std(r1d[rr & st])), float(np.std(r1d[rr & ~st]))
    f20 = S.fwd(20)
    fin = np.isfinite(sma200)[:, None]
    p_up = float(np.nanmean(f20[S.uni & fin & above[:, None]] < -0.10))
    p_dn = float(np.nanmean(f20[S.uni & fin & ~above[:, None]] < -0.10))
    res["R6_regime"] = {"spy_vol_above_ann": round(100 * v_in * np.sqrt(252), 1), "spy_vol_below_ann": round(100 * v_out * np.sqrt(252), 1),
                        "ratio": round(v_out / v_in, 2), "days_below": int((rr & ~st).sum()),
                        "stock_p_loss10_20d_above": round(p_up, 4), "stock_p_loss10_20d_below": round(p_dn, 4)}
    res["R6_pass"] = bool(v_out / v_in >= RISK_CRITERIA["regime_vol_ratio_min"] and p_dn > p_up)
    for k in ("R1", "R2", "R3", "R4", "R5", "R6"):
        log_trial("VAL", "VAL_risk", k, "VAL", "pass", float(res[f"{k}_pass"]), note="pre-registered")
    return res


def main() -> int:
    if OUT.exists():
        print("The validation run has already been made; refusing to repeat it (protocol section 3).")
        return 2
    S = Study("VAL")
    res = {"sample": "VAL 2018-07-02..2022-12-30", "universe_names_per_day": float(S.uni[S.rows].sum(axis=1).mean())}
    res["directional"] = directional(S)
    res["risk"] = risk(S)
    OUT.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
