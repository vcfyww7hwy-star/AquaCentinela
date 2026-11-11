"""The single lockbox run (protocol sections 1-3; docs/05_preregistration_lockbox.md).

Sample LOCKBOX: 2023-01-03 .. 2026-11-09, survivorship-free, never read before this run.
Opening it writes a dated record to registry/lockbox.json; the script refuses to run if
results/lockbox.json exists. `--sample VAL` executes the same code on validation data as a dry
run (it must reproduce the validation results for the unchanged claims) and opens nothing.

    SWINGLAB_OPEN_LOCKBOX=I-HAVE-FROZEN-THE-RULES python -m research.confirm.run_lockbox
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DRY = "--sample" in sys.argv and sys.argv[sys.argv.index("--sample") + 1] != "LOCKBOX"
os.environ["SWINGLAB_REGISTRY_TAG"] = "dryrun" if DRY else "lockbox"

import numpy as np
from scipy import stats as sps

from research.confirm import prereg_lockbox as LB
from research.confirm import prereg_val as PR
from research.confirm import run_val as RV
from research.swinglab import candidates as C
from research.swinglab import earnings as EA
from research.swinglab import engine as E
from research.swinglab.data import open_lockbox
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

OUT = Path(__file__).resolve().parents[1] / "results" / "lockbox.json"


def directional_one(S, sig, h, sgn, name):
    st = RV.day_and_event(S, sig, None, h)
    p, df = RV.p_student(st["t"], sgn, st["days"], h)
    ew_p = float(sps.norm.sf(sgn * st["ew_t"]))
    r = {"h": h, "predicted_sign": sgn, "bp": round(st["bp"], 1), "t": round(st["t"], 2), "df": df, "p_one_sided": round(p, 5),
         "event_weighted_bp": round(st["ew_bp"], 1), "event_weighted_t": round(st["ew_t"], 2), "event_weighted_p": round(ew_p, 4),
         "events": st["events"], "days_with_signal": st["days"]}
    r["day_weighted_pass"] = bool(np.sign(st["bp"]) == sgn and p <= LB.E1_P_MAX)
    r["event_weighted_pass"] = bool(np.sign(st["ew_bp"]) == sgn and ew_p <= LB.EW_P_MAX)
    r["pass"] = bool(r["day_weighted_pass"] and r["event_weighted_pass"])
    r["sign_agrees"] = bool(np.sign(st["bp"]) == sgn and np.sign(st["ew_bp"]) == sgn)
    log_trial("LOCKBOX", "LOCKBOX_directional", name, S.sample, "xs_bp", st["bp"], tstat=st["t"], n=st["events"], params={"h": h}, note="frozen list")
    return r, st["d"]


def slice_rows(S, a, b):
    return S.rows & (S.dates >= np.datetime64(a)) & (S.dates <= np.datetime64(b))


def directional(S, post) -> dict:
    res = {}
    F = C.Feat(S)
    ev = EA.load(S)
    e1, _ = C.SPEC["E1_episodic_pivot"]["fn"](F)
    res["L5_E1"], d = directional_one(S, e1, 10, +1, "L5 E1")
    out = S.fwd(10)
    s = e1 & S.uni & np.isfinite(out)
    m_ctl, _ = E.day_means(out, S.uni, 20)
    cost = np.where(S.adv60 >= 50e6, 0.0010, 0.0020)
    diag = {"event_weighted_net_of_protocol_costs_bp": round(1e4 * float(np.nanmean((out - m_ctl[:, None] - cost)[s])), 1),
            "raw_net_return_bp": round(1e4 * float(np.nanmean((out - cost)[s])), 1),
            "signals_per_month": round(float(s.sum() / (S.rows.sum() / 21.0)), 1)}
    T = F.c.shape[0]
    survives = (S.P.last[None, :] >= np.arange(T)[:, None] + 126) | S.P.alive[None, :]
    for lab, m in (("excluding_names_gone_within_126_bars", e1 & survives), ("on_reaction_bars", e1 & ev["react"]), ("off_reaction_bars", e1 & ~ev["react"]),
                   ("half_A", e1 & S.half_a[None, :]), ("half_B", e1 & ~S.half_a[None, :])):
        st = RV.day_and_event(S, m, None, 10)
        diag[lab] = {"bp": round(st["bp"], 1), "t": round(st["t"], 2), "event_weighted_bp": round(st["ew_bp"], 1), "events": st["events"]}
    if post is not None and post.sum() > 15:
        dd = d[post]
        diag["post_cutoff_slice"] = {"mean_daily_spread_bp": round(1e4 * float(np.nanmean(dd)), 1) if np.isfinite(dd).any() else None,
                                     "days_with_signal": int(np.isfinite(dd).sum()), "events": int((e1 & S.uni & post[:, None] & np.isfinite(out)).sum())}
    res["L5_E1"]["diagnostics"] = diag
    pe1 = ev["react"] & S.uni & (S.z(1) >= 3)
    res["S1_PE1"], _ = directional_one(S, pe1, LB.PE1_H, +1, "S1 PE1")
    return res


def product(S, risk, post) -> dict:
    """The constants the scripts display, tested exactly as displayed."""
    from research.experiments.g50_calibration import band_y
    res = {"bands": {}}
    ok_all = True
    for h, (q05, q25, q75, q95) in LB.PRODUCT_BANDS.items():
        y, ok = band_y(S, h)
        v = y[ok]
        c90, c50 = float(np.mean((v >= q05) & (v <= q95))), float(np.mean((v >= q25) & (v <= q75)))
        cell = {"coverage_90": round(c90, 4), "coverage_50": round(c50, 4), "below_5pct_line": round(float(np.mean(v < q05)), 4),
                "above_95pct_line": round(float(np.mean(v > q95)), 4), "n": int(len(v)),
                "by_block_90": [round(float(np.mean((y[ok & slice_rows(S, a, b)[:, None]] >= q05) & (y[ok & slice_rows(S, a, b)[:, None]] <= q95))), 4)
                                for a, b in (LB.BLOCKS if S.sample == "LOCKBOX" else PR.RISK_CRITERIA["blocks"]) if (ok & slice_rows(S, a, b)[:, None]).sum() > 1000]}
        if post is not None and (ok & post[:, None]).sum() > 1000:
            vp = y[ok & post[:, None]]
            cell["post_cutoff_slice"] = {"coverage_90": round(float(np.mean((vp >= q05) & (vp <= q95))), 4), "coverage_50": round(float(np.mean((vp >= q25) & (vp <= q75))), 4), "n": int(len(vp))}
        cell["pass"] = bool(LB.BAND90_COVERAGE[0] <= c90 <= LB.BAND90_COVERAGE[1] and LB.BAND50_COVERAGE[0] <= c50 <= LB.BAND50_COVERAGE[1])
        ok_all &= cell["pass"]
        res["bands"][h] = cell
        log_trial("LOCKBOX", "LOCKBOX_product", f"bands h{h}", S.sample, "coverage_90", c90, note="frozen list")
    res["bands_pass"] = bool(ok_all)
    worst = 0.0
    tab = {}
    for key, ref in LB.PRODUCT_STOP_TABLE.items():
        val = risk["R3_stop_table"][key]["val"]
        tab[key] = {"observed": val, "displayed": ref, "diff": round(val - ref, 3)}
        worst = max(worst, abs(val - ref))
    res["stop_table"] = tab
    res["stop_table_max_abs_diff"] = round(worst, 3)
    res["stop_table_pass"] = bool(worst <= LB.PRODUCT_STOP_TOLERANCE)
    eg = risk["R4_earnings_gap"]
    obs = {"p_gap_lt_-1atr": eg["p_gap_lt_-1atr_reaction"], "p_gap_lt_-2atr": eg["p_gap_lt_-2atr_reaction"], "p_gap_lt_-3atr": eg["p_gap_lt_-3atr_reaction"]}
    res["earnings_odds"] = {"observed": obs, "displayed": LB.PRODUCT_EARNINGS}
    res["earnings_odds_pass"] = bool(all(lo <= obs[k] <= hi for k, (lo, hi) in LB.EARNINGS_RANGES.items()))
    return res


def main() -> int:
    sample = sys.argv[sys.argv.index("--sample") + 1] if "--sample" in sys.argv else "LOCKBOX"
    if sample == "LOCKBOX":
        if OUT.exists():
            print("The lockbox has already been opened and evaluated; refusing to repeat it (protocol section 2).")
            return 2
        panel = open_lockbox("single frozen evaluation, docs/05_preregistration_lockbox.md", LB.PRIMARY + LB.SECONDARY)
        S = Study("LOCKBOX", panel=panel)
        PR.RISK_CRITERIA = {**PR.RISK_CRITERIA, "blocks": LB.BLOCKS}
        post = slice_rows(S, *LB.POSTCUTOFF)
    else:
        S = Study(sample)
        post = None
    res = {"sample": sample, "dates": [str(S.dates[S.rows][0]), str(S.dates[S.rows][-1])], "trading_days": int(S.rows.sum()),
           "universe_names_per_day": float(S.uni[S.rows].sum(axis=1).mean())}
    res["directional"] = directional(S, post)
    res["risk"] = RV.risk(S)
    res["product"] = product(S, res["risk"], post)
    R, P, D = res["risk"], res["product"], res["directional"]
    res["verdicts"] = {
        "L1_range_calibration": bool(R["R2_pass"] and P["bands_pass"]),
        "L2_stop_out_odds": bool(R["R3_pass"] and P["stop_table_pass"]),
        "L3_earnings_gap_risk": bool(R["R4_pass"] and P["earnings_odds_pass"]),
        "L4_market_state": bool(R["R6_pass"]),
        "L5_E1": bool(D["L5_E1"]["pass"]),
        "S1_PE1_secondary": {"pass": bool(D["S1_PE1"]["pass"]), "sign_agrees": bool(D["S1_PE1"]["sign_agrees"])},
        "S2_R1_secondary": bool(R["R1_pass"]),
        "S3_R5_secondary": bool(R["R5_pass"]),
        "E1_sign_agrees": bool(D["L5_E1"]["sign_agrees"]),
    }
    target = OUT if sample == "LOCKBOX" else OUT.with_name(f"lockbox_dryrun_{sample}.json")
    target.write_text(json.dumps(res, indent=1, default=str))
    print(f"\nSAMPLE {sample} {res['dates']}  {res['trading_days']} days  {res['universe_names_per_day']:.0f} names a day")
    for k in ("L5_E1", "S1_PE1"):
        r = D[k]
        print(f"  {k:<8s} h={r['h']:<2d} | day-wtd {r['bp']:+7.1f} bp (t {r['t']:+5.2f}, df {r['df']}) p {r['p_one_sided']:.4f} | event-wtd {r['event_weighted_bp']:+7.1f} (t {r['event_weighted_t']:+5.2f}) p {r['event_weighted_p']:.3f} | n={r['events']} | pass {r['pass']}")
    print("     E1 diagnostics:", D["L5_E1"]["diagnostics"])
    print("  R1 ", R["R1_forecast_ranking"], "PASS" if R["R1_pass"] else "FAIL", " refit", R["R1b_scale_refit"])
    print("  R2 ", R["R2_calibration"], "PASS" if R["R2_pass"] else "FAIL")
    print("  bands", {h: {k: v for k, v in c.items()} for h, c in P["bands"].items()}, "PASS" if P["bands_pass"] else "FAIL")
    print("  R3 max |diff| vs development", R["R3_max_abs_diff"], R["R3_stop_table"]["k2.0_h10"], "PASS" if R["R3_pass"] else "FAIL")
    print("  displayed stop table: max |diff|", P["stop_table_max_abs_diff"], {k: v["observed"] for k, v in P["stop_table"].items()}, "PASS" if P["stop_table_pass"] else "FAIL")
    print("  R4 ", R["R4_earnings_gap"], "PASS" if R["R4_pass"] else "FAIL", "| displayed odds", "PASS" if P["earnings_odds_pass"] else "FAIL")
    print("  R5 ", R["R5_exits"], "PASS" if R["R5_pass"] else "FAIL")
    print("  R6 ", R["R6_regime"], "PASS" if R["R6_pass"] else "FAIL")
    print("\nVERDICTS", json.dumps(res["verdicts"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
