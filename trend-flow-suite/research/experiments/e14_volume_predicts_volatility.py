#!/usr/bin/env python3
"""E14 - Does relative volume predict future volatility and stop-outs beyond what price already says?
(review of the Relative Volume pane)

Reviewer claim under test
  The best-documented information in volume is about future volatility and liquidity, not direction.
  Proposed monitor: dollar volume, Amihud illiquidity z-score, stock-specific relative volume, used to
  size positions and widen stops. Proposed validation: HAR regression of future realised volatility
  plus log volume measures; success = significant coefficients and better out-of-sample R2 / QLIKE.

Design (everything below was fixed on set A before any other set was scored)
  V1 targets   y_h = ln(rv_fwd_h) - ln(sig0), h = 5, 10, 20; Parkinson twin ln(pk_fwd10) - ln(sig0).
  V2 baseline  B0 = const, ln RV over 1 / 5 / 22 bars from r and from Parkinson (each minus ln sig0;
               the 1-bar terms floored at 0.1 sigma), and az = |r|/sig0 of today (capped at 8).
               B1 ("rich", robustness) = B0 + leverage min(r,0)/sig0 + |gap|/sig0 + two hinge terms of
               az (knots 1 and 2) + ln(ATR/close/sig0) + the cross-sectional median of ln RV1, ln RV5,
               ln RV22 and az on the date (the PRICE twin of the market part of volume).
  V3 candidates, one at a time on B0 and then jointly:
               lrvol (today) | lrvol5 (mean of the last 5 bars) | spec = lrvol - mkt_lrvol |
               mkt = mkt_lrvol | amz250 and amz100 = ln(20-bar mean of |r|/dvol) standardised with the
               mean and sd of the previous 250 / 100 bars of the same stock | inter = lrvol * sign(r).
               Shape check: lrvol split at 0 into its positive and negative part.
               Decomposition of the Amihud score (added on set A, where it was the strongest single
               candidate): pz250 = the same z-score of ln(20-bar mean |r|) (price only) and
               dz250 = the same z-score of ln(20-bar mean dollar volume) (volume only).
  V4 out of sample: (i) inside each set, fit on the first 60% of months (training rows whose forward
               window reaches the test period are purged), score on the last 40%;
               (ii) fit A -> score B; fit LH -> score MS; fit MS -> score LH; fit LH -> score the part
               of MS after LH ends (out of stock AND out of time).
               R2_oos = 1 - SSE / SST with SST around the TRAINING mean of y. Gain = R2(aug) - R2(base).
               Intervals: month-block bootstrap (2000) of the per-month sums of the test set.
               QLIKE (h = 10): variance forecast = sig0^2 * exp(2*yhat) * smearing factor of the
               training residuals; loss = RV^2/F - ln(RV^2/F) - 1.
               Coefficients: full-set OLS, month-block bootstrap of the per-month X'X and X'y.
  V5 table     median rv_fwd10/sig0 (and against the ATR-implied volatility) by rvol bucket inside each
               bucket of today's |r|/sig0; differences against the 0.8-1.25 bucket with intervals.
  V6 stops     P(lowest low of bars t+1..t+10 <= close - k*ATR), k = 2 and 3, same buckets; the mirror
               (highest high >= close + k*ATR); and a linear probability model with the B0 terms,
               ln(ATR/close/sig0) and lrvol.
  V7 sizing    out-of-sample mean absolute error of ln volatility: sig0 alone, ATR alone (constant
               ratio), ATR regression, B0, B0 + best single volume measure, B0 + all volume measures.
               Direct test of the proposed sizing rule: on bars flagged by rvol >= 2, rvol >= 3,
               stock-specific rvol >= 2 (rvol / market median) or Amihud z >= 1.28 (90th percentile of a
               normal score), is the next-10-bar volatility higher than ATR implies, against all
               unflagged bars? Same for the 2-ATR and 3-ATR stop.

Choices made on set A and then frozen: the floor and caps, the Amihud decomposition, "best single" =
Amihud z-score (250 bars), "best augmented" = B0 + all candidates jointly.

What set A showed (written down before any other set was scored; the other sets test exactly this)
  C1 today's lrvol raises the next-5-bar volatility beyond price (2x day: +5.8%, interval 4.5..7.4),
     fades by 10 bars (+1.3%, interval -0.4..+3.1) and is gone at 20 bars.
  C2 at 10 bars the Amihud z-score is the strongest single candidate (out-of-sample R2 gain +0.011,
     coefficient +0.035 per unit), and what it carries is its VOLUME denominator: the dollar-volume twin
     dz250 has a NEGATIVE coefficient (-0.043: more dollar volume than usual over the last 20 bars means
     LOWER volatility ahead than price says), the price twin pz250 has none.
  C3 the market part of volume is absorbed by the market part of price (mkt coefficient 0.15 on B0,
     0.04 with interval -0.07..+0.20 on B1).
  C4 against ATR, volatility after high-volume days is NOT higher (rvol >= 2: -2.9%; rvol >= 3: -8.8%)
     and 2-ATR / 3-ATR stops are not hit more often.
  C5 the volume terms cut the out-of-sample absolute error of ln volatility by about 1% or less.

No look-ahead: every feature of bar t uses bars <= t of the stock (and same-day bars of the other
stocks for the cross-sectional medians). Forward windows start at t+1.

  python3 -I experiments/e14_volume_predicts_volatility.py [--panel DIR] [--sets A B DJ LH MS] [--out FILE]
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import argparse
import json
import time

import numpy as np
import pandas as pd

import experiments.e05_validation_lite as e05

DEFAULT_PANEL = "/tmp/claude-0/-home-user-AquaCentinela/b2916ecb-3cd8-557a-8730-1dacd8557876/scratchpad/panel"
SEED = 20261123
N_BOOT = 2000
SET_ORDER = ("A", "B", "DJ", "LH", "MS")
SEED_OFFSET = {"A": 1, "B": 2, "DJ": 3, "LH": 4, "MS": 5}
COLS = ["ticker", "date", "t", "month", "high", "low", "close", "dvol", "r", "sig0", "rvol", "lrvol",
        "mkt_lrvol", "atr", "pk", "gap", "rv_fwd5", "rv_fwd10", "rv_fwd20", "pk_fwd10", "eval"]
HORIZONS = (5, 10, 20)
FLOOR = 0.1                    # floor of the 1-bar volatility terms, in sig0 units
AZ_CAP = 8.0                   # cap of |r|/sig0 and |gap|/sig0 in the linear terms
LOG_CLIP = 3.0                 # log-ratio features are clipped to +-3 (a ratio of 20), z-scores to +-5
Z_CLIP = 5.0
AMI_SMOOTH = 20
RVOL_EDGES = (0.6, 0.8, 1.25, 2.0, 3.0)
RVOL_LABELS = ("<0.6", "0.6-0.8", "0.8-1.25", "1.25-2", "2-3", ">=3")
REF_BUCKET = 2                 # 0.8-1.25
AZ_EDGES = (0.5, 1.0, 2.0)
AZ_LABELS = ("<0.5", "0.5-1", "1-2", ">=2")
STOP_BARS = 10
STOP_K = (2.0, 3.0)

BASE = ["const", "lr1", "lr5", "lr22", "lp1", "lp5", "lp22", "az"]
RICH = BASE + ["neg", "agap", "az_k1", "az_k2", "latr", "m_lr1", "m_lr5", "m_lr22", "m_az"]
CANDS = {"lrvol": ["lrvol"], "lrvol5": ["lrvol5"], "spec": ["spec"], "mkt": ["mkt"],
         "amz250": ["amz250"], "amz100": ["amz100"], "inter": ["inter"]}
JOINT = ["spec", "mkt", "lrvol5", "amz250", "inter"]
ALL_FEATS = RICH + ["lrvol", "lrvol5", "spec", "mkt", "amz250", "amz100", "inter", "lrv_pos", "lrv_neg",
                    "pz250", "dz250"]
FI = {k: i for i, k in enumerate(ALL_FEATS)}

# model name -> feature list. "best single" and "best augmented" were chosen on set A (see CHOSEN).
MODELS = {"sig0": ["const"], "atr_reg": ["const", "latr"], "B0": BASE, "B1": RICH,
          "B0+spec+mkt": BASE + ["spec", "mkt"], "B0+joint": BASE + JOINT,
          "B0+lrv_pos+lrv_neg": BASE + ["lrv_pos", "lrv_neg"],
          "B1+lrvol": RICH + ["lrvol"], "B1+lrvol5": RICH + ["lrvol5"], "B1+spec+mkt": RICH + ["spec", "mkt"],
          "B1+joint": RICH + JOINT,
          "B0+pz250": BASE + ["pz250"], "B0+dz250": BASE + ["dz250"],
          "B0+pz250+amz250": BASE + ["pz250", "amz250"], "B0+pz250+dz250": BASE + ["pz250", "dz250"],
          "B1+amz250": RICH + ["amz250"], "B1+dz250": RICH + ["dz250"]}
for _k, _v in CANDS.items():
    MODELS[f"B0+{_k}"] = BASE + _v
PAIRS = ([(f"B0+{k}", "B0") for k in CANDS]
         + [("B0+spec+mkt", "B0"), ("B0+joint", "B0"), ("B0+lrv_pos+lrv_neg", "B0+lrvol"),
            ("B1", "B0"), ("B1+lrvol", "B1"), ("B1+lrvol5", "B1"), ("B1+spec+mkt", "B1"), ("B1+joint", "B1"),
            ("B0+pz250", "B0"), ("B0+dz250", "B0"), ("B0+pz250+amz250", "B0+pz250"),
            ("B0+pz250+dz250", "B0+pz250"), ("B1+amz250", "B1"), ("B1+dz250", "B1")])
CHOSEN = {"best_single": "B0+amz250", "best_augmented": "B0+joint"}     # fixed on set A
COEF_MODELS = ["B0+lrvol", "B0+lrvol5", "B0+spec", "B0+mkt", "B0+amz250", "B0+amz100", "B0+inter",
               "B0+spec+mkt", "B0+joint", "B0+lrv_pos+lrv_neg", "B1+lrvol", "B1+lrvol5", "B1+spec+mkt",
               "B1+joint", "B0+pz250", "B0+dz250", "B0+pz250+amz250", "B0+pz250+dz250", "B1+amz250", "B1+dz250"]
VOL_TERMS = {"lrvol", "lrvol5", "spec", "mkt", "amz250", "amz100", "inter", "lrv_pos", "lrv_neg", "pz250", "dz250"}

N_COMPARISONS = 0


def _count(k=1):
    global N_COMPARISONS
    N_COMPARISONS += k


def rnd(x, k=4):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, k)


# --------------------------------------------------------------------------- features
def _roll(s: pd.Series, code: pd.Series, w: int, how="mean", minp=None) -> np.ndarray:
    """rolling statistic over bars t-w+1 .. t inside each ticker (rows sorted by ticker, date)."""
    g = s.groupby(code, sort=False).rolling(w, min_periods=w if minp is None else minp)
    out = g.mean() if how == "mean" else g.std()
    return out.reset_index(level=0, drop=True).reindex(s.index).to_numpy()


def _fwd_extreme(x: np.ndarray, code: np.ndarray, k: int, lowest: bool) -> np.ndarray:
    """lowest (or highest) x over bars t+1 .. t+k of the same ticker; NaN when the window is incomplete."""
    n = len(x)
    out = np.full(n, np.inf if lowest else -np.inf)
    for j in range(1, k + 1):
        sh = np.full(n, np.nan)
        sh[:-j] = x[j:]
        same = np.zeros(n, dtype=bool)
        same[:-j] = code[j:] == code[:-j]
        sh[~same] = np.nan
        out = np.minimum(out, sh) if lowest else np.maximum(out, sh)      # NaN propagates
    return out


def _shift_fwd(x: np.ndarray, code: np.ndarray, k: int, fill):
    n = len(x)
    out = np.full(n, fill, dtype=x.dtype)
    out[:-k] = x[k:]
    same = np.zeros(n, dtype=bool)
    same[:-k] = code[k:] == code[:-k]
    out[~same] = fill
    return out


def load_set(panel_dir: str, name: str) -> dict:
    d = pd.read_parquet(pathlib.Path(panel_dir) / f"panel_{name}.parquet", columns=COLS)
    assert d["ticker"].is_monotonic_increasing
    d = d.reset_index(drop=True)
    code = pd.Series(pd.factorize(d["ticker"])[0], index=d.index)
    cnp = code.to_numpy()
    t = d["t"].to_numpy()
    assert bool(np.all((np.diff(t) == 1) | (np.diff(cnp) == 1)))          # contiguous bars per ticker
    r = d["r"].to_numpy(dtype=float)
    sig0 = d["sig0"].to_numpy(dtype=float)
    sig0 = np.where(sig0 > 0, sig0, np.nan)
    pk = d["pk"].to_numpy(dtype=float)
    close = d["close"].to_numpy(dtype=float)
    atr = d["atr"].to_numpy(dtype=float)
    lrvol_raw = d["lrvol"].to_numpy(dtype=float)
    lrvol = np.clip(lrvol_raw, -LOG_CLIP, LOG_CLIP)
    mkt = d["mkt_lrvol"].to_numpy(dtype=float)
    rv10 = d["rv_fwd10"].to_numpy(dtype=float)

    def lclip(x):
        return np.clip(x, -LOG_CLIP, LOG_CLIP)
    dvol = d["dvol"].to_numpy(dtype=float)
    f = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        lsig = np.log(sig0)
        az_raw = np.abs(r) / sig0
        r2 = pd.Series(r * r, index=d.index)
        pks = pd.Series(pk, index=d.index)
        f["const"] = np.ones(len(d))
        f["lr1"] = np.log(np.maximum(az_raw, FLOOR))
        f["lr5"] = lclip(0.5 * np.log(_roll(r2, code, 5)) - lsig)
        f["lr22"] = lclip(0.5 * np.log(_roll(r2, code, 22)) - lsig)
        f["lp1"] = np.log(np.maximum(np.sqrt(pk) / sig0, FLOOR))
        f["lp5"] = lclip(0.5 * np.log(_roll(pks, code, 5)) - lsig)
        f["lp22"] = lclip(0.5 * np.log(_roll(pks, code, 22)) - lsig)
        f["az"] = np.minimum(az_raw, AZ_CAP)
        f["neg"] = np.maximum(np.minimum(r, 0.0) / sig0, -AZ_CAP)
        f["agap"] = np.minimum(np.abs(d["gap"].to_numpy(dtype=float)) / sig0, AZ_CAP)
        f["az_k1"] = np.maximum(f["az"] - 1.0, 0.0)
        f["az_k2"] = np.maximum(f["az"] - 2.0, 0.0)
        f["latr"] = lclip(np.log(atr / close) - lsig)
        f["lrvol"] = lrvol
        f["lrvol5"] = _roll(pd.Series(lrvol, index=d.index), code, 5)
        f["spec"] = lclip(lrvol_raw - mkt)
        f["mkt"] = mkt
        illiq = pd.Series(np.where(dvol > 0, np.abs(r) / dvol, np.nan), index=d.index)
        absr = pd.Series(np.abs(r), index=d.index)
        dvs = pd.Series(np.where(dvol > 0, dvol, np.nan), index=d.index)

        def zscore(x20, w, mp):
            """z-score of ln(x20) against the mean and sd of its previous w bars (same stock)."""
            lx = pd.Series(np.log(np.where(x20 > 0, x20, np.nan)), index=d.index)
            lag = lx.groupby(code, sort=False).shift(1)
            mu = _roll(lag, code, w, "mean", mp)
            sd = _roll(lag, code, w, "std", mp)
            return np.clip(np.where(sd > 0, (lx.to_numpy() - mu) / sd, np.nan), -Z_CLIP, Z_CLIP)

        il20 = _roll(illiq, code, AMI_SMOOTH, minp=15)
        f["amz250"] = zscore(il20, 250, 125)
        f["amz100"] = zscore(il20, 100, 50)
        f["pz250"] = zscore(_roll(absr, code, AMI_SMOOTH, minp=15), 250, 125)
        f["dz250"] = zscore(_roll(dvs, code, AMI_SMOOTH, minp=15), 250, 125)
        f["inter"] = lrvol * np.sign(r)
        f["lrv_pos"] = np.maximum(lrvol, 0.0)
        f["lrv_neg"] = np.minimum(lrvol, 0.0)
    # cross-sectional medians of the price terms on each date (all tickers present that date)
    for k in ("lr1", "lr5", "lr22", "az"):
        s = pd.Series(f[k], index=d.index).replace([np.inf, -np.inf], np.nan)
        f["m_" + k] = s.groupby(d["date"]).transform("median").to_numpy()
    # targets
    y = {}
    with np.errstate(divide="ignore", invalid="ignore"):
        for h in HORIZONS:
            v = d[f"rv_fwd{h}"].to_numpy(dtype=float)
            y[f"rv{h}"] = np.where(v > 0, np.log(v) - lsig, np.nan)
        v = d["pk_fwd10"].to_numpy(dtype=float)
        y["pk10"] = np.where(v > 0, np.log(v) - lsig, np.nan)
        y["rv10_atr"] = np.where((rv10 > 0) & (atr > 0), np.log(rv10) - np.log(atr / close), np.nan)
        ratio10, ratio10_atr, atr_sig = rv10 / sig0, rv10 / (atr / close), atr / close / sig0
    low_f = _fwd_extreme(d["low"].to_numpy(dtype=float), cnp, STOP_BARS, True)
    high_f = _fwd_extreme(d["high"].to_numpy(dtype=float), cnp, STOP_BARS, False)
    dates = d["date"].to_numpy()
    fwd_end = _shift_fwd(dates, cnp, max(HORIZONS), np.datetime64("NaT", "ns"))
    ev = d["eval"].to_numpy()
    F = np.column_stack([f[k] for k in ALL_FEATS])
    fin = np.isfinite(F).all(1)
    yok = np.all([np.isfinite(y[k]) for k in ("rv5", "rv10", "rv20", "pk10", "rv10_atr")], axis=0)
    ok = ev & fin & yok & np.isfinite(low_f) & np.isfinite(high_f)
    S = {"name": name, "F": F[ok], "month": d["month"].to_numpy()[ok].astype(np.int64),
         "date": dates[ok], "fwd_end": fwd_end[ok], "code": cnp[ok],
         "y": {k: v[ok] for k, v in y.items()},
         "rvol": d["rvol"].to_numpy(dtype=float)[ok], "az_raw": az_raw[ok],
         "ratio10": ratio10[ok], "ratio10_atr": ratio10_atr[ok], "atr_sig": atr_sig[ok], "r": r[ok],
         "spec_raw": (lrvol_raw - mkt)[ok]}
    c, a = close[ok], atr[ok]
    for k in STOP_K:
        S[f"hit_dn{k:g}"] = (low_f[ok] <= c - k * a).astype(float)
        S[f"hit_up{k:g}"] = (high_f[ok] >= c + k * a).astype(float)
    S["counts"] = {"rows_all": int(len(d)), "eval_rows": int(ev.sum()), "used_rows": int(ok.sum()),
                   "dropped_feature_nan": int((ev & ~fin).sum()), "dropped_target": int((ev & fin & ~yok).sum()),
                   "stocks": int(d["ticker"].nunique()), "months": int(len(np.unique(S["month"]))),
                   "first": str(S["date"].min())[:10], "last": str(S["date"].max())[:10],
                   "zero_volume_eval": int((ev & ~np.isfinite(lrvol)).sum())}
    S["_check"] = {"d": d, "code": cnp, "f": f, "ok": ok, "low_f": low_f} if name == "A" else None
    S["counts"]["clipped_share"] = {k: rnd(np.mean(np.abs(f[k][ok]) >= LOG_CLIP), 6)
                                    for k in ("lr5", "lr22", "lp5", "lp22", "latr", "lrvol", "spec")}
    return S


# --------------------------------------------------------------------------- statistics
def _cols(model, mods=MODELS):
    return [FI[k] for k in mods[model]]


def _ci(bt):
    bt = bt[np.isfinite(bt)]
    lo, hi = np.percentile(bt, [2.5, 97.5])
    return rnd(lo), rnd(hi)


def _fit_all(F, y):
    """OLS of every model: P x n_models coefficient matrix (zeros for unused terms). The last column is
    "ATR alone with a constant ratio": ln rv = ln(ATR/close) + mean(y - latr)."""
    XtX, Xty = F.T @ F, F.T @ y
    names = list(MODELS) + ["atr_const"]
    B = np.zeros((F.shape[1], len(names)))
    for j, name in enumerate(MODELS):
        c = _cols(name)
        B[c, j] = np.linalg.solve(XtX[np.ix_(c, c)], Xty[c])
    c0, la = FI["const"], FI["latr"]
    B[la, -1] = 1.0
    B[c0, -1] = (Xty[c0] - XtX[c0, la]) / XtX[c0, c0]
    return names, B


def _smear(F, y, B, chunk=300_000):
    """Duan smearing factor of each model: mean of exp(2 * residual) on the training rows."""
    tot = np.zeros(B.shape[1])
    for a in range(0, len(y), chunk):
        tot += np.exp(2.0 * (y[a:a + chunk, None] - F[a:a + chunk] @ B)).sum(0)
    return tot / len(y)


def _resid_sums(F, y, B, mi, M, smear=None, chunk=300_000):
    """per-month sums of squared errors, absolute errors and QLIKE losses of every model."""
    nm = B.shape[1]
    sse, sae = np.zeros((nm, M)), np.zeros((nm, M))
    sql = np.zeros((nm, M)) if smear is not None else None
    for a in range(0, len(y), chunk):
        E = y[a:a + chunk, None] - F[a:a + chunk] @ B
        m = mi[a:a + chunk]
        for j in range(nm):
            e = E[:, j]
            sse[j] += np.bincount(m, weights=e * e, minlength=M)
            sae[j] += np.bincount(m, weights=np.abs(e), minlength=M)
            if smear is not None:
                lq = 2.0 * e - np.log(smear[j])                 # ln(RV^2 / F)
                sql[j] += np.bincount(m, weights=np.exp(lq) - lq - 1.0, minlength=M)
    return sse, sae, sql


def oos(tr: dict, te: dict, tr_mask, te_mask, target: str, rng, qlike=False, mae=False) -> dict:
    """fit every model on the training rows, score on the test rows; month-block bootstrap of the test."""
    Ftr = tr["F"] if tr_mask is None else tr["F"][tr_mask]
    ytr = tr["y"][target] if tr_mask is None else tr["y"][target][tr_mask]
    Fte = te["F"] if te_mask is None else te["F"][te_mask]
    yte = te["y"][target] if te_mask is None else te["y"][target][te_mask]
    mte = te["month"] if te_mask is None else te["month"][te_mask]
    mcodes, mi = np.unique(mte, return_inverse=True)
    M = len(mcodes)
    idx = rng.integers(0, M, (N_BOOT, M))
    names, B = _fit_all(Ftr, ytr)
    ybar = ytr.mean()
    sst = np.bincount(mi, weights=(yte - ybar) ** 2, minlength=M)
    nmth = np.bincount(mi, minlength=M).astype(float)
    smear = _smear(Ftr, ytr, B) if qlike else None
    sse_, sae_, sql_ = _resid_sums(Fte, yte, B, mi, M, smear)
    sse = {k: sse_[j] for j, k in enumerate(names)}
    sae = {k: sae_[j] for j, k in enumerate(names)}
    out = {"n_train": int(len(ytr)), "n_test": int(len(yte)), "test_months": int(M),
           "ybar_train": rnd(ybar), "ybar_test": rnd(yte.mean()), "sd_y_test": rnd(yte.std()),
           "r2": {k: rnd(1.0 - v.sum() / sst.sum()) for k, v in sse.items()}, "gain": {}}
    for aug, base in PAIRS:
        g = (sse[base].sum() - sse[aug].sum()) / sst.sum()
        lo, hi = _ci((sse[base][idx].sum(1) - sse[aug][idx].sum(1)) / sst[idx].sum(1))
        rel = 1.0 - sse[aug].sum() / sse[base].sum()
        rlo, rhi = _ci(1.0 - sse[aug][idx].sum(1) / sse[base][idx].sum(1))
        out["gain"][f"{aug} vs {base}"] = {"r2_gain": rnd(g, 5), "lo": lo, "hi": hi,
                                           "mse_cut": rnd(rel, 5), "mse_cut_lo": rlo, "mse_cut_hi": rhi}
        _count()
    if qlike:
        sql = {k: sql_[j] for j, k in enumerate(names)}
        out["qlike"] = {k: rnd(v.sum() / nmth.sum(), 5) for k, v in sql.items()}
        out["qlike_diff"] = {}
        for aug, base in PAIRS + [("B0", "atr_const"), ("B0", "sig0")]:
            dq = (sql[aug].sum() - sql[base].sum()) / nmth.sum()
            lo, hi = _ci((sql[aug][idx].sum(1) - sql[base][idx].sum(1)) / nmth[idx].sum(1))
            out["qlike_diff"][f"{aug} vs {base}"] = {"diff": rnd(dq, 5), "lo": lo, "hi": hi}
            _count()
    if mae:
        out["mae"] = {k: rnd(v.sum() / nmth.sum(), 5) for k, v in sae.items()}
        out["mae_ratio"] = {}
        bs, ba = CHOSEN["best_single"], CHOSEN["best_augmented"]
        for num, den in ((bs, "B0"), (ba, "B0"), ("B0", "atr_const"), ("B0", "atr_reg"), ("B0", "sig0"),
                         (bs, "atr_const"), (ba, "atr_const"), (ba, "atr_reg"), (ba, "sig0"),
                         ("B1", "B0"), ("B1+joint", "B1"), ("B1+joint", "atr_const"), ("B1", "atr_const")):
            ratio = sae[num].sum() / sae[den].sum()
            lo, hi = _ci(sae[num][idx].sum(1) / sae[den][idx].sum(1))
            out["mae_ratio"][f"{num} / {den}"] = {"ratio": rnd(ratio, 5), "lo": lo, "hi": hi}
            _count()
    return out


def gram(S: dict, rng):
    """per-month X'X of the full feature matrix and one set of month-block bootstrap weights."""
    F = S["F"]
    mcodes, mi = np.unique(S["month"], return_inverse=True)
    M, P = len(mcodes), F.shape[1]
    order = np.argsort(mi, kind="stable")
    bounds = np.searchsorted(mi[order], np.arange(M + 1))
    A = np.empty((M, P * P))
    for m in range(M):
        X = F[order[bounds[m]:bounds[m + 1]]]
        A[m] = (X.T @ X).ravel()
    idx = rng.integers(0, M, (N_BOOT, M))
    w = np.zeros((N_BOOT, M))
    np.add.at(w, (np.repeat(np.arange(N_BOOT), M), idx.ravel()), 1.0)
    S["_gram"] = {"mi": mi, "M": M, "P": P, "A": A.sum(0).reshape(P, P), "Ab": (w @ A).reshape(N_BOOT, P, P), "w": w}


