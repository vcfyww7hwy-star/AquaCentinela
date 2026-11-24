#!/usr/bin/env python3
"""E11 - Is the "absorption at lows" mark about volume at all? (strict control)

Tests four claims of the external review of pine/relative_volume.pine on the shared panel of E10:
  (a) the published control (all bars >= 1.5 ATR below the baseline) did not hold the price action
      fixed, so the effect may be "the price stopped falling" and not volume;
  (b) the close-to-close definition also marks a gap up that is sold all day (close location);
  (c) the events cluster in market-wide sell-offs; a market-relative volume would behave differently;
  (d) after multiplicity and costs the edge is marginal or nil.

Definitions (all on rows with eval == True; every feature is known at the close of bar t):
  S         ext <= -1.5 and |z| <= 0.5 and finite rvol         "stretched low, price stopped"
  T         S and rvol >= 2          (identical to the shipped absorb_bottom flag; asserted)
  C         S and rvol < 2           strict control: same price action, no unusual volume
  C_normal  S and 0.8 <= rvol <= 1.25
  OC        ext <= -1.5 and not climax_dn and not absorb_bottom    the control of E05 / E08
  idio      rvol / exp(mkt_lrvol)    volume relative to the median stock of the set that day

Tests P1..P7 were specified before this script was run on any set other than A. PRIMARY family:
T - C on fzd10 (date-demeaned 10-bar forward return in risk units) in the five sets, Holm-adjusted.
Everything else is SECONDARY and descriptive. Every difference with an interval is counted.

POST HOC (section "post_hoc", added after the first full run had been read; the numbers of P1..P7
did not change because every test has its own random generator): the primary difference on the last
36 months of each set, where selection of survivors is weakest; entry at the next open instead of
the signal close; quarter blocks instead of month blocks for the primary interval.

Uncertainty: month-block bootstrap, 2000 resamples (same algorithm as experiments/e05; the primary
test is cross-checked against e05.boot_diff, a pandas route and a month-clustered standard error).

  python3 -I experiments/e11_absorption_strict_control.py [--panel DIR] [--sets A B DJ LH MS]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json
import math
import time
import zlib

import numpy as np
import pandas as pd

import experiments.e05_validation_lite as e05

DEFAULT_PANEL = "/tmp/claude-0/-home-user-AquaCentinela/b2916ecb-3cd8-557a-8730-1dacd8557876/scratchpad/panel"
SETS = ("A", "B", "DJ", "LH", "MS")
SEED = 20261123
N_BOOT = 2000
PUBLISHED_T = {"A": 439, "B": 499, "DJ": 60, "LH": 2386, "MS": 9312}
PUBLISHED_OLD_FZ10 = {"A": 0.2197, "B": 0.1276, "DJ": 0.0169, "LH": 0.018, "MS": 0.0794}
COST_ROUND_TRIP_PCT = {"A": (0.10, 0.20), "B": (0.10, 0.20), "DJ": (0.10, 0.20), "LH": (0.10, 0.20),
                       "MS": (0.30, 0.60)}
COLS = ["ticker", "date", "month", "half", "eval", "rvol", "z", "ext", "sigma", "sig0", "clv", "gap", "body",
        "absorb_bottom", "climax_dn", "mkt_lrvol", "r_mkt", "spy_rvol",
        "f5", "f10", "fx5", "fx10", "fz5", "fz10", "fz20", "fzd5", "fzd10", "fzd20", "fzx10"]
P1_METRICS = ("fzd10", "fz10", "fz5", "fz20", "fzd5", "fzd20", "fzx10")
BUCKETS = (("<0.6", 0.0, 0.6), ("0.6-0.8", 0.6, 0.8), ("0.8-1.25", 0.8, 1.25), ("1.25-2", 1.25, 2.0),
           ("2-3", 2.0, 3.0), (">=3", 3.0, np.inf))
COUNT = {}                      # section -> number of differences / slopes with an interval


def rng_for(label: str):
    """One generator per test, so a result does not depend on the order of the tests."""
    return np.random.default_rng([SEED, zlib.crc32(label.encode())])


def _r(x, k=4):
    return None if x is None or not np.isfinite(x) else round(float(x), k)


# --------------------------------------------------------------------------- bootstrap helpers
def boot_diff_p(v_s, m_s, v_c, m_c, rng):
    """Same algorithm and random draws as e05.boot_diff; also returns the bootstrap standard error
    and two-sided p-values (percentile bootstrap and normal approximation)."""
    ks, kc = np.isfinite(v_s), np.isfinite(v_c)
    v_s, m_s, v_c, m_c = v_s[ks], m_s[ks], v_c[kc], m_c[kc]
    if len(v_s) == 0 or len(v_c) == 0:
        return {"diff": None, "lo": None, "hi": None, "n": int(len(v_s)), "n_control": int(len(v_c))}
    mc = np.unique(np.concatenate([m_s, m_c]))
    ss, ns = e05._agg(v_s, m_s, mc)
    sc, nc = e05._agg(v_c, m_c, mc)
    est = ss.sum() / ns.sum() - sc.sum() / nc.sum()
    idx = rng.integers(0, len(mc), (N_BOOT, len(mc)))
    with np.errstate(divide="ignore", invalid="ignore"):
        bt = ss[idx].sum(1) / ns[idx].sum(1) - sc[idx].sum(1) / nc[idx].sum(1)
    bt = bt[np.isfinite(bt)]
    lo, hi = np.percentile(bt, [2.5, 97.5])
    se = float(bt.std(ddof=1))
    p_boot = min(1.0, 2.0 * min((1 + int((bt <= 0).sum())) / (len(bt) + 1),
                                (1 + int((bt >= 0).sum())) / (len(bt) + 1)))
    p_norm = math.erfc(abs(est) / se / math.sqrt(2.0)) if se > 0 else None
    return {"diff": _r(est), "lo": _r(lo), "hi": _r(hi), "n": int(len(v_s)), "n_control": int(len(v_c)),
            "mean_signal": _r(ss.sum() / ns.sum()), "mean_control": _r(sc.sum() / nc.sum()),
            "se": _r(se), "p_boot": _r(p_boot, 5), "p_norm": _r(p_norm, 6),
            "months": int(len(mc)), "months_with_signal": int((ns > 0).sum()),
            "valid_resamples": int(len(bt))}


def cmp(D, col, s_mask, c_mask, label, section, scale=1.0, values=None):
    """Difference of means (signal - control) of column col, month-block bootstrap. Counted."""
    v = (D[col] if values is None else values) * scale
    m = D["month"]
    COUNT[section] = COUNT.get(section, 0) + 1
    return boot_diff_p(v[s_mask], m[s_mask], v[c_mask], m[c_mask], rng_for(label))


def mean_ci(D, col, mask, label, scale=1.0, values=None):
    v = (D[col] if values is None else values) * scale
    return e05.boot_mean(v[mask], D["month"][mask], rng_for(label))


def ols_month_boot(y, X, months, rng, names):
    """OLS with intercept already in X; month-block bootstrap of the normal equations."""
    k = np.isfinite(y) & np.isfinite(X).all(1)
    y, X, months = y[k], X[k], months[k]
    mc, inv = np.unique(months, return_inverse=True)
    p = X.shape[1]
    xtx = np.zeros((len(mc), p, p))
    xty = np.zeros((len(mc), p))
    for i in range(p):
        xty[:, i] = np.bincount(inv, weights=X[:, i] * y, minlength=len(mc))
        for j in range(p):
            xtx[:, i, j] = np.bincount(inv, weights=X[:, i] * X[:, j], minlength=len(mc))
    beta = np.linalg.solve(xtx.sum(0), xty.sum(0))
    idx = rng.integers(0, len(mc), (N_BOOT, len(mc)))
    A, b = xtx[idx].sum(1), xty[idx].sum(1)
    ok = np.abs(np.linalg.det(A)) > 1e-12
    bs = np.linalg.solve(A[ok], b[ok][:, :, None])[:, :, 0]
    out = {"n": int(len(y)), "months": int(len(mc))}
    for j, name in enumerate(names):
        lo, hi = np.percentile(bs[:, j], [2.5, 97.5])
        out[name] = {"coef": _r(beta[j]), "lo": _r(lo), "hi": _r(hi), "se": _r(bs[:, j].std(ddof=1))}
    return out


def same_date_diff(D, v, T, C, label, section):
    """P4: dates with at least one T and one C bar; within-date mean(T) - mean(C), weighted by the
    number of T bars on the date; months resampled."""
    COUNT[section] = COUNT.get(section, 0) + 1
    dc, nd = D["date_code"], D["n_dates"]
    fin = np.isfinite(v)
    T, C = T & fin, C & fin
    nT = np.bincount(dc[T], minlength=nd).astype(float)
    nC = np.bincount(dc[C], minlength=nd).astype(float)
    sT = np.bincount(dc[T], weights=v[T], minlength=nd)
    sC = np.bincount(dc[C], weights=v[C], minlength=nd)
    ok = (nT > 0) & (nC > 0)
    if not ok.any():
        return {"diff": None}
    delta, w, mo = sT[ok] / nT[ok] - sC[ok] / nC[ok], nT[ok], D["month_of_date"][ok]
    mc, inv = np.unique(mo, return_inverse=True)
    num = np.bincount(inv, weights=w * delta, minlength=len(mc))
    den = np.bincount(inv, weights=w, minlength=len(mc))
    est = num.sum() / den.sum()
    idx = rng_for(label).integers(0, len(mc), (N_BOOT, len(mc)))
    bt = num[idx].sum(1) / den[idx].sum(1)
    lo, hi = np.percentile(bt, [2.5, 97.5])
    return {"diff": _r(est), "lo": _r(lo), "hi": _r(hi), "n_T_used": int(w.sum()), "n_T_total": int(T.sum()),
            "dates_used": int(ok.sum()), "months": int(len(mc)), "se": _r(bt.std(ddof=1)),
            "mean_C_per_date": _r(nC[ok].mean(), 1)}


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = round(run, 6)
    return out


# --------------------------------------------------------------------------- data
def load(panel_dir, name):
    df = pd.read_parquet(pathlib.Path(panel_dir) / f"panel_{name}.parquet", columns=COLS)
    # date-level market series from ALL rows of the set (as built in E10), then a trailing 10-bar
    # market return that is known at the close of t
    dl = df.groupby("date", sort=True).agg(r_mkt=("r_mkt", "first"), mkt_lrvol=("mkt_lrvol", "first"))
    dl["r_mkt10"] = dl["r_mkt"].rolling(10).sum()
    # entry at the next open: forward log return from open[t+1] to close[t+10] = f10 - gap[t+1]
    tk = df["ticker"].to_numpy()
    gap_next = np.r_[df["gap"].to_numpy(dtype=float)[1:], np.nan]
    gap_next[np.r_[tk[1:] != tk[:-1], True]] = np.nan
    df["f10o"] = df["f10"].to_numpy(dtype=float) - gap_next
    df["fx10o"] = df["f10o"] - df.groupby("date")["f10o"].transform("mean")
    n_all, n_tickers = len(df), df["ticker"].nunique()
    ev = df[df["eval"]].reset_index(drop=True)
    del df
    D = {"name": name, "n_all_rows": n_all, "n_tickers": n_tickers, "n": len(ev)}
    for c in COLS:
        if c in ("ticker", "date", "half", "eval"):
            continue
        a = ev[c].to_numpy()
        D[c] = a.astype(np.float64) if a.dtype.kind == "f" else a
    D["f10o"], D["fx10o"] = ev["f10o"].to_numpy(dtype=float), ev["fx10o"].to_numpy(dtype=float)
    D["ticker"] = ev["ticker"].to_numpy()
    D["half"] = ev["half"].to_numpy()
    codes, uniq = pd.factorize(ev["date"], sort=True)
    D["date_code"], D["n_dates"], D["dates"] = codes, len(uniq), pd.DatetimeIndex(uniq)
    mo = np.zeros(len(uniq), dtype=np.int64)
    mo[codes] = D["month"]
    D["month_of_date"] = mo
    dle = dl.reindex(D["dates"])
    D["date_r_mkt"], D["date_mkt_lrvol"] = dle["r_mkt"].to_numpy(float), dle["mkt_lrvol"].to_numpy(float)
    D["date_r_mkt10"] = dle["r_mkt10"].to_numpy(float)
    D["r_mkt10"] = D["date_r_mkt10"][codes]
    D["n_eval_per_date"] = np.bincount(codes, minlength=len(uniq))
    return D


# --------------------------------------------------------------------------- analysis of one set
def analyse(D):
    name = D["name"]
    R = {}
    rvol, z, ext = D["rvol"], D["z"], D["ext"]
    fin = np.isfinite(rvol)
    with np.errstate(invalid="ignore"):
        E = ext <= -1.5                                           # stretched low, any move, any volume
        S = E & (np.abs(z) <= 0.5) & fin
        T = S & (rvol >= 2.0)
        C = S & (rvol < 2.0)
        Cn = S & (rvol >= 0.8) & (rvol <= 1.25)
        OC = E & ~D["climax_dn"] & ~D["absorb_bottom"]
    assert (T == D["absorb_bottom"]).all(), "T must equal the shipped absorb_bottom flag"
    assert int(T.sum()) == PUBLISHED_T[name], (name, int(T.sum()))
    assert not (T & C).any() and ((T | C) == S).all()
    stock_years = D["n"] / 252.0
    R["counts"] = {
        "tickers": int(D["n_tickers"]), "eval_rows": int(D["n"]), "eval_dates": int(D["n_dates"]),
        "eval_months": int(len(np.unique(D["month"]))),
        "first_eval": str(D["dates"][0].date()), "last_eval": str(D["dates"][-1].date()),
        "stretched_E": int(E.sum()), "S": int(S.sum()), "T": int(T.sum()), "C": int(C.sum()),
        "C_normal": int(Cn.sum()), "old_control_OC": int(OC.sum()),
        "share_of_S_with_rvol_ge2_pct": _r(100 * T.sum() / S.sum(), 2),
        "share_of_eval_rows_in_S_pct": _r(100 * S.sum() / D["n"], 2),
        "T_per_stock_year": _r(T.sum() / stock_years, 3),
        "S_per_stock_year": _r(S.sum() / stock_years, 2),
        "nan_fzd10_in_S": int(np.isnan(D["fzd10"][S]).sum()),
        "max_abs_fzd10_in_S": _r(np.nanmax(np.abs(D["fzd10"][S])), 2),
        "median_sig0_T_pct_per_day": _r(100 * np.median(D["sig0"][T]), 3),
        "median_sig0_C_pct_per_day": _r(100 * np.median(D["sig0"][C]), 3),
        "pct_per_risk_unit_h10_T": _r(100 * np.median(D["sig0"][T]) * math.sqrt(10), 3),
        "median_ext_T": _r(np.median(ext[T]), 2), "median_ext_C": _r(np.median(ext[C]), 2),
        "median_rvol_T": _r(np.median(rvol[T]), 2), "median_rvol_C": _r(np.median(rvol[C]), 2)}

    # ------------------------------------------------------------------ P1 strict control
    p1 = {"T_minus_C": {}, "T_minus_C_normal": {}}
    for k in P1_METRICS:
        sec = "P1_primary" if k == "fzd10" else "P1_secondary"
        p1["T_minus_C"][k] = cmp(D, k, T, C, f"{name}|P1|T-C|{k}", sec)
        p1["T_minus_C_normal"][k] = cmp(D, k, T, Cn, f"{name}|P1|T-Cn|{k}", "P1_secondary")
    p1["old_comparison_T_minus_OC_fz10"] = cmp(D, "fz10", T, OC, f"{name}|P1|old|fz10", "P1_reference")
    # decomposition of the old number: (T - OC) = (T - C) + (C - OC), exact
    p1["C_minus_OC_fz10"] = cmp(D, "fz10", C, OC, f"{name}|P1|C-OC|fz10", "P1_reference")
    old, strict, comp = (p1["old_comparison_T_minus_OC_fz10"]["diff"], p1["T_minus_C"]["fz10"]["diff"],
                         p1["C_minus_OC_fz10"]["diff"])
    p1["decomposition_fz10"] = {"old_T_minus_OC": old, "volume_part_T_minus_C": strict,
                                "price_stopped_part_C_minus_OC": comp,
                                "identity_error": _r(old - strict - comp, 4)}
    with np.errstate(invalid="ignore"):
        p1["old_control_composition_pct"] = {
            "stopped_abs_z_le_0.5": _r(100 * (OC & (np.abs(z) <= 0.5)).sum() / OC.sum(), 1),
            "falling_z_lt_-0.5": _r(100 * (OC & (z < -0.5)).sum() / OC.sum(), 1),
            "rising_z_gt_0.5": _r(100 * (OC & (z > 0.5)).sum() / OC.sum(), 1)}
    # robustness of the primary (SECONDARY)
    rob = {}
    rob["fzd10_clipped_pm5"] = cmp(D, "fzd10", T, C, f"{name}|P1|clip", "P1_robustness",
                                   values=np.clip(D["fzd10"], -5, 5))
    if len(np.unique(D["half"])) == 2:                 # sets A and B are one ticker half each
        for hname in ("A", "B"):
            hm = D["half"] == hname
            rob[f"ticker_half_{hname}"] = cmp(D, "fzd10", T & hm, C & hm, f"{name}|P1|half{hname}", "P1_robustness")
    mmed = np.median(np.unique(D["month"]))
    early = D["month"] <= mmed
    rob["first_half_of_months"] = cmp(D, "fzd10", T & early, C & early, f"{name}|P1|early", "P1_robustness")
    rob["second_half_of_months"] = cmp(D, "fzd10", T & ~early, C & ~early, f"{name}|P1|late", "P1_robustness")
    rob["split_month_last_of_first_half"] = f"{int(mmed) // 12}-{int(mmed) % 12 + 1:02d}"
    COUNT["P1_robustness"] = COUNT.get("P1_robustness", 0) + 1
    Xs = np.c_[np.ones(S.sum()), T[S].astype(float), ext[S], z[S]]
    rob["ols_fzd10_on_T_ext_z_inside_S"] = ols_month_boot(D["fzd10"][S], Xs, D["month"][S],
                                                         rng_for(f"{name}|P1|ols"), ("intercept", "T", "ext", "z"))
    p1["robustness"] = rob
    yr = D["month"] // 12
    p1["by_year_descriptive_fzd10"] = {
        str(int(y)): {"n_T": int((T & (yr == y)).sum()), "n_C": int((C & (yr == y)).sum()),
                      "T_minus_C": _r(D["fzd10"][T & (yr == y)].mean() - D["fzd10"][C & (yr == y)].mean(), 3)
                      if (T & (yr == y)).any() and (C & (yr == y)).any() else None}
        for y in np.unique(yr)}
    R["P1"] = p1
    # rows of S kept for the pooled confirmation estimate (B + LH + MS)
    R["_pool"] = {"month": D["month"][S], "T": T[S], "fzd10": D["fzd10"][S], "fz10": D["fz10"][S],
                  "x10": 100 * D["fx10"][S], "r10": 100 * np.expm1(D["f10"][S])}

    # ------------------------------------------------------------------ P2 dose-response inside S
    p2 = {"buckets": {}}
    for lab, lo, hi in BUCKETS:
        if lab == "0.8-1.25":
            bm = S & (rvol >= lo) & (rvol <= hi)
        elif lab == "1.25-2":
            bm = S & (rvol > lo) & (rvol < hi)
        else:
            bm = S & (rvol >= lo) & (rvol < hi)
        p2["buckets"][lab] = {"n": int(bm.sum()),
                              "fz10": mean_ci(D, "fz10", bm, f"{name}|P2|{lab}|fz10"),
                              "fzd10": mean_ci(D, "fzd10", bm, f"{name}|P2|{lab}|fzd10")}
    with np.errstate(divide="ignore", invalid="ignore"):
        lrv = np.where(rvol > 0, np.log(rvol), np.nan)
    for k in ("fzd10", "fz10"):
        COUNT["P2_slope"] = COUNT.get("P2_slope", 0) + 1
        sl = ols_month_boot(D[k][S], np.c_[np.ones(S.sum()), lrv[S]], D["month"][S],
                            rng_for(f"{name}|P2|slope|{k}"), ("intercept", "lrvol"))
        sl["effect_of_doubling_volume"] = {q: _r(sl["lrvol"][q2] * math.log(2.0))
                                           for q, q2 in (("est", "coef"), ("lo", "lo"), ("hi", "hi"))}
        p2[f"slope_{k}_on_lrvol"] = sl
    R["P2"] = p2

    # ------------------------------------------------------------------ P3 "price stopped", volume ignored
    with np.errstate(invalid="ignore"):
        stop, fall, rise = E & (np.abs(z) <= 0.5), E & (z < -0.5), E & (z > 0.5)
    p3 = {"n": {"stopped": int(stop.sum()), "falling": int(fall.sum()), "rising": int(rise.sum())}}
    for k in ("fz10", "fzd10"):
        p3[k] = {"mean_stopped": mean_ci(D, k, stop, f"{name}|P3|stop|{k}"),
                 "mean_falling": mean_ci(D, k, fall, f"{name}|P3|fall|{k}"),
                 "mean_rising": mean_ci(D, k, rise, f"{name}|P3|rise|{k}"),
                 "stopped_minus_falling": cmp(D, k, stop, fall, f"{name}|P3|s-f|{k}", "P3"),
                 "stopped_minus_rising": cmp(D, k, stop, rise, f"{name}|P3|s-r|{k}", "P3"),
                 "stopped_minus_rest": cmp(D, k, stop, fall | rise, f"{name}|P3|s-rest|{k}", "P3")}
    # P3b: is high volume informative at stretched lows when the price did NOT stop?
    hv = fin & (rvol >= 2.0)
    lv = fin & (rvol < 2.0)
    p3["high_volume_minus_rest_by_move"] = {}
    for gname, g in (("falling", fall), ("rising", rise)):
        p3["high_volume_minus_rest_by_move"][gname] = {
            k: cmp(D, k, g & hv, g & lv, f"{name}|P3b|{gname}|{k}", "P3b") for k in ("fzd10", "fz10")}
    R["P3"] = p3

    # ------------------------------------------------------------------ P4 same-date control
    R["P4"] = {"fzd10": same_date_diff(D, D["fzd10"], T, C, f"{name}|P4|fzd10", "P4"),
               "fz10": same_date_diff(D, D["fz10"], T, C, f"{name}|P4|fz10", "P4"),
               "r10_pct": same_date_diff(D, 100 * np.expm1(D["f10"]), T, C, f"{name}|P4|r10", "P4")}

    # ------------------------------------------------------------------ P5 close location
    clv = D["clv"]
    with np.errstate(divide="ignore", invalid="ignore"):
        gz, bz = D["gap"] / D["sigma"], D["body"] / D["sigma"]
        gap_sold = (gz >= 0.5) & (bz <= -0.5) & (clv <= 0.33)
    hi_c, lo_c = clv >= 0.5, clv < 0.5
    q = lambda a, m: {p: _r(np.nanquantile(a[m], p / 100), 3) for p in (5, 25, 50, 75, 95)}
    p5 = {"describe_T": {"clv": q(clv, T), "gap_in_sigma": q(gz, T), "body_in_sigma": q(bz, T),
                         "share_clv_lt_0.5_pct": _r(100 * (T & lo_c).sum() / T.sum(), 1),
                         "share_clv_le_0.33_pct": _r(100 * (T & (clv <= 0.33)).sum() / T.sum(), 1),
                         "share_gap_up_then_sold_pct": _r(100 * (T & gap_sold).sum() / T.sum(), 1),
                         "n_gap_up_then_sold": int((T & gap_sold).sum())},
          "describe_C": {"share_clv_lt_0.5_pct": _r(100 * (C & lo_c).sum() / C.sum(), 1),
                         "share_gap_up_then_sold_pct": _r(100 * (C & gap_sold).sum() / C.sum(), 1)},
          "n": {"T_clv_ge_0.5": int((T & hi_c).sum()), "T_clv_lt_0.5": int((T & lo_c).sum()),
                "C_clv_ge_0.5": int((C & hi_c).sum()), "C_clv_lt_0.5": int((C & lo_c).sum())}}
    for k in ("fz10", "fzd10"):
        p5[k] = {"T_high_close_minus_T_low_close": cmp(D, k, T & hi_c, T & lo_c, f"{name}|P5|Thi-Tlo|{k}", "P5"),
                 "T_high_close_minus_C_high_close": cmp(D, k, T & hi_c, C & hi_c, f"{name}|P5|Thi-Chi|{k}", "P5"),
                 "T_low_close_minus_C_low_close": cmp(D, k, T & lo_c, C & lo_c, f"{name}|P5|Tlo-Clo|{k}", "P5_extra"),
                 "C_high_close_minus_C_low_close": cmp(D, k, C & hi_c, C & lo_c, f"{name}|P5|Chi-Clo|{k}", "P5_extra")}
    p5["gap_up_then_sold_T_minus_other_T_fzd10"] = cmp(D, "fzd10", T & gap_sold, T & ~gap_sold,
                                                       f"{name}|P5|gapsold", "P5_extra")
    R["P5"] = p5

    # ------------------------------------------------------------------ P6 clustering, idiosyncratic volume
    dc, nd = D["date_code"], D["n_dates"]
    cntT = np.bincount(dc[T], minlength=nd)
    ktop = int(math.ceil(0.05 * nd))
    top_share = lambda cnt, k: float(np.sort(cnt)[::-1][:k].sum() / cnt.sum())
    rr = rng_for(f"{name}|P6|null")
    s_codes = dc[S]
    null_S = [top_share(np.bincount(rr.choice(s_codes, size=int(T.sum()), replace=False), minlength=nd), ktop)
              for _ in range(200)]
    null_U = [top_share(rr.multinomial(int(T.sum()), D["n_eval_per_date"] / D["n"]), ktop) for _ in range(200)]
    thr_vol = np.nanquantile(D["date_mkt_lrvol"], 0.9)
    thr_ret = np.nanquantile(D["date_r_mkt"], 0.1)
    thr_ret10 = np.nanquantile(D["date_r_mkt10"], 0.1)
    idio = rvol / np.exp(D["mkt_lrvol"])
    with np.errstate(invalid="ignore"):
        Ti, Ci = S & (idio >= 2.0), S & (idio < 2.0)
        allhv = fin & (rvol >= 2.0)
    share = lambda m, cond: _r(100 * (m & cond).sum() / m.sum(), 1)
    groups = (("T", T), ("C", C), ("all_eval_rvol_ge2", allhv), ("all_eval_rows", np.ones(D["n"], bool)))
    n_evd = int((cntT > 0).sum())
    p6 = {"n_T": int(T.sum()), "distinct_dates_with_T": n_evd, "eval_dates": int(nd),
          "share_of_dates_with_T_pct": _r(100 * n_evd / nd, 1),
          "max_T_on_one_date": int(cntT.max()), "busiest_date": str(D["dates"][int(cntT.argmax())].date()),
          "top5pct_of_eval_dates_n": ktop,
          "share_T_on_top5pct_of_eval_dates_pct": _r(100 * top_share(cntT, ktop), 1),
          "same_if_T_drawn_at_random_from_S_pct": _r(100 * float(np.mean(null_S)), 1),
          "same_if_T_drawn_at_random_from_all_eval_rows_pct": _r(100 * float(np.mean(null_U)), 1),
          "share_T_on_top5pct_of_event_dates_pct": _r(100 * top_share(cntT, int(math.ceil(0.05 * n_evd))), 1),
          "share_T_on_dates_with_at_least_5_T_pct": _r(100 * cntT[cntT >= 5].sum() / cntT.sum(), 1),
          "threshold_mkt_rvol_top_decile": _r(math.exp(thr_vol), 3),
          "share_on_top_decile_market_volume_dates_pct": {g: share(m, D["mkt_lrvol"] >= thr_vol) for g, m in groups},
          "share_on_bottom_decile_market_return_dates_pct": {g: share(m, D["r_mkt"] <= thr_ret) for g, m in groups},
          "share_on_bottom_decile_trailing10_market_return_dates_pct":
              {g: share(m, D["r_mkt10"] <= thr_ret10) for g, m in groups},
          "median_market_rvol_on_T_bars": _r(float(np.exp(np.median(D["mkt_lrvol"][T]))), 3),
          "median_market_rvol_on_C_bars": _r(float(np.exp(np.median(D["mkt_lrvol"][C]))), 3),
          "idio": {"n_T_idio": int(Ti.sum()), "n_C_idio": int(Ci.sum()),
                   "share_of_T_that_is_idio_pct": _r(100 * (T & Ti).sum() / T.sum(), 1),
                   "n_T_and_idio": int((T & Ti).sum()), "n_T_not_idio": int((T & ~Ti).sum()),
                   "n_idio_not_T": int((Ti & ~T).sum())}}
    p6["idio"]["T_idio_minus_C_idio"] = {k: cmp(D, k, Ti, Ci, f"{name}|P6|Ti-Ci|{k}", "P6_idio") for k in P1_METRICS}
    p6["idio"]["three_groups"] = {}
    for k in ("fzd10", "fz10"):
        p6["idio"]["three_groups"][k] = {
            "stock_specific_T_and_idio_minus_C": cmp(D, k, T & Ti, C, f"{name}|P6|Tidio-C|{k}", "P6_idio"),
            "market_wide_T_not_idio_minus_C": cmp(D, k, T & ~Ti, C, f"{name}|P6|Tmkt-C|{k}", "P6_idio")}
    spy = D["spy_rvol"]
    with np.errstate(divide="ignore", invalid="ignore"):
        ok_spy = np.isfinite(spy) & (spy > 0)
        rs = rvol / spy
        Tsp, Csp = S & ok_spy & (rs >= 2.0), S & ok_spy & (rs < 2.0)
    p6["spy_relative"] = {"rows_of_S_with_spy_pct": _r(100 * (S & ok_spy).sum() / S.sum(), 1),
                          "n_T_spy": int(Tsp.sum()), "n_C_spy": int(Csp.sum())}
    if Tsp.sum() and Csp.sum():
        for k in ("fzd10", "fz10"):
            p6["spy_relative"][k] = cmp(D, k, Tsp, Csp, f"{name}|P6|spy|{k}", "P6_idio")
    R["P6"] = p6

    # ------------------------------------------------------------------ P7 economics
    every = np.ones(D["n"], bool)
    r5, r10 = 100 * np.expm1(D["f5"]), 100 * np.expm1(D["f10"])
    x5, x10 = 100 * D["fx5"], 100 * D["fx10"]
    lo_w, hi_w = np.nanquantile(r10, [0.005, 0.995])
    series = {"r5_pct": r5, "r10_pct": r10, "x5_pct_vs_set_mean_same_date": x5,
              "x10_pct_vs_set_mean_same_date": x10}
    p7 = {"note": "r = simple close-to-close return in percent; x = log return minus the same-date mean of the set, "
                  "in percent", "T_per_stock_year": _r(T.sum() / stock_years, 3),
          "years_between_marks_per_stock": _r(stock_years / T.sum(), 2)}
    for sname, v in series.items():
        p7[sname] = {"mean_T": mean_ci(D, None, T, f"{name}|P7|T|{sname}", values=v),
                     "mean_C": mean_ci(D, None, C, f"{name}|P7|C|{sname}", values=v),
                     "mean_all_eval": mean_ci(D, None, every, f"{name}|P7|all|{sname}", values=v),
                     "median_T": _r(np.nanmedian(v[T]), 3), "median_C": _r(np.nanmedian(v[C]), 3),
                     "T_minus_C": cmp(D, None, T, C, f"{name}|P7|T-C|{sname}", "P7", values=v)}
    p7["r10_pct"]["T_minus_all_eval"] = cmp(D, None, T, every, f"{name}|P7|T-all|r10", "P7", values=r10)
    p7["r10_pct"]["T_minus_C_winsorised_0.5pct_tails"] = cmp(D, None, T, C, f"{name}|P7|T-C|r10w", "P7",
                                                           values=np.clip(r10, lo_w, hi_w))
    p7["r10_pct"]["share_T_positive_pct"] = _r(100 * float((r10[T] > 0).mean()), 1)
    p7["r10_pct"]["share_C_positive_pct"] = _r(100 * float((r10[C] > 0).mean()), 1)
    c_lo, c_hi = COST_ROUND_TRIP_PCT[name]
    d10 = p7["r10_pct"]["T_minus_C"]
    xT = p7["x10_pct_vs_set_mean_same_date"]["mean_T"]
    p7["after_costs"] = {
        "round_trip_cost_pct_assumed": [c_lo, c_hi],
        "incremental_edge_T_minus_C_r10_pct": {"gross": d10["diff"], "gross_lo": d10["lo"], "gross_hi": d10["hi"],
                                               "net_low_cost": _r(d10["diff"] - c_lo), "net_high_cost": _r(d10["diff"] - c_hi),
                                               "net_low_cost_at_interval_hi": _r(d10["hi"] - c_lo)},
        "excess_over_set_mean_of_T_x10_pct": {"gross": xT["est"], "gross_lo": xT["lo"], "gross_hi": xT["hi"],
                                              "net_low_cost": _r(xT["est"] - c_lo), "net_high_cost": _r(xT["est"] - c_hi),
                                              "net_low_cost_at_interval_hi": _r(xT["hi"] - c_lo)}}
    R["P7"] = p7

    # ------------------------------------------------------------------ POST HOC (see module docstring)
    um = np.unique(D["month"])
    last36 = D["month"] >= um[-36] if len(um) >= 36 else np.ones(D["n"], bool)
    ph = {"label": "POST HOC, not pre-specified",
          "last_36_months_from": f"{int(um[-36] if len(um) >= 36 else um[0]) // 12}-"
                                 f"{int(um[-36] if len(um) >= 36 else um[0]) % 12 + 1:02d}",
          "last_36_months_fzd10_T_minus_C": cmp(D, "fzd10", T & last36, C & last36, f"{name}|PH|last36", "post_hoc"),
          "earlier_months_fzd10_T_minus_C": cmp(D, "fzd10", T & ~last36, C & ~last36, f"{name}|PH|early", "post_hoc")
          if (T & ~last36).any() else None,
          "entry_next_open": {
              "r10_pct_T_minus_C": cmp(D, None, T, C, f"{name}|PH|r10o", "post_hoc", values=100 * np.expm1(D["f10o"])),
              "x10_pct_T_minus_C": cmp(D, None, T, C, f"{name}|PH|x10o", "post_hoc", values=100 * D["fx10o"]),
              "mean_overnight_gap_after_T_pct": _r(100 * np.nanmean(D["f10"][T] - D["f10o"][T]), 3),
              "mean_overnight_gap_after_C_pct": _r(100 * np.nanmean(D["f10"][C] - D["f10o"][C]), 3)}}
    COUNT["post_hoc"] = COUNT.get("post_hoc", 0) + 1
    ph["primary_with_quarter_blocks"] = boot_diff_p(D["fzd10"][T], D["month"][T] // 3, D["fzd10"][C],
                                                    D["month"][C] // 3, rng_for(f"{name}|PH|quarter"))
    R["post_hoc"] = ph
    R["_pool"]["last36"] = last36[S]

    # ------------------------------------------------------------------ checks (second routes)
    chk = {}
    v, m = D["fzd10"], D["month"]
    ref = e05.boot_diff(v[T], m[T], v[C], m[C], rng_for(f"{name}|P1|T-C|fzd10"))
    mine = p1["T_minus_C"]["fzd10"]
    chk["primary_equals_e05_boot_diff"] = bool(ref["diff"] == mine["diff"] and ref["lo"] == mine["lo"]
                                               and ref["hi"] == mine["hi"] and ref["n"] == mine["n"])
    # pandas route with its own resampling code and generator
    fr = pd.DataFrame({"v": v[S], "m": m[S], "t": T[S]})
    g = fr.groupby(["m", "t"])["v"].agg(["sum", "count"]).unstack("t").fillna(0.0)
    sT_, nT_, sC_, nC_ = (g[("sum", True)].to_numpy(), g[("count", True)].to_numpy(),
                          g[("sum", False)].to_numpy(), g[("count", False)].to_numpy())
    direct = float(fr.loc[fr["t"], "v"].mean() - fr.loc[~fr["t"], "v"].mean())
    r2 = np.random.default_rng(SEED + 7)
    bt = []
    for _ in range(1000):
        i = r2.integers(0, len(g), len(g))
        if nT_[i].sum() > 0:
            bt.append(sT_[i].sum() / nT_[i].sum() - sC_[i].sum() / nC_[i].sum())
    chk["primary_pandas_route"] = {"diff": _r(direct), "lo": _r(np.percentile(bt, 2.5)), "hi": _r(np.percentile(bt, 97.5))}
    # month-clustered sandwich standard error of the difference (OLS on a dummy)
    y = v[S]
    X = np.c_[np.ones(len(y)), T[S].astype(float)]
    beta = np.linalg.solve(X.T @ X, X.T @ y)
    e = y - X @ beta
    mc, inv = np.unique(m[S], return_inverse=True)
    sc0, sc1 = np.bincount(inv, weights=e), np.bincount(inv, weights=e * X[:, 1])
    G = np.c_[sc0, sc1]
    bread = np.linalg.inv(X.T @ X)
    V = bread @ (G.T @ G) @ bread * (len(mc) / (len(mc) - 1))
    chk["primary_month_clustered_ols"] = {"diff": _r(beta[1]), "se": _r(math.sqrt(V[1, 1])),
                                          "lo": _r(beta[1] - 1.96 * math.sqrt(V[1, 1])),
                                          "hi": _r(beta[1] + 1.96 * math.sqrt(V[1, 1]))}
    chk["old_comparison_matches_panel_info"] = bool(
        abs(p1["old_comparison_T_minus_OC_fz10"]["diff"] - PUBLISHED_OLD_FZ10[name]) < 2e-4)
    chk["T_equals_absorb_bottom_and_published_count"] = True
    R["checks"] = chk
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=DEFAULT_PANEL)
    ap.add_argument("--sets", nargs="+", default=list(SETS), choices=SETS)
    ap.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parents[1] / "results"
                                         / "e11_absorption_strict_control.json"))
    a = ap.parse_args()
    e05.N_BOOT = N_BOOT
    t0 = time.time()
    out = {"experiment": "e11_absorption_strict_control", "seed": SEED, "n_boot": N_BOOT,
           "bootstrap": "month blocks, percentile intervals (95%)",
           "definitions": {
               "S": "eval & ext<=-1.5 & |z|<=0.5 & finite rvol", "T": "S & rvol>=2 (== absorb_bottom)",
               "C": "S & rvol<2", "C_normal": "S & 0.8<=rvol<=1.25",
               "OC": "eval & ext<=-1.5 & not climax_dn & not absorb_bottom (control of E05/E08)",
               "idio": "rvol / exp(mkt_lrvol); T_idio = S & idio>=2, C_idio = S & idio<2",
               "gap_up_then_sold": "gap>=+0.5*sigma & body<=-0.5*sigma & clv<=0.33",
               "primary_family": "T - C on fzd10 in A, B, DJ, LH, MS (Holm)",
               "units": "fz*, fzd*, fzx* in risk units (forward log return / (sig0*sqrt(h))); P7 in percent"},
           "sets": {}}
    for name in a.sets:
        D = load(a.panel, name)
        out["sets"][name] = analyse(D)
        print(f"[{name}] done, {time.time() - t0:.0f}s", flush=True)
        del D
    pools = {s: out["sets"][s].pop("_pool") for s in a.sets}
    conf = [s for s in ("B", "LH", "MS") if s in pools]      # DJ lies inside LH; A is the development set
    if len(conf) == 3:
        pm = np.concatenate([pools[s]["month"] for s in conf])
        pt = np.concatenate([pools[s]["T"] for s in conf])
        out["pooled_confirmation_B_LH_MS"] = {
            "note": "SECONDARY. Rows of S from B, LH and MS stacked (no stock-date appears twice); months "
                    "resampled jointly across the three sets. fzd10/x10 are demeaned by date inside each set.",
            "n_T": int(pt.sum()), "n_C": int((~pt).sum())}
        for k, lab in (("fzd10", "fzd10"), ("fz10", "fz10"), ("x10", "x10_pct"), ("r10", "r10_pct")):
            v = np.concatenate([pools[s][k] for s in conf])
            COUNT["pooled"] = COUNT.get("pooled", 0) + 1
            out["pooled_confirmation_B_LH_MS"][lab] = boot_diff_p(v[pt], pm[pt], v[~pt], pm[~pt],
                                                                  rng_for(f"pooled|{k}"))
    rec = [s for s in ("B", "MS") if s in pools]
    if len(rec) == 2:
        k36 = np.concatenate([pools[s]["last36"] for s in rec])
        pm = np.concatenate([pools[s]["month"] for s in rec])[k36]
        pt = np.concatenate([pools[s]["T"] for s in rec])[k36]
        v = np.concatenate([pools[s]["fzd10"] for s in rec])[k36]
        COUNT["post_hoc"] = COUNT.get("post_hoc", 0) + 1
        out["post_hoc_pooled_B_MS_last_36_months_fzd10"] = dict(
            boot_diff_p(v[pt], pm[pt], v[~pt], pm[~pt], rng_for("pooled|last36")),
            note="POST HOC. Non-development data closest to the end of the sample (about 2014-11 .. 2018-01).")
    del pools
    prim = {s: out["sets"][s]["P1"]["T_minus_C"]["fzd10"] for s in a.sets}
    out["primary_family"] = {
        "test": "T - C on fzd10", "sets": list(a.sets),
        "results": prim,
        "holm_adjusted_p_from_p_norm": holm({s: prim[s]["p_norm"] for s in a.sets}),
        "holm_adjusted_p_from_p_boot": holm({s: prim[s]["p_boot"] for s in a.sets}),
        "holm_without_development_set_A_from_p_norm": holm({s: prim[s]["p_norm"] for s in a.sets if s != "A"}),
        "note": "A and B share dates; DJ lies inside LH; Holm is valid under any dependence. A is the "
                "development set of the original indicator; MS was never used before."}
    out["comparisons_by_section"] = dict(sorted(COUNT.items()))
    out["comparisons_run"] = int(sum(COUNT.values()))
    out["seconds"] = round(time.time() - t0)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))

    # console summary
    f = lambda r: ("n/a" if r.get("diff") is None else
                   f"{r['diff']:+.3f} [{r['lo']:+.3f},{r['hi']:+.3f}] n={r.get('n', r.get('n_T_used'))}")
    for s in a.sets:
        r = out["sets"][s]
        print(f"\n=== {s}  T={r['counts']['T']}  C={r['counts']['C']}  S={r['counts']['S']}")
        print("  old  T-OC fz10 :", f(r["P1"]["old_comparison_T_minus_OC_fz10"]), " C-OC:", f(r["P1"]["C_minus_OC_fz10"]))
        for k in P1_METRICS:
            print(f"  P1 T-C  {k:6s}:", f(r["P1"]["T_minus_C"][k]), "| vs C_normal:", f(r["P1"]["T_minus_C_normal"][k]))
        print("  P4 same-date fzd10:", f(r["P4"]["fzd10"]), " r10%:", f(r["P4"]["r10_pct"]))
        print("  P6 idio fzd10:", f(r["P6"]["idio"]["T_idio_minus_C_idio"]["fzd10"]))
        print("  P7 r10% T-C:", f(r["P7"]["r10_pct"]["T_minus_C"]), " x10% T-C:",
              f(r["P7"]["x10_pct_vs_set_mean_same_date"]["T_minus_C"]))
        print("  checks:", r["checks"])
    if "pooled_confirmation_B_LH_MS" in out:
        pc = out["pooled_confirmation_B_LH_MS"]
        print("\npooled B+LH+MS:", {k: f(pc[k]) for k in ("fzd10", "fz10", "x10_pct", "r10_pct")})
    print("\nprimary Holm (p_norm):", out["primary_family"]["holm_adjusted_p_from_p_norm"])
    print("comparisons:", out["comparisons_run"], out["comparisons_by_section"])
    print("wrote", a.out)


if __name__ == "__main__":
    main()
