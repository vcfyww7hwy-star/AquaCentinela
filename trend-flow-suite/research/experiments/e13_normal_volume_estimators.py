#!/usr/bin/env python3
"""E13 - What is the best definition of "normal volume"? (review of the Relative Volume pane)

Reviewer claims under test
  (a) The pane's reference is an ARITHMETIC EWMA (span 50) of a heavy-tailed variable. One day of 10x
      normal volume lifts it by about 35%, so relative volume is understated for weeks afterwards.
      Log volume with winsorised updates would nearly remove this.
  (b) Fixed multiples (2x, 3x) confuse dispersion with rarity: 2x is +2.8 sd of log volume for a
      stable defensive stock (sd about 0.25) and +1.15 sd for a volatile mid cap (sd about 0.60).
      A z-score of log volume would make thresholds comparable across stocks.
  (c) In single stocks the median of volume / EWMA(volume) sits below 1 (about 0.80-0.90); the
      author's sanity check on the SPX index (median 0.996) hid this.

Estimators of normal volume. Every one is the value BEFORE bar t is included (bars <= t-1 only).
V = volume, lv = ln(V), a(n) = 2 / (n + 1).
  M0          shipped: EWMA mean of V, span 50, seeded with the first bar (tfs.core.slot_ewma_lagged,
              one slot). Recomputed here and checked against the panel column `ev`.
              M0_20 and M0_100: the same with spans 20 and 100 (added so that a span effect is not
              mistaken for an effect of the definition).
  M1          geometric: normal = exp(mu), mu = EWMA of lv, span 50, seeded with the first valid lv.
              Scale s1 = sqrt(EWMA span 50 of e^2), e = lv - mu (the one-step innovation), previous
              bars only. zM1 = e / s1.
  M2_<m>_<q>  winsorised geometric: normal = exp(mu). On each bar e = lv - mu; once q innovations
              have been seen (and s > 0) e is clipped to +-3 s; then mu += a(m) * e_clipped and
              s^2 += a(q) * (e_clipped^2 - s^2). s^2 is seeded with the first squared innovation.
              m (span of mu) in {20, 50, 100}, q (span of s) in {50, 100}. zM2 = e (unclipped) / s,
              both taken before the update. State per series: mu, s^2 and a counter.
              M2_50_250 (q = 250) is NOT in the reviewer's list. It was added during development on
              set A, when the first run showed that after a spike the scale s of the z-score inflates
              and zV >= 2 becomes as hard to reach as the shipped 2x (the same feedback the reviewer
              criticised in the price sigma). A slow scale is the obvious remedy; it was then run
              once on the other sets like everything else.
  M3          median of V over the previous 50 bars (bars t-50 .. t-1).
  X_M0cap     NOT in the reviewer's list, added as the smallest possible patch: the shipped EWMA
              with each update capped at 3x the current reference (after 50 bars).
Zero-volume bars (0 in A, B, DJ; 281 in LH; 848 in MS): lv is undefined, so M1 and M2 skip the bar
and hold their state (the Pine convention for `na`). M0, M3 and X_M0cap include the zero as a
value, as shipped. Such bars are excluded from every statistic below, for all estimators alike.

Analysis rows = eval rows (t >= 400, forward window available) with V > 0 and every estimator finite.

Criteria (none uses returns)
  C1 one-step forecast error of ln V: err = lv - ln(normal). MAE, RMSE, mean, and the same after
     removing the pooled median error of the set ("centred": tracking without the level bias).
  C2 centring and shape: median of V / normal (pooled, and its distribution across stocks), mean, sd,
     skewness and tail shares of zV against the normal benchmarks, shares of V / normal >= 2 and >= 3.
  C3 comparability across stocks: per-stock frequency of V/M0 >= 2 (shipped rule) and of zV >= 2,
     their cross-stock distribution, and how each relates to the stock's own sd of log volume
     (sd of the M1 innovation e). For an out-of-sample ranking the sd is also measured on the
     pre-evaluation bars 100..399 and stocks are sorted into quintiles by it.
  C4 bias after spikes: spike = V >= 5 x M3. For k = 1..30 bars since the LAST spike, the mean of
     ln(V / normal) minus the same stock's mean over all its analysis rows. Negative = relative
     volume is understated after spikes. Also the lift of each reference on the bar after a spike.
  C5 how often the flags disagree (V/M0 >= 2 against zV >= 2 under the primary M2), and what the
     change does to the count of "A" marks (absorption at lows) - counts only, no returns.
     Also the flag rate 1-10 and 11-30 bars after a spike against the SAME stock's rate on calm bars
     (no spike in the previous 30 bars), for seven rules: V/M0 >= 2, V/M2 >= 2, V/M2 >= 2.2 (the
     multiple of M2 with the pooled frequency of 2x M0 on set A), V/M3 >= 2 (a reference a spike
     cannot move, the benchmark), zV >= 2 (primary), zV >= 2 with the slow scale, zM1 >= 2.

Discipline: everything was developed on set A (--sets A). PRIMARY (the M2 variant used for C3-C5)
and every threshold were fixed before B, LH and MS were run, once. DJ is run too but its stocks and
dates lie inside LH, so it is not an independent confirmation.

Uncertainty: month-block bootstrap, 2000 resamples (experiments.e05_validation_lite.boot_mean /
boot_diff; the pooled median uses the same month resampling on a histogram). Every interval
computed is counted as one comparison and listed in the output.

  python3 -I experiments/e13_normal_volume_estimators.py [--panel DIR] [--sets A B DJ LH MS]
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
from scipy import stats as sps

import experiments.e05_validation_lite as e05
from tfs.core import slot_ewma_lagged
from tfs.data import load_bundled
from tfs.flow import volume_flow_v2

DEFAULT_PANEL = "/tmp/claude-0/-home-user-AquaCentinela/b2916ecb-3cd8-557a-8730-1dacd8557876/scratchpad/panel"
SEED = 20261123
SET_ORDER = ("A", "B", "DJ", "LH", "MS")
SEED_OFFSET = {"A": 1, "B": 2, "DJ": 3, "LH": 4, "MS": 5}
COLS = ["ticker", "date", "t", "month", "volume", "ev", "rvol", "z", "ext", "absorb_bottom", "eval", "spy_rvol"]
SPAN = 50
CLIP = 3.0
M2_VARIANTS = ((20, 50), (20, 100), (50, 50), (50, 100), (100, 50), (100, 100), (50, 250))   # (span mu, span s)
PRIMARY = "M2_50_100"          # chosen on set A before any other set was run (see results: "primary_choice")
ZPRIMARY = "z" + PRIMARY
ZSLOW = "zM2_50_250"            # slow scale, added on set A after the scale feedback was seen (see docstring)
EST = ["M0", "M0_20", "M0_100", "M1", "M3", "X_M0cap"] + [f"M2_{m}_{q}" for m, q in M2_VARIANTS]
ZEST = ["zM1"] + [f"zM2_{m}_{q}" for m, q in M2_VARIANTS]
SPIKE_MULT = 5.0
REBASED = 2.2                  # multiple of M2 with the pooled frequency of 2x M0 on set A (2.215), fixed there
SD_BUCKETS = ((0.0, 0.30), (0.30, 0.40), (0.40, 0.50), (0.50, 0.60), (0.60, 0.70), (0.70, 9.9))
KMAX = 30
WINDOWS = ((1, 5), (6, 10), (11, 20), (21, 30))
C4_EST = ("M0", "M1", PRIMARY, "M3", "X_M0cap")
C4_EXTRA = ("M0_20", "M2_20_100", "M0_100", "M2_100_100")   # profile only, no intervals
FLAG_WINDOWS = ((1, 10), (11, 30))
MIN_STOCK_ROWS = 250
NAMED = ("JNJ", "PG", "KO", "PEP", "WMT", "XOM", "MSFT", "AAPL", "NVDA", "AMD", "NFLX", "MU", "FCX", "INCY",
         "CHK", "TSLA")
P_NORM_2 = float(sps.norm.sf(2.0))
P_NORM_3 = float(sps.norm.sf(3.0))
PUBLISHED_ABSORB = {"A": 439, "B": 499, "DJ": 60, "LH": 2386, "MS": 9312}
COMPARISONS: list[str] = []


# --------------------------------------------------------------------------- helpers
def rd(x, nd=4):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, nd)


def bmean(label, v, m, rng, scale=1.0, nd=4):
    """Counted month-block bootstrap of a mean. e05 rounds to 4 decimals, so small quantities are
    scaled up before the call and back afterwards."""
    COMPARISONS.append(label)
    o = e05.boot_mean(np.asarray(v, dtype=float) * scale, m, rng)
    return {k: (rd(o[k] / scale, nd + 2) if k != "n" and o[k] is not None else o[k]) for k in o}


def bdiff(label, v_s, m_s, v_c, m_c, rng, scale=1.0, nd=4):
    COMPARISONS.append(label)
    o = e05.boot_diff(np.asarray(v_s, dtype=float) * scale, m_s, np.asarray(v_c, dtype=float) * scale, m_c, rng)
    out = {k: (rd(o[k] / scale, nd + 2) if k != "n" and o[k] is not None else o[k]) for k in o}
    out["n_control"] = int(np.isfinite(v_c).sum())
    return out


def boot_median_ratio(label, lr, month, rng, lo=-5.0, hi=5.0, width=0.002):
    """Median of exp(lr) with a month-block bootstrap interval, on a histogram of lr (bin 0.002)."""
    COMPARISONS.append(label)
    mc, mi = np.unique(month, return_inverse=True)
    nb = int(round((hi - lo) / width))
    b = np.clip(((lr - lo) / width).astype(np.int64), 0, nb - 1)
    cnt = np.bincount(mi * nb + b, minlength=len(mc) * nb).reshape(len(mc), nb).astype(np.float32)
    idx = rng.integers(0, len(mc), (e05.N_BOOT, len(mc)))
    w = np.zeros((e05.N_BOOT, len(mc)), dtype=np.float32)
    np.add.at(w, (np.repeat(np.arange(e05.N_BOOT), len(mc)), idx.ravel()), 1.0)
    cum = np.cumsum(w @ cnt, axis=1, dtype=np.float64)
    half = cum[:, -1] / 2.0
    j = (cum >= half[:, None]).argmax(axis=1)
    below = np.where(j > 0, cum[np.arange(len(j)), np.maximum(j - 1, 0)], 0.0)
    inbin = cum[np.arange(len(j)), j] - below
    med = lo + width * (j + (half - below) / np.where(inbin > 0, inbin, 1.0))
    q = np.percentile(med, [2.5, 97.5])
    return {"est": rd(np.exp(np.median(lr))), "lo": rd(np.exp(q[0])), "hi": rd(np.exp(q[1])), "n": int(len(lr))}


def pct(x, qs=(5, 25, 50, 75, 95)):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return {f"p{q}": rd(np.percentile(x, q)) for q in qs} if len(x) else {}


def dist(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    o = pct(x)
    o.update(mean=rd(x.mean()), cv=rd(x.std() / x.mean()) if x.mean() != 0 else None, n=int(len(x)))
    return o


# --------------------------------------------------------------------------- estimators (rows = series)
def ewma_lagged(x, span):
    """Twin of tfs.core.slot_ewma_lagged with one slot, vectorised across the rows of x."""
    a = 2.0 / (span + 1.0)
    st = np.full(x.shape[0], np.nan)
    out = np.empty_like(x)
    for t in range(x.shape[1]):
        out[:, t] = st
        v = x[:, t]
        ok = ~np.isnan(v)
        st = np.where(ok, np.where(np.isnan(st), v, a * v + (1.0 - a) * st), st)
    return out


def ewma_capped_lagged(x, span, cap):
    """X_M0cap: the shipped EWMA, each update capped at cap x the current reference after `span` bars."""
    a = 2.0 / (span + 1.0)
    st = np.full(x.shape[0], np.nan)
    n = np.zeros(x.shape[0])
    out = np.empty_like(x)
    for t in range(x.shape[1]):
        out[:, t] = st
        v = x[:, t]
        ok = ~np.isnan(v)
        with np.errstate(invalid="ignore"):
            vc = np.where((n >= span) & (st > 0), np.minimum(v, cap * st), v)
        st = np.where(ok, np.where(np.isnan(st), v, a * vc + (1.0 - a) * st), st)
        n += ok
    return out


def wins_geo_lagged(lv, span_mu, span_s, clip=CLIP):
    """M2. Returns (mu, s) before each bar. NaN lv (zero volume, padding) holds the state."""
    am, aq = 2.0 / (span_mu + 1.0), 2.0 / (span_s + 1.0)
    k = lv.shape[0]
    mu, s2, n = np.full(k, np.nan), np.full(k, np.nan), np.zeros(k)
    out_mu, out_s = np.empty_like(lv), np.empty_like(lv)
    for t in range(lv.shape[1]):
        out_mu[:, t] = mu
        out_s[:, t] = np.sqrt(s2)
        x = lv[:, t]
        ok = ~np.isnan(x)
        upd = ok & ~np.isnan(mu)
        with np.errstate(invalid="ignore"):
            e = x - mu
            lim = clip * np.sqrt(s2)
            ec = np.where((n >= span_s) & (s2 > 0), np.clip(e, -lim, lim), e)
            s2n = np.where(np.isnan(s2), ec * ec, aq * ec * ec + (1.0 - aq) * s2)
        mu = np.where(upd, mu + am * ec, np.where(ok, x, mu))
        s2 = np.where(upd, s2n, s2)
        n += upd
    return out_mu, out_s


def all_estimators(v):
    """v: (series, bars) volume, NaN padded. Returns ln(normal) per estimator, zV per z version, lv."""
    with np.errstate(divide="ignore", invalid="ignore"):
        lv = np.where(v > 0, np.log(v), np.nan)
        ln = {"M0": np.log(ewma_lagged(v, SPAN)), "M0_20": np.log(ewma_lagged(v, 20)),
              "M0_100": np.log(ewma_lagged(v, 100)), "X_M0cap": np.log(ewma_capped_lagged(v, SPAN, CLIP))}
        mu1 = ewma_lagged(lv, SPAN)
        e1 = lv - mu1
        s1 = np.sqrt(ewma_lagged(e1 * e1, SPAN))
        ln["M1"] = mu1
        z = {"zM1": e1 / s1}
        scale = {"zM1": s1}
        for m, q in M2_VARIANTS:
            mu, s = wins_geo_lagged(lv, m, q)
            ln[f"M2_{m}_{q}"] = mu
            z[f"zM2_{m}_{q}"] = (lv - mu) / s
            scale[f"zM2_{m}_{q}"] = s
        med = pd.DataFrame(v.T).rolling(SPAN, min_periods=SPAN).median().shift(1).to_numpy().T
        ln["M3"] = np.log(med)
    for k in ln:
        ln[k] = np.where(np.isfinite(ln[k]), ln[k], np.nan)
    for k in z:
        z[k] = np.where(np.isfinite(z[k]), z[k], np.nan)
    return ln, z, scale, lv, e1


def self_check(v, ln, z, n_series=4):
    """Second route: plain scalar loops (and tfs.core.slot_ewma_lagged) for a few series against the
    vectorised estimators. Returns the largest absolute deviation on bars >= 400."""
    worst = {"M0": 0.0, "M1": 0.0, PRIMARY: 0.0, ZPRIMARY: 0.0, "M3": 0.0}
    m, q = (int(x) for x in PRIMARY.split("_")[1:])
    am, aq = 2.0 / (m + 1.0), 2.0 / (q + 1.0)
    for i in np.linspace(0, v.shape[0] - 1, n_series).astype(int):
        keep = ~np.isnan(v[i])
        x = v[i][keep]
        nbar = len(x)
        zero = np.zeros(nbar, dtype=int)
        with np.errstate(divide="ignore", invalid="ignore"):
            lx = np.where(x > 0, np.log(x), np.nan)
            ref = {"M0": np.log(slot_ewma_lagged(x, zero, SPAN)), "M1": slot_ewma_lagged(lx, zero, SPAN)}
        mu, s2, cnt = np.nan, np.nan, 0
        mu_o, z_o = np.full(nbar, np.nan), np.full(nbar, np.nan)
        for t in range(nbar):
            mu_o[t] = mu
            if np.isnan(lx[t]):
                continue
            if np.isnan(mu):
                mu = lx[t]
                continue
            e = lx[t] - mu
            if not np.isnan(s2) and s2 > 0:
                z_o[t] = e / np.sqrt(s2)
            ec = e
            if cnt >= q and s2 > 0:
                lim = CLIP * np.sqrt(s2)
                ec = min(max(e, -lim), lim)
            mu += am * ec
            s2 = ec * ec if np.isnan(s2) else aq * ec * ec + (1.0 - aq) * s2
            cnt += 1
        ref[PRIMARY], ref[ZPRIMARY] = mu_o, z_o
        with np.errstate(divide="ignore"):
            ref["M3"] = np.array([np.log(np.median(x[t - SPAN:t])) if t >= SPAN else np.nan for t in range(nbar)])
        for k in worst:
            got = (z[k] if k.startswith("z") else ln[k])[i][keep]
            both = np.isfinite(ref[k][400:]) & np.isfinite(got[400:])
            if both.any():
                worst[k] = max(worst[k], float(np.max(np.abs(ref[k][400:][both] - got[400:][both]))))
    return {k: float(f"{x:.3g}") for k, x in worst.items()}


# --------------------------------------------------------------------------- claim (a): arithmetic
def claim_a_synthetic(seed):
    """Lift of each reference after ONE day of 10x volume, by running the estimator code on a
    simulated log-normal series with and without the spike (same noise). sd of ln V = 0.25, 0.40, 0.60."""
    out = {"algebra": {"M0_lift_pct": rd(100 * (2 / 51) * 9, 2), "M1_lift_pct": rd(100 * (np.exp(np.log(10) * 2 / 51) - 1), 2),
                       "M2_lift_pct_if_s_0.25": rd(100 * (np.exp(0.75 * 2 / 51) - 1), 2),
                       "M2_lift_pct_if_s_0.40": rd(100 * (np.exp(1.2 * 2 / 51) - 1), 2),
                       "M2_lift_pct_if_s_0.60": rd(100 * (np.exp(1.8 * 2 / 51) - 1), 2),
                       "M0_bars_until_lift_below_10pct": int(np.ceil(np.log(0.353 / 0.10) / -np.log(1 - 2 / 51))),
                       "M0_bars_until_lift_below_5pct": int(np.ceil(np.log(0.353 / 0.05) / -np.log(1 - 2 / 51)))},
           "simulated": {}}
    rng = np.random.default_rng(seed)
    nser, nbar, t0 = 400, 900, 700
    for sd in (0.25, 0.40, 0.60):
        base = np.exp(rng.normal(0.0, sd, (nser, nbar)))
        spk = base.copy()
        # the spike day is 10x the level the shipped reference shows on that day
        ref = ewma_lagged(base, SPAN)[:, t0]
        spk[:, t0] = 10.0 * ref
        ln_b, _, _, _, _ = all_estimators(base)
        ln_s, _, _, _, _ = all_estimators(spk)
        o = {}
        for k in ("M0", "M1", PRIMARY, "M2_50_50", "M3", "X_M0cap"):
            lift = np.exp(ln_s[k] - ln_b[k]) - 1.0
            o[k] = {f"lift_pct_k{j}": rd(100 * lift[:, t0 + j].mean(), 2) for j in (1, 5, 10, 20, 30, 50)}
        out["simulated"][f"sd_{sd:.2f}"] = o
    return out


def spx_check():
    """The author's sanity check: median of volume / EWMA(volume) on the bundled SPX index."""
    out = {}
    for name in ("SPX", "NASDAQ", "GOOG"):
        try:
            d = load_bundled(name)
        except Exception as exc:                                  # bundled data not installed
            out[name] = {"error": str(exc)[:80]}
            continue
        rv = volume_flow_v2(d)["rvol"].to_numpy()[400:]
        rv = rv[np.isfinite(rv)]
        out[name] = {"bars": int(len(rv)), "median_rvol": rd(np.median(rv)), "mean_rvol": rd(rv.mean()),
                     "sd_ln_rvol": rd(np.log(rv[rv > 0]).std())}
    return out