def coefs(S: dict, y: np.ndarray, models, mods=MODELS, report_all=()) -> dict:
    """full-set OLS coefficients of the volume terms with month-block bootstrap intervals."""
    G = S["_gram"]
    F = S["F"]
    g = np.column_stack([np.bincount(G["mi"], weights=F[:, j] * y, minlength=G["M"]) for j in range(G["P"])])
    g0, gb = g.sum(0), G["w"] @ g
    out = {}
    for name in models:
        c = _cols(name, mods)
        b = np.linalg.solve(G["A"][np.ix_(c, c)], g0[c])
        bb = np.linalg.solve(G["Ab"][:, c][:, :, c], gb[:, c, None])[:, :, 0]
        res = {}
        for j, k in enumerate(mods[name]):
            if k in VOL_TERMS or name in report_all:
                lo, hi = np.percentile(bb[:, j], [2.5, 97.5])
                res[k] = {"b": rnd(b[j], 5), "lo": rnd(lo, 5), "hi": rnd(hi, 5)}
                if k in VOL_TERMS:
                    _count()
        out[name] = res
    return out


def pct(b):
    """coefficient on ln(rvol) -> percent change of volatility for a 2x and a 3x day."""
    return {f"x{m}": {k: rnd(100.0 * (np.exp(v * np.log(m)) - 1.0), 2) for k, v in b.items()} for m in (2, 3)}


