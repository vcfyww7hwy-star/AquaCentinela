"""E04 - Trend & Setups v1: calibration and smoke test (Nov 2026). NOT a validation.

HISTORICAL: results/e04_trend_setups_smoke.json was produced with engine v1 (commit e13573e).
The engine has since changed (docs/06_validation_lite.md); this script is kept as a record and
no longer reproduces that file.

Checks that the engine behaves as designed on the offline daily data (S&P 500, NASDAQ, GOOG):
  1. calibration: trend score ~ N(0,1) on the same returns with their order shuffled (no trend);
  2. regime behaviour: time in each state, switches per year (whipsaw) vs the VFI's zero line;
  3. illustrative regime test (long when the trend is up) vs buy & hold and 130-day momentum;
  4. setup frequencies and trade statistics with the weekly context filter (and RS vs SPX for GOOG).
Three series in one era: numbers describe behaviour, they are not evidence of an edge (Phase 4).
Run from research/:  python3 -m experiments.e04_trend_setups_smoke
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from tfs.backtest import long_flat_returns, summary
from tfs.data import load_bundled
from tfs.trend import TrendParams, regime, trend_score, trend_setups, weekly_context_dir
from tfs.vfi import vfi

EVAL_START = 300   # skip warm-up bars


def zero_cross_rate(x: pd.Series, years: float) -> float:
    s = np.sign(x.dropna())
    s = s[s != 0]
    return round(float(((s != s.shift(1)).sum() - 1) / years), 1)


def run(name: str, bench: pd.Series | None, rng) -> dict:
    df = load_bundled(name)
    p = TrendParams()
    htf = weekly_context_dir(df, p)
    bclose = None if bench is None else bench.reindex(df.index).ffill().to_numpy()
    f, trades = trend_setups(df, p=p, bench_close=bclose, htf_dir=htf)
    ev = f.iloc[EVAL_START:]
    years = len(ev) / 252
    # 1. calibration
    r = np.diff(np.log(df["close"].to_numpy()))
    shuffled_sd = []
    for _ in range(20):
        lp = np.r_[0.0, np.cumsum(rng.permutation(r))]
        shuffled_sd.append(np.std(trend_score(lp, p.sigma_span)[EVAL_START:]))
    # 2. regime behaviour
    d = ev["dir"]
    switches = int((d != d.shift(1)).iloc[1:].sum())
    old = vfi(df, length=130)["vfi"].iloc[EVAL_START:]
    # 3. illustrative regime test (decide at close t, hold over t+1; 5 bp per switch)
    mret = df["close"].pct_change().fillna(0).to_numpy()[EVAL_START:]
    mom = (np.log(df["close"]).diff(130) > 0).astype(int).to_numpy()[EVAL_START:]
    rules = {"buy_and_hold": np.ones(len(ev)), "trend_up_only": (d == 1).astype(int).to_numpy(),
             "trend_not_down": (d >= 0).astype(int).to_numpy(), "momentum_130": mom,
             "vfi_above_zero": (old > 0).astype(int).to_numpy()}
    illus = {k: {**summary(long_flat_returns(v, mret, 5.0).ravel()),
                 "switches_per_year": round(float(np.abs(np.diff(v)).sum()) / years, 1)} for k, v in rules.items()}
    # 4. setups
    tr = trades[trades.entry_bar >= EVAL_START] if len(trades) else trades
    by_setup = {}
    for sid, name_s in ((1, "S1_pullback"), (2, "S2_breakout"), (3, "S3_reversal")):
        t = tr[tr.setup == sid] if len(tr) else tr
        by_setup[name_s] = {"trades": int(len(t)), "per_year": round(len(t) / years, 1),
                            "win_rate_pct": round(100 * float((t.r > 0).mean()), 1) if len(t) else None,
                            "avg_r": round(float(t.r.mean()), 2) if len(t) else None,
                            "median_r": round(float(t.r.median()), 2) if len(t) else None,
                            "avg_bars_held": round(float(t.bars.mean()), 1) if len(t) else None}
    exits = tr.reason.value_counts().to_dict() if len(tr) else {}
    return {
        "bars": int(len(ev)), "from": str(ev.index[0].date()), "to": str(ev.index[-1].date()),
        "calibration": {"trend_score_sd_real": round(float(ev["ts"].std()), 2),
                        "trend_score_sd_shuffled_mean": round(float(np.mean(shuffled_sd)), 3),
                        "trend_score_mean_shuffled_abs_max": None},
        "regime": {"pct_up": round(100 * float((d == 1).mean()), 1),
                   "pct_neutral": round(100 * float((d == 0).mean()), 1),
                   "pct_down": round(100 * float((d == -1).mean()), 1),
                   "switches_per_year": round(switches / years, 1),
                   "vfi_zero_crosses_per_year": zero_cross_rate(old, years)},
        "illustrative_regime_test": illus,
        "setups": by_setup,
        "exit_reasons": {{1: "stop", 2: "trail", 3: "regime"}[int(k)]: int(v) for k, v in exits.items()},
        "all_trades": {"n": int(len(tr)),
                       "win_rate_pct": round(100 * float((tr.r > 0).mean()), 1) if len(tr) else None,
                       "avg_r": round(float(tr.r.mean()), 2) if len(tr) else None,
                       "sum_r": round(float(tr.r.sum()), 1) if len(tr) else None},
    }


def main(seed: int = 11):
    rng = np.random.default_rng(seed)
    spx = load_bundled("SPX")
    out = {"SPX_D": run("SPX", None, rng), "NASDAQ_D": run("NASDAQ", None, rng),
           "GOOG_D_vs_SPX": run("GOOG", spx["close"], rng)}
    for v in out.values():
        v["calibration"].pop("trend_score_mean_shuffled_abs_max")
    path = Path(__file__).resolve().parents[1] / "results" / "e04_trend_setups_smoke.json"
    path.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
