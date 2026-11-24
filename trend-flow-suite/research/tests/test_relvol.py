import numpy as np
import pandas as pd

from tfs.relvol import (RelVolParams, log_level_lagged, mechanical_day, quarterly_expiry, relative_volume,
                        russell_reconstitution, slot_keys, var_lagged)
from tests.test_flow import synthetic_daily, synthetic_intraday

P = RelVolParams()


def test_reference_uses_earlier_bars_only():
    df = synthetic_daily(n=900, seed=4)
    full = relative_volume(df)
    cut = relative_volume(df.iloc[:700])
    for col in ("rvol", "zv", "z", "normal"):
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
    # the pace in units of its own spread: the day's zV at the close, and consistent with the multiple everywhere
    _, s_d, _ = log_level_lagged(day_vol.to_numpy(), np.zeros(len(day_vol), dtype=np.int64), P.span_intraday, P.scale_span)
    assert np.allclose(last["pace_z"].to_numpy(), (np.log(day_rvol) / s_d[60:]).to_numpy(), rtol=1e-9)
    k = f["pace_z"].notna()
    assert k.sum() > 600 and (np.sign(f["pace_z"][k]) == np.sign(np.log(f["pace"][k]))).all()
    assert relative_volume(synthetic_daily(n=100))["pace_z"].isna().all()


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


def test_mechanical_days_follow_the_holiday_and_the_russell_reconstitution():
    # 19 June 2026 is a Friday and a market holiday (Juneteenth): the expiry is Thursday 18 June
    idx = pd.DatetimeIndex(["2026-06-18", "2026-06-17", "2020-06-19", "2020-06-18", "2025-06-20", "2025-06-18", "2037-06-18"])
    assert list(quarterly_expiry(idx)) == [True, False, True, False, True, False, True]
    # 19 June 2027 is a Saturday, observed on Friday 18 June (NYSE calendar): the expiry is Thursday 17 June
    idx = pd.DatetimeIndex(["2027-06-17", "2027-06-16", "2021-06-17", "2021-06-18", "2032-06-17"])
    assert list(quarterly_expiry(idx)) == [True, False, False, True, True]
    # fourth Friday of June: 2018-06-22, 2019-06-28, 2024-06-28, 2026-06-26; not the third or the fifth
    idx = pd.DatetimeIndex(["2018-06-22", "2019-06-28", "2024-06-28", "2026-06-26", "2018-06-29", "2026-06-19", "2026-07-24"])
    assert list(russell_reconstitution(idx)) == [True, True, True, True, False, False, False]
    idx = pd.DatetimeIndex(["2026-06-18", "2026-06-26", "2026-09-18", "2026-06-25", "2026-10-16"])
    assert list(mechanical_day(idx)) == [True, True, True, False, False]
    f = relative_volume(synthetic_daily(n=300, seed=5))
    assert (f["mech_day"] == mechanical_day(f.index)).all() and (f["q_expiry"] == quarterly_expiry(f.index)).all()


# ---------------- flags, warm-up, counting rules ----------------
def test_flags_and_thresholds():
    df = synthetic_daily(n=500, seed=21)
    f0 = relative_volume(df)
    v = df["volume"].to_numpy().copy()
    v[492] = 4.0 * f0["normal"].iloc[492]
    row = relative_volume(df.assign(volume=v)).iloc[492]
    assert row["unusual"] and row["zv"] >= P.flag_z and np.isclose(row["rvol"], 4.0)
    assert not f0["unusual"].iloc[492] or f0["zv"].iloc[492] >= P.flag_z
    f = relative_volume(synthetic_daily(n=600, seed=22))
    k = f["zv"].notna()
    assert np.allclose(f["level"][k], np.exp(P.flag_z * f["s"][k]))
    assert np.allclose(np.log(f["level"][k]) / f["s"][k], P.flag_z)          # volume = level x normal gives zV = flag
    assert ((f["zv"] >= P.flag_z) == f["unusual"]).all() and ((f["zv"] >= P.extreme_z) == f["extreme"]).all()
    assert not {"ext", "atr", "heavy_no_move", "heavy_no_move_low", "quiet"} & set(f.columns)   # removed in v4


