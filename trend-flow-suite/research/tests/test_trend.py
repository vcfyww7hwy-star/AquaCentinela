import numpy as np
import pandas as pd
import pytest

from tfs.core import ema1
from tfs.trend import (PAIRS, TrendParams, composite_null_sd, pair_null_sd, regime, trend_score,
                       trend_setups, weekly_context_dir)


def ohlcv_from_returns(r, seed=0, start="2000-01-03"):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(r))
    prev = np.r_[100, close[:-1]]
    rng_hl = np.abs(rng.normal(0, 0.006, len(r)))
    high = np.maximum(prev, close) * np.exp(rng_hl)
    low = np.minimum(prev, close) * np.exp(-rng_hl)
    vol = rng.lognormal(14, 0.4, len(r))
    return pd.DataFrame({"open": prev, "high": high, "low": low, "close": close, "volume": vol},
                        index=pd.bdate_range(start, periods=len(r)))


# ---------------- calibration ----------------
def test_pair_null_sd_matches_simulation():
    rng = np.random.default_rng(0)
    lp = np.cumsum(rng.normal(0, 1, 200_000))
    for s, l in PAIRS:
        x = ema1(lp, s) - ema1(lp, l)
        assert abs(np.std(x[2000:]) / pair_null_sd(s, l) - 1) < 0.03


def test_trend_score_is_standard_normal_without_trend_and_positive_with_drift():
    rng = np.random.default_rng(1)
    ts0 = trend_score(np.cumsum(rng.normal(0, 0.01, 60_000)))[2000:]
    assert abs(np.mean(ts0)) < 0.1 and 0.92 < np.std(ts0) < 1.08
    ts1 = trend_score(np.cumsum(rng.normal(0.003, 0.01, 5_000)))[500:]
    assert np.mean(ts1) > 2.0
    assert 0.9 < composite_null_sd() < 0.95


def test_regime_hysteresis():
    seq = [0.0, 0.9, 1.1, 0.5, 0.31, 0.29, -0.5, -1.0, -0.4, -0.29, 1.2, -1.3]
    assert list(regime(np.array(seq), 1.0, 0.3)) == [0, 0, 1, 1, 1, 0, 0, -1, -1, 0, 1, -1]


# ---------------- structure and AVWAP ----------------
def test_zigzag_confirms_swings_on_close_reversal():
    # 60 bars up, 30 down, 60 up: clean swing high then swing low
    r = np.r_[np.full(60, 0.01), np.full(30, -0.012), np.full(60, 0.01)]
    df = ohlcv_from_returns(r, seed=2)
    f, _ = trend_setups(df)
    sh_bars = np.flatnonzero(f["new_sh"].to_numpy())
    sl_bars = np.flatnonzero(f["new_sl"].to_numpy())
    assert len(sh_bars) >= 1 and len(sl_bars) >= 1
    t = sh_bars[0]
    peak = df["high"].iloc[:t + 1].max()
    assert f["last_sh"].iloc[t] == peak                             # level = highest high of the up-leg
    assert df["close"].iloc[t] < peak - 2.0 * f["atr"].iloc[t]       # confirmed by a 2-ATR close reversal
    assert df["close"].iloc[t - 1] >= peak - 2.0 * f["atr"].iloc[t - 1] or f["new_sh"].iloc[t - 1]


def test_avwap_matches_manual_computation():
    rng = np.random.default_rng(3)
    df = ohlcv_from_returns(rng.normal(0, 0.015, 800), seed=3)
    f, _ = trend_setups(df)
    tp = ((df["high"] + df["low"] + df["close"]) / 3).to_numpy()
    v = df["volume"].to_numpy()
    sl_conf = np.flatnonzero(f["new_sl"].to_numpy())
    t_conf = sl_conf[-1]
    pivot = int(np.flatnonzero(df["low"].to_numpy() == f["last_sl"].iloc[t_conf])[-1])
    for t in (t_conf, min(t_conf + 5, len(df) - 1)):
        if f["new_sl"].iloc[t] and t != t_conf:
            continue
        manual = np.sum(tp[pivot:t + 1] * v[pivot:t + 1]) / np.sum(v[pivot:t + 1])
        assert np.isclose(f["avwap_low"].iloc[t], manual, rtol=1e-12)