# --------------------------------------------------------------------------- one set
def run_set(name, panel_dir, seed):
    rng = np.random.default_rng(seed + SEED_OFFSET[name])
    d = pd.read_parquet(pathlib.Path(panel_dir) / f"panel_{name}.parquet", columns=COLS)
    tk, ti = np.unique(d["ticker"].to_numpy(), return_inverse=True)
    t = d["t"].to_numpy().astype(np.int64)
    nb = int(t.max()) + 1

    def grid(col, fill=np.nan, dtype=float):
        g = np.full((len(tk), nb), fill, dtype=dtype)
        g[ti, t] = d[col].to_numpy()
        return g

    v = grid("volume")
    ln, z, scale, lv, e1 = all_estimators(v)
    ev_panel, evalg = grid("ev"), grid("eval", False, bool)
    month = grid("month", -1, np.int64)
    with np.errstate(invalid="ignore", divide="ignore"):
        m0_dev = np.nanmax(np.abs(np.exp(ln["M0"]) / ev_panel - 1.0)[evalg])
    ok = evalg & (v > 0)
    n_eval, n_zero = int(evalg.sum()), int((evalg & ~(v > 0)).sum())
    for k in EST:
        ok &= np.isfinite(ln[k])
    for k in ZEST:
        ok &= np.isfinite(z[k])
    si = np.nonzero(ok)[0]                       # stock index of each analysis row
    mth = month[ok]
    lr = {k: (lv - ln[k])[ok] for k in EST}      # ln(V / normal)
    zz = {k: z[k][ok] for k in ZEST}
    n = int(ok.sum())
    nstk = len(tk)
    cnt = np.bincount(si, minlength=nstk).astype(float)
    big = cnt >= MIN_STOCK_ROWS
    stock_years = n / 252.0
    out = {"stocks": int(nstk), "eval_rows": n_eval, "analysis_rows": n, "eval_rows_zero_volume": n_zero,
           "eval_rows_dropped_other": n_eval - n_zero - n, "stock_years": rd(stock_years, 1),
           "stocks_with_min_rows": int(big.sum()),
           "check_M0_vs_panel_ev_max_rel_dev_on_eval": float(f"{m0_dev:.3g}"),
           "check_scalar_loops_max_abs_dev": self_check(v, ln, z)}

    # ---------------- C1 forecast accuracy of ln V
    c1 = {}
    a0, q0 = np.abs(lr["M0"]), lr["M0"] ** 2
    for k in EST:
        e = lr[k]
        med = np.median(e)
        o = {"mae": rd(np.abs(e).mean()), "rmse": rd(np.sqrt((e * e).mean())), "mean_err": rd(e.mean()),
             "median_err": rd(med), "mae_centred": rd(np.abs(e - med).mean()), "sd_err": rd(e.std())}
        if k != "M0":
            o["mae_minus_M0"] = bmean(f"C1 {name} MAE {k}-M0", np.abs(e) - a0, mth, rng, 100)
            o["mse_minus_M0"] = bmean(f"C1 {name} MSE {k}-M0", e * e - q0, mth, rng, 100)
            o["mae_centred_minus_M0"] = bmean(f"C1 {name} centred MAE {k}-M0",
                                              np.abs(e - med) - np.abs(lr["M0"] - np.median(lr["M0"])), mth, rng, 100)
        c1[k] = o
    out["C1_forecast"] = c1

    # ---------------- C2 centring and shape
    c2 = {"normal_benchmark": {"p_z_ge_2_pct": rd(100 * P_NORM_2, 3), "p_z_ge_3_pct": rd(100 * P_NORM_3, 3)},
          "ratio": {}, "z": {}}
    for k in EST:
        e = lr[k]
        r = np.exp(e)
        smed = pd.Series(e).groupby(si).median().reindex(range(nstk)).to_numpy()
        smed = np.exp(smed[big])
        o = {"median": rd(np.median(r)), "mean": rd(r.mean()),
             "p_ge_2_pct": rd(100 * (r >= 2).mean(), 3), "p_ge_3_pct": rd(100 * (r >= 3).mean(), 3),
             "p_le_0.6_pct": rd(100 * (r <= 0.6).mean(), 3), "p_le_0.5_pct": rd(100 * (r <= 0.5).mean(), 3),
             "per_year_ge_2": rd(252 * (r >= 2).mean(), 2), "per_year_ge_3": rd(252 * (r >= 3).mean(), 2),
             "multiple_matching_M0_2x_frequency": rd(np.exp(np.quantile(e, 1 - (lr["M0"] >= np.log(2)).mean())), 3),
             "multiple_matching_M0_3x_frequency": rd(np.exp(np.quantile(e, 1 - (lr["M0"] >= np.log(3)).mean())), 3),
             "multiple_matching_M0_0.6x_frequency": rd(np.exp(np.quantile(e, (lr["M0"] <= np.log(0.6)).mean())), 3),
             "skew_ln_ratio": rd(sps.skew(e)), "stock_median": pct(smed),
             "share_stocks_median_below_1_pct": rd(100 * (smed < 1).mean(), 1),
             "share_stocks_median_0.80_to_0.90_pct": rd(100 * ((smed >= 0.80) & (smed <= 0.90)).mean(), 1),
             "share_stocks_median_below_0.80_pct": rd(100 * (smed < 0.80).mean(), 1)}
        if k in ("M0", "M1", PRIMARY, "M3", "X_M0cap"):
            o["median_ci"] = boot_median_ratio(f"C2 {name} median ratio {k}", e, mth, rng)
        if k in ("M0", PRIMARY):
            o["p_ge_2_ci"] = bmean(f"C2 {name} P(ratio>=2) {k}", 100.0 * (r >= 2), mth, rng)
            o["p_ge_3_ci"] = bmean(f"C2 {name} P(ratio>=3) {k}", 100.0 * (r >= 3), mth, rng)
            o["p_le_0.6_ci"] = bmean(f"C2 {name} P(ratio<=0.6) {k}", 100.0 * (r <= 0.6), mth, rng)
        c2["ratio"][k] = o
    for k in ZEST:
        x = zz[k]
        o = {"mean": rd(x.mean()), "sd": rd(x.std()), "median": rd(np.median(x)), "skew": rd(sps.skew(x)),
             "excess_kurtosis": rd(sps.kurtosis(x)),
             "p_ge_2_pct": rd(100 * (x >= 2).mean(), 3), "p_ge_3_pct": rd(100 * (x >= 3).mean(), 3),
             "p_le_-2_pct": rd(100 * (x <= -2).mean(), 3), "p_le_-3_pct": rd(100 * (x <= -3).mean(), 3),
             "per_year_ge_2": rd(252 * (x >= 2).mean(), 2), "per_year_ge_3": rd(252 * (x >= 3).mean(), 2),
             "ratio_to_normal_ge_2": rd((x >= 2).mean() / P_NORM_2, 2),
             "ratio_to_normal_ge_3": rd((x >= 3).mean() / P_NORM_3, 2),
             "z_matching_M0_2x_frequency": rd(np.quantile(x, 1 - (lr["M0"] >= np.log(2)).mean()), 3),
             "z_matching_M0_3x_frequency": rd(np.quantile(x, 1 - (lr["M0"] >= np.log(3)).mean()), 3)}
        if k in ("zM1", ZPRIMARY, ZSLOW):
            o["mean_ci"] = bmean(f"C2 {name} mean {k}", x, mth, rng)
            o["p_ge_2_ci"] = bmean(f"C2 {name} P({k}>=2)", 100.0 * (x >= 2), mth, rng)
            o["p_ge_3_ci"] = bmean(f"C2 {name} P({k}>=3)", 100.0 * (x >= 3), mth, rng)
        c2["z"][k] = o
    sm = pd.Series(d["spy_rvol"].to_numpy(), index=d["date"].to_numpy())
    sm = sm[~sm.index.duplicated()].dropna()
    c2["spy_rvol_by_date"] = {"dates": int(len(sm)), "median": rd(sm.median()) if len(sm) else None,
                              "mean": rd(sm.mean()) if len(sm) else None}
    out["C2_centring"] = c2

    # ---------------- C3 comparability across stocks
    e1a = e1[ok]
    s_mean = np.bincount(si, weights=e1a, minlength=nstk) / np.maximum(cnt, 1)
    sd_stock = np.sqrt(np.maximum(np.bincount(si, weights=e1a * e1a, minlength=nstk) / np.maximum(cnt, 1) - s_mean ** 2, 0))
    g1 = pd.Series(e1a).groupby(si)
    q25, q75 = (g1.quantile(q).reindex(range(nstk)).to_numpy() for q in (0.25, 0.75))
    sd_rob = (q75 - q25) / 1.349
    s_run_med = pd.Series(scale[ZPRIMARY][ok]).groupby(si).median().reindex(range(nstk)).to_numpy()
    pre = np.where((np.arange(nb)[None, :] >= 100) & (np.arange(nb)[None, :] < 400), e1, np.nan)
    with np.errstate(invalid="ignore"):
        sd_pre = np.nanstd(pre, axis=1)
    f0 = (lr["M0"] >= np.log(2)).astype(float)
    f0_3 = (lr["M0"] >= np.log(3)).astype(float)
    fg = (lr[PRIMARY] >= np.log(2)).astype(float)
    fz = (zz[ZPRIMARY] >= 2).astype(float)
    fz3 = (zz[ZPRIMARY] >= 3).astype(float)
    fz1 = (zz["zM1"] >= 2).astype(float)
    fzs = (zz[ZSLOW] >= 2).astype(float)
    fgr = (lr[PRIMARY] >= np.log(REBASED)).astype(float)
    freq = {key: np.bincount(si, weights=f, minlength=nstk) / np.maximum(cnt, 1)
            for key, f in (("M0_ge_2x", f0), ("M0_ge_3x", f0_3), (f"{PRIMARY}_ge_2x", fg), (f"{ZPRIMARY}_ge_2", fz),
                           (f"{ZPRIMARY}_ge_3", fz3), ("zM1_ge_2", fz1), (f"{ZSLOW}_ge_2", fzs),
                           (f"{PRIMARY}_ge_{REBASED:g}x", fgr), ("M3_ge_2x", (lr["M3"] >= np.log(2)).astype(float)))}
    c3 = {"sd_ln_volume_innovation_across_stocks": dist(sd_stock[big]),
          "robust_sd_iqr_across_stocks": dist(sd_rob[big]),
          "median_running_s_primary_across_stocks": dist(s_run_med[big]),
          "zV_2_as_multiple_of_normal_exp_2s_across_stocks": dist(np.exp(2.0 * s_run_med[big])),
          "zV_2_as_multiple_of_normal_pooled_rows": pct(np.exp(2.0 * scale[ZPRIMARY][ok]), (1, 5, 25, 50, 75, 95, 99)),
          "sd_pre_eval_bars_100_399_across_stocks": dist(sd_pre[big]),
          "spearman_sd_pre_vs_sd_eval": rd(sps.spearmanr(sd_pre[big], sd_stock[big], nan_policy="omit").statistic, 3),
          "implied_z_of_2x_ln2_over_sd": dist(np.log(2) / sd_stock[big]),
          "share_stocks_sd_le_0.25_pct": rd(100 * (sd_stock[big] <= 0.25).mean(), 1),
          "share_stocks_sd_ge_0.60_pct": rd(100 * (sd_stock[big] >= 0.60).mean(), 1),
          "share_stocks_robust_sd_le_0.25_pct": rd(100 * (sd_rob[big] <= 0.25).mean(), 1),
          "share_stocks_robust_sd_ge_0.60_pct": rd(100 * (sd_rob[big] >= 0.60).mean(), 1),
          "frequency_pct_across_stocks": {}, "by_sd_pre_quintile": {}}
    for key, f in freq.items():
        x = 100 * f[big]
        p = f[big].mean()
        o = dist(x)
        o["per_year_p5_p50_p95"] = [rd(2.52 * np.percentile(x, q), 2) for q in (5, 50, 95)]
        o["p95_over_p5"] = rd(np.percentile(x, 95) / np.percentile(x, 5), 2) if np.percentile(x, 5) > 0 else None
        o["cv_expected_from_binomial_noise_alone"] = rd(np.sqrt(np.mean((1 - p) / (cnt[big] * p))), 3) if p > 0 else None
        o["cv_in_excess_of_noise"] = (rd(np.sqrt(max(o["cv"] ** 2 - o["cv_expected_from_binomial_noise_alone"] ** 2, 0.0)), 3)
                                      if p > 0 else None)
        o["spearman_with_sd_eval"] = rd(sps.spearmanr(sd_stock[big], f[big]).statistic, 3)
        o["spearman_with_robust_sd_eval"] = rd(sps.spearmanr(sd_rob[big], f[big]).statistic, 3)
        o["spearman_with_sd_pre"] = rd(sps.spearmanr(sd_pre[big], f[big], nan_policy="omit").statistic, 3)
        c3["frequency_pct_across_stocks"][key] = o
    edges = np.nanquantile(sd_pre[big], [0.2, 0.4, 0.6, 0.8])
    qs = np.where(big & np.isfinite(sd_pre), np.searchsorted(edges, sd_pre, side="right"), -1)   # 0 = calmest, 4 = most erratic
    qrow = qs[si]
    for key, f in (("M0_ge_2x", f0), (f"{PRIMARY}_ge_2x", fg), (f"{ZPRIMARY}_ge_2", fz), ("zM1_ge_2", fz1),
                   (f"{ZSLOW}_ge_2", fzs), (f"{PRIMARY}_ge_{REBASED:g}x", fgr)):
        o = {"pct_by_quintile_low_to_high_sd": [rd(100 * f[qrow == j].mean(), 3) for j in range(5)],
             "sd_pre_quintile_medians": [rd(np.median(sd_pre[qs == j]), 3) for j in range(5)]}
        o["top_minus_bottom_pct_points"] = bdiff(f"C3 {name} {key} top-bottom sd quintile", 100 * f[qrow == 4],
                                                 mth[qrow == 4], 100 * f[qrow == 0], mth[qrow == 0], rng)
        lo_, hi_ = f[qrow == 0].mean(), f[qrow == 4].mean()
        o["top_over_bottom_ratio"] = rd(hi_ / lo_, 2) if lo_ > 0 else None
        c3["by_sd_pre_quintile"][key] = o
    # the reviewer's example in his own terms: stocks grouped by their sd of log volume (same period)
    c3["by_sd_eval_bucket"] = []
    for lo_, hi_ in SD_BUCKETS:
        mk = big & (sd_stock >= lo_) & (sd_stock < hi_)
        rows = mk[si]
        if not mk.any():
            c3["by_sd_eval_bucket"].append({"sd_from": lo_, "sd_to": hi_, "stocks": 0})
            continue
        c3["by_sd_eval_bucket"].append({
            "sd_from": lo_, "sd_to": hi_, "stocks": int(mk.sum()), "rows": int(rows.sum()),
            "median_sd": rd(np.median(sd_stock[mk]), 3), "ln2_over_median_sd": rd(np.log(2) / np.median(sd_stock[mk]), 2),
            "pct_M0_ge_2x": rd(100 * f0[rows].mean(), 2), "one_M0_2x_day_every_n_bars": rd(1 / max(f0[rows].mean(), 1e-9), 1),
            f"pct_{PRIMARY}_ge_{REBASED:g}x": rd(100 * fgr[rows].mean(), 2),
            f"pct_{ZPRIMARY}_ge_2": rd(100 * fz[rows].mean(), 2), f"pct_{ZSLOW}_ge_2": rd(100 * fzs[rows].mean(), 2),
            "median_rvol_M0": rd(np.exp(np.median(lr["M0"][rows])), 3)})
    named = {}
    for nm in NAMED:
        j = np.flatnonzero(tk == nm)
        if len(j) and big[j[0]]:
            j = j[0]
            named[nm] = {"sd_ln_volume": rd(sd_stock[j], 3), "robust_sd": rd(sd_rob[j], 3),
                         "ln2_over_sd": rd(np.log(2) / sd_stock[j], 2), "ln2_over_robust_sd": rd(np.log(2) / sd_rob[j], 2),
                         "median_rvol_M0": rd(np.exp(np.median(lr["M0"][si == j])), 3),
                         "pct_days_M0_ge_2x": rd(100 * freq["M0_ge_2x"][j], 2),
                         f"pct_days_{ZPRIMARY}_ge_2": rd(100 * freq[f"{ZPRIMARY}_ge_2"][j], 2), "rows": int(cnt[j])}
    c3["named_stocks"] = named
    order = np.argsort(np.where(big, sd_stock, np.nan))
    order = order[: int(big.sum())]
    c3["lowest_sd_stocks"] = [{"ticker": str(tk[j]), "sd": rd(sd_stock[j], 3), "pct_days_M0_ge_2x": rd(100 * freq["M0_ge_2x"][j], 2),
                               f"pct_days_{ZPRIMARY}_ge_2": rd(100 * freq[f"{ZPRIMARY}_ge_2"][j], 2)} for j in order[:5]]
    c3["highest_sd_stocks"] = [{"ticker": str(tk[j]), "sd": rd(sd_stock[j], 3), "pct_days_M0_ge_2x": rd(100 * freq["M0_ge_2x"][j], 2),
                                f"pct_days_{ZPRIMARY}_ge_2": rd(100 * freq[f"{ZPRIMARY}_ge_2"][j], 2)} for j in order[-5:]]
    out["C3_comparability"] = c3

    # ---------------- C4 bias after spikes
    with np.errstate(invalid="ignore"):
        spike = (lv - ln["M3"]) >= np.log(SPIKE_MULT)
        spike10 = (lv - ln["M3"]) >= np.log(10.0)
    pos = np.arange(nb)[None, :]

    def bars_since(flag):
        last = np.maximum.accumulate(np.where(flag, pos, -1), axis=1)
        last = np.concatenate([np.full((len(tk), 1), -1), last[:, :-1]], axis=1)
        return np.where(last >= 0, pos - last, 10 ** 6)

    age = bars_since(spike)[ok]
    age10 = bars_since(spike10)[ok]
    sp_ok = spike & ok
    c4 = {"spikes_on_analysis_rows": int(sp_ok.sum()), "spikes_per_stock_year": rd(sp_ok.sum() / stock_years, 3),
          "spikes_10x_on_analysis_rows": int((spike10 & ok).sum()),
          "spikes_10x_per_stock_year": rd((spike10 & ok).sum() / stock_years, 3),
          "share_rows_within_30_after_spike_pct": rd(100 * (age <= KMAX).mean(), 2),
          "share_stocks_with_a_spike_pct": rd(100 * (np.bincount(si, weights=spike[ok].astype(float), minlength=nstk)[big] > 0).mean(), 1),
          "median_spike_multiple_of_M3": rd(np.exp(np.median((lv - ln["M3"])[sp_ok])), 2) if sp_ok.any() else None,
          "median_spike_multiple_of_M0": rd(np.exp(np.median((lv - ln["M0"])[sp_ok])), 2) if sp_ok.any() else None,
          "reference_lift_next_bar_pct": {}, "profile": {}, "windows": {}, "windows_10x": {}}
    c4["reference_lift_next_bar_pct_10x"] = {}
    for key, flag in (("reference_lift_next_bar_pct", sp_ok), ("reference_lift_next_bar_pct_10x", spike10 & ok)):
        for k in C4_EST:
            step = (ln[k][:, 1:] - ln[k][:, :-1])[flag[:, :-1]]
            step = step[np.isfinite(step)]
            c4[key][k] = {"mean": rd(100 * (np.exp(step).mean() - 1), 2),
                          "median": rd(100 * (np.exp(np.median(step)) - 1), 2), "n": int(len(step))} if len(step) else {}
    dm = {}
    agec = np.minimum(age, KMAX + 1)
    nk = np.bincount(agec, minlength=KMAX + 2)

    def demean(x):
        return x - (np.bincount(si, weights=x, minlength=nstk) / np.maximum(cnt, 1))[si]

    for k in C4_EST + C4_EXTRA:
        dm[k] = demean(lr[k])
        prof = np.bincount(agec, weights=dm[k], minlength=KMAX + 2)
        c4["profile"][k] = [rd(prof[j] / nk[j]) if nk[j] else None for j in range(1, KMAX + 1)]
    c4["profile_n"] = [int(x) for x in nk[1:KMAX + 1]]
    # the scale of the z-scores after a spike: ln(s) minus the stock's own mean of ln(s)
    c4["scale_profile_ln_s_minus_stock_mean"] = {}
    for k in (ZPRIMARY, "zM2_50_50", ZSLOW, "zM1"):
        ds = demean(np.log(scale[k][ok]))
        c4["scale_profile_ln_s_minus_stock_mean"][k] = {
            f"k{lo}-{hi}": rd(ds[(age >= lo) & (age <= hi)].mean()) for lo, hi in WINDOWS}
    for lo, hi in WINDOWS:
        m = (age >= lo) & (age <= hi)
        m10 = (age10 >= lo) & (age10 <= hi)
        tag = f"k{lo}-{hi}"
        w = {"n": int(m.sum())}
        w10 = {"n": int(m10.sum())}
        for k in C4_EST:
            w[k] = bmean(f"C4 {name} {tag} {k}", dm[k][m], mth[m], rng, 100) if m.any() else None
            w10[k] = rd(dm[k][m10].mean()) if m10.any() else None
            if k != "M0" and m.any():
                w[f"{k}_minus_M0"] = bmean(f"C4 {name} {tag} {k}-M0", dm[k][m] - dm["M0"][m], mth[m], rng, 100)
        w["understatement_M0_pct"] = rd(100 * (np.exp(w["M0"]["est"]) - 1), 2) if w.get("M0") else None
        c4["windows"][tag] = w
        c4["windows_10x"][tag] = w10
    out["C4_after_spikes"] = c4

    # ---------------- C5 disagreement of the flags
    b0, bz, bg, bs, br = f0 > 0, fz > 0, fg > 0, fzs > 0, fgr > 0

    def table(a, b, la, lb):
        both, oa, ob = int((a & b).sum()), int((a & ~b).sum()), int((~a & b).sum())
        return {f"n_{la}": int(a.sum()), f"n_{lb}": int(b.sum()), "both": both, f"only_{la}": oa, f"only_{lb}": ob,
                "jaccard": rd(both / max(both + oa + ob, 1), 3),
                f"share_of_{la}_flags_kept_pct": rd(100 * both / max(a.sum(), 1), 1),
                f"share_of_{lb}_flags_also_{la}_pct": rd(100 * both / max(b.sum(), 1), 1),
                "disagree_pct_of_bars": rd(100 * (oa + ob) / n, 3),
                "disagree_per_stock_year": rd((oa + ob) / stock_years, 2),
                f"only_{la}_per_stock_year": rd(oa / stock_years, 2), f"only_{lb}_per_stock_year": rd(ob / stock_years, 2)}

    c5 = {"M0_2x_vs_zV_2": table(b0, bz, "M0_2x", "zV_2"),
          "M0_2x_vs_zSlow_2": table(b0, bs, "M0_2x", "zSlow_2"),
          "M0_2x_vs_primary_2x": table(b0, bg, "M0_2x", "M2_2x"),
          "M0_2x_vs_primary_rebased": table(b0, br, "M0_2x", "M2_rebased"),
          "M0_3x_vs_zV_3": table(f0_3 > 0, fz3 > 0, "M0_3x", "zV_3")}
    c5["M0_2x_vs_zV_2"]["disagree_ci_pct_of_bars"] = bmean(f"C5 {name} disagree M0 2x vs zV 2", 100.0 * (b0 != bz), mth, rng)
    # Flag rates by bars since the last spike. Stocks with erratic volume have more spikes AND a higher
    # base rate for a fixed multiple, so the pooled rates are confounded by composition. The contrast
    # reported with an interval is within stock: flag minus the same stock's rate on its calm rows
    # (no spike in the previous 30 bars); "observed_over_expected" is the same thing as a ratio.
    calm = age > KMAX
    ncalm = np.bincount(si, weights=calm.astype(float), minlength=nstk)
    has_calm = (ncalm >= 100)[si]
    rules = {"M0_2x": b0, "M2_2x": bg, "M2_rebased": br, "M3_2x": lr["M3"] >= np.log(2), "zV_2": bz, "zSlow_2": bs,
             "zM1_2": fz1 > 0}
    base = {r: (np.bincount(si, weights=(b & calm).astype(float), minlength=nstk) / np.maximum(ncalm, 1))[si]
            for r, b in rules.items()}
    c5["flag_rate_by_bars_since_spike"] = {"no_spike_in_last_30_bars": dict(
        rows=int(calm.sum()), **{f"pct_{r}": rd(100 * b[calm].mean(), 3) for r, b in rules.items()})}
    for lo, hi in FLAG_WINDOWS:
        m = (age >= lo) & (age <= hi) & has_calm
        w = {"rows": int(m.sum())}
        for r, b in rules.items():
            if not m.any():
                continue
            w[f"pct_{r}"] = rd(100 * b[m].mean(), 3)
            w[f"pct_{r}_expected_from_own_calm_rate"] = rd(100 * base[r][m].mean(), 3)
            w[f"{r}_observed_over_expected"] = rd(b[m].mean() / base[r][m].mean(), 3) if base[r][m].mean() > 0 else None
            w[f"{r}_minus_own_calm_rate_pct_points"] = bmean(f"C5 {name} P({r}) k{lo}-{hi} - own calm rate",
                                                             100.0 * (b[m] - base[r][m]), mth[m], rng)
        c5["flag_rate_by_bars_since_spike"][f"k{lo}-{hi}"] = w
    c5["disagreement_by_sd_pre_quintile"] = [
        {"quintile": j + 1, "pct_only_M0_2x": rd(100 * (b0 & ~bz)[qrow == j].mean(), 3),
         "pct_only_zV_2": rd(100 * (~b0 & bz)[qrow == j].mean(), 3), "pct_both": rd(100 * (b0 & bz)[qrow == j].mean(), 3),
         "pct_only_M0_2x_vs_zSlow": rd(100 * (b0 & ~bs)[qrow == j].mean(), 3),
         "pct_only_zSlow_2": rd(100 * (~b0 & bs)[qrow == j].mean(), 3)}
        for j in range(5)]
    # the "A" mark (absorption at lows) under each rule: counts only
    zp, ext, ab = grid("z"), grid("ext"), grid("absorb_bottom", False, bool)
    with np.errstate(invalid="ignore"):
        price_leg = (np.abs(zp) <= 0.5) & (ext <= -1.5)
        ab_re = (grid("rvol") >= 2.0) & price_leg
    pl = price_leg[ok]
    c5["absorption_at_lows"] = {
        "published_count_eval": PUBLISHED_ABSORB.get(name), "panel_flag_eval": int((ab & evalg).sum()),
        "recomputed_from_columns_eval": int((ab_re & evalg).sum()), "panel_flag_analysis_rows": int(ab[ok].sum()),
        "with_zV_ge_2": int((bz & pl).sum()), "with_M2_ratio_ge_2": int((bg & pl).sum()),
        "with_zSlow_ge_2": int((bs & pl).sum()), "shipped_and_zSlow": int((ab[ok] & bs & pl).sum()),
        "with_M2_rebased": int((br & pl).sum()), "shipped_and_M2_rebased": int((ab[ok] & br & pl).sum()),
        "shipped_and_zV": int((ab[ok] & bz & pl).sum()), "shipped_and_M2_ratio": int((ab[ok] & bg & pl).sum()),
        "per_stock_year_shipped": rd(ab[ok].sum() / stock_years, 3), "per_stock_year_zV": rd((bz & pl).sum() / stock_years, 3)}
    out["C5_disagreement"] = c5
    return out