def test_intraday_warm_up_half_days_and_required_bar_length():
    df, _ = synthetic_intraday(days=60)
    bm = np.full(len(df), 60)
    f = relative_volume(df, intraday=True, bar_minutes=bm)
    per_slot = f.groupby(f.index.time)["rvol"].apply(lambda x: int(x.isna().sum()))
    assert (per_slot == P.min_obs_intraday).all()                             # 10 earlier sessions per slot, not fewer
    # a half day: the 12:30 bar of session 40 is 30 minutes long
    i = np.where((df.index.normalize() == df.index.normalize().unique()[40]) & (df.index.time == pd.Timestamp("12:30").time()))[0][0]
    bm2 = bm.copy()
    bm2[i] = 30
    d2 = df.copy()
    d2.iloc[i, d2.columns.get_loc("volume")] *= 0.2
    g = relative_volume(d2, intraday=True, bar_minutes=bm2)
    assert np.isnan(g["rvol"].iloc[i])                                        # its own slot, still warming up
    nxt = i + 7                                                               # the next session's 12:30 bar
    ref_without = relative_volume(df.drop(df.index[i]), intraday=True, bar_minutes=np.full(len(df) - 1, 60))
    assert np.isclose(g["normal"].iloc[nxt], ref_without["normal"].iloc[nxt - 1])   # the short bar left it untouched
    try:
        relative_volume(df, intraday=True)
        assert False, "must require bar_minutes or keys"
    except ValueError:
        pass


def test_counting_rules():
    keys = np.zeros(6, dtype=np.int64)
    v, n = var_lagged(np.array([0.01, 0.0, np.nan, 0.02, 0.0, 0.01]), keys, 50)
    assert list(n) == [0, 1, 2, 2, 3, 4]                                      # zero returns count, missing ones do not
    assert v[2] < v[1]                                                        # a zero return lowers the variance
    mu, s, cnt = log_level_lagged(np.array([100.0, 0.0, np.nan, 120.0, 110.0]), keys[:5], 50, 100)
    assert list(cnt) == [0, 1, 1, 1, 2] and np.isclose(mu[3], np.log(100.0))  # zero and missing volume are skipped
    # clipping starts only after min_clip earlier observations
    base = np.full(40, 1000.0)
    early, late = base.copy(), base.copy()
    early[5], late[30] = 50000.0, 50000.0
    rng = np.random.default_rng(1)
    noise = np.exp(rng.normal(0, 0.3, 40))
    mu_e, _, _ = log_level_lagged(early * noise, np.zeros(40, dtype=np.int64), 50, 100, 3.0, 20)
    mu_l, _, _ = log_level_lagged(late * noise, np.zeros(40, dtype=np.int64), 50, 100, 3.0, 20)
    mu_0, _, _ = log_level_lagged(base * noise, np.zeros(40, dtype=np.int64), 50, 100, 3.0, 20)
    assert mu_e[6] - mu_0[6] > 0.5 and mu_l[31] - mu_0[31] < 0.1              # unclipped early, clipped later


# ---------------- literal transcription of the Pine functions ----------------
def _pine_log_level(vol, keys, span, scale_span, clip, min_clip):
    m_num, m_den, m_num2, m_den2, m_cnt = {}, {}, {}, {}, {}
    out = []
    for x, key in zip(vol, keys):
        cnt = m_cnt.get(key, 0)
        num, den, num2, den2 = m_num.get(key, 0.0), m_den.get(key, 0.0), m_num2.get(key, 0.0), m_den2.get(key, 0.0)
        mu = num / den if cnt > 0 and den > 0 else np.nan
        s = np.sqrt(num2 / den2) if den2 > 0 and num2 > 0 else np.nan
        if not np.isnan(x) and x > 0:
            a, b, lx = 2.0 / (span + 1), 2.0 / (scale_span + 1), np.log(x)
            if cnt == 0:
                m_num[key], m_den[key], m_cnt[key] = a * lx, a, 1
            else:
                e = lx - mu
                if cnt >= min_clip and not np.isnan(s) and s > 0:
                    e = max(-clip * s, min(clip * s, e))
                m_num[key] = (1.0 - a) * num + a * (mu + e)
                m_den[key] = (1.0 - a) * den + a
                m_num2[key] = (1.0 - b) * num2 + b * e * e
                m_den2[key] = (1.0 - b) * den2 + b
                m_cnt[key] = cnt + 1
        out.append((mu, s, cnt))
    return np.array(out, dtype=float).T