# --------------------------------------------------------------------------- V5 / V6 tables
def buckets(S: dict):
    rb = np.searchsorted(np.asarray(RVOL_EDGES), S["rvol"], side="right")
    ab = np.searchsorted(np.asarray(AZ_EDGES), S["az_raw"], side="right")
    return rb, ab


def vol_table(S: dict, rng) -> dict:
    rb, ab = buckets(S)
    y, ya, m = S["y"]["rv10"], S["y"]["rv10_atr"], S["month"]
    out = {"cells": {}, "diff_vs_ref": {}, "marginal": {}, "marginal_diff": {}}
    years = S["counts"]["used_rows"] / 252.0
    for j, rl in enumerate(RVOL_LABELS):
        k = rb == j
        out["marginal"][rl] = {"n": int(k.sum()), "share": rnd(k.mean(), 5),
                               "per_stock_year": rnd(252.0 * k.mean(), 2),
                               "median_ratio_sig0": rnd(np.median(S["ratio10"][k])),
                               "median_ratio_atr": rnd(np.median(S["ratio10_atr"][k])),
                               "mean_az": rnd(S["az_raw"][k].mean(), 3)}
        if j != REF_BUCKET:
            ref = rb == REF_BUCKET
            for nm, v in (("ln_ratio_sig0", y), ("ln_ratio_atr", ya)):
                dd = e05.boot_diff(v[k], m[k], v[ref], m[ref], rng)
                dd["pct"] = rnd(100.0 * (np.exp(dd["diff"]) - 1.0), 2)
                dd["pct_lo"] = rnd(100.0 * (np.exp(dd["lo"]) - 1.0), 2)
                dd["pct_hi"] = rnd(100.0 * (np.exp(dd["hi"]) - 1.0), 2)
                out["marginal_diff"][f"{rl} vs ref | {nm}"] = dd
                _count()
    for i, al in enumerate(AZ_LABELS):
        ref = (ab == i) & (rb == REF_BUCKET)
        for j, rl in enumerate(RVOL_LABELS):
            k = (ab == i) & (rb == j)
            n = int(k.sum())
            cell = {"n": n}
            if n > 0:
                cell.update({"median_ratio_sig0": rnd(np.median(S["ratio10"][k])),
                             "median_ratio_atr": rnd(np.median(S["ratio10_atr"][k])),
                             "mean_ln_ratio_sig0": rnd(y[k].mean()), "mean_az": rnd(S["az_raw"][k].mean(), 3),
                             "median_atr_over_sig0": rnd(np.median(S["atr_sig"][k]), 3)})
            out["cells"][f"az {al} | rvol {rl}"] = cell
            if j != REF_BUCKET and n >= 30:
                for nm, v in (("ln_ratio_sig0", y), ("ln_ratio_atr", ya)):
                    dd = e05.boot_diff(v[k], m[k], v[ref], m[ref], rng)
                    dd["pct"] = rnd(100.0 * (np.exp(dd["diff"]) - 1.0), 2)
                    dd["pct_lo"] = rnd(100.0 * (np.exp(dd["lo"]) - 1.0), 2)
                    dd["pct_hi"] = rnd(100.0 * (np.exp(dd["hi"]) - 1.0), 2)
                    out["diff_vs_ref"][f"az {al} | rvol {rl} vs ref | {nm}"] = dd
                    _count()
    out["stock_years"] = rnd(years, 1)
    return out


