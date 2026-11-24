#!/usr/bin/env python3
"""E27 - What should be paired with the volume pane? The price-side evidence on 2018-2026.

Every result behind Trend & Setups v2 ends in early 2018. Before recommending it, or anything else,
as the companion of Relative Volume v4, the frozen tests are repeated unchanged on the modern set
EM (1,123 liquid US stocks listed in Nov 2026, evaluated Feb 2018 - Oct 2026; survivors only).

PLAN (written before the numbers were computed)
 Part 1, frozen tests, nothing re-tuned:
   C1-C4 of docs/06 section 2.3 (experiments/e07): dips in a long-term uptrend, rule D as trades
         against random entries, 12-1 momentum, dips without an uptrend.
   H1 of docs/06 section 2.6 (experiments/e09): the long-term trend as a risk switch.
   The benchmark is the equal-weight index of the set itself (no index series reaches 2026 here).
 Part 2, exploratory, descriptive (no multiplicity adjustment):
   P1  Do the two indicators interact? Rule-D bars with unusual volume (zV >= 2) against rule-D bars
       with ordinary volume: f1, f3, f5, f10; and rule D on expiry and index-rebalance days.
   P2  Rule D by sub-period, and (added after part 1 was seen) by the market's own trend state.
   P3  Selection: 12-1 relative strength and nearness to the 52-week high, top against bottom fifth
       of each day, market-adjusted forward returns over 20 and 60 bars, by sub-period.
   P4  Events: after a bar with extreme volume (zV >= 3) and a move of at least 2 sigma, the signed
       market-adjusted return over the next 5, 20 and 60 bars (+ = drift in the direction of the move).
   P5  The risk switch on the bars that matter to a swing trader: 20-bar forward return and the
       frequency of a loss beyond 3 sigma-units, long-term trend down against not down.

  python3 -I experiments/e27_pairing_evidence_modern.py [--panel DIR]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json
from multiprocessing import Pool

import numpy as np
import pandas as pd

import experiments.e05_validation_lite as e05
import experiments.e09_regime_risk as e09
import experiments.e18_relvol_v3_confirmation as e18
from experiments.e06_explore_reversal_momentum import extra
from experiments.e07_confirm_dip_momentum import DIP_Z, confirm_set, diff
from tfs.relvol import mechanical_day

PERIODS = {"2018-02..2019-12": ("2018-02-08", "2019-12-31"), "2020-01..2022-12": ("2020-01-01", "2022-12-31"),
           "2023-01..2026-10": ("2023-01-01", "2026-11-30")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=e18.DEFAULT_PANEL)
    ap.add_argument("--seed", type=int, default=2727)
    ap.add_argument("--reuse-part1", action="store_true", help="take the frozen tests from the saved results file")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    raw = pd.read_parquet(pathlib.Path(a.panel) / "panel_EM.parquet",
                          columns=["ticker", "date", "open", "high", "low", "close", "volume", "r", "gap", "eval"])
    bench = np.exp(raw.groupby("date")["r"].mean().sort_index().fillna(0.0).cumsum())      # equal-weight index of the set
    e05._BENCH = bench
    e09._BENCH = bench
    stocks = {t: g.set_index("date")[["open", "high", "low", "close", "volume"]] for t, g in raw.groupby("ticker", sort=False)}
    out = {"set": "EM", "stocks": len(stocks), "benchmark": "equal-weight index of the set"}

    # ---- Part 1: frozen tests
    res = pathlib.Path(__file__).resolve().parents[1] / "results" / "e27_pairing_evidence_modern.json"
    if a.reuse_part1 and res.exists():
        old = json.loads(res.read_text())
        out["C1_C4_frozen"], out["H1_risk_switch_frozen"] = old["C1_C4_frozen"], old["H1_risk_switch_frozen"]
    else:
        out["C1_C4_frozen"] = confirm_set("EM", stocks, rng)
        out["H1_risk_switch_frozen"] = e09.run_set("EM", stocks, PERIODS)
        res.write_text(json.dumps(out, indent=1, default=str))

    # ---- Part 2: exploratory
    with Pool(4) as pool:
        fp = pool.map(e05.features, sorted(stocks.items()), chunksize=4)
    exs = [extra(f[0]) for f in fp]
    pan = pd.concat([r[1] for r in fp], ignore_index=True).merge(pd.concat(exs, ignore_index=True), on=["ticker", "t"], how="left")
    vol = raw.sort_values(["ticker", "date"])
    groups = [(g["volume"].to_numpy(dtype=float), g["r"].to_numpy(dtype=float)) for _, g in vol.groupby("ticker", sort=True)]
    with Pool(3) as pool:
        zz = pool.map(e18.feats, groups, chunksize=16)
    vol = vol.assign(zv=np.concatenate([x[0] for x in zz]), zmove=np.concatenate([x[1] for x in zz]),
                     t=vol.groupby("ticker").cumcount())
    pan = pan.merge(vol[["ticker", "t", "date", "zv", "zmove", "gap"]], on=["ticker", "t"], how="left")
    pan["mech"] = mechanical_day(pd.DatetimeIndex(pan["date"]))
    up = (pan["ctx"] == 1).to_numpy()
    dip = pan["z5"].to_numpy() <= DIP_Z
    D = up & dip
    with np.errstate(invalid="ignore"):
        hv = (pan["zv"] >= 2).to_numpy()
        lv = (pan["zv"] < 2).to_numpy()
    mech = pan["mech"].to_numpy()
    out["P1_rule_D_and_volume"] = {
        "D_bars": int(D.sum()), "D_bars_with_unusual_volume_pct": round(100 * float(hv[D].mean()), 1),
        "unusual_minus_ordinary_volume": {k: diff(pan, D & hv & ~mech, D & lv & ~mech, k, rng) for k in ("f1", "f3", "f5", "f10", "fx5")},
        "D_with_unusual_volume_vs_uptrend_no_dip": {k: diff(pan, D & hv & ~mech, up & ~dip, k, rng) for k in ("f5", "f10")},
        "D_with_ordinary_volume_vs_uptrend_no_dip": {k: diff(pan, D & lv & ~mech, up & ~dip, k, rng) for k in ("f5", "f10")},
        "D_on_expiry_or_rebalance_days_vs_other_D": {k: diff(pan, D & mech, D & ~mech, k, rng) for k in ("f5", "f10")}}
    dt = pan["date"]
    out["P2_rule_D_by_period"] = {}
    for lab, (lo, hi) in PERIODS.items():
        m = ((dt >= lo) & (dt <= hi)).to_numpy()
        out["P2_rule_D_by_period"][lab] = {k: diff(pan, D & m, up & ~dip & m, k, rng) for k in ("f5", "f10", "fx5")}

    mkt_dn = (pan["mkt"] == -1).to_numpy()
    out["P2b_rule_D_by_market_trend"] = {
        "share_of_D_bars_with_market_trend_down_pct": round(100 * float(mkt_dn[D].mean()), 1),
        "market_not_down": {k: diff(pan, D & ~mkt_dn, up & ~dip & ~mkt_dn, k, rng) for k in ("f5", "f10")},
        "market_down": {k: diff(pan, D & mkt_dn, up & ~dip & mkt_dn, k, rng) for k in ("f5", "f10")}}

    def fifths(col, key, m):
        x = pan[col].where(pd.Series(m, index=pan.index))
        q = x.groupby(pan["date"]).transform(lambda s: pd.qcut(s.rank(method="first"), 5, labels=False) if s.notna().sum() >= 50 else np.nan).to_numpy()
        return diff(pan, q == 4, q == 0, key, rng)
    allm = np.ones(len(pan), dtype=bool)
    out["P3_selection_top_minus_bottom_fifth"] = {}
    for col in ("rs12_1", "hi252"):
        r = {"all": {k: fifths(col, k, allm) for k in ("fx20", "fx60")}}
        for lab, (lo, hi) in PERIODS.items():
            r[lab] = {"fx60": fifths(col, "fx60", ((dt >= lo) & (dt <= hi)).to_numpy())}
        out["P3_selection_top_minus_bottom_fifth"][col] = r

    with np.errstate(invalid="ignore"):
        ev = (pan["zv"] >= 3).to_numpy() & (np.abs(pan["zmove"].to_numpy()) >= 2) & ~mech
        sg = np.sign(pan["zmove"].to_numpy())
        gp = ev & (np.abs(pan["gap"].to_numpy() / pan_sig(pan)) >= 2)
    m = pan["month"].to_numpy()
    out["P4_event_drift"] = {"events": int(ev.sum()), "events_with_gap": int(gp.sum())}
    for lab, mask in (("all_events", ev), ("events_up", ev & (sg > 0)), ("events_down", ev & (sg < 0)), ("gap_events", gp)):
        out["P4_event_drift"][lab] = {k: e05.boot_mean((sg * pan[k].to_numpy())[mask], m[mask], rng) for k in ("fx5", "fx20", "fx60")}

    down = (pan["ctx"] == -1).to_numpy()
    f20 = pan["f20"].to_numpy()
    out["P5_long_term_trend_down_vs_not"] = {
        "share_of_bars_down_pct": round(100 * float(down.mean()), 1),
        "f20_down_minus_not_down": diff(pan, down, ~down, "f20", rng),
        "loss_beyond_3_units_over_20_bars_pct": {"down": round(100 * float(np.nanmean(f20[down] <= -3 / np.sqrt(20) * 1.0)), 2),
                                                 "not_down": round(100 * float(np.nanmean(f20[~down] <= -3 / np.sqrt(20) * 1.0)), 2)},
        "sd_of_f20": {"down": round(float(np.nanstd(f20[down])), 3), "not_down": round(float(np.nanstd(f20[~down])), 3)}}

    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e27_pairing_evidence_modern.json"
    p.write_text(json.dumps(out, indent=1, default=str))
    for k in ("P1_rule_D_and_volume", "P2_rule_D_by_period", "P2b_rule_D_by_market_trend", "P3_selection_top_minus_bottom_fifth", "P4_event_drift", "P5_long_term_trend_down_vs_not"):
        print(k, json.dumps(out[k], default=str))


def pan_sig(pan):
    """daily sigma implied by the panel: |f1| is in units of sig0, so recover sig0 from z5 and prices is not possible here;
    use the robust scale of the gap itself per stock as the unit."""
    g = pan["gap"]
    s = g.groupby(pan["ticker"]).transform(lambda x: 1.4826 * (x - x.median()).abs().median())
    return s.replace(0, np.nan).to_numpy()


if __name__ == "__main__":
    main()
