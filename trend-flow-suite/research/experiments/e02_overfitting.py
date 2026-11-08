"""E02 - What is a brute-force-optimised backtest actually worth?

Question (Nov 2026): "test the indicator on the S&P, NASDAQ, DJI, Russell 2000 thousands or
millions of times until we get the best backtest". This experiment does exactly that on the data
available offline (S&P 500 and NASDAQ Composite, daily 1999-2018) and measures the result.

Part 1  Theory: expected best Sharpe from pure luck vs number of trials and years of data.
Part 2  Real search: 5,280 VFI-rule variants (length x dead band x volume cap x smoothing x rule).
        In-sample (IS) = mid-2001..2009 (two bear markets), out-of-sample (OOS) = 2010..2018.
        Reports the IS winner's OOS result, IS/OOS rank correlation, the Probability of Backtest
        Overfitting (CSCV, 16 blocks = 12,870 splits) and the Deflated Sharpe Ratio of the winner.
Part 3  Null world: the identical search on synthetic histories with NO exploitable structure
        (i.i.d. bootstrap of real daily bars: same bar shapes, gaps and volume/return link, but no
        serial dependence). If the real best IS "timing Sharpe" is not unusual relative to the
        null distribution of best IS results, the search found nothing distinguishable from luck.

Run from research/:  python3 -m experiments.e02_overfitting
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from tfs.backtest import long_flat_returns, summary
from tfs.data import load_bundled
from tfs.validation import (deflated_sharpe, effective_trials, expected_max_sr, pbo_cscv, sharpe)

LENGTHS = [20, 30, 40, 50, 65, 80, 100, 130, 160, 200, 250]
COEFS = [0.0, 0.1, 0.2, 0.3, 0.5]
VCOEFS = [1.5, 2.5, 3.5, 5.0]
SMOOTHS = [1, 3, 10]                       # EMA span of the VFI (1 = unsmoothed)
LEVELS = [-5.0, -2.0, 0.0, 2.0, 5.0]       # rule "VFI > level"
MA_LENS = [5, 20, 50]                      # rule "VFI > EMA_n(VFI)"
WARMUP = 560                               # common start: longest length needs ~2x250 bars + EMAs
COST_BPS = 5.0
IS_END, OOS_START = "2009-12-31", "2010-01-01"


def vfi_family_positions(df: pd.DataFrame):
    """Long/flat positions (T x N bool) for every variant, plus labels. Pine-equivalent VFI maths."""
    h, l, c, v = (df[k] for k in ("high", "low", "close", "volume"))
    tp = (h + l + c) / 3.0
    band = (np.log(tp).diff()).rolling(30).std(ddof=0) * c       # cutoff = coef * band
    mf = tp.diff()
    signs = {}
    for k in COEFS:
        s = np.where(mf > k * band, 1.0, np.where(mf < -k * band, -1.0, 0.0))
        s[band.isna().values] = np.nan
        signs[k] = s
    blocks, labels = [], []
    for L in LENGTHS:
        vave = v.rolling(L).mean().shift(1)
        cols, keys = {}, []
        for m in VCOEFS:
            vc = np.minimum(v.values, (vave * m).values)
            for k in COEFS:
                cols[(k, m)] = signs[k] * vc
                keys.append((k, m))
        raw = pd.DataFrame(cols, index=df.index).rolling(L).sum().div(vave.where(vave > 0), axis=0)
        for sm in SMOOTHS:
            vs = raw if sm == 1 else raw.ewm(span=sm, adjust=False).mean()
            arr = vs.values
            for th in LEVELS:
                blocks.append(arr > th)
                labels += [dict(length=L, coef=k, vcoef=m, smooth=sm, rule=f"VFI>{th:g}") for k, m in keys]
            for n in MA_LENS:
                sig = vs.ewm(span=n, adjust=False).mean().values
                blocks.append(arr > sig)
                labels += [dict(length=L, coef=k, vcoef=m, smooth=sm, rule=f"VFI>EMA{n}") for k, m in keys]
    pos = np.hstack(blocks)
    return pos, labels


def iid_bar_bootstrap(df: pd.DataFrame, n_bars: int, rng: np.random.Generator) -> pd.DataFrame:
    """Synthetic history with no serial dependence: resample whole daily bars (relative OHLC and
    relative volume, jointly) with replacement and chain them."""
    pc = df["close"].shift(1)
    rel = pd.DataFrame({"o": df["open"] / pc, "h": df["high"] / pc, "l": df["low"] / pc,
                        "c": df["close"] / pc,
                        "v": df["volume"] / df["volume"].rolling(50).mean().shift(1)}).dropna()
    s = rel.iloc[rng.integers(0, len(rel), n_bars)].to_numpy()
    close = 100.0 * np.cumprod(s[:, 3])
    prev = np.r_[100.0, close[:-1]]
    idx = pd.bdate_range("2000-01-03", periods=n_bars)
    return pd.DataFrame({"open": prev * s[:, 0], "high": prev * s[:, 1], "low": prev * s[:, 2],
                         "close": close, "volume": s[:, 4] * 1e6}, index=idx)


def best_is_timing_sharpe(df: pd.DataFrame, n_is: int) -> float:
    """Max over variants of the IS Sharpe on DETRENDED returns (pure timing skill, no drift credit)."""
    pos, _ = vfi_family_positions(df)
    r = df["close"].pct_change().fillna(0).values
    seg = slice(WARMUP, WARMUP + n_is)
    r_dt = r.copy()
    r_dt[seg] = r[seg] - r[seg].mean()
    R = long_flat_returns(pos, r_dt, COST_BPS)[seg]
    return float(sharpe(R).max())


def theory_table():
    rows = []
    for n in (10, 100, 1_000, 10_000, 100_000, 1_000_000):
        z = expected_max_sr(n)
        rows.append({"trials": n, "E[max z]": round(z, 2),
                     **{f"best_SR_from_luck_{y}y": round(z / np.sqrt(y), 2) for y in (10, 20, 30)}})
    return rows


def run_index(name: str, n_null: int, rng: np.random.Generator) -> dict:
    df = load_bundled(name)
    t0 = time.perf_counter()
    pos, labels = vfi_family_positions(df)
    t_family = time.perf_counter() - t0
    r = df["close"].pct_change().fillna(0).values
    t0 = time.perf_counter()
    R = long_flat_returns(pos, r, COST_BPS)[WARMUP:]
    t_bt = time.perf_counter() - t0
    dates = df.index[WARMUP:]
    is_m = np.asarray(dates <= IS_END)
    oos_m = np.asarray(dates >= OOS_START)
    n = R.shape[1]

    sr_is, sr_oos = sharpe(R[is_m]), sharpe(R[oos_m])
    order = np.argsort(-sr_is)
    best = int(order[0])
    bh_is = summary(r[WARMUP:][is_m])
    bh_oos = summary(r[WARMUP:][oos_m])
    n_eff = effective_trials(R[is_m])
    trial_srs_pp = sr_is / np.sqrt(252)
    dsr_n = deflated_sharpe(R[is_m][:, best], trial_srs_pp, n)
    dsr_eff = deflated_sharpe(R[is_m][:, best], trial_srs_pp, n_eff)
    pbo = pbo_cscv(R, n_blocks=16)

    # Null world (timing skill only)
    n_is = int(is_m.sum())
    real_timing = best_is_timing_sharpe(df.iloc[: WARMUP + n_is], n_is)
    null = [best_is_timing_sharpe(iid_bar_bootstrap(df, WARMUP + n_is, rng), n_is) for _ in range(n_null)]
    p_val = (1 + sum(x >= real_timing for x in null)) / (1 + n_null)

    return {
        "variants": n,
        "eval_period": [str(dates[0].date()), str(dates[-1].date())],
        "is_period": [str(dates[is_m][0].date()), str(dates[is_m][-1].date())],
        "oos_period": [str(dates[oos_m][0].date()), str(dates[oos_m][-1].date())],
        "compute_seconds": {"build_all_variants": round(t_family, 2), "backtest_all_variants": round(t_bt, 2)},
        "buy_hold": {"is": bh_is, "oos": bh_oos},
        "is_winner": {"config": labels[best], "sharpe_is": round(float(sr_is[best]), 3),
                      "sharpe_oos": round(float(sr_oos[best]), 3),
                      "oos_percentile_among_variants": round(100 * float((sr_oos < sr_oos[best]).mean()), 1),
                      "is_summary": summary(R[is_m][:, best]), "oos_summary": summary(R[oos_m][:, best])},
        "top10_is": [{"config": labels[i], "sharpe_is": round(float(sr_is[i]), 3),
                      "sharpe_oos": round(float(sr_oos[i]), 3)} for i in order[:10]],
        "median_sharpe": {"is": round(float(np.median(sr_is)), 3), "oos": round(float(np.median(sr_oos)), 3)},
        "spearman_rank_corr_is_vs_oos": round(float(spearmanr(sr_is, sr_oos)[0]), 3),
        "effective_independent_trials": round(n_eff, 1),
        "deflated_sharpe_is_winner": {"with_all_trials": dsr_n, "with_effective_trials": dsr_eff},
        "pbo_cscv": pbo,
        "null_test": {"real_best_is_timing_sharpe": round(real_timing, 3),
                      "null_best_is_timing_sharpe": [round(x, 3) for x in null],
                      "null_median": round(float(np.median(null)), 3),
                      "null_p90": round(float(np.quantile(null, 0.9)), 3),
                      "p_value": round(p_val, 3), "n_null": n_null},
    }


def main(n_null: int = 100, seed: int = 7):
    rng = np.random.default_rng(seed)
    out = {"theory_best_sharpe_from_luck": theory_table()}
    spx, ndq = load_bundled("SPX"), load_bundled("NASDAQ")
    rr = pd.concat([spx["close"].pct_change(), ndq["close"].pct_change()], axis=1).dropna()
    out["corr_daily_returns_spx_nasdaq"] = round(float(rr.corr().iloc[0, 1]), 3)
    for name in ("SPX", "NASDAQ"):
        out[name] = run_index(name, n_null, rng)
    path = Path(__file__).resolve().parents[1] / "results" / "e02_overfitting.json"
    path.write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
