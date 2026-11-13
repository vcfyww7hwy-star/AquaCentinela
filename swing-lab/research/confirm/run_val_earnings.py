"""Second (and last) pre-registered look at the validation sample: drift after earnings reactions.

Pre-registration: docs/04_preregistration_earnings.md, protocol amendment 3. Runs ONCE on VAL
(refuses if results/val_earnings.json exists). `--sample DEV` is a dry run on 2017-01..2018-06.

Family of two, published sign (post-earnings-announcement drift measured by the announcement
return: Chan, Jegadeesh & Lakonishok 1996; Brandt, Kishore, Santa-Clara & Venkatachalam 2008):
    PE1  reaction bar with a close-to-close move >= +3 sigma   -> outperforms over the next 20 bars
    PE2  reaction bar with a close-to-close move <= -3 sigma   -> underperforms over the next 20 bars
"Confirmed" needs: day-weighted Newey-West t (40 lags) with |t| >= 2.0 and one-sided Student-t p
significant under Holm at 5% across the two, AND the event-weighted estimate with the predicted
sign and one-sided p <= 0.10. Everything else printed is a declared diagnostic without a verdict.

    SWINGLAB_VAL_TOKEN=PRE-REGISTERED python -m research.confirm.run_val_earnings
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

from research.confirm.run_val import day_and_event, p_student
from research.swinglab import candidates as C
from research.swinglab import earnings as EA
from research.swinglab.registry import log_trial
from research.swinglab.study import Study

OUT = Path(__file__).resolve().parents[1] / "results" / "val_earnings.json"
H = 20
FAMILY = {"PE1_reaction_up_3sigma": +1, "PE2_reaction_down_3sigma": -1}
T_MIN, ALPHA, EW_P_MAX = 2.0, 0.05, 0.10


def main() -> int:
    sample = sys.argv[sys.argv.index("--sample") + 1] if "--sample" in sys.argv else "VAL"
    if sample == "VAL" and OUT.exists():
        print("The earnings validation run has already been made; refusing to repeat it.")
        return 2
    S = Study(sample)
    ev = EA.load(S)
    react = ev["react"] & S.uni
    z1 = S.z(1)
    sigs = {"PE1_reaction_up_3sigma": react & (z1 >= 3), "PE2_reaction_down_3sigma": react & (z1 <= -3)}
    res: dict = {"sample": sample, "reaction_bars": int(react.sum())}
    for name, sgn in FAMILY.items():
        st = day_and_event(S, sigs[name], None, H)
        p, df = p_student(st["t"], sgn, st["days"], H)
        ew_p = float(sps.norm.sf(sgn * st["ew_t"]))
        res[name] = {"h": H, "predicted_sign": sgn, "bp": round(st["bp"], 1), "t": round(st["t"], 2), "df": df, "p_one_sided": round(p, 5),
                     "event_weighted_bp": round(st["ew_bp"], 1), "event_weighted_t": round(st["ew_t"], 2), "event_weighted_p": round(ew_p, 4),
                     "events": st["events"], "days_with_signal": st["days"]}
        log_trial("VAL2", "VAL_earnings", name, S.sample, "xs_bp", st["bp"], tstat=st["t"], n=st["events"], params={"h": H}, note="pre-registered")
    order = sorted(FAMILY, key=lambda k: res[k]["p_one_sided"])
    still = True
    for i, k in enumerate(order):
        r = res[k]
        thr = ALPHA / (len(order) - i)
        holm_ok = still and r["p_one_sided"] <= thr and abs(r["t"]) >= T_MIN and np.sign(r["t"]) == r["predicted_sign"]
        still = holm_ok
        ew_ok = np.sign(r["event_weighted_bp"]) == r["predicted_sign"] and r["event_weighted_p"] <= EW_P_MAX
        r["holm_threshold"], r["day_weighted_pass"], r["event_weighted_pass"] = round(thr, 4), bool(holm_ok), bool(ew_ok)
        r["verdict"] = "CONFIRMED" if (holm_ok and ew_ok) else ("right sign, not significant" if np.sign(r["bp"]) == r["predicted_sign"] else "WRONG SIGN")
    # ---- declared diagnostics, no verdict
    diag = {}
    for name in FAMILY:
        for h in (5, 10, 60):
            st = day_and_event(S, sigs[name], None, h)
            diag[f"{name}_h{h}"] = {"bp": round(st["bp"], 1), "t": round(st["t"], 2), "event_weighted_bp": round(st["ew_bp"], 1), "event_weighted_t": round(st["ew_t"], 2)}
            log_trial("VAL2", "VAL_earnings_diag", f"{name} h{h}", S.sample, "xs_bp", st["bp"], tstat=st["t"], n=st["events"], params={"h": h}, note="declared diagnostic")
    F = C.Feat(S)
    e1, _ = C.SPEC["E1_episodic_pivot"]["fn"](F)
    for lab, m in (("E1_on_reaction_bars", e1 & ev["react"]), ("E1_off_reaction_bars", e1 & ~ev["react"])):
        st = day_and_event(S, m, None, 10)
        diag[lab] = {"h": 10, "bp": round(st["bp"], 1), "t": round(st["t"], 2), "event_weighted_bp": round(st["ew_bp"], 1), "event_weighted_t": round(st["ew_t"], 2), "events": st["events"]}
        log_trial("VAL2", "VAL_earnings_diag", lab, S.sample, "xs_bp", st["bp"], tstat=st["t"], n=st["events"], params={"h": 10}, note="declared diagnostic")
    res["diagnostics"] = diag
    if sample == "VAL":
        OUT.write_text(json.dumps(res, indent=1, default=str))
    else:
        OUT.with_name(f"val_earnings_dryrun_{sample}.json").write_text(json.dumps(res, indent=1, default=str))
    print(f"\nSAMPLE {sample}  reaction bars in the universe: {res['reaction_bars']}")
    for k in FAMILY:
        r = res[k]
        print(f"  {k:<28s} h={r['h']} sign {r['predicted_sign']:+d} | day-wtd {r['bp']:+7.1f} bp (t {r['t']:+5.2f}, df {r['df']}) p {r['p_one_sided']:.4f} thr {r['holm_threshold']:.3f} | "
              f"event-wtd {r['event_weighted_bp']:+7.1f} (t {r['event_weighted_t']:+5.2f}) p {r['event_weighted_p']:.3f} | {r['verdict']}  n={r['events']}")
    for k, v in diag.items():
        print(f"     diagnostic {k:<34s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
