"""G80 - An outside review of the Relative Volume pane, checked against the data.

Pre-registered in docs/RESEARCH_LOG.md, entry 10 (committed before this script was run).
Definitions follow trend-flow-suite/pine/relative_volume.pine on daily bars:
    rvol = v / lagged EWMA50(v);  z = r / sqrt(lagged EWMA50(r^2));  ext = (c - EMA25(EMA25(c))) / ATR14
    A    = rvol >= 2 & |z| <= 0.5 & ext <= -1.5           CLV = (c - l) / (h - l)
Samples: DEV 2011-01..2018-06 (biased) and POST 2018-07-02..2026-11-09 (survivorship-free, post-hoc).

Run:   cd swing-lab && python -m research.experiments.g80_rvol_review
Saves: research/results/g80_rvol_review.json
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["SWINGLAB_REGISTRY_TAG"] = "g80"

import numpy as np

from research.swinglab import engine as E
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

SPAN = 50
MIN_OBS = 60
H = 10
Q05, Q95, Q25, Q75 = -1.26, 1.10, -0.40, 0.47        # SL Risk Desk, h = 10
STOP_K = 3.0
EDGES = [0.0, 0.6, 1.0, 1.5, 2.0, 3.0, np.inf]


def ewma_lagged(x: np.ndarray, span: int) -> np.ndarray:
    """Value of a Pine-style EWMA BEFORE bar t is included (seeded with the first finite value)."""
    a = 2.0 / (span + 1.0)
    out = np.full(x.shape, np.nan, dtype=np.float64)
    state = np.full(x.shape[1], np.nan)
    for t in range(x.shape[0]):
        out[t] = state
        xt = x[t]
        ok = np.isfinite(xt)
        seed = ok & ~np.isfinite(state)
        state = np.where(seed, xt, np.where(ok, a * xt + (1.0 - a) * state, state))
    return out


def features(S: Study) -> dict:
    P = S.P
    c, cf, h, l, o, v = P.c, P.cf, P.h, P.l, P.o, P.v
    have = np.isfinite(c) & np.isfinite(v)
    vv = np.where(have, v, np.nan)
    nobs = np.cumsum(have, axis=0) - have                       # earlier valid bars
    ev = ewma_lagged(vv, SPAN)
    with np.errstate(divide="ignore", invalid="ignore"):
        rvol = np.where(ev > 0, vv / ev, np.nan)
        lc = np.log(np.where(have, c, np.nan))
        prev = E.lag(np.log(cf), 1)
        r = lc - prev
        s2 = ewma_lagged(r * r, SPAN)
        z = np.where(s2 > 0, r / np.sqrt(s2), np.nan)
        lv = np.log(np.where(vv > 0, vv, np.nan))
        lev = ewma_lagged(lv, SPAN)
    atr = S.atr(14)
    alpha = 2.0 / 26.0
    base = E.ewma(E.ewma(cf, alpha), alpha)
    with np.errstate(divide="ignore", invalid="ignore"):
        ext = np.where(atr > 0, (cf - base) / atr, np.nan)
        rng = h - l
        clv = np.where(rng > 0, (c - l) / rng, 0.5)
    ok = have & (nobs >= MIN_OBS) & np.isfinite(rvol) & np.isfinite(z) & np.isfinite(ext)
    return {"rvol": rvol, "z": z, "ext": ext, "clv": clv, "atr": atr, "ok": ok, "lv_dev": lv - lev}


def risk_outcomes(S: Study, F: dict) -> tuple[np.ndarray, np.ndarray]:
    """y = ln(c[t+H]/c[t]) / (ATR/c * sqrt(H)); stop hit = min(low[t+1..t+H]) <= open[t+1] - 3 ATR."""
    P = S.P
    cf, l, o = P.cf, P.l, P.o
    T = cf.shape[0]
    last = int(np.flatnonzero(S.rows)[-1])
    y = np.full(cf.shape, np.nan)
    hit = np.full(cf.shape, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        unit = F["atr"] / cf * np.sqrt(H)
        y[: T - H] = np.log(cf[H:] / cf[: T - H]) / unit[: T - H]
        lo = np.full(cf.shape, np.inf)
        for k in range(1, H + 1):
            lk = np.full(cf.shape, np.nan)
            lk[: T - k] = l[k:]
            lo = np.fmin(lo, np.where(np.isfinite(lk), lk, np.inf))
        o1 = np.full(cf.shape, np.nan)
        o1[: T - 1] = o[1:]
        stop = o1 - STOP_K * F["atr"]
        hit = np.where(np.isfinite(stop) & np.isfinite(lo), (lo <= stop).astype(float), np.nan)
    y[~S.rows] = np.nan
    hit[~S.rows] = np.nan
    y[max(last - H + 1, 0):] = np.nan
    hit[max(last - H + 1, 0):] = np.nan
    return y, hit


def run(S: Study, label: str, earnings_react=None) -> dict:
    F = features(S)
    uni = S.uni & F["ok"]
    rvol, z, ext, clv = F["rvol"], F["z"], F["ext"], F["clv"]
    out: dict = {"sample": label}

    # V1 descriptive
    rv = rvol[uni]
    out["V1"] = {"stock_days": int(uni.sum()), "median_rvol": float(np.median(rv)), "mean_rvol": float(np.mean(rv)),
                 "share_rvol_ge_2": float((rv >= 2).mean()), "share_rvol_ge_3": float((rv >= 3).mean())}
    lvd = np.where(uni, F["lv_dev"], np.nan)
    sd_stock = np.nanstd(lvd, axis=0)
    n_stock = np.isfinite(lvd).sum(axis=0)
    sel = n_stock >= 250
    share2 = np.nansum(np.where(uni, rvol >= 2, np.nan), axis=0) / np.maximum(n_stock, 1)
    out["V1"]["per_stock"] = {
        "stocks": int(sel.sum()),
        "sd_log_volume_p10_p50_p90": [float(x) for x in np.percentile(sd_stock[sel], [10, 50, 90])],
        "share_days_rvol_ge_2_p10_p50_p90": [float(x) for x in np.percentile(share2[sel], [10, 50, 90])]}
    for k, val in (("median_rvol", out["V1"]["median_rvol"]), ("share_rvol_ge_2", out["V1"]["share_rvol_ge_2"])):
        log_trial("G80", "rvol_review_V1", k, label, k, val, note="descriptive")

    # V2 / V3
    flat = np.abs(z) <= 0.5
    stretched = ext <= -1.5
    A = uni & (rvol >= 2) & flat & stretched
    selling_climax = (rvol >= 3) & (z <= -2) & (ext <= -2.5)
    C_vol = uni & flat & stretched & (rvol < 2)
    C_e05 = uni & stretched & ~A & ~selling_climax
    A_hi, A_lo = A & (clv >= 0.5), A & (clv < 0.5)
    out["counts"] = {"A": int(A.sum()), "C_vol": int(C_vol.sum()), "C_e05": int(C_e05.sum()),
                     "A_clv_lt_0.5_share": float(A_lo.sum() / max(A.sum(), 1)),
                     "A_per_stock_year": float(A.sum() / max(uni.sum(), 1) * 252)}
    ev = lambda name, sig, ctrl: S.event("G80", "rvol_review", f"{label}: {name}", sig, control=ctrl, hs=(5, 10),
                                         note="post-hoc on POST" if label == "POST" else "")
    out["V2"] = {"A_vs_C_vol": ev("A vs same price action without high volume", A, C_vol),
                 "A_vs_C_e05": ev("A vs E05 control (stretched bars)", A, C_e05),
                 "A_vs_universe": ev("A vs universe", A, None),
                 "C_vol_vs_C_e05": ev("flat stretched bars without high volume vs E05 control", C_vol, C_e05)}
    out["V3"] = {"A_clv_hi_vs_C_vol": ev("A with CLV >= 0.5 vs C_vol", A_hi, C_vol),
                 "A_clv_lo_vs_C_vol": ev("A with CLV < 0.5 vs C_vol", A_lo, C_vol)}

    # V4 risk
    y, hit = risk_outcomes(S, F)
    base_ok = uni & np.isfinite(y) & np.isfinite(hit)
    def cell(mask):
        yy, hh = y[mask], hit[mask]
        return {"n": int(mask.sum()), "cov90": float(((yy >= Q05) & (yy <= Q95)).mean()),
                "cov50": float(((yy >= Q25) & (yy <= Q75)).mean()), "below5": float((yy < Q05).mean()),
                "above95": float((yy > Q95).mean()), "stop_hit": float(hh.mean())}
    v4 = {"all": cell(base_ok)}
    for lo_, hi_ in zip(EDGES[:-1], EDGES[1:]):
        m = base_ok & (rvol > lo_) & (rvol <= hi_)
        v4[f"({lo_},{hi_}]"] = cell(m)
    if earnings_react is not None:
        hi = base_ok & (rvol > 2)
        v4["rvol>2 & earnings reaction day"] = cell(hi & earnings_react)
        v4["rvol>2 & not earnings"] = cell(hi & ~earnings_react)
        v4["rvol<=2 & not earnings"] = cell(base_ok & (rvol <= 2) & ~earnings_react)
    out["V4"] = v4
    for k, c_ in v4.items():
        for m in ("cov90", "stop_hit"):
            log_trial("G80", "rvol_review_V4", f"{label}: {m} for rvol {k}", label, m, c_[m], n=c_["n"], note="descriptive")
    return out


def main():
    which = sys.argv[1:] or ["DEV", "POST"]
    res = {}
    if "DEV" in which:
        res["DEV"] = run(Study("DEV"), "DEV")
        print(json.dumps(res["DEV"]["V1"], indent=1), json.dumps(res["DEV"]["counts"]))
    if "POST" in which:
        os.environ["SWINGLAB_OPEN_LOCKBOX"] = "I-HAVE-FROZEN-THE-RULES"
        from research.swinglab.data import PARTITIONS, open_lockbox
        from research.swinglab import earnings as ER
        panel = open_lockbox("G80: data check of an outside review of the Relative Volume pane (post-hoc, pre-registered in RESEARCH_LOG entry 10)",
                             ["G80 V1-V4 as written in docs/RESEARCH_LOG.md entry 10"])
        PARTITIONS["LOCKBOX"] = ("2018-07-02", "2026-11-09")
        S = Study("LOCKBOX", panel=panel)
        evs = ER.load(S)
        react = evs["react"]
        react = react | np.vstack([np.zeros((1, react.shape[1]), bool), react[:-1]])   # the reaction bar or the bar after it
        res["POST"] = run(S, "POST", earnings_react=react)
        print(json.dumps(res["POST"]["V1"], indent=1), json.dumps(res["POST"]["counts"]))
    path = Path(__file__).resolve().parents[1] / "results" / "g80_rvol_review.json"
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update(res)
    path.write_text(json.dumps(old, indent=1, default=str))
    for k, r in res.items():
        print(f"\n=== {k}")
        for name, tab in {**r["V2"], **r["V3"]}.items():
            print(f"{name:>22s}  " + "  ".join(f"h{h}: {c['xs_bp']:+.1f} bp (t {c['xs_t']:+.2f}, n {c['events']})" for h, c in tab.items()))
        print("V4:")
        for b, c in r["V4"].items():
            print(f"  {b:>32s}  n {c['n']:>9d}  cov90 {100 * c['cov90']:5.1f}  cov50 {100 * c['cov50']:5.1f}  <5% {100 * c['below5']:4.1f}  >95% {100 * c['above95']:4.1f}  stop {100 * c['stop_hit']:5.1f}")


if __name__ == "__main__":
    main()
