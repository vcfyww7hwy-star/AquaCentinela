import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from tfs.core import (ema1, phi, pivot_high, slot_ewma_lagged, slot_index, smooth2,
                      span_from_window, true_range)
from tfs.flow import FlowParams, _rolling_ols_persistence, ltf_direction, volume_flow_v2


def synthetic_daily(n=1600, seed=0, vol_tilt=0.0):
    """Random walk with lognormal volume; vol_tilt > 0 makes volume heavier on up days."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0003, 0.012, n)
    close = 100 * np.exp(np.cumsum(r))
    prev = np.r_[100, close[:-1]]
    open_ = prev * np.exp(rng.normal(0, 0.003, n))
    high = np.maximum(open_, close) * np.exp(np.abs(rng.normal(0, 0.006, n)))
    low = np.minimum(open_, close) * np.exp(-np.abs(rng.normal(0, 0.006, n)))
    vol = rng.lognormal(15, 0.4, n) * np.exp(vol_tilt * np.sign(r))
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol},
                        index=pd.bdate_range("2001-01-02", periods=n))


def synthetic_intraday(days=120, seed=1):
    """7 hourly bars per session, U-shaped volume, larger moves at the open (overnight gap)."""
    rng = np.random.default_rng(seed)
    profile = np.array([2.2, 1.1, 0.8, 0.7, 0.8, 1.1, 1.8])
    vol_scale = np.array([2.0, 1.0, 0.8, 0.7, 0.8, 1.0, 1.3])
    rows, price = [], 100.0
    for d, day in enumerate(pd.bdate_range("2024-01-02", periods=days)):
        for k in range(7):
            ts = day + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(hours=k)
            r = rng.normal(0, 0.004 * vol_scale[k])
            o = price
            c = price * np.exp(r)
            rows.append((ts, o, max(o, c) * 1.001, min(o, c) * 0.999, c,
                         profile[k] * rng.lognormal(13, 0.3)))
            price = c
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"]).set_index("ts")
    return df, profile


# ---------------- core maths ----------------
def test_phi_matches_scipy():
    x = np.linspace(-8, 8, 4001)
    assert np.max(np.abs(phi(x) - norm.cdf(x))) < 2e-7


def test_ema_seeding_and_nan_hold():
    out = ema1(np.array([np.nan, np.nan, 1.0, 2.0, np.nan, 4.0]), 3)  # alpha 0.5
    assert np.isnan(out[:2]).all()
    assert np.allclose(out[2:], [1.0, 1.5, 1.5, 2.75])


def test_ema_matches_pandas_without_nans():
    x = np.random.default_rng(0).normal(size=500)
    ref = pd.Series(x).ewm(span=20, adjust=False).mean().to_numpy()
    assert np.allclose(ema1(x, 20), ref, atol=1e-12)


def test_two_pole_mean_lag_and_span():
    n = 33
    x = np.r_[np.zeros(5), 1.0, np.zeros(3000)]
    w = smooth2(x, n)[5:]
    lag = np.sum(np.arange(len(w)) * w) / np.sum(w)
    assert abs(lag - (n - 1)) < 0.05
    assert span_from_window(130) == 65 and span_from_window(40) == 20


def test_slot_ewma_has_no_self_inclusion_and_separates_slots():
    slots = np.tile([0, 1], 50)
    x = np.where(slots == 0, 10.0, 100.0)
    out = slot_ewma_lagged(x, slots, 5)
    assert np.isnan(out[0]) and np.isnan(out[1])
    assert np.allclose(out[2:], np.where(slots[2:] == 0, 10.0, 100.0))
    x2 = x.copy()
    x2[60] = 1e9  # changing the current bar must not change its own expectation
    assert slot_ewma_lagged(x2, slots, 5)[60] == out[60]


def test_slot_index_resets_each_session():
    idx = pd.DatetimeIndex([f"2024-01-0{d} {h}:30" for d in (2, 3) for h in range(9, 16)])
    assert list(slot_index(idx, True)) == list(range(7)) * 2
    assert not slot_index(idx, False).any()


def test_pivot_high_timing_and_ties():
    x = np.array([1, 2, 3, 9, 3, 2, 1, 1, 5, 5, 1, 1.0])
    ph = pivot_high(x, 2, 2)
    assert ph[5] == 9 and np.isnan(np.delete(ph, 5)).all()  # reported 2 bars after the peak; tie at 5,5 is no pivot


def test_true_range_first_bar():
    tr = true_range([10, 11], [9, 10], [9.5, 10.5])
    assert tr[0] == 1.0 and tr[1] == 1.5


# ---------------- Volume Flow v2 ----------------
def test_flow_is_bounded():
    f = volume_flow_v2(synthetic_daily())
    for col in ("f_fast", "f_slow", "f_unweighted"):
        x = f[col].dropna()
        assert (x.abs() <= 1 + 1e-12).all()


def test_asymmetry_is_zero_with_constant_volume_and_positive_when_volume_favours_up_bars():
    df = synthetic_daily()
    df_const = df.assign(volume=1e6)
    a0 = volume_flow_v2(df_const)["asym"].dropna()
    assert a0.abs().max() < 1e-12
    a1 = volume_flow_v2(synthetic_daily(vol_tilt=0.3))["asym"].dropna()
    assert a1.iloc[300:].mean() > 0.02


def test_no_lookahead_truncation_invariance():
    df = synthetic_daily(n=1400, seed=3)
    full = volume_flow_v2(df)
    for k in (700, 1100):
        part = volume_flow_v2(df.iloc[:k])
        a, b = full.iloc[:k], part
        for col in full.columns:
            x, y = a[col].to_numpy(), b[col].to_numpy()
            if x.dtype == bool:
                assert (x == y).all(), col
            else:
                assert np.allclose(x, y, equal_nan=True, rtol=1e-9, atol=1e-12), col


def test_time_of_day_normalisation_flattens_u_shape():
    df, profile = synthetic_intraday()
    f = volume_flow_v2(df, intraday=True)
    late = f.iloc[7 * 40:]
    by_slot = late.groupby("slot")["rvol"].median()
    assert by_slot.between(0.85, 1.15).all()
    raw = df["volume"].iloc[7 * 40:].groupby(f["slot"].iloc[7 * 40:]).median()
    assert raw.iloc[0] / raw.iloc[3] > 2.5          # raw volume is strongly U-shaped
    assert late.groupby("slot")["z"].std().between(0.8, 1.25).all()  # per-slot sigma works too


def test_ltf_direction_rule():
    ltf = pd.DataFrame({"open": [10, 11, 10.5, 9], "close": [11, 10.5, 10.5, 9],
                        "volume": [10, 5, 3, 4]})
    bar_id = np.array([0, 0, 1, 1])
    out = ltf_direction(ltf, bar_id, 3)
    # bar 0: +10 up, -5 down -> 5/15; bar 1: 10.5==10.5 -> equal to prev close 10.5 -> repeat last
    # direction (down) for 3; 9==9 -> below prev close 10.5 -> down for 4 -> (0-7)/7 = -1
    assert np.isclose(out[0], 5 / 15) and np.isclose(out[1], -1.0) and np.isnan(out[2])


@pytest.mark.parametrize("sign", [1, -1])
def test_persistence_regression_recovers_sign(sign):
    rng = np.random.default_rng(7)
    n = 3000
    lv = rng.normal(0, 0.5, n)
    r = np.zeros(n)
    for t in range(1, n):
        r[t] = sign * 0.3 * r[t - 1] * lv[t - 1] + rng.normal(0, 0.01)
    b2, t2 = _rolling_ols_persistence(r, np.exp(lv), 500, 100)
    assert np.sign(np.nanmedian(b2)) == sign and np.nanmedian(np.abs(t2)) > 3


def test_event_columns_are_clean_booleans():
    f = volume_flow_v2(synthetic_daily())
    for col in ("climax_up", "climax_dn", "absorb_top", "absorb_bottom", "dryup",
                "accumulation", "distribution", "bear_div", "bull_div"):
        assert f[col].dtype == bool


def test_relative_weights_remove_spurious_asymmetry_from_time_of_day_drift():
    """Opening bars drift up and carry 2.2x volume, but volume carries no information beyond
    time of day. Raw-volume weighting reports 'accumulation'; relative weighting does not."""
    rng = np.random.default_rng(11)
    profile = np.array([2.2, 1.1, 0.8, 0.7, 0.8, 1.1, 1.8])
    rows, price = [], 100.0
    for day in pd.bdate_range("2024-01-02", periods=300):
        for k in range(7):
            r = rng.normal(0.002 if k == 0 else 0.0, 0.008 if k == 0 else 0.004)
            c = price * np.exp(r)
            rows.append((day + pd.Timedelta(hours=9.5 + k), price, max(price, c), min(price, c), c,
                         profile[k] * rng.lognormal(13, 0.3)))
            price = c
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"]).set_index("ts")
    f = volume_flow_v2(df, intraday=True)
    ns = span_from_window(FlowParams().slow_window)
    sv_raw = df["volume"].to_numpy() * f["s"].to_numpy()
    ok = ~np.isnan(sv_raw)
    a_raw = (smooth2(sv_raw, ns) / smooth2(np.where(ok, df["volume"], np.nan), ns)
             - smooth2(np.where(ok, f["s"], np.nan), ns))
    late = slice(7 * 60, None)
    assert np.nanmean(a_raw[late]) > 0.012
    assert abs(np.nanmean(f["asym"].to_numpy()[late])) < 0.006


def test_parity_tool_passes_on_identical_values_and_flags_a_perturbation(tmp_path):
    from tools.parity_check import SERIES, compare
    df = synthetic_daily(n=1300, seed=9)
    ours = volume_flow_v2(df)
    tv = df.copy()
    for key, col in SERIES.items():
        tv[f"Volume Flow v2: {key}"] = ours[col]   # mimic TradingView's "<script>: <plot>" headers
    ok, _ = compare(tv, intraday=False, warmup=600, rtol=1e-6, atol=1e-9)
    assert ok
    tv["Volume Flow v2: dbg_f_slow"] = tv["Volume Flow v2: dbg_f_slow"] * 1.001
    ok, rows = compare(tv, intraday=False, warmup=600, rtol=1e-6, atol=1e-9)
    assert not ok and [r for r in rows if r["series"] == "dbg_f_slow"][0]["status"] == "MISMATCH"
