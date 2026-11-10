#!/usr/bin/env python3
"""E05 - Validation-lite on real single stocks. Plan and decision rules: docs/06_validation_lite.md
(pre-registered before this script was run on the stock data).

The data folders are public Kaggle sets and are NOT part of this repository (see the plan).
  python3 -I experiments/e05_validation_lite.py --sp5 DIR --dj DIR
  python3 -I experiments/e05_validation_lite.py --smoke        # pipeline check on bundled data
Run with -I: the data folders are third-party downloads.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import hashlib
import json
import time
from dataclasses import replace
from multiprocessing import Pool

import numpy as np
import pandas as pd

from tfs.data import load_bundled, load_ohlcv_dir
from tfs.flow import volume_flow_v2
from tfs.trend import (TrendParams, robust_var_lagged, simulate_trades, trend_setups,
                       weekly_context_dir)

EVAL_START = 400
HORIZONS = (5, 10, 20)
N_BOOT = 2000
N_RANDOM = 20
RAW = TrendParams(use_ctx=False, use_rs=False, use_mkt=False, use_pull_vol=False, warmup=EVAL_START)
METRICS = ("fz5", "fz10", "fz20", "fzx10")
_BENCH = None


def half(ticker: str) -> str:
    return "A" if int(hashlib.md5(ticker.encode()).hexdigest(), 16) % 2 == 0 else "B"


# --------------------------------------------------------------------------- features
def features(item):
    ticker, df = item
    b = _BENCH.reindex(df.index).ffill().bfill().to_numpy()
    ctx = weekly_context_dir(df)
    sw, _ = trend_setups(df, p=RAW, bench_close=b, htf_dir=ctx)
    bl, _ = trend_setups(df, p=replace(RAW, s1_mode="baseline"), bench_close=b, htf_dir=ctx)
    fl = volume_flow_v2(df)
    c = df["close"].to_numpy()
    lnc, lnb = np.log(c), np.log(b)
    sig0 = np.sqrt(robust_var_lagged(np.r_[np.nan, np.diff(lnc)], 100, 3.0))
    n = len(df)
    feat = {"ticker": ticker, "n": n, "dates": df.index.to_numpy(),
            "o": df["open"].to_numpy(), "h": df["high"].to_numpy(), "l": df["low"].to_numpy(), "c": c,
            "atr": sw["atr"].to_numpy(), "d": sw["dir"].to_numpy(), "last_sl": sw["last_sl"].to_numpy(),
            "ctx": ctx, "rs": sw["rs_dir"].to_numpy(), "mkt": sw["mkt_dir"].to_numpy(),
            "raw1_swing": sw["raw_s1"].to_numpy(), "stop1_swing": sw["stop1"].to_numpy(),
            "pbv_swing": sw["pb_rvol"].to_numpy(),
            "raw1_baseline": bl["raw_s1"].to_numpy(), "stop1_baseline": bl["stop1"].to_numpy(),
            "pbv_baseline": bl["pb_rvol"].to_numpy(),
            "raw2": sw["raw_s2"].to_numpy(), "stop2": sw["stop2"].to_numpy(),
            "raw3": sw["raw_s3"].to_numpy(), "stop3": sw["stop3"].to_numpy()}
    pan = {"month": (df.index.year * 12 + df.index.month - 1).to_numpy(),
           "ts": sw["ts"].to_numpy(), "dir": feat["d"], "ctx": ctx, "rs": feat["rs"], "mkt": feat["mkt"],
           "ext": sw["ext"].to_numpy(), "rvol": sw["rvol"].to_numpy(),
           "raw1_swing": feat["raw1_swing"], "raw1_baseline": feat["raw1_baseline"],
           "pbv_swing": feat["pbv_swing"], "pbv_baseline": feat["pbv_baseline"],
           "raw2": feat["raw2"], "raw3": feat["raw3"], "asym_z": fl["asym_z"].to_numpy()}
    for k in ("accumulation", "distribution", "climax_up", "climax_dn", "absorb_top", "absorb_bottom",
              "bear_div", "bull_div", "dryup"):
        pan[k] = fl[k].to_numpy()
    for hz in HORIZONS:
        fwd = np.full(n, np.nan)
        fwd[:-hz] = lnc[hz:] - lnc[:-hz]
        pan[f"fz{hz}"] = fwd / (sig0 * np.sqrt(hz))
        if hz == 10:
            fb = np.full(n, np.nan)
            fb[:-hz] = lnb[hz:] - lnb[:-hz]
            pan["fzx10"] = (fwd - fb) / (sig0 * np.sqrt(hz))
    pan = pd.DataFrame(pan)
    pan["ticker"] = ticker
    keep = (np.arange(n) >= EVAL_START) & pan["fz20"].notna().to_numpy() & np.isfinite(pan["fz10"].to_numpy())
    return feat, pan[keep]


# --------------------------------------------------------------------------- statistics
def _agg(vals, months, mcodes):
    idx = np.searchsorted(mcodes, months)
    return (np.bincount(idx, weights=vals, minlength=len(mcodes)),
            np.bincount(idx, minlength=len(mcodes)).astype(float))


def boot_diff(v_s, m_s, v_c, m_c, rng):
    """Difference of means (signal - control); months resampled jointly."""
    ks, kc = np.isfinite(v_s), np.isfinite(v_c)
    v_s, m_s, v_c, m_c = v_s[ks], m_s[ks], v_c[kc], m_c[kc]
    if len(v_s) == 0 or len(v_c) == 0:
        return {"diff": None, "lo": None, "hi": None, "n": int(len(v_s))}
    mc = np.unique(np.concatenate([m_s, m_c]))
    ss, ns = _agg(v_s, m_s, mc)
    sc, nc = _agg(v_c, m_c, mc)
    est = ss.sum() / ns.sum() - sc.sum() / nc.sum()
    idx = rng.integers(0, len(mc), (N_BOOT, len(mc)))
    with np.errstate(divide="ignore", invalid="ignore"):
        bt = ss[idx].sum(1) / ns[idx].sum(1) - sc[idx].sum(1) / nc[idx].sum(1)
    bt = bt[np.isfinite(bt)]
    lo, hi = np.percentile(bt, [2.5, 97.5])
    return {"diff": round(float(est), 4), "lo": round(float(lo), 4), "hi": round(float(hi), 4),
            "n": int(len(v_s))}


def boot_mean(v, m, rng, denom=None):
    """Mean of v (or sum(v)/denom when denom is given); months resampled."""
    k = np.isfinite(v)
    v, m = v[k], m[k]
    if len(v) == 0:
        return {"est": None, "lo": None, "hi": None, "n": 0}
    mc = np.unique(m)
    s, c = _agg(v, m, mc)
    idx = rng.integers(0, len(mc), (N_BOOT, len(mc)))
    if denom is None:
        est = s.sum() / c.sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            bt = s[idx].sum(1) / c[idx].sum(1)
    else:
        est = s.sum() / denom
        bt = s[idx].sum(1) / denom
    bt = bt[np.isfinite(bt)]
    lo, hi = np.percentile(bt, [2.5, 97.5])
    return {"est": round(float(est), 4), "lo": round(float(lo), 4), "hi": round(float(hi), 4), "n": int(len(v))}


def verdict(r, predicted):
    if r["diff"] is None:
        return "no data"
    sig = r["lo"] > 0 or r["hi"] < 0
    right = (r["diff"] > 0) == (predicted > 0)
    return ("significant, predicted sign" if sig and right else "significant, WRONG sign" if sig
            else "not significant, predicted sign" if right else "not significant, wrong sign")


def event_test(pan, s_mask, c_mask, rng, predicted=1):
    m = pan["month"].to_numpy()
    out = {"n_signal": int(s_mask.sum()), "n_control": int(c_mask.sum())}
    for k in METRICS:
        v = pan[k].to_numpy()
        out[k] = boot_diff(v[s_mask], m[s_mask], v[c_mask], m[c_mask], rng)
    out["mean_signal_fz10"] = round(float(np.nanmean(pan["fz10"].to_numpy()[s_mask])), 4) if s_mask.any() else None
    out["mean_control_fz10"] = round(float(np.nanmean(pan["fz10"].to_numpy()[c_mask])), 4) if c_mask.any() else None
    out["verdict_fz10"] = verdict(out["fz10"], predicted)
    return out


def ols_boot(pan, rng):
    """fz10 ~ 1 + trend score + asymmetry z; coefficient CIs by month bootstrap of the normal equations."""
    d = pan[["fz10", "ts", "asym_z", "month"]].dropna()
    X = np.c_[np.ones(len(d)), d["ts"].to_numpy(), d["asym_z"].to_numpy()]
    y = d["fz10"].to_numpy()
    mc, inv = np.unique(d["month"].to_numpy(), return_inverse=True)
    xtx = np.zeros((len(mc), 3, 3))
    xty = np.zeros((len(mc), 3))
    np.add.at(xtx, inv, X[:, :, None] * X[:, None, :])
    np.add.at(xty, inv, X * y[:, None])
    beta = np.linalg.solve(xtx.sum(0), xty.sum(0))
    bs = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(mc), len(mc))
        try:
            bs.append(np.linalg.solve(xtx[i].sum(0), xty[i].sum(0)))
        except np.linalg.LinAlgError:
            pass
    bs = np.array(bs)
    out = {"n": int(len(d))}
    for j, name in enumerate(("intercept", "trend_score", "asym_z")):
        lo, hi = np.percentile(bs[:, j], [2.5, 97.5])
        out[name] = {"coef": round(float(beta[j]), 4), "lo": round(float(lo), 4), "hi": round(float(hi), 4)}
    return out


# --------------------------------------------------------------------------- trades
def compose(feat, p: TrendParams, s1: str):
    """Signal and stop arrays for one stock under parameter set p (same rules as trend_setups)."""
    n, c, atr = feat["n"], feat["c"], feat["atr"]
    f_all = np.ones(n, dtype=bool)
    if p.use_ctx:
        f_all &= feat["ctx"] >= 0
    if p.use_rs:
        f_all &= feat["rs"] >= 0
    if p.use_mkt:
        f_all &= feat["mkt"] >= 0
    pbv = feat[f"pbv_{s1}"]
    f_vol = np.ones(n, dtype=bool) if not p.use_pull_vol else (np.isnan(pbv) | (pbv <= p.pull_vol_max))
    m1 = feat[f"raw1_{s1}"] & f_all & f_vol if p.use_s1 else np.zeros(n, dtype=bool)
    m2 = (~m1) & feat["raw2"] & f_all if p.use_s2 else np.zeros(n, dtype=bool)
    m3 = (~m1) & (~m2) & feat["raw3"] if p.use_s3 else np.zeros(n, dtype=bool)
    sig = np.zeros(n, dtype=int)
    st = np.full(n, np.nan)
    sig[m1], st[m1] = 1, feat[f"stop1_{s1}"][m1]
    sig[m2], st[m2] = 2, feat["stop2"][m2]
    sig[m3], st[m3] = 3, feat["stop3"][m3]
    st = np.minimum(st, c - p.min_stop_atr * atr)
    bad = np.isnan(st) | (c - st <= 0)
    sig[bad], st[bad] = 0, np.nan
    sig[:p.warmup], st[:p.warmup] = 0, np.nan
    return sig, st


def run_config(store, p: TrendParams, s1="swing", sig_override=None):
    rows, exposure, stock_years = [], 0.0, 0.0
    for feat in store:
        sig, st = sig_override[feat["ticker"]] if sig_override is not None else compose(feat, p, s1)
        cols, trades = simulate_trades(feat["o"], feat["h"], feat["l"], feat["c"], feat["atr"], feat["d"],
                                       feat["last_sl"], sig, st, p)
        exposure += cols["in_trade"][EVAL_START:].sum()
        stock_years += (feat["n"] - EVAL_START) / 252.0
        for tr in trades:
            ts_ = pd.Timestamp(feat["dates"][tr["entry_bar"]])
            rows.append((feat["ticker"], ts_.year * 12 + ts_.month - 1, tr["setup"], tr["r"], tr["bars"],
                         tr["reason"], (tr["entry"] - tr["stop"]) / feat["atr"][tr["entry_bar"]], tr["entry_bar"]))
    t = pd.DataFrame(rows, columns=["ticker", "month", "setup", "r", "bars", "reason", "stop_atr", "entry_bar"])
    return t, exposure / max(stock_years * 252.0, 1.0), stock_years


def trade_summary(t, exposure, stock_years, rng):
    if len(t) == 0:
        return {"trades": 0}
    r, m = t["r"].to_numpy(), t["month"].to_numpy()
    return {"trades": int(len(t)), "per_stock_year": round(len(t) / stock_years, 2),
            "win_pct": round(100 * float((r > 0).mean()), 1),
            "avg_r": boot_mean(r, m, rng), "median_r": round(float(np.median(r)), 3),
            "r_per_stock_year": boot_mean(r, m, rng, denom=stock_years),
            "avg_bars": round(float(t["bars"].mean()), 1),
            "worst_r": round(float(r.min()), 2), "pct_worse_than_minus_1_5r": round(100 * float((r < -1.5).mean()), 2),
            "avg_stop_atr": round(float(t["stop_atr"].mean()), 2),
            "exposure_pct": round(100 * exposure, 1),
            "exit_reasons": {k: int(v) for k, v in t["reason"].map({1: "stop", 2: "trail", 3: "regime"}).value_counts().items()}}


def random_entry_baseline(store, p, actual, rng):
    """Q7: random entries on up-regime bars, same count per stock, stop distances drawn from the
    actual S1 trades, same exits."""
    dist = actual["stop_atr"].to_numpy()
    counts = actual.groupby("ticker").size().to_dict()
    avg = []
    for _ in range(N_RANDOM):
        over = {}
        for feat in store:
            n = feat["n"]
            sig, st = np.zeros(n, dtype=int), np.full(n, np.nan)
            k = counts.get(feat["ticker"], 0)
            ok = np.flatnonzero((feat["d"] == 1) & (np.arange(n) >= EVAL_START) & (np.arange(n) < n - 1)
                                & np.isfinite(feat["atr"]))
            if k and len(ok):
                pick = rng.choice(ok, size=min(k, len(ok)), replace=False)
                sig[pick] = 1
                st[pick] = feat["c"][pick] - rng.choice(dist, size=len(pick)) * feat["atr"][pick]
            over[feat["ticker"]] = (sig, st)
        t, _, _ = run_config(store, p, sig_override=over)
        avg.append(float(t["r"].mean()) if len(t) else np.nan)
    avg = np.array(avg)
    a = float(actual["r"].mean())
    return {"actual_avg_r": round(a, 4), "random_avg_r_mean": round(float(np.nanmean(avg)), 4),
            "random_avg_r_sd": round(float(np.nanstd(avg)), 4),
            "p_value": round((1 + int((avg >= a).sum())) / (1 + N_RANDOM), 3)}


# --------------------------------------------------------------------------- analysis
def analyse(pan, store, rng):
    R = {}
    b = lambda col: pan[col].to_numpy().astype(bool)
    dr, ctx, rs, mkt = (pan[k].to_numpy() for k in ("dir", "ctx", "rs", "mkt"))
    ext, az = pan["ext"].to_numpy(), pan["asym_z"].to_numpy()
    every = np.ones(len(pan), dtype=bool)

    R["Q1_regime"] = {
        "chart_up_vs_rest": event_test(pan, dr == 1, dr != 1, rng),
        "chart_down_vs_rest": event_test(pan, dr == -1, dr != -1, rng, -1),
        "context_up_vs_rest": event_test(pan, ctx == 1, ctx != 1, rng),
        "context_down_vs_rest": event_test(pan, ctx == -1, ctx != -1, rng, -1),
        "market_up_vs_rest": event_test(pan, mkt == 1, mkt != 1, rng),
        "market_down_vs_rest": event_test(pan, mkt == -1, mkt != -1, rng, -1),
        "strength_up_vs_rest": event_test(pan, rs == 1, rs != 1, rng),
        "strength_down_vs_rest": event_test(pan, rs == -1, rs != -1, rng, -1)}

    s_sw, s_bl = b("raw1_swing"), b("raw1_baseline")
    R["Q2_s1_rule"] = {
        "v2_swing_vs_up_regime": event_test(pan, s_sw, (dr == 1) & ~s_sw, rng),
        "v1_baseline_vs_up_regime": event_test(pan, s_bl, (dr == 1) & ~s_bl, rng),
        "v1_minus_v2": event_test(pan, s_bl & ~s_sw, s_sw & ~s_bl, rng)}

    R["Q3_s1_filters"] = {}
    for mode, s, pbv in (("v2_swing", s_sw, pan["pbv_swing"].to_numpy()), ("v1_baseline", s_bl, pan["pbv_baseline"].to_numpy())):
        R["Q3_s1_filters"][mode] = {
            "context_not_down": event_test(pan, s & (ctx >= 0), s & (ctx < 0), rng),
            "context_up": event_test(pan, s & (ctx == 1), s & (ctx < 1), rng),
            "market_not_down": event_test(pan, s & (mkt >= 0), s & (mkt < 0), rng),
            "market_up": event_test(pan, s & (mkt == 1), s & (mkt < 1), rng),
            "strength_not_down": event_test(pan, s & (rs >= 0), s & (rs < 0), rng),
            "strength_up": event_test(pan, s & (rs == 1), s & (rs < 1), rng),
            "light_pullback_volume": event_test(pan, s & (pbv <= 1.0), s & (pbv > 1.0), rng)}

    s2, s3 = b("raw2"), b("raw3")
    R["Q4_s2_s3"] = {"s2_breakout_vs_not_down": event_test(pan, s2, (dr >= 0) & ~s2, rng),
                     "s3_reversal_vs_not_up": event_test(pan, s3, (dr <= 0) & ~s3, rng)}

    cu, cd, at, ab = b("climax_up"), b("climax_dn"), b("absorb_top"), b("absorb_bottom")
    hi_ctl, lo_ctl = (ext >= 1.5) & ~cu & ~at, (ext <= -1.5) & ~cd & ~ab
    R["Q5_volume"] = {
        "accumulation_event": event_test(pan, b("accumulation"), every, rng),
        "distribution_event": event_test(pan, b("distribution"), every, rng, -1),
        "accumulation_state_z>=2": event_test(pan, az >= 2, ~(az >= 2), rng),
        "distribution_state_z<=-2": event_test(pan, az <= -2, ~(az <= -2), rng, -1),
        "up_regime_z>=1_vs_z<=-1": event_test(pan, (dr == 1) & (az >= 1), (dr == 1) & (az <= -1), rng),
        "buying_climax_vs_extended_up": event_test(pan, cu, hi_ctl, rng, -1),
        "absorption_top_vs_extended_up": event_test(pan, at, hi_ctl, rng, -1),
        "selling_climax_vs_extended_down": event_test(pan, cd, lo_ctl, rng),
        "absorption_bottom_vs_extended_down": event_test(pan, ab, lo_ctl, rng),
        "bearish_divergence": event_test(pan, b("bear_div"), every, rng, -1),
        "bullish_divergence": event_test(pan, b("bull_div"), every, rng),
        "dryup_in_up_regime": event_test(pan, (dr == 1) & b("dryup"), (dr == 1) & ~b("dryup"), rng),
        "regression_fz10_on_trend_and_asym": ols_boot(pan, rng)}

    cfg = {"base_all_setups": (RAW, "swing"),
           "s1_only_v2_swing": (replace(RAW, use_s2=False, use_s3=False), "swing"),
           "s1_only_v1_baseline": (replace(RAW, use_s2=False, use_s3=False), "baseline"),
           "s2_only": (replace(RAW, use_s1=False, use_s3=False), "swing"),
           "s3_only": (replace(RAW, use_s1=False, use_s2=False), "swing"),
           "stop_on_close": (replace(RAW, stop_mode="close"), "swing"),
           "exit_structure": (replace(RAW, exit_mode="structure"), "swing"),
           "no_min_stop": (replace(RAW, min_stop_atr=0.0), "swing"),
           "filter_context": (replace(RAW, use_ctx=True), "swing"),
           "filter_market": (replace(RAW, use_mkt=True), "swing"),
           "filter_strength": (replace(RAW, use_rs=True), "swing"),
           "filter_pullback_volume": (replace(RAW, use_pull_vol=True), "swing"),
           "filters_context_market_strength": (replace(RAW, use_ctx=True, use_mkt=True, use_rs=True), "swing")}
    runs = {k: run_config(store, p, s1) for k, (p, s1) in cfg.items()}
    R["Q6_trades"] = {k: trade_summary(t, e, sy, rng) for k, (t, e, sy) in runs.items()}
    base_t, _, base_sy = runs["base_all_setups"]
    cmp = {}
    for k in ("stop_on_close", "exit_structure", "no_min_stop", "filter_context", "filter_market",
              "filter_strength", "filter_pullback_volume", "filters_context_market_strength"):
        t, _, sy = runs[k]
        if len(t) and len(base_t):
            cmp[f"{k}_minus_base"] = {
                "avg_r": boot_diff(t["r"].to_numpy(), t["month"].to_numpy(), base_t["r"].to_numpy(), base_t["month"].to_numpy(), rng),
                "r_per_stock_year": round(float(t["r"].sum() / sy - base_t["r"].sum() / base_sy), 4)}
    R["Q6_comparisons"] = cmp
    s1_t = runs["s1_only_v2_swing"][0]
    R["Q7_random_entries"] = random_entry_baseline(store, cfg["s1_only_v2_swing"][0], s1_t, rng) if len(s1_t) else {}
    return R


def self_check(store, stocks, bench):
    """compose() must reproduce trend_setups() exactly."""
    p = replace(RAW, use_ctx=True, use_mkt=True, use_rs=True, use_pull_vol=True)
    for feat in store[:3]:
        df = stocks[feat["ticker"]]
        b = bench.reindex(df.index).ffill().bfill().to_numpy()
        f, _ = trend_setups(df, p=p, bench_close=b, htf_dir=weekly_context_dir(df))
        sig, st = compose(feat, p, "swing")
        assert (sig == f["sig"].to_numpy()).all() and np.allclose(st, f["sig_stop"].to_numpy(), equal_nan=True), feat["ticker"]


def main():
    global _BENCH, N_BOOT, N_RANDOM
    ap = argparse.ArgumentParser()
    ap.add_argument("--sp5")
    ap.add_argument("--dj")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default=str(pathlib.Path(__file__).resolve().parents[1] / "results" / "e05_validation_lite.json"))
    ap.add_argument("--seed", type=int, default=20261110)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    _BENCH = load_bundled("SPX")["close"]
    t0 = time.time()
    if a.smoke:
        N_BOOT, N_RANDOM = 200, 3
        g = load_bundled("GOOG")
        sets, audits = {"SMOKE": {"GOOG": g, "GOOG2": g.iloc[200:]}}, {}
    else:
        sp5, au1 = load_ohlcv_dir(a.sp5, "*_data.csv", min_bars=700)
        dj, au2 = load_ohlcv_dir(a.dj, "*_2006-01-01_to_2018-01-01.csv", min_bars=700, end="2013-02-07")
        sets = {"A": {k: v for k, v in sp5.items() if half(k) == "A"},
                "B": {k: v for k, v in sp5.items() if half(k) == "B"}, "DJ": dj}
        audits = {"SP5": au1, "DJ": au2}
    out = {"plan": "docs/06_validation_lite.md", "seed": a.seed, "eval_start_bar": EVAL_START,
           "n_boot": N_BOOT, "data_audit": audits, "sets": {}}
    for name, stocks in sets.items():
        with Pool(4) as pool:
            res = pool.map(features, sorted(stocks.items()), chunksize=4)
        store = [r[0] for r in res]
        pan = pd.concat([r[1] for r in res], ignore_index=True)
        self_check(store, stocks, _BENCH)
        out["sets"][name] = {"stocks": len(store), "panel_rows": int(len(pan)),
                             "months": int(pan["month"].nunique()),
                             "first_eval_date": str(min(pd.Timestamp(f["dates"][EVAL_START]) for f in store).date()),
                             "last_date": str(max(pd.Timestamp(f["dates"][-1]) for f in store).date()),
                             "mean_fz10_all_bars": round(float(pan["fz10"].mean()), 4),
                             "results": analyse(pan, store, rng)}
        print(f"[{name}] {len(store)} stocks, {len(pan)} rows, {time.time() - t0:.0f}s", flush=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
