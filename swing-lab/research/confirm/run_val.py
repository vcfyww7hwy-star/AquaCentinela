"""The single pre-registered validation run (protocol sections 2-3; docs/03_preregistration_val.md).

Sample VAL: 2018-07-02 .. 2022-12-30, survivorship-free universe. Runs ONCE: it refuses to run if
results/val_confirmation.json exists. `--sample DEV` executes the same code on development data
for a dry run and writes nothing to that file.

Part D  seven directional candidates. Verdict "confirmed" needs BOTH
          (1) day-weighted mean spread, Newey-West 2h lags, one-sided Student-t p-value with
              df = floor(days with a spread / 2h) - 1, significant under Holm at 5% across the seven;
          (2) event-weighted spread with the predicted sign and one-sided p <= 0.10.
        Also: a global test of the six avoid states (month-block bootstrap), bars 2-5 for A3 and
        A5, the "material for a trend follower" label, an E1 diagnostic, and two survivor-bias
        diagnostics without verdicts.
Part R  risk-engine claims with pass/fail margins fixed in research/confirm/prereg_val.py.

    SWINGLAB_VAL_TOKEN=PRE-REGISTERED python -m research.confirm.run_val
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if "--sample" in sys.argv and sys.argv[sys.argv.index("--sample") + 1] != "VAL":
    os.environ["SWINGLAB_REGISTRY_TAG"] = "dryrun"
else:
    os.environ.setdefault("SWINGLAB_REGISTRY_TAG", "val")

import numpy as np
from scipy import stats as sps

from research.confirm import prereg_val as PR
from research.experiments import g12_risk_engine as G12
from research.swinglab import candidates as C
from research.swinglab import earnings as EA
from research.swinglab import engine as E
from research.swinglab import pinelike as ta
from research.swinglab import trades as TR
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

OUT = Path(__file__).resolve().parents[1] / "results" / "val_confirmation.json"


# ----------------------------------------------------------------------------- statistics
def day_and_event(S, sig, ctrl, h):
    """Daily spread series (signal mean - control mean), its day-weighted mean and NW t, and the
    event-weighted mean with a date-clustered t."""
    out = S.fwd(h)
    u = S.uni if ctrl is None else (ctrl & S.uni)
    s = sig & S.uni
    d, ns = E.spread_series(out, s, u)
    r = S.rows
    m, t, n_days = E.nw_mean(d[r], 2 * h)
    ok = r & np.isfinite(d)
    n = np.where(ok, ns, 0).astype(float)
    ew = float(np.nansum(n * np.where(ok, d, 0.0)) / max(n.sum(), 1.0))
    x = (n * np.where(ok, d, 0.0))[r] / max(n[r].mean(), 1e-12)
    _, ew_t, _ = E.nw_mean(x, 2 * h)
    return {"d": d, "bp": 1e4 * m, "t": t, "days": n_days, "ew_bp": 1e4 * ew, "ew_t": float(ew_t), "events": int(n.sum())}


def p_student(t: float, sign: int, days: int, h: int) -> tuple[float, int]:
    df = max(int(days // (2 * h)) - 1, 2)
    return float(sps.t.sf(sign * t, df)), df


def month_blocks(dates: np.ndarray, rows: np.ndarray) -> list[np.ndarray]:
    mm = dates.astype("datetime64[M]").astype(int)
    idx = np.flatnonzero(rows)
    return [idx[mm[idx] == m] for m in np.unique(mm[idx])]


def directional(S) -> dict:
    F = C.Feat(S)
    res, series = {}, {}
    # ---- the seven
    for name in PR.DIRECTIONAL:
        spec = C.SPEC[name]
        sig, ctrl = spec["fn"](F)
        h, sgn = spec["h"], spec["sign"]
        st = day_and_event(S, sig, ctrl, h)
        series[name] = st["d"]
        p, df = p_student(st["t"], sgn, st["days"], h)
        ew_p = float(sps.norm.sf(sgn * st["ew_t"]))
        res[name] = {"h": h, "predicted_sign": sgn, "use": spec["use"], "bp": round(st["bp"], 1), "t": round(st["t"], 2),
                     "df": df, "p_one_sided": round(p, 5), "event_weighted_bp": round(st["ew_bp"], 1),
                     "event_weighted_t": round(st["ew_t"], 2), "event_weighted_p": round(ew_p, 4),
                     "events": st["events"], "days_with_signal": st["days"]}
        log_trial("VAL", "VAL_directional", name, S.sample, "xs_bp", st["bp"], tstat=st["t"], n=st["events"], params={"h": h}, note="pre-registered")
    order = sorted(PR.DIRECTIONAL, key=lambda k: res[k]["p_one_sided"])
    m, still = len(order), True
    for i, k in enumerate(order):
        thr = PR.HOLM_ALPHA / (m - i)
        holm_ok = still and res[k]["p_one_sided"] <= thr
        still = holm_ok
        r = res[k]
        right = np.sign(r["bp"]) == r["predicted_sign"]
        ew_ok = (np.sign(r["event_weighted_bp"]) == r["predicted_sign"]) and r["event_weighted_p"] <= PR.EVENT_WEIGHTED_P_MAX
        r["holm_threshold"], r["holm_pass"], r["event_weighted_pass"] = round(thr, 5), bool(holm_ok), bool(ew_ok)
        r["verdict"] = "CONFIRMED" if (holm_ok and ew_ok) else ("right sign, not significant" if right else "WRONG SIGN")
    # ---- material label
    c = F.c
    sel = S.uni & (c > F.s200) & (F.prox >= 0.85)
    for name in PR.AVOID_FAMILY:
        spec = C.SPEC[name]
        sig, _ = spec["fn"](F)
        st = day_and_event(S, sig & sel, sel, spec["h"])
        share = float((sig & sel).sum() / max(sel.sum(), 1))
        res[name]["inside_trend_selection"] = {"event_weighted_bp": round(st["ew_bp"], 1), "event_weighted_t": round(st["ew_t"], 2),
                                               "day_weighted_bp": round(st["bp"], 1), "share_of_selection_days": round(share, 5), "events": st["events"]}
        res[name]["material_for_trend_follower"] = bool(st["ew_bp"] <= PR.MATERIAL_AVOID_BP)
    # E1 net of protocol costs (5 bp a side at >= $50M median dollar volume, 10 bp a side at $20-50M)
    sig, _ = C.SPEC["E1_episodic_pivot"]["fn"](F)
    out = S.fwd(10)
    s = sig & S.uni & np.isfinite(out)
    m_ctl, _ = E.day_means(out, S.uni, 20)
    cost = np.where(S.adv60 >= 50e6, 0.0010, 0.0020)
    net = (out - m_ctl[:, None] - cost)[s]
    res["E1_episodic_pivot"]["event_weighted_net_of_protocol_costs_bp"] = round(1e4 * float(np.nanmean(net)), 1)
    res["E1_episodic_pivot"]["raw_net_return_bp"] = round(1e4 * float(np.nanmean((out - cost)[s])), 1)
    res["E1_episodic_pivot"]["material_for_trend_follower"] = bool(1e4 * float(np.nanmean(net)) >= PR.MATERIAL_ENTER_NET_BP)
    res["E1_episodic_pivot"]["signals_per_month"] = round(float(s.sum() / (S.rows.sum() / 21.0)), 1)
    # E1 diagnostic: without names that stop trading within 126 bars of the event (descriptive)
    T = c.shape[0]
    t_idx = np.arange(T)[:, None]
    survives = (S.P.last[None, :] >= t_idx + 126) | S.P.alive[None, :]
    stx = day_and_event(S, sig & survives, None, 10)
    res["E1_episodic_pivot"]["diagnostic_excluding_names_gone_within_126_bars"] = {"bp": round(stx["bp"], 1), "t": round(stx["t"], 2),
                                                                                    "event_weighted_bp": round(stx["ew_bp"], 1), "events": stx["events"]}
    # ---- bars 2-5 for the one-session suspects
    for name in PR.DELAYED_ENDPOINT:
        spec = C.SPEC[name]
        sig, ctrl = spec["fn"](F)
        st = day_and_event(S, ta.shift(sig, 1), None if ctrl is None else ta.shift(ctrl, 1), 4)
        res[name]["bars_2_to_5"] = {"bp": round(st["bp"], 1), "t": round(st["t"], 2), "event_weighted_bp": round(st["ew_bp"], 1),
                                    "event_weighted_t": round(st["ew_t"], 2)}
    # ---- global test of the avoid family: mean sign-adjusted t, joint month-block bootstrap, recentred
    blocks = month_blocks(S.dates, S.rows)
    hs = {k: C.SPEC[k]["h"] for k in PR.AVOID_FAMILY}
    def stat(get):
        ts = []
        for k in PR.AVOID_FAMILY:
            _, t, _ = E.nw_mean(get(k), 2 * hs[k])
            ts.append(-t if np.isfinite(t) else 0.0)
        return float(np.mean(ts))
    obs = stat(lambda k: series[k][S.rows])
    centred = {k: series[k] - np.nanmean(series[k][S.rows]) for k in PR.AVOID_FAMILY}
    rng = np.random.default_rng(PR.BOOTSTRAP_SEED)
    nb = len(blocks)
    draws = np.empty(PR.BOOTSTRAP_DRAWS)
    for b in range(PR.BOOTSTRAP_DRAWS):
        start = rng.integers(0, nb, size=(nb + 1) // 2)
        pick = np.concatenate([np.concatenate([blocks[(s0 + j) % nb] for j in range(2)]) for s0 in start])[: int(S.rows.sum())]
        draws[b] = stat(lambda k: centred[k][pick])
    res["_avoid_family_global"] = {"mean_sign_adjusted_t": round(obs, 3), "bootstrap_p_one_sided": round(float(np.mean(draws >= obs)), 4),
                                   "pass": bool(np.mean(draws >= obs) <= 0.05), "draws": PR.BOOTSTRAP_DRAWS}
    # ---- diagnostics without verdicts
    for name in PR.DIAGNOSTICS:
        spec = C.SPEC[name]
        sig, ctrl = spec["fn"](F)
        st = day_and_event(S, sig, ctrl, spec["h"])
        res[f"_diagnostic_{name}"] = {"h": spec["h"], "bp": round(st["bp"], 1), "t": round(st["t"], 2),
                                      "event_weighted_bp": round(st["ew_bp"], 1), "event_weighted_t": round(st["ew_t"], 2), "events": st["events"]}
    return res


# ----------------------------------------------------------------------------- risk engine
def risk(S) -> dict:
    res: dict = {}
    K = PR.RISK_CRITERIA
    c = S.P.cf
    est = G12.estimators(S)
    sc = K["scale_from_ctx"]
    blocks = [(np.datetime64(a), np.datetime64(b)) for a, b in K["blocks"]]
    in_sample_blocks = [bl for bl in blocks if ((S.dates >= bl[0]) & (S.dates <= bl[1]) & S.rows).sum() > 60]
    # ---- R1 forecast ranking
    def loss(rv, f, scale):
        with np.errstate(divide="ignore", invalid="ignore"):
            x = (rv / (f * scale)) ** 2
            L = x - np.log(x) - 1.0
        return np.where(S.uni & np.isfinite(L) & (rv > 0), L, np.nan)
    r1 = {}
    for h in (5, 10, 20):
        rv = G12.realised(S, h)
        L = {k: loss(rv, est[k], sc[k][str(h)]) for k in ("atr14/close", "ewma20", "yang_zhang20")}
        ok = np.isfinite(L["atr14/close"]) & np.isfinite(L["ewma20"]) & np.isfinite(L["yang_zhang20"])
        means = {k: float(np.nanmean(np.where(ok, v, np.nan))) for k, v in L.items()}
        r1[h] = {"qlike": {k: round(v, 4) for k, v in means.items()}}
        if h == 10:
            for comp in ("ewma20", "yang_zhang20"):
                dser = np.nanmean(np.where(ok, L[comp] - L["atr14/close"], np.nan), axis=1)
                _, t, _ = E.nw_mean(dser[S.rows], 20)
                same = 0
                for a, b in in_sample_blocks:
                    bl = (S.dates >= a) & (S.dates <= b) & S.rows
                    same += int(np.nanmean(dser[bl]) > 0)
                r1[h][f"vs_{comp}"] = {"t": round(float(t), 2), "rel_improvement": round(1 - means["atr14/close"] / means[comp], 4),
                                       "blocks_with_atr_better": f"{same}/{len(in_sample_blocks)}", "_same": same}
    res["R1_forecast_ranking"] = r1
    need_blocks = min(K["qlike_blocks_min"], len(in_sample_blocks))
    res["R1_pass"] = bool(all(r1[10][f"vs_{cmp}"]["t"] >= K["qlike_t_min"] and r1[10][f"vs_{cmp}"]["rel_improvement"] >= K["qlike_rel_improvement_min"]
                              and r1[10][f"vs_{cmp}"]["_same"] >= need_blocks for cmp in ("ewma20", "yang_zhang20"))
                          and all(r1[h]["qlike"]["atr14/close"] < min(r1[h]["qlike"]["ewma20"], r1[h]["qlike"]["yang_zhang20"]) for h in (5, 20)))
    # ---- R1b the constant refitted
    scale_val = G12.best_scale(G12.realised(S, 10), est["atr14/close"], S.uni)
    res["R1b_scale_refit"] = round(scale_val, 4)
    res["R1b_pass"] = bool(K["scale_range"][0] <= scale_val <= K["scale_range"][1])
    # ---- R2 calibration
    f = est["atr14/close"] * sc["atr14/close"]["10"]
    with np.errstate(divide="ignore", invalid="ignore"):
        xa = np.log1p(S.fwd(10)) / (f * np.sqrt(10))
    okx = S.uni & np.isfinite(xa)
    x = xa[okx]
    lo, hi = K["band"]
    q05, q95 = float(np.quantile(x, 0.05)), float(np.quantile(x, 0.95))
    cov = float(np.mean((x >= lo) & (x <= hi)))
    fv = f[okx]
    t1, t2 = np.quantile(fv, [1 / 3, 2 / 3])
    cov_terc = [float(np.mean((x[m] >= lo) & (x[m] <= hi))) for m in (fv <= t1, (fv > t1) & (fv <= t2), fv > t2)]
    cov_blocks = []
    for a, b in in_sample_blocks:
        m = okx & ((S.dates >= a) & (S.dates <= b))[:, None]
        cov_blocks.append(float(np.mean((xa[m] >= lo) & (xa[m] <= hi))))
    res["R2_calibration"] = {"q05": round(q05, 3), "q95": round(q95, 3), "coverage_pooled": round(cov, 4),
                             "coverage_by_vol_tercile": [round(v, 4) for v in cov_terc], "coverage_by_block": [round(v, 4) for v in cov_blocks],
                             "share_beyond_2": round(float(np.mean(np.abs(x) > 2)), 4), "n": int(len(x))}
    blocks_ok = sum(K["coverage_block"][0] <= v <= K["coverage_block"][1] for v in cov_blocks)
    res["R2_pass"] = bool(K["q05_range"][0] <= q05 <= K["q05_range"][1] and K["q95_range"][0] <= q95 <= K["q95_range"][1]
                          and K["coverage_pooled"][0] <= cov <= K["coverage_pooled"][1]
                          and all(K["coverage_tercile"][0] <= v <= K["coverage_tercile"][1] for v in cov_terc)
                          and blocks_ok >= min(K["coverage_blocks_min"], len(in_sample_blocks)))
    # ---- R3 stop-out table
    rng = np.random.default_rng(12)
    rnd = S.uni & (rng.random(S.uni.shape) < 0.02)
    atr = S.atr(14)
    tabl, worst = {}, 0.0
    for k in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
        for h in (5, 10, 20):
            tr = TR.simulate(S.P, rnd, atr, rows=S.rows, stop_k=k, max_hold=h, cost_bp=0, stop_extra_bp=0)
            stp = tr["reason"].isin(["stop", "gap_stop"])
            p = float(stp.mean())
            dev = PR.DEV_STOP_TABLE[f"k{k}_h{h}"]
            cell = {"val": round(p, 3), "dev": dev, "diff": round(p - dev, 3)}
            if k == 2.0 and h == 10:
                cell["gap_through_share"] = round(float((tr["reason"] == "gap_stop").sum() / max(stp.sum(), 1)), 3)
                cell["share_worse_than_-1.5R"] = round(float((tr["R"] < -1.5).mean()), 4)
                cell["worst_R"] = round(float(tr["R"].min()), 1)
                cell["delisting_exits"] = int((tr["reason"] == "delist").sum())
                trs = TR.simulate(S.P, rnd, atr, rows=S.rows, stop_k=k, max_hold=h, cost_bp=0, stop_extra_bp=0, haircut=-1.0)
                cell["stress_-100pct_delisting"] = {"share_worse_than_-1.5R": round(float((trs["R"] < -1.5).mean()), 4), "mean_ret_bp": round(1e4 * float(trs["ret"].mean()), 1),
                                                    "base_mean_ret_bp": round(1e4 * float(tr["ret"].mean()), 1)}
            tabl[f"k{k}_h{h}"] = cell
            worst = max(worst, abs(p - dev))
    res["R3_stop_table"] = tabl
    res["R3_max_abs_diff"] = round(worst, 3)
    ref = tabl["k2.0_h10"]
    res["R3_pass"] = bool(worst <= K["stop_table_tolerance"] and K["gap_through_share_range"][0] <= ref["gap_through_share"] <= K["gap_through_share_range"][1]
                          and ref["share_worse_than_-1.5R"] <= K["tail_1p5R_max"])
    # ---- R4 earnings gap risk
    ev = EA.load(S)
    react = ev["react"] & S.uni
    near = ev["react"] | ev["ann"]
    non = S.uni & ~near
    with np.errstate(divide="ignore", invalid="ignore"):
        gap_atr = (S.P.o - ta.shift(c, 1)) / ta.shift(atr, 1)
    ge, go = gap_atr[react & np.isfinite(gap_atr)], gap_atr[non & np.isfinite(gap_atr)]
    pe, po = float(np.mean(ge < -2)), float(np.mean(go < -2))
    res["R4_earnings_gap"] = {"p_gap_lt_-2atr_reaction": round(pe, 4), "p_gap_lt_-2atr_ordinary": round(po, 5), "ratio": round(pe / max(po, 1e-9), 1),
                              "p_gap_lt_-1atr_reaction": round(float(np.mean(ge < -1)), 4), "p_gap_lt_-3atr_reaction": round(float(np.mean(ge < -3)), 4),
                              "reaction_bars": int(len(ge))}
    res["R4_pass"] = bool(pe / max(po, 1e-9) >= K["earnings_gap_ratio_min"])
    # ---- R5 exits on the same random entries: difference in net bp per bar, month-block bootstrap
    below20 = c < ta.sma(c, 20)
    rules = {"hold20_no_stop": dict(stop_k=1e6, max_hold=20), "stop2atr_hold20": dict(stop_k=2.0, max_hold=20),
             "stop3atr_hold20": dict(stop_k=3.0, max_hold=20), "exit_under_20d_avg": dict(stop_k=1e6, max_hold=20, exit_sig=below20)}
    mm = S.dates.astype("datetime64[M]").astype(int)
    agg = {}
    for nm, kw in rules.items():
        tr = TR.simulate(S.P, rnd, atr, rows=S.rows, **kw)
        mo = mm[tr["entry"].to_numpy()]
        months = np.unique(mm[S.rows])
        R = np.array([tr["ret"].to_numpy()[mo == m_].sum() for m_ in months])
        B = np.array([tr["bars"].to_numpy()[mo == m_].sum() for m_ in months])
        agg[nm] = (R, B)
    def bpbar(R, B):
        return 1e4 * R.sum() / max(B.sum(), 1)
    base = {nm: round(bpbar(*agg[nm]), 2) for nm in rules}
    rng2 = np.random.default_rng(PR.BOOTSTRAP_SEED + 5)
    nmo = len(agg["hold20_no_stop"][0])
    pv = {}
    for comp in ("stop2atr_hold20", "exit_under_20d_avg"):
        obs = bpbar(*agg["hold20_no_stop"]) - bpbar(*agg[comp])
        cnt = 0
        for _ in range(PR.BOOTSTRAP_DRAWS):
            pick = rng2.integers(0, nmo, nmo)
            dlt = bpbar(agg["hold20_no_stop"][0][pick], agg["hold20_no_stop"][1][pick]) - bpbar(agg[comp][0][pick], agg[comp][1][pick])
            cnt += int(dlt <= 0)
        pv[comp] = {"difference_bp_per_bar": round(obs, 2), "bootstrap_p_one_sided": round(cnt / PR.BOOTSTRAP_DRAWS, 4)}
    res["R5_exits"] = {"bp_per_bar": base, "hold_minus": pv}
    res["R5_pass"] = bool(all(v["difference_bp_per_bar"] > 0 and v["bootstrap_p_one_sided"] <= K["exit_p_max"] for v in pv.values()))
    # ---- R6 regime
    spy = c[:, [S.spy]]
    sma200 = ta.sma(spy, 200)[:, 0]
    above = spy[:, 0] > sma200
    r1d = S.P.ret[:, S.spy]
    st = np.r_[False, above[:-1]]
    known = np.r_[False, np.isfinite(sma200)[:-1]]
    rr = S.rows & np.isfinite(r1d) & known
    v_in, v_out = float(np.std(r1d[rr & st])), float(np.std(r1d[rr & ~st]))
    f20 = S.fwd(20)
    fin = np.isfinite(sma200)[:, None]
    p_up = float(np.nanmean(f20[S.uni & fin & above[:, None]] < -0.10))
    p_dn = float(np.nanmean(f20[S.uni & fin & ~above[:, None]] < -0.10))
    res["R6_regime"] = {"spy_vol_above_ann": round(100 * v_in * np.sqrt(252), 1), "spy_vol_below_ann": round(100 * v_out * np.sqrt(252), 1),
                        "ratio": round(v_out / max(v_in, 1e-12), 2), "days_below": int((rr & ~st).sum()),
                        "spy_mean_bp_above": round(1e4 * float(np.mean(r1d[rr & st])), 1), "spy_mean_bp_below": round(1e4 * float(np.mean(r1d[rr & ~st])), 1),
                        "stock_p_loss10_20d_above": round(p_up, 4), "stock_p_loss10_20d_below": round(p_dn, 4)}
    res["R6_pass"] = bool(v_out / max(v_in, 1e-12) >= K["regime_vol_ratio_min"] and p_dn > p_up)
    for k in ("R1", "R1b", "R2", "R3", "R4", "R5", "R6"):
        log_trial("VAL", "VAL_risk", k, S.sample, "pass", float(res[f"{k}_pass"]), note="pre-registered")
    for h in r1:
        for cmp in ("vs_ewma20", "vs_yang_zhang20"):
            if cmp in r1[h]:
                r1[h][cmp].pop("_same", None)
    return res


def show(res: dict) -> None:
    D = res["directional"]
    print(f"\nSAMPLE {res['sample']}   universe names per day {res['universe_names_per_day']:.0f}")
    print(f"{'candidate':<26s} h sign |  day-wtd bp (t, df)   p     Holm thr | event-wtd bp (t)   p    | verdict")
    for k in PR.DIRECTIONAL:
        r = D[k]
        print(f"{k:<26s} {r['h']:>2d} {r['predicted_sign']:+d}  | {r['bp']:+7.1f} ({r['t']:+5.2f}, {r['df']:>3d}) {r['p_one_sided']:.4f}  {r['holm_threshold']:.4f} | "
              f"{r['event_weighted_bp']:+7.1f} ({r['event_weighted_t']:+5.2f}) {r['event_weighted_p']:.3f} | {r['verdict']}   n={r['events']}")
    for k in PR.AVOID_FAMILY:
        i = D[k]["inside_trend_selection"]
        print(f"   inside a trend selection  {k:<26s} event-wtd {i['event_weighted_bp']:+7.1f} (t {i['event_weighted_t']:+5.2f})  share of selection days {100 * i['share_of_selection_days']:.2f}%  material: {D[k]['material_for_trend_follower']}")
    e = D["E1_episodic_pivot"]
    print(f"   E1: net of protocol costs, event-weighted {e['event_weighted_net_of_protocol_costs_bp']:+.1f} bp; raw net return {e['raw_net_return_bp']:+.1f} bp; {e['signals_per_month']} signals a month; material: {e['material_for_trend_follower']}")
    print(f"   E1 diagnostic (names gone within 126 bars excluded): {e['diagnostic_excluding_names_gone_within_126_bars']}")
    for k in PR.DELAYED_ENDPOINT:
        print(f"   {k} bars 2-5: {D[k]['bars_2_to_5']}")
    print(f"   avoid family, global test: {D['_avoid_family_global']}")
    for k in PR.DIAGNOSTICS:
        print(f"   diagnostic {k}: {D['_diagnostic_' + k]}")
    R = res["risk"]
    print("\nRISK ENGINE")
    print("  R1 ", {h: v for h, v in R["R1_forecast_ranking"].items()}, "PASS" if R["R1_pass"] else "FAIL")
    print("  R1b scale refit", R["R1b_scale_refit"], "PASS" if R["R1b_pass"] else "FAIL")
    print("  R2 ", R["R2_calibration"], "PASS" if R["R2_pass"] else "FAIL")
    print("  R3 max |diff|", R["R3_max_abs_diff"], {k: v["val"] for k, v in R["R3_stop_table"].items()}, "\n      ", R["R3_stop_table"]["k2.0_h10"], "PASS" if R["R3_pass"] else "FAIL")
    print("  R4 ", R["R4_earnings_gap"], "PASS" if R["R4_pass"] else "FAIL")
    print("  R5 ", R["R5_exits"], "PASS" if R["R5_pass"] else "FAIL")
    print("  R6 ", R["R6_regime"], "PASS" if R["R6_pass"] else "FAIL")


def main() -> int:
    sample = sys.argv[sys.argv.index("--sample") + 1] if "--sample" in sys.argv else "VAL"
    if sample == "VAL" and OUT.exists():
        print("The validation run has already been made; refusing to repeat it (protocol section 3).")
        return 2
    S = Study(sample)
    res = {"sample": {"VAL": "VAL 2018-07-02..2022-12-30", "DEV": "DEV 2011-01-03..2018-06-29 (dry run)"}.get(sample, sample),
           "universe_names_per_day": float(S.uni[S.rows].sum(axis=1).mean())}
    res["directional"] = directional(S)
    res["risk"] = risk(S)
    if sample == "VAL":
        OUT.write_text(json.dumps(res, indent=1, default=str))
    else:
        OUT.with_name(f"val_dryrun_{sample}.json").write_text(json.dumps(res, indent=1, default=str))
    show(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
