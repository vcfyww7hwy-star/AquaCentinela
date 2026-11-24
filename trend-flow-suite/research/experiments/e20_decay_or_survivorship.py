#!/usr/bin/env python3
"""E20 - The old mark has an effect before about 2014 and none in 2018-2026. Did the effect decay,
is it a difference between data sources, or is it a survivorship artefact that grows with the time
between the event and the date of the data snapshot?

Test: the strict-control comparison of E11 (mark = ext<=-1.5 & |z|<=0.5 & rvol>=2 against the same
price action with rvol<2; fzd10, month-block bootstrap) on
  - the same calendar periods seen from two snapshots: set MS (stocks listed in Nov 2017) and set EO
    (the 2026 source restricted to 2006-2017: stocks still listed in Nov 2026);
  - MS stocks that are in the 2026 file against MS stocks that are not (delisted, acquired, renamed,
    or simply absent from that collection);
  - set EM (2018-2026) by period.
Reading: if survivorship drove the effect, the snapshot that demands more years of survival would
show more of it in the same period. EO is built with experiments/e10b_build_em_panel.py (see there).

  python3 -I experiments/e20_decay_or_survivorship.py [--panel DIR]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import argparse
import json

import numpy as np
import pandas as pd

import experiments.e05_validation_lite as e05

DEFAULT_PANEL = "/tmp/claude-0/-home-user-AquaCentinela/b2916ecb-3cd8-557a-8730-1dacd8557876/scratchpad/panel"
COLS = ["ticker", "date", "month", "eval", "ext", "z", "rvol", "fzd10", "fx10"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=DEFAULT_PANEL)
    a = ap.parse_args()
    pan = {s: pd.read_parquet(pathlib.Path(a.panel) / f"panel_{s}.parquet", columns=COLS) for s in ("A", "B", "MS", "EO", "EM")}
    pan = {s: d[d["eval"]] for s, d in pan.items()}
    ms_t, eo_t = set(pan["MS"]["ticker"].unique()), set(pan["EO"]["ticker"].unique())

    def run(name, lo, hi, tickers=None, seed=3):
        p = pan[name]
        p = p[(p["date"] >= lo) & (p["date"] < hi)]
        if tickers is not None:
            p = p[p["ticker"].isin(tickers)]
        s = (p["ext"] <= -1.5) & (p["z"].abs() <= 0.5) & p["rvol"].notna()
        t, c = (s & (p["rvol"] >= 2)).to_numpy(), (s & (p["rvol"] < 2)).to_numpy()
        rng, m = np.random.default_rng(seed), p["month"].to_numpy()
        out = {"stocks": int(p["ticker"].nunique()), "marks": int(t.sum())}
        for k, sc in (("fzd10", 1.0), ("fx10", 100.0)):
            v = p[k].to_numpy() * sc
            out[k if sc == 1.0 else "fx10_pct"] = e05.boot_diff(v[t], m[t], v[c], m[c], rng)
        return out

    res = {
        "same_period_two_snapshots": {
            "2014-11..2017-10 MS (listed Nov 2017, 0-3 years of survival)": run("MS", "2014-11-01", "2017-11-11"),
            "2014-11..2017-10 EO (listed Nov 2026, 9-12 years)": run("EO", "2014-11-01", "2017-11-11"),
            "2006-08..2014-10 MS (3-11 years)": run("MS", "2006-08-01", "2014-11-01"),
            "2006-08..2014-10 EO (12-20 years)": run("EO", "2006-08-01", "2014-11-01"),
            "2014-09..2018-01 A (listed Feb 2018)": run("A", "2014-09-01", "2018-03-01"),
            "2014-09..2018-01 B (listed Feb 2018)": run("B", "2014-09-01", "2018-03-01"),
        },
        "ms_by_presence_in_2026_file": {
            "MS tickers also in the 2026 file": run("MS", "2006-08-01", "2017-11-11", ms_t & eo_t),
            "MS tickers not in the 2026 file": run("MS", "2006-08-01", "2017-11-11", ms_t - eo_t),
            "MS tickers not in the 2026 file, 2014-11..2017-10": run("MS", "2014-11-01", "2017-11-11", ms_t - eo_t),
        },
        "em_by_period": {f"{lo[:7]}..{hi[:7]}": run("EM", lo, hi) for lo, hi in
                         (("2018-02-08", "2020-02-01"), ("2020-02-01", "2020-07-01"), ("2020-07-01", "2023-01-01"),
                          ("2023-01-01", "2025-01-01"), ("2025-01-01", "2026-11-30"))},
        "eo_whole": run("EO", "2006-08-01", "2017-11-11"),
        "tickers": {"MS": len(ms_t), "EO": len(eo_t), "both": len(ms_t & eo_t)},
    }
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "e20_decay_or_survivorship.json"
    p.write_text(json.dumps(res, indent=1))
    for grp, d in res.items():
        if grp in ("eo_whole", "tickers"):
            print(grp, d if grp == "tickers" else (d["marks"], d["fzd10"]))
            continue
        print(grp)
        for k, v in d.items():
            f = v["fzd10"]
            print(f"  {k:62s} stocks={v['stocks']:5d} marks={v['marks']:5d} fzd10 {f['diff']:+.3f} [{f['lo']:+.3f},{f['hi']:+.3f}]")


if __name__ == "__main__":
    main()