# --------------------------------------------------------------------------- main
def headline(res):
    h = {}
    for name, s in res["sets"].items():
        c1, c2, c3, c4, c5 = (s[k] for k in ("C1_forecast", "C2_centring", "C3_comparability", "C4_after_spikes",
                                              "C5_disagreement"))
        fq = c3["frequency_pct_across_stocks"]
        h[name] = {
            "median_rvol_M0": c2["ratio"]["M0"]["median_ci"], "median_ratio_primary": c2["ratio"][PRIMARY]["median_ci"],
            "share_stocks_median_M0_below_1_pct": c2["ratio"]["M0"]["share_stocks_median_below_1_pct"],
            "mae": {k: c1[k]["mae"] for k in ("M0", "M1", PRIMARY, "M3", "X_M0cap")},
            "mae_centred": {k: c1[k]["mae_centred"] for k in ("M0", "M1", PRIMARY, "M3", "X_M0cap")},
            "mae_primary_minus_M0": c1[PRIMARY]["mae_minus_M0"],
            "zV_primary": {k: c2["z"][ZPRIMARY][k] for k in ("mean", "sd", "skew", "p_ge_2_pct", "p_ge_3_pct")},
            "sd_ln_volume_p5_p50_p95": [c3["sd_ln_volume_innovation_across_stocks"][k] for k in ("p5", "p50", "p95")],
            "freq_M0_2x_p5_p50_p95_cv": [fq["M0_ge_2x"][k] for k in ("p5", "p50", "p95", "cv")],
            "freq_zV_2_p5_p50_p95_cv": [fq[f"{ZPRIMARY}_ge_2"][k] for k in ("p5", "p50", "p95", "cv")],
            "spearman_freq_vs_sd_pre": {"M0_2x": fq["M0_ge_2x"]["spearman_with_sd_pre"],
                                        "zV_2": fq[f"{ZPRIMARY}_ge_2"]["spearman_with_sd_pre"]},
            "post_spike_k1_5": {k: c4["windows"]["k1-5"][k]["est"] for k in C4_EST},
            "post_spike_k6_10": {k: c4["windows"]["k6-10"][k]["est"] for k in C4_EST},
            "post_spike_k11_20": {k: c4["windows"]["k11-20"][k]["est"] for k in C4_EST},
            "post_spike_k21_30": {k: c4["windows"]["k21-30"][k]["est"] for k in C4_EST},
            "reference_lift_after_10x_day_median_pct": {k: v.get("median") for k, v in c4["reference_lift_next_bar_pct_10x"].items()},
            "post_spike_10x_k11_20": {k: v for k, v in c4["windows_10x"]["k11-20"].items()},
            "flag_rate_k11_30_over_own_calm_rate": {
                r_: c5["flag_rate_by_bars_since_spike"]["k11-30"].get(f"{r_}_observed_over_expected")
                for r_ in ("M0_2x", "M2_2x", "M2_rebased", "M3_2x", "zV_2", "zSlow_2", "zM1_2")},
            "pct_days": {"M0_ge_2x": c2["ratio"]["M0"]["p_ge_2_pct"], f"{PRIMARY}_ge_2x": c2["ratio"][PRIMARY]["p_ge_2_pct"],
                         "zV_ge_2": c2["z"][ZPRIMARY]["p_ge_2_pct"], "zSlow_ge_2": c2["z"][ZSLOW]["p_ge_2_pct"],
                         "M0_le_0.6": c2["ratio"]["M0"]["p_le_0.6_pct"], f"{PRIMARY}_le_0.6": c2["ratio"][PRIMARY]["p_le_0.6_pct"]},
            "top_over_bottom_sd_quintile": {k: v["top_over_bottom_ratio"] for k, v in c3["by_sd_pre_quintile"].items()},
            "zV_2_as_multiple_p5_p50_p95": [c3["zV_2_as_multiple_of_normal_exp_2s_across_stocks"][k] for k in ("p5", "p50", "p95")],
            "share_M0_2x_flags_kept_by_zV_pct": c5["M0_2x_vs_zV_2"]["share_of_M0_2x_flags_kept_pct"],
            "flags_jaccard_M0_2x_vs_zV_2": c5["M0_2x_vs_zV_2"]["jaccard"],
            "flags_disagree_per_stock_year": c5["M0_2x_vs_zV_2"]["disagree_per_stock_year"],
            "absorption_counts": {k: c5["absorption_at_lows"][k] for k in ("panel_flag_analysis_rows", "with_zV_ge_2", "shipped_and_zV")}}
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=DEFAULT_PANEL)
    ap.add_argument("--sets", nargs="*", default=list(SET_ORDER))
    ap.add_argument("--out", default=str(ROOT / "results" / "e13_normal_volume_estimators.json"))
    ap.add_argument("--seed", type=int, default=SEED)
    a_ = ap.parse_args()
    t0 = time.time()
    res = {"experiment": "e13_normal_volume_estimators", "seed": a_.seed, "n_boot": e05.N_BOOT, "panel": a_.panel,
           "primary": PRIMARY, "slow_scale_version": ZSLOW, "rebased_multiple": REBASED,
           "estimators": EST, "z_versions": ZEST,
           "development_notes_set_A": {
               "primary_choice": "mu span 50 = the shipped span, so the comparison with M0 isolates the definition. "
                                 "On A the span of s changed nothing in the reference (MAE 0.3063 vs 0.3064) and span "
                                 "100 gave a z-score slightly closer to unit sd (1.059 vs 1.075), so M2_50_100.",
               "slow_scale": "M2_50_250 added on A after the scale feedback was seen; run once elsewhere.",
               "rebased_multiple": "2.2 = the multiple of M2 whose pooled frequency on A equals 2x M0 (2.215), rounded.",
               "tried_on_A_and_dropped": "scales that ignore upward moves (downside-only EWMA; clip at 2 s or 1.5 s for "
                                         "the scale only), spans 100 and 250, frequency-matched thresholds. They traded "
                                         "post-spike sensitivity (flag rate 11-30 bars after a spike at 0.61-0.78 of the "
                                         "stock's calm rate) against cross-stock comparability (CV of the per-stock "
                                         "frequency 0.20-0.33 against 0.17 for the z-score). No clear gain; not kept."},
           "definitions": {
               "analysis_rows": "eval rows with volume > 0 and every estimator finite",
               "err": "ln(volume) - ln(normal), normal from bars <= t-1",
               "sd_ln_volume": "per-stock sd of the M1 innovation ln V - EWMA50(ln V) on analysis rows",
               "sd_pre": "the same sd on bars 100..399 of each stock (before the evaluation window)",
               "spike": f"volume >= {SPIKE_MULT:g} x M3 (median of the previous 50 bars)",
               "C4": "mean over rows k bars after the last spike of ln(V/normal) minus the stock's own mean",
               "units": "rates in percent of bars; x 2.52 = events per stock per year",
               "intervals": "95%, month-block bootstrap, 2000 resamples",
               "independence": "A = development. B shares A's dates. DJ lies inside LH. MS is new."},
           "claim_a_arithmetic": claim_a_synthetic(a_.seed), "spx_sanity_check": spx_check(), "sets": {}}
    for name in SET_ORDER:
        if name not in a_.sets:
            continue
        t1 = time.time()
        res["sets"][name] = run_set(name, a_.panel, a_.seed)
        print(f"{name}: {res['sets'][name]['analysis_rows']} rows, {time.time() - t1:.0f}s", flush=True)
    res["headline"] = headline(res)
    res["n_comparisons"] = len(COMPARISONS)
    res["comparisons"] = COMPARISONS
    res["seconds"] = round(time.time() - t0)
    pathlib.Path(a_.out).write_text(json.dumps(res, indent=1))
    print("wrote", a_.out, f"({len(COMPARISONS)} intervals, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
