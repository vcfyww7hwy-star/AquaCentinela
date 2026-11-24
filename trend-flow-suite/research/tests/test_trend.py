import numpy as np
import pandas as pd
import pytest

from tfs.core import ema1
from tfs.trend import (PAIRS, TrendParams, composite_null_sd, pair_null_sd, regime,
                       robust_var_lagged, simulate_trades, trend_score, trend_setups,
                       weekly_context_dir)

NOFILT = dict(use_ctx=False, use_rs=False, use_mkt=False)


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


def test_robust_variance_is_nearly_unbiased_and_bounded_against_one_outlier():
    rng = np.random.default_rng(5)
    r = rng.normal(0, 0.01, 40_000)
    v = robust_var_lagged(r, 100, 3.0)[2000:]
    assert abs(np.sqrt(np.mean(v)) / 0.01 - 1) < 0.02            # ~0.3% theoretical bias
    r2 = r.copy()
    r2[5000] = 0.30                                              # a 30-sigma gap
    plain = robust_var_lagged(r2, 100, 0.0)
    robust = robust_var_lagged(r2, 100, 3.0)
    assert plain[5001] / plain[5000] > 15                        # unprotected estimate explodes
    assert robust[5001] / robust[5000] < 1.2                     # capped at 1 + 8a = 1.16
    assert np.isnan(robust_var_lagged(r, 100, 3.0)[0])           # lagged: no value on the first bar


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


# ---------------- S1 "higher low" ----------------
def test_s1_fires_on_first_close_above_prior_high_after_a_confirmed_swing_high():
    rng = np.random.default_rng(31)
    r = np.r_[rng.normal(0.004, 0.008, 320), np.full(4, -0.02), [0.012], rng.normal(0.003, 0.008, 40)]
    df = ohlcv_from_returns(r, seed=31)
    f, _ = trend_setups(df, p=TrendParams(s1_mode="swing", **NOFILT))
    sh = np.flatnonzero(f["new_sh"].to_numpy() & (np.arange(len(f)) >= 320))
    s1 = np.flatnonzero(f["raw_s1"].to_numpy() & (np.arange(len(f)) >= 320))
    assert len(sh) >= 1 and len(s1) >= 1
    t_sh, t = sh[0], s1[0]
    assert t > t_sh and f["dir"].iloc[t] == 1
    hi_bar = int(np.flatnonzero(df["high"].to_numpy()[:t_sh + 1] == f["last_sh"].iloc[t_sh])[-1])
    assert df["close"].iloc[t] > df["high"].iloc[t - 1]
    for k in range(t_sh + 1, t):                                   # it is the FIRST such close
        assert not df["close"].iloc[k] > df["high"].iloc[k - 1]
    pb_low = df["low"].iloc[hi_bar:t + 1].min()
    assert np.isclose(f["stop1"].iloc[t], pb_low - 0.25 * f["atr"].iloc[t])
    assert np.isclose(f["pb_rvol"].iloc[t], f["rvol"].iloc[hi_bar + 1:t + 1].mean())
    assert f["raw_s1"].iloc[t_sh + 1:t].sum() == 0 and f["raw_s1"].iloc[t + 1:t + 3].sum() == 0  # one per swing


def test_signals_do_not_depend_on_the_open_position():
    rng = np.random.default_rng(32)
    df = ohlcv_from_returns(rng.normal(0.001, 0.015, 1500), seed=32)
    runs = [trend_setups(df, p=TrendParams(s1_mode="swing", use_s2=True, use_s3=True, stop_mode=sm, exit_mode=em, **NOFILT))[0]
            for sm in ("intrabar", "close") for em in ("chandelier", "structure")]
    for f in runs[1:]:
        for col in ("sig", "raw_s1", "raw_s2", "raw_s3"):
            assert (f[col].to_numpy() == runs[0][col].to_numpy()).all()
        assert np.allclose(f["sig_stop"], runs[0]["sig_stop"], equal_nan=True)
    f0 = runs[0]
    assert ((f0["sig"] > 0) & f0["in_trade"].shift(1, fill_value=False)).sum() > 0  # signals while in a trade exist