def stop_table(S: dict, rng) -> dict:
    rb, ab = buckets(S)
    m = S["month"]
    out = {"cells": {}, "diff_vs_ref": {}, "marginal": {}, "marginal_diff": {}}
    keys = [f"hit_{side}{k:g}" for k in STOP_K for side in ("dn", "up")]
    for j, rl in enumerate(RVOL_LABELS):
        k = rb == j
        out["marginal"][rl] = {"n": int(k.sum()), **{h: rnd(S[h][k].mean()) for h in keys}}
        if j != REF_BUCKET:
            ref = rb == REF_BUCKET
            for h in keys:
                out["marginal_diff"][f"{rl} vs ref | {h}"] = e05.boot_diff(S[h][k], m[k], S[h][ref], m[ref], rng)
                _count()
    for i, al in enumerate(AZ_LABELS):
        ref = (ab == i) & (rb == REF_BUCKET)
        for j, rl in enumerate(RVOL_LABELS):
            k = (ab == i) & (rb == j)
            n = int(k.sum())
            cell = {"n": n}
            if n >= 30:
                for h in keys:
                    bm = e05.boot_mean(S[h][k], m[k], rng)
                    cell[h] = {"p": bm["est"], "lo": bm["lo"], "hi": bm["hi"]}
            out["cells"][f"az {al} | rvol {rl}"] = cell
            if j != REF_BUCKET and n >= 30:
                for h in keys:
                    out["diff_vs_ref"][f"az {al} | rvol {rl} vs ref | {h}"] = e05.boot_diff(
                        S[h][k], m[k], S[h][ref], m[ref], rng)
                    _count()
    # linear probability model: B0 terms + ln(ATR/close/sig0) + lrvol
    lpm = {"LPM": BASE + ["latr", "lrvol"], "LPM5": BASE + ["latr", "lrvol5"]}
    out["lpm"] = {}
    for h in keys:
        res = coefs(S, S[h], ["LPM", "LPM5"], mods=lpm, report_all=("LPM",))
        out["lpm"][h] = {"lrvol": res["LPM"]["lrvol"], "latr": res["LPM"]["latr"], "az": res["LPM"]["az"],
                         "lrvol5": res["LPM5"]["lrvol5"], "base_rate": rnd(S[h].mean())}
    return out