def _pine_var(ret, keys, span, clip, min_clip):
    m_num, m_den, m_cnt = {}, {}, {}
    out = []
    for x, key in zip(ret, keys):
        cnt = m_cnt.get(key, 0)
        num, den = m_num.get(key, 0.0), m_den.get(key, 0.0)
        v = num / den if cnt > 0 and den > 0 else np.nan
        if not np.isnan(x):
            a, x2 = 2.0 / (span + 1), x * x
            if cnt >= min_clip and not np.isnan(v) and v > 0:
                x2 = min(x2, clip * clip * v)
            m_num[key], m_den[key], m_cnt[key] = (1.0 - a) * num + a * x2, (1.0 - a) * den + a, cnt + 1
        out.append((v, cnt))
    return np.array(out, dtype=float).T


def test_python_twin_equals_a_literal_transcription_of_the_pine_functions():
    rng = np.random.default_rng(77)
    for trial in range(6):
        n = 1500
        keys = rng.integers(0, 5, n) * 600000 + rng.choice([60, 60, 60, 30], n)
        vol = rng.lognormal(12, 0.5, n) * np.where(rng.random(n) < 0.01, 12.0, 1.0)
        vol[rng.random(n) < 0.02] = 0.0
        vol[rng.random(n) < 0.01] = np.nan
        ret = rng.normal(0, 0.01, n) * np.where(rng.random(n) < 0.01, 8.0, 1.0)
        ret[rng.random(n) < 0.05] = 0.0
        ret[rng.random(n) < 0.01] = np.nan
        mu, s, cnt = log_level_lagged(vol, keys, 20, 100, 3.0, 20)
        pm, ps, pc = _pine_log_level(vol, keys, 20, 100, 3.0, 20)
        assert np.allclose(mu, pm, rtol=0, atol=1e-12, equal_nan=True) and np.allclose(s, ps, rtol=0, atol=1e-12, equal_nan=True)
        assert (cnt == pc).all()
        v, nv = var_lagged(ret, keys, 20, 3.0, 20)
        pv, pn = _pine_var(ret, keys, 20, 3.0, 20)
        assert np.allclose(v, pv, rtol=0, atol=1e-15, equal_nan=True) and (nv == pn).all()


# ---------------- the day estimate ----------------
def test_pine_script_carries_the_same_constants_as_the_twin():
    import pathlib
    import re
    src = (pathlib.Path(__file__).resolve().parents[2] / "pine" / "relative_volume.pine").read_text()
    assert re.search(r"float\s+CLIP\s*=\s*3\.0", src) and re.search(r"int\s+MIN_CLIP\s*=\s*20", src)
    assert "int  minObs  = todOK ? 10 : 25" in src
    assert f"input.int({P.span_intraday}, \"Intraday" in src and f"input.int({P.span_daily}, \"Daily" in src
    assert f"input.int({P.scale_span}, \"Spread" in src and "input.float(2.0, \"Unusual" in src
    assert "input.float(3.0, \"Extreme" in src
    # the calendar rule of the twin, as written in the script
    assert "dayofweek == dayofweek.friday and dayofmonth >= 15 and dayofmonth <= 21" in src
    assert "year >= 2022 and month == 6 and dayofweek == dayofweek.thursday and (dayofmonth == 17 or dayofmonth == 18)" in src
    assert "month == 6 and dayofweek == dayofweek.friday and dayofmonth >= 22 and dayofmonth <= 28" in src
    # state is updated on closed bars only, and a bar open at load is not a closed bar
    assert src.count("MIN_CLIP, conf)") == 3
    assert "bool conf       = barstate.isconfirmed and not openAtLoad" in src
    assert "barstate.islast and barstate.ishistory and (na(time_close) or timenow < time_close + feedLag)" in src
    # removed in v4
    for gone in ("DAY_SHARE", "estRvol", "showH", "hMark", "dbg_ext", "showQuiet"):
        assert gone not in src
    # the first plots are the numeric series the alert messages refer to by position
    plots = re.findall(r"^plot\((\w+), \"([^\"]+)\"", src, flags=re.M)
    assert plots[:5] == [("rvol", "RVOL"), ("zv", "zV"), ("z", "Move"), ("paceShow", "Pace"), ("paceZShow", "Pace z")]
    assert "paceZ >= paceAlert and not paceFired" in src