# ---------------- trade engine: invariants on many random paths ----------------
@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize("stop_mode", ["intrabar", "close"])
@pytest.mark.parametrize("exit_mode", ["chandelier", "structure"])
@pytest.mark.parametrize("s1_mode", ["dip", "swing", "baseline"])
def test_trade_invariants(seed, stop_mode, exit_mode, s1_mode):
    rng = np.random.default_rng(100 + seed)
    drift = rng.choice([-0.001, 0.0, 0.001, 0.002])
    df = ohlcv_from_returns(rng.normal(drift, 0.015, 1500), seed=seed)
    p = TrendParams(stop_mode=stop_mode, exit_mode=exit_mode, s1_mode=s1_mode, use_s2=True, use_s3=True, tick=0.01, **NOFILT)
    f, trades = trend_setups(df, p=p, htf_dir=weekly_context_dir(df))
    dip = s1_mode == "dip"
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    lvl = f["stop_level"].to_numpy()
    for _, tr in trades.iterrows():
        e, x = int(tr.entry_bar), int(tr.exit_bar)
        assert e >= p.warmup and x > e and f["sig"].iloc[e] == tr.setup
        assert tr.entry - tr.stop >= p.min_stop_atr * f["atr"].iloc[e] - 0.006    # floor (within a tick)
        assert abs(tr.stop / 0.01 - round(tr.stop / 0.01)) < 1e-6                  # rounded to the tick
        assert np.isclose(tr.r, (tr.exit - tr.entry) / (tr.entry - tr.stop))
        assert f["in_trade"].iloc[e:x].all() and not f["in_trade"].iloc[x]         # one position at a time
        assert (np.diff(lvl[e:x]) >= -1e-9).all()                                  # the stop never moves down
        if tr.setup == 1 and dip:
            assert f["ctx_dir"].iloc[e] == 1 and f["dip_z"].iloc[e] <= p.dip_z
            assert abs((tr.entry - tr.stop) - p.dip_stop_atr * f["atr"].iloc[e]) < 0.006   # 2 ATR, tick-rounded
        elif tr.setup in (1, 2):
            assert f["dir"].iloc[e] >= (1 if tr.setup == 1 else 0)
        if tr.reason == 3:
            trend = f["ctx_dir"] if (dip and tr.setup == 1) else f["dir"]
            assert trend.iloc[x] == -1 and tr.exit == c[x]
        elif stop_mode == "intrabar":
            assert l[x] <= lvl[x - 1] and np.isclose(tr.exit, min(o[x], lvl[x - 1]))
            assert (l[e + 1:x] > lvl[e:x - 1]).all()                               # not hit earlier
        else:
            assert tr.exit == c[x] and (c[e + 1:x] >= lvl[e + 1:x]).all()
    assert set(np.unique(f["entry"].to_numpy())) <= {0, 1, 2, 3}


def test_intrabar_stop_fills_at_the_open_on_a_gap_and_at_the_stop_otherwise():
    n = 6
    o = np.array([100, 100, 100, 100, 90.0, 90])
    h = np.array([101, 101, 101, 101, 91.0, 91])
    l = np.array([99, 99, 99, 99, 89.0, 89])
    c = np.array([100, 100, 100, 100, 90.0, 90])
    atr, d, sl = np.full(n, 1.0), np.ones(n, dtype=int), np.full(n, np.nan)
    sig, stop = np.zeros(n, dtype=int), np.full(n, np.nan)
    sig[1], stop[1] = 1, 97.0
    _, tr = simulate_trades(o, h, l, c, atr, d, sl, sig, stop, TrendParams(stop_mode="intrabar"))
    assert len(tr) == 1 and tr[0]["exit_bar"] == 4 and tr[0]["exit"] == 90.0     # gap: filled at the open
    assert np.isclose(tr[0]["r"], (90 - 100) / 3)                                # worse than -1R
    l2 = l.copy(); o2 = o.copy(); o2[4] = 99.0; l2[4] = 96.0
    _, tr2 = simulate_trades(o2, h, l2, c, atr, d, sl, sig, stop, TrendParams(stop_mode="intrabar"))
    assert tr2[0]["exit"] == 98.0                                                # trailed stop: 101 - 3 ATR
    _, tr3 = simulate_trades(o2, h, l2, c, atr, d, sl, sig, stop, TrendParams(stop_mode="close"))
    assert tr3[0]["exit"] == 90.0 and tr3[0]["exit_bar"] == 4                    # close-based: exits at the close