def flag_table(S: dict, rng) -> dict:
    """the proposed sizing rule, tested directly: flagged bars against all unflagged bars."""
    m = S["month"]
    amz = S["F"][:, FI["amz250"]]
    flags = {"rvol>=2": S["rvol"] >= 2.0, "rvol>=3": S["rvol"] >= 3.0,
             "specific rvol>=2": S["spec_raw"] >= np.log(2.0),
             "amihud z>=1.28": amz >= 1.2816,
             "specific rvol>=2 or amihud z>=1.28": (S["spec_raw"] >= np.log(2.0)) | (amz >= 1.2816)}
    targets = {"ln_ratio_atr": S["y"]["rv10_atr"], "ln_ratio_sig0": S["y"]["rv10"],
               "hit_dn2": S["hit_dn2"], "hit_dn3": S["hit_dn3"], "hit_up2": S["hit_up2"]}
    out = {}
    for fl, k in flags.items():
        res = {"n": int(k.sum()), "share": rnd(k.mean(), 5), "per_stock_year": rnd(252.0 * k.mean(), 2)}
        for tn, v in targets.items():
            dd = e05.boot_diff(v[k], m[k], v[~k], m[~k], rng)
            if tn.startswith("ln_"):
                for a, b in (("pct", "diff"), ("pct_lo", "lo"), ("pct_hi", "hi")):
                    dd[a] = rnd(100.0 * (np.exp(dd[b]) - 1.0), 2)
            else:
                dd["rate_flagged"] = rnd(v[k].mean())
                dd["rate_rest"] = rnd(v[~k].mean())
            res[tn] = dd
            _count()
        out[fl] = res
    return out


