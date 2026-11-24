import math

import numpy as np
import pandas as pd
import pytest

from tfs.backtest import long_flat_returns
from tfs.validation import (deflated_sharpe, effective_trials, expected_max_sr, pbo_cscv)
from tfs.vfi import change_decomposition, vfi


def synthetic_ohlcv(n=1500, seed=0):
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0003, 0.012, n)
    close = 100 * np.exp(np.cumsum(r))
    prev = np.r_[100, close[:-1]]
    open_ = prev * np.exp(rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * np.exp(np.abs(rng.normal(0, 0.006, n)))
    low = np.minimum(open_, close) * np.exp(-np.abs(rng.normal(0, 0.006, n)))
    vol = rng.lognormal(15, 0.4, n)
    idx = pd.bdate_range("2000-01-03", periods=n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


# ---------- validation statistics ----------
@pytest.mark.parametrize("n", [100, 1000])
def test_expected_max_matches_simulation(n):
    rng = np.random.default_rng(1)
    sim = rng.standard_normal((4000, n)).max(axis=1).mean()
    assert abs(expected_max_sr(n) - sim) / sim < 0.03


def test_pbo_is_about_half_for_pure_noise():
    rng = np.random.default_rng(2)
    r = rng.normal(0, 0.01, (2000, 200))
    res = pbo_cscv(r, n_blocks=10)
    assert 0.35 < res["pbo"] < 0.65


def test_pbo_is_low_when_one_variant_has_real_skill():
    rng = np.random.default_rng(3)
    r = rng.normal(0, 0.01, (2000, 200))
    r[:, 7] += 0.003  # Sharpe ~ 4.8 annualised: genuine and persistent
    res = pbo_cscv(r, n_blocks=10)
    assert res["pbo"] < 0.05


def test_dsr_with_one_trial_equals_psr_against_zero():
    rng = np.random.default_rng(4)
    x = rng.normal(0.0005, 0.01, 2500)
    res = deflated_sharpe(x, trial_srs=np.array([0.01, 0.02, 0.03]), n_trials=1)
    assert math.isclose(res["dsr"], res["psr_vs_zero"], rel_tol=1e-12)


def test_effective_trials_bounds():
    rng = np.random.default_rng(5)
    base = rng.normal(0, 1, (1000, 1))
    same = np.hstack([base + 1e-6 * rng.normal(0, 1, (1000, 1)) for _ in range(50)])
    indep = rng.normal(0, 1, (1000, 50))
    assert effective_trials(same) < 1.1
    assert effective_trials(indep) > 40


# ---------- backtest timing ----------
def test_position_applies_to_next_bar_and_costs_on_change():
    r = np.array([0.0, 0.10, -0.05, 0.02])
    pos = np.array([1, 1, 0, 0])            # decided at the close of each bar
    out = long_flat_returns(pos, r, cost_bps=10).ravel()
    # bar0: nothing held; bar1: held (decided at bar0) earns +10% minus entry cost;
    # bar2: still held earns -5%; bar3: flat (decided at bar2) pays exit cost.
    expected = np.array([0.0, 0.10 - 0.001, -0.05, -0.001])
    assert np.allclose(out, expected, atol=1e-7)


# ---------- VFI reference ----------
def test_vfi_change_decomposition_is_exact():
    df = synthetic_ohlcv()
    f = vfi(df, length=130)
    d = change_decomposition(f, length=130)
    err = (d["new_bar"] + d["leaving_bar"] + d["renorm"] - d["d_vfi"]).abs().max()
    assert err < 1e-9


def test_single_bar_contribution_is_capped_by_vcoef():
    df = synthetic_ohlcv()
    df.iloc[800, df.columns.get_loc("volume")] *= 50  # volume spike
    f = vfi(df, length=130, vcoef=2.5)
    d = change_decomposition(f, length=130)
    assert d["new_bar"].abs().max() <= 2.5 + 1e-12