def test_no_lookahead_truncation_invariance():
    rng = np.random.default_rng(9)
    df = ohlcv_from_returns(rng.normal(0.0008, 0.015, 1400), seed=9)
    bench = 100 * np.exp(np.cumsum(np.random.default_rng(10).normal(0.0003, 0.01, 1400)))
    ctx = weekly_context_dir(df)
    full, trades_full = trend_setups(df, bench_close=bench, htf_dir=ctx)
    for k in (600, 1000):
        part, trades_part = trend_setups(df.iloc[:k], bench_close=bench[:k], htf_dir=weekly_context_dir(df.iloc[:k]))
        for col in full.columns:
            a, b = full[col].iloc[:k].to_numpy(), part[col].to_numpy()
            if a.dtype == object or a.dtype == bool:
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


def test_filters_block_signals_when_context_market_or_strength_is_down():
    rng = np.random.default_rng(33)
    df = ohlcv_from_returns(rng.normal(0.002, 0.012, 1200), seed=33)
    falling = 100 * np.exp(np.cumsum(np.full(1200, -0.004)))          # market in a steady downtrend
    base, _ = trend_setups(df, p=TrendParams(s1_mode="swing", use_s2=True, **NOFILT))
    assert (base["sig"] > 0).sum() > 0
    mkt, _ = trend_setups(df, p=TrendParams(s1_mode="swing", use_s2=True, use_ctx=False, use_rs=False, use_mkt=True), bench_close=falling)
    assert (mkt["mkt_dir"].iloc[300:] == -1).all() and (mkt["sig"] > 0).sum() == 0
    ctx, _ = trend_setups(df, p=TrendParams(s1_mode="swing", use_s2=True, use_ctx=True, use_rs=False, use_mkt=False),
                          htf_dir=np.full(1200, -1))
    assert (ctx["sig"] > 0).sum() == 0
    assert (mkt["raw_s1"] == base["raw_s1"]).all()                    # filters do not change raw detection


def test_s2_compression_breakout_fires_on_constructed_path():
    """Normal volatility, then a tight 40-bar range, then a high-volume breakout bar."""
    rng = np.random.default_rng(21)
    r = np.r_[rng.normal(0.0015, 0.015, 300), rng.normal(0.0, 0.002, 40), [0.04], rng.normal(0.001, 0.01, 30)]
    df = ohlcv_from_returns(r, seed=21)
    df.iloc[340, df.columns.get_loc("volume")] *= 4.0                 # breakout bar volume
    f, _ = trend_setups(df, p=TrendParams(use_s1=False, use_s2=True, **NOFILT))    # the trade may still be open
    entries = np.flatnonzero(f["entry"].to_numpy() == 2)
    assert len(entries) >= 1 and entries[0] == 340
    e = int(entries[0])
    raw_stop = df["low"].iloc[e - 9:e + 1].min() - 0.25 * f["atr"].iloc[e]
    assert np.isclose(f["stop2"].iloc[e], raw_stop)
    assert np.isclose(f["sig_stop"].iloc[e], min(raw_stop, df["close"].iloc[e] - f["atr"].iloc[e]))
    assert f["in_trade"].iloc[e]