# --------------------------------------------------------------------------- driver
def split_masks(S: dict, frac=0.6):
    months = np.unique(S["month"])
    k = int(np.floor(frac * len(months)))
    te = np.isin(S["month"], months[k:])
    test_start = S["date"][te].min()
    tr = (~te) & (S["fwd_end"] < test_start)           # purge forward windows that reach the test period
    return tr, te, {"train_months": int(k), "test_months": int(len(months) - k),
                    "test_start": str(test_start)[:10], "purged_rows": int((~te).sum() - tr.sum())}


def self_check(S: dict) -> dict:
    """second route for the rolling features, the stop target and one regression coefficient."""
    ck = S["_check"]
    d, f, code = ck["d"], ck["f"], ck["code"]
    rows = np.flatnonzero(code == code[len(code) // 2])
    r = d["r"].to_numpy(dtype=float)[rows]
    sig0 = d["sig0"].to_numpy(dtype=float)[rows]
    low = d["low"].to_numpy(dtype=float)[rows]
    dv = d["dvol"].to_numpy(dtype=float)[rows]
    n = len(rows)
    err = {"lr5": 0.0, "amz250": 0.0, "low_f": 0.0}
    il = np.full(n, np.nan)
    for i in range(19, n):
        w = np.abs(r[i - 19:i + 1]) / dv[i - 19:i + 1]
        if np.isfinite(w).sum() >= 15:
            il[i] = np.log(np.nanmean(w))
    for i in range(450, n - 20, 37):
        a = np.clip(0.5 * np.log(np.mean(r[i - 4:i + 1] ** 2)) - np.log(sig0[i]), -LOG_CLIP, LOG_CLIP)
        err["lr5"] = max(err["lr5"], abs(a - f["lr5"][rows[i]]))
        hist = il[i - 250:i]
        a = np.clip((il[i] - np.nanmean(hist)) / np.nanstd(hist, ddof=1), -Z_CLIP, Z_CLIP)
        err["amz250"] = max(err["amz250"], abs(a - f["amz250"][rows[i]]))
        err["low_f"] = max(err["low_f"], abs(low[i + 1:i + 11].min() - ck["low_f"][rows[i]]))
    c = _cols("B0+lrvol")
    b1 = np.linalg.lstsq(S["F"][:, c], S["y"]["rv10"], rcond=None)[0][-1]
    X = S["F"][:, c]
    b2 = np.linalg.solve(X.T @ X, X.T @ S["y"]["rv10"])[-1]
    # Frisch-Waugh route: residualise y and lrvol on B0, then a one-variable slope
    c0 = _cols("B0")
    X0 = S["F"][:, c0]
    ry = S["y"]["rv10"] - X0 @ np.linalg.lstsq(X0, S["y"]["rv10"], rcond=None)[0]
    rx = S["F"][:, FI["lrvol"]] - X0 @ np.linalg.lstsq(X0, S["F"][:, FI["lrvol"]], rcond=None)[0]
    b3 = float(rx @ ry / (rx @ rx))
    out = {"max_abs_err": {k: float(f"{v:.3g}") for k, v in err.items()},
           "b_lrvol_lstsq": rnd(b1, 6), "b_lrvol_normal_eq": rnd(b2, 6), "b_lrvol_fwl": rnd(b3, 6)}
    assert err["lr5"] < 1e-6 and err["amz250"] < 1e-4 and err["low_f"] < 1e-9, out
    assert abs(b1 - b2) < 1e-8 and abs(b1 - b3) < 1e-8, out
    return out


def analyse_set(S: dict) -> dict:
    name = S["name"]
    rng = np.random.default_rng(SEED + SEED_OFFSET[name])
    res = {"counts": S["counts"]}
    tr, te, info = split_masks(S)
    res["split"] = info
    res["oos_within"] = {}
    for tg in ("rv5", "rv10", "rv20", "pk10"):
        res["oos_within"][tg] = oos(S, S, tr, te, tg, rng, qlike=(tg in ("rv10", "pk10")), mae=(tg == "rv10"))
    gram(S, rng)
    res["coef"] = {}
    for tg in ("rv5", "rv10", "rv20", "pk10"):
        res["coef"][tg] = coefs(S, S["y"][tg], COEF_MODELS, report_all=("B0+lrvol",))
    for tg in ("rv5", "rv10", "rv20"):
        res["coef"][tg]["effect_pct"] = {
            "B0+lrvol": pct(res["coef"][tg]["B0+lrvol"]["lrvol"]),
            "B1+lrvol": pct(res["coef"][tg]["B1+lrvol"]["lrvol"]),
            "B0+lrv_pos (positive side)": pct(res["coef"][tg]["B0+lrv_pos+lrv_neg"]["lrv_pos"])}
    # raw effect against ATR: ln(rv_fwd10 / ATR-implied) on const + lrvol, and with az added
    extra = {"ATRraw": ["const", "lrvol"], "ATR+az": ["const", "lr1", "az", "lrvol"]}
    ra = coefs(S, S["y"]["rv10_atr"], ["ATRraw", "ATR+az"], mods=extra)
    res["vs_atr"] = {k: {"lrvol": v["lrvol"], "effect_pct": pct(v["lrvol"])} for k, v in ra.items()}
    res["vol_table"] = vol_table(S, rng)
    res["stops"] = stop_table(S, rng)
    res["flags"] = flag_table(S, rng)
    amz = S["F"][:, FI["amz250"]]
    q50, q90 = np.percentile(amz, [50, 90])
    res["amihud_effect_pct_median_to_p90"] = {
        tg: {mod: {k: rnd(100.0 * (np.exp(v * (q90 - q50)) - 1.0), 2)
                   for k, v in res["coef"][tg][mod]["amz250"].items()}
             for mod in ("B0+amz250", "B1+amz250", "B0+pz250+amz250")}
        for tg in ("rv5", "rv10", "rv20")}
    res["amihud_z_p50_p90"] = [rnd(q50, 3), rnd(q90, 3)]
    sd = {k: rnd(S["F"][:, FI[k]].std(), 4)
          for k in ("lrvol", "lrvol5", "spec", "mkt", "amz250", "amz100", "inter", "pz250", "dz250")}
    res["feature_sd"] = sd
    names = ("lrvol", "az", "lr1", "lr5", "lp1", "amz250", "mkt", "m_az")
    cm = np.corrcoef(S["F"][:, [FI[k] for k in names]].T)
    res["corr_lrvol_with"] = {k: rnd(cm[0, i], 3) for i, k in enumerate(names) if i}
    cm = np.corrcoef(S["F"][:, [FI[k] for k in ("amz250", "pz250", "dz250", "lr22", "lrvol5")]].T)
    res["corr_amz250_with"] = {k: rnd(cm[0, i + 1], 3) for i, k in enumerate(("pz250", "dz250", "lr22", "lrvol5"))}
    res["headline"] = headline(res)
    return res


def headline(res: dict) -> dict:
    """the handful of numbers a reader needs first (all are copies of entries elsewhere in the file)."""
    w, c = res["oos_within"], res["coef"]
    h = {"n": res["counts"]["used_rows"],
         "lrvol_effect_pct_B0": {tg: c[tg]["effect_pct"]["B0+lrvol"] for tg in ("rv5", "rv10", "rv20")},
         "lrvol_effect_pct_B1": {tg: c[tg]["effect_pct"]["B1+lrvol"] for tg in ("rv5", "rv10", "rv20")},
         "lrvol_effect_pct_vs_ATR_raw": res["vs_atr"]["ATRraw"]["effect_pct"],
         "coef_rv10": {"lrvol|B0": c["rv10"]["B0+lrvol"]["lrvol"], "lrvol5|B0": c["rv10"]["B0+lrvol5"]["lrvol5"],
                       "spec|B0": c["rv10"]["B0+spec"]["spec"], "mkt|B0": c["rv10"]["B0+mkt"]["mkt"],
                       "mkt|B1": c["rv10"]["B1+spec+mkt"]["mkt"], "amz250|B0": c["rv10"]["B0+amz250"]["amz250"],
                       "amz250|B1": c["rv10"]["B1+amz250"]["amz250"], "dz250|B0": c["rv10"]["B0+dz250"]["dz250"],
                       "pz250|B0": c["rv10"]["B0+pz250"]["pz250"], "inter|B0": c["rv10"]["B0+inter"]["inter"]},
         "oos_within_rv10": {"r2_B0": w["rv10"]["r2"]["B0"], "r2_B1": w["rv10"]["r2"]["B1"],
                             **{k: w["rv10"]["gain"][k] for k in (
                                 "B0+lrvol vs B0", "B0+lrvol5 vs B0", "B0+spec vs B0", "B0+mkt vs B0",
                                 "B0+amz250 vs B0", "B0+amz100 vs B0", "B0+inter vs B0", "B0+joint vs B0",
                                 "B0+dz250 vs B0", "B0+pz250 vs B0", "B1+joint vs B1", "B1 vs B0")}},
         "oos_within_rv5_lrvol": w["rv5"]["gain"]["B0+lrvol vs B0"],
         "mae_ratio_rv10": w["rv10"]["mae_ratio"],
         "flags_vs_rest": {k: {"per_stock_year": v["per_stock_year"],
                               "vol_vs_ATR_pct": [v["ln_ratio_atr"]["pct"], v["ln_ratio_atr"]["pct_lo"], v["ln_ratio_atr"]["pct_hi"]],
                               "vol_vs_sig0_pct": [v["ln_ratio_sig0"]["pct"], v["ln_ratio_sig0"]["pct_lo"], v["ln_ratio_sig0"]["pct_hi"]],
                               "stop2_diff": [v["hit_dn2"]["diff"], v["hit_dn2"]["lo"], v["hit_dn2"]["hi"]],
                               "stop3_diff": [v["hit_dn3"]["diff"], v["hit_dn3"]["lo"], v["hit_dn3"]["hi"]]}
                           for k, v in res["flags"].items()}}
    return h


def cross(tr: dict, te: dict, te_mask=None, label="") -> dict:
    rng = np.random.default_rng(SEED + 100 * SEED_OFFSET[tr["name"]] + SEED_OFFSET[te["name"]] + (7 if label else 0))
    out = {}
    for tg in ("rv5", "rv10", "rv20", "pk10"):
        out[tg] = oos(tr, te, None, te_mask, tg, rng, qlike=(tg in ("rv10", "pk10")), mae=(tg == "rv10"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=DEFAULT_PANEL)
    ap.add_argument("--sets", nargs="+", default=list(SET_ORDER))
    ap.add_argument("--out", default=str(ROOT / "results" / "e14_volume_predicts_volatility.json"))
    a = ap.parse_args()
    t0 = time.time()
    out = {"experiment": "e14_volume_predicts_volatility", "seed": SEED, "n_boot": N_BOOT,
           "design": {"floor": FLOOR, "az_cap": AZ_CAP, "base": BASE, "rich": RICH, "joint": JOINT,
                      "chosen_on_A": CHOSEN, "rvol_buckets": RVOL_LABELS, "az_buckets": AZ_LABELS,
                      "stop_bars": STOP_BARS, "stop_k": STOP_K},
           "sets": {}, "cross": {}}
    data = {}
    for name in [s for s in SET_ORDER if s in a.sets]:
        S = load_set(a.panel, name)
        if name == "A":
            out["self_check"] = self_check(S)
        S["_check"] = None
        data[name] = S
        out["sets"][name] = analyse_set(S)
        S["_gram"] = None
        print(f"[{time.time() - t0:6.0f}s] {name}: {S['counts']}", flush=True)
    for trn, ten in (("A", "B"), ("LH", "MS"), ("MS", "LH")):
        if trn in data and ten in data:
            out["cross"][f"{trn}->{ten}"] = cross(data[trn], data[ten])
            print(f"[{time.time() - t0:6.0f}s] cross {trn}->{ten}", flush=True)
    if "LH" in data and "MS" in data:
        late = data["MS"]["date"] > data["LH"]["date"].max() + np.timedelta64(31, "D")
        out["cross"]["LH->MS_after_LH"] = cross(data["LH"], data["MS"], late, "late")
        out["cross"]["LH->MS_after_LH"]["first_test_date"] = str(data["MS"]["date"][late].min())[:10]
    out["comparisons_run"] = N_COMPARISONS
    out["seconds"] = round(time.time() - t0)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.out}  comparisons={N_COMPARISONS}  {out['seconds']}s")


if __name__ == "__main__":
    main()
