import numpy as np
import pandas as pd

from tfs.relvol import (RelVolParams, log_level_lagged, quarterly_expiry, relative_volume, slot_keys,
                        var_lagged)
from tests.test_flow import synthetic_daily, synthetic_intraday

P = RelVolParams()


def test_reference_uses_earlier_bars_only():
    df = synthetic_daily(n=900, seed=4)
    full = relative_volume(df)
    cut = relative_volume(df.iloc[:700])
    for col in ("rvol", "zv", "z", "ext", "normal"):
        assert np.allclose(full[col].to_numpy()[:700], cut[col].to_numpy(), equal_nan=True)
    # the reference of bar t does not depend on the volume of bar t
    d2 = df.copy()
    d2.iloc[650, d2.columns.get_loc("volume")] *= 50
    assert np.isclose(relative_volume(d2)["normal"].iloc[650], full["normal"].iloc[650])


def test_values_appear_only_after_the_warm_up():
    f = relative_volume(synthetic_daily(n=200, seed=5))
    assert f["rvol"].iloc[:P.min_obs_daily].isna().all() and f["rvol"].iloc[P.min_obs_daily:].notna().all()
    assert f["z"].iloc[:P.min_obs_daily + 1].isna().all() and f["z"].iloc[P.min_obs_daily + 2:].notna().all()


def test_centred_and_scaled_on_lognormal_volume():
    f = relative_volume(synthetic_daily(n=6000, seed=6)).iloc[500:]
    assert 0.97 < f["rvol"].median() < 1.03                      # the arithmetic reference of v2 sat near 0.92 here
    assert 0.9 < f["zv"].std() < 1.15 and abs(f["zv"].mean()) < 0.08
    assert 0.9 < f["z"].std() < 1.15


def test_one_extreme_day_barely_moves_the_reference():
    df = synthetic_daily(n=800, seed=7)
    spike = df.copy()
    spike.iloc[600, spike.columns.get_loc("volume")] = 10 * relative_volume(df)["normal"].iloc[600]
    a, b = relative_volume(df)["normal"], relative_volume(spike)["normal"]
    lift = b.iloc[601] / a.iloc[601] - 1.0
    assert 0.0 < lift < 0.08                                      # v2's arithmetic average rose by 35%
    assert abs(b.iloc[640] / a.iloc[640] - 1.0) < 0.03
    s_a, s_b = relative_volume(df)["s"], relative_volume(spike)["s"]
    assert s_b.iloc[601] / s_a.iloc[601] < 1.10                   # and the spread is not blown up either


def test_zero_volume_and_zero_returns_are_harmless():
    df = synthetic_daily(n=400, seed=8)
    df.iloc[0, df.columns.get_loc("volume")] = 0.0                # a zero first bar seeded v2 with zero
    df.iloc[200, df.columns.get_loc("volume")] = 0.0
    df.iloc[1, df.columns.get_loc("close")] = df["close"].iloc[0]  # zero return on the second bar
    f = relative_volume(df)
    assert np.isfinite(f["rvol"].iloc[P.min_obs_daily + 2:]).all() and f["rvol"].iloc[200] == 0.0
    assert np.isnan(f["zv"].iloc[200])
    assert f["rvol"].iloc[P.min_obs_daily + 2:].max() < 8 and np.isfinite(f["z"].iloc[P.min_obs_daily + 3:]).all()
    assert np.isclose(f["normal"].iloc[201], f["normal"].iloc[200])  # the zero bar did not update the reference


def test_time_of_day_slots_remove_the_u_shape():
    df, profile = synthetic_intraday(days=160)
    f = relative_volume(df, intraday=True, bar_minutes=np.full(len(df), 60))
    late = f.iloc[7 * 60:]
    med = late.groupby(late.index.time)["rvol"].median()
    assert med.between(0.93, 1.07).all()
    assert late.groupby(late.index.time)["z"].std().between(0.85, 1.2).all()


def test_a_missing_bar_does_not_shift_the_other_slots():
    df, _ = synthetic_intraday(days=120)
    bm = np.full(len(df), 60)
    full = relative_volume(df, intraday=True, bar_minutes=bm)
    drop = df.index[7 * 90 + 1]                                    # the 10:30 bar of one session disappears
    part = df.drop(drop)
    cut = relative_volume(part, intraday=True, bar_minutes=np.full(len(part), 60))
    same_day = part.index[(part.index.normalize() == drop.normalize()) & (part.index > drop)]
    assert np.allclose(cut.loc[same_day, "rvol"], full.loc[same_day, "rvol"])
    assert np.allclose(cut.loc[same_day, "normal"], full.loc[same_day, "normal"])


def test_a_short_bar_gets_its_own_slot():
    idx = pd.DatetimeIndex(["2026-11-25 12:30", "2026-11-27 12:30"])
    k = slot_keys(idx, True, bar_minutes=[60, 30])
    assert k[0] != k[1] and k[0] == (12 * 60 + 30) * 10000 + 60
    assert not slot_keys(idx, False).any()


def test_session_pace_matches_the_day_at_the_close():
    df, _ = synthetic_intraday(days=160)
    f = relative_volume(df, intraday=True, bar_minutes=np.full(len(df), 60))
    last = f[f.index.time == pd.Timestamp("15:30").time()].iloc[60:]
    day_vol = df["volume"].groupby(df.index.normalize()).sum()
    mu, _, n = log_level_lagged(day_vol.to_numpy(), np.zeros(len(day_vol), dtype=np.int64), P.span_intraday, P.scale_span)
    day_rvol = pd.Series(day_vol.to_numpy() / np.exp(mu), index=day_vol.index).iloc[60:]
    assert np.allclose(last["pace"].to_numpy(), day_rvol.to_numpy(), rtol=1e-9)
    assert f["pace"].iloc[7 * 30:].notna().all() and relative_volume(synthetic_daily(n=100))["pace"].isna().all()


def test_clipped_variance_is_not_inflated_by_a_shock():
    rng = np.random.default_rng(3)
    r = rng.normal(0, 0.01, 600)
    r[400] = 0.08                                                  # an 8-sigma bar
    v, n = var_lagged(r, np.zeros(600, dtype=np.int64), 50)
    assert np.sqrt(v[401] / v[400]) < 1.17                         # unclipped: sqrt(1 + 63 * 2/51) = 1.86
    assert n[0] == 0 and np.isnan(v[0]) and n[-1] == 599


def test_quarterly_expiry_days():
    idx = pd.DatetimeIndex(["2026-09-18", "2026-12-18", "2026-10-16", "2026-09-11", "2026-09-17", "2027-03-19 10:30"])
    assert list(quarterly_expiry(idx)) == [True, True, False, False, False, True]