def test_regime_flip_exit_when_stops_are_out_of_reach():
    rng = np.random.default_rng(22)
    r = np.r_[rng.normal(0.002, 0.01, 450), rng.normal(-0.003, 0.01, 250)]
    df = ohlcv_from_returns(r, seed=22)
    # stop and trail can never be hit; warm-up off because the only pullbacks to the baseline come early
    p = TrendParams(trail_atr=1e6, stop_buf=1e3, s1_mode="baseline", warmup=0, **NOFILT)
    f, trades = trend_setups(df, p=p)
    assert len(trades) >= 1 and (trades.reason == 3).all()
    for x in trades.exit_bar.astype(int):
        assert f["dir"].iloc[x] == -1 and f["dir"].iloc[x - 1] != -1  # exits on the first down bar


# ---------------- D "dip in a long-term uptrend" (default setup) ----------------
def test_dip_setup_matches_its_definition_exactly():
    rng = np.random.default_rng(41)
    df = ohlcv_from_returns(rng.normal(0.0012, 0.015, 2500), seed=41)
    ctx = weekly_context_dir(df)
    p = TrendParams()
    f, _ = trend_setups(df, p=p, htf_dir=ctx)
    lnc = np.log(df["close"].to_numpy())
    sig = np.sqrt(robust_var_lagged(np.r_[np.nan, np.diff(lnc)], p.sigma_span, p.sigma_clip))
    z = np.full(len(df), np.nan)
    z[5:] = (lnc[5:] - lnc[:-5]) / (sig[5:] * np.sqrt(5))
    assert np.allclose(f["dip_z"], z, equal_nan=True)
    with np.errstate(invalid="ignore"):
        in_dip = z <= -1.5
    first = in_dip & ~np.r_[False, in_dip[:-1]]
    expected = first & (ctx == 1) & np.isfinite(f["atr"].to_numpy())
    assert expected.sum() > 20 and (f["raw_s1"].to_numpy() == expected).all()
    t = np.flatnonzero(expected)
    assert np.allclose(f["stop1"].to_numpy()[t], df["close"].to_numpy()[t] - 2.0 * f["atr"].to_numpy()[t])
    assert (f["sig"].to_numpy()[t][t >= p.warmup] == 1).all()
    none, _ = trend_setups(df, p=p)                                   # no context supplied -> no dip signals
    assert none["raw_s1"].sum() == 0


def test_dip_trade_follows_the_context_regime_and_the_time_exit():
    n = 10
    o = h = l = c = np.full(n, 100.0)
    h, l = c + 0.5, c - 0.5
    atr, last_sl = np.full(n, 1.0), np.full(n, np.nan)
    chart_down = -np.ones(n, dtype=int)                               # must be ignored for setup 1
    ctx = np.array([1, 1, 1, 1, 1, -1, -1, -1, -1, -1])
    sig, stop = np.zeros(n, dtype=int), np.full(n, np.nan)
    sig[1], stop[1] = 1, 98.0
    _, tr = simulate_trades(o, h, l, c, atr, chart_down, last_sl, sig, stop, TrendParams(), d_dip=ctx)
    assert len(tr) == 1 and tr[0]["exit_bar"] == 5 and tr[0]["reason"] == 3
    _, tr = simulate_trades(o, h, l, c, atr, chart_down, last_sl, sig, stop, TrendParams(max_bars=3), d_dip=ctx)
    assert tr[0]["exit_bar"] == 4 and tr[0]["reason"] == 4 and tr[0]["bars"] == 3
    sig2 = sig.copy(); sig2[1] = 2                                    # setup 2 follows the chart regime
    _, tr = simulate_trades(o, h, l, c, atr, chart_down, last_sl, sig2, stop, TrendParams(), d_dip=ctx)
    assert tr[0]["exit_bar"] == 2 and tr[0]["reason"] == 3