# ---------------- setups: invariants on many random paths ----------------
@pytest.mark.parametrize("seed", range(6))
def test_trade_invariants(seed):
    rng = np.random.default_rng(100 + seed)
    drift = rng.choice([-0.001, 0.0, 0.001, 0.002])
    df = ohlcv_from_returns(rng.normal(drift, 0.015, 1500), seed=seed)
    f, trades = trend_setups(df)
    p = TrendParams()
    for _, tr in trades.iterrows():
        e, x = int(tr.entry_bar), int(tr.exit_bar)
        assert e >= p.warmup and x > e
        assert tr.stop < tr.entry                                         # positive initial risk
        assert np.isclose(tr.r, (tr.exit - tr.entry) / (tr.entry - tr.stop))
        assert f["in_trade"].iloc[e:x].all() and not f["in_trade"].iloc[x]  # one position at a time
        if tr.setup in (1, 2):
            assert f["dir"].iloc[e] >= (1 if tr.setup == 1 else 0)
        if tr.reason == 3:
            assert f["dir"].iloc[x] == -1
        else:
            prev_level = f["stop_level"].iloc[x - 1]
            assert df["close"].iloc[x] < max(prev_level, df["high"].iloc[e:x + 1].max() - 3 * f["atr"].iloc[x]) + 1e-9
    ent = f["entry"].to_numpy()
    assert set(np.unique(ent)) <= {0, 1, 2, 3}


def test_no_lookahead_truncation_invariance():
    rng = np.random.default_rng(9)
    df = ohlcv_from_returns(rng.normal(0.0008, 0.015, 1400), seed=9)
    full, trades_full = trend_setups(df)
    for k in (600, 1000):
        part, trades_part = trend_setups(df.iloc[:k])
        for col in full.columns:
            a, b = full[col].iloc[:k].to_numpy(), part[col].to_numpy()
            if a.dtype == object:
                assert (a == b).all(), col
            elif a.dtype == bool:
                assert (a == b).all(), col
            else:
                assert np.allclose(a.astype(float), b.astype(float), equal_nan=True), col
        done = trades_full[trades_full.exit_bar < k] if len(trades_full) else trades_full
        assert len(done) == len(trades_part)


def test_weekly_context_uses_only_completed_weeks():
    rng = np.random.default_rng(4)
    df = ohlcv_from_returns(rng.normal(0.0005, 0.012, 2000), seed=4)
    wd = weekly_context_dir(df)
    wk = df.resample("W-FRI").agg({"open": "first", "high": "max", "low": "min",
                                   "close": "last", "volume": "sum"}).dropna()
    reg = pd.Series(regime(trend_score(np.log(wk["close"].to_numpy())), 1.0, 0.3), index=wk.index)
    for i in range(300, len(df), 37):
        day = df.index[i]
        done = reg[reg.index < day]                 # weeks that ended strictly before this day
        assert wd[i] == (done.iloc[-1] if len(done) else 0)


def test_s2_compression_breakout_fires_on_constructed_path():
    """Normal volatility, then a tight 40-bar range, then a high-volume breakout bar."""
    rng = np.random.default_rng(21)
    r = np.r_[rng.normal(0.0015, 0.015, 300), rng.normal(0.0, 0.002, 40), [0.04], rng.normal(0.001, 0.01, 30)]
    df = ohlcv_from_returns(r, seed=21)
    df.iloc[340, df.columns.get_loc("volume")] *= 4.0                 # breakout bar volume
    p = TrendParams(pull_ext=-1e9)                                     # disable S1 to isolate S2
    f, _ = trend_setups(df, p=p)                                       # the trade may still be open
    entries = np.flatnonzero(f["entry"].to_numpy() == 2)
    assert len(entries) >= 1 and entries[0] == 340
    e = int(entries[0])
    expected_stop = df["low"].iloc[e - 9:e + 1].min() - 0.25 * f["atr"].iloc[e]
    assert np.isclose(f["stop_px"].iloc[e], expected_stop)
    assert f["in_trade"].iloc[e]


def test_regime_flip_exit_when_stops_are_out_of_reach():
    rng = np.random.default_rng(22)
    r = np.r_[rng.normal(0.002, 0.01, 450), rng.normal(-0.003, 0.01, 250)]
    df = ohlcv_from_returns(r, seed=22)
    p = TrendParams(trail_atr=1e6, stop_buf=1e3)                       # stop and trail can never be hit
    f, trades = trend_setups(df, p=p)
    assert len(trades) >= 1 and (trades.reason == 3).all()
    for x in trades.exit_bar.astype(int):
        assert f["dir"].iloc[x] == -1 and f["dir"].iloc[x - 1] != -1  # exits on the first down bar
