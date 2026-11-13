"""G60 - After the lockbox: why were earnings nights more dangerous than displayed?

Descriptive only. The lockbox evaluation is finished (research/results/lockbox.json); this reads
the full panel again to recalibrate one displayed constant, and the reading is recorded in
registry/lockbox.json. Nothing computed here is evidence: the recalibrated odds are "untested".

Opening gap of the reaction bar in units of the previous bar's ATR(14), by year and by whether
the time of day of the announcement is known (known from 2020; before that the reaction bar is
guessed from volume, and a wrong guess dilutes the odds with an ordinary night).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["SWINGLAB_REGISTRY_TAG"] = "g60"
os.environ["SWINGLAB_OPEN_LOCKBOX"] = "I-HAVE-FROZEN-THE-RULES"

import numpy as np

from research.swinglab import earnings as EA
from research.swinglab import pinelike as ta
from research.swinglab.data import PARTITIONS, open_lockbox
from research.swinglab.registry import log_trial
from research.swinglab.study import Study


def main():
    panel = open_lockbox("post-evaluation recalibration of the displayed earnings odds (descriptive, G60)", ["none: descriptive"])
    PARTITIONS["LOCKBOX"] = ("2017-01-03", "2026-11-09")         # read all years with earnings dates in one pass
    S = Study("LOCKBOX", panel=panel)
    ev = EA.load(S)
    c = S.P.cf
    atr = S.atr(14)
    with np.errstate(divide="ignore", invalid="ignore"):
        g = (S.P.o - ta.shift(c, 1)) / ta.shift(atr, 1)
    react = ev["react"] & S.uni & np.isfinite(g)
    # time of day of the announcement that produced each reaction bar
    when_r = np.where(ev["ann"] & react, ev["when"], 0)
    prev = np.zeros_like(ev["when"]); prev[1:] = ev["when"][:-1]
    prev_ann = np.zeros_like(ev["ann"]); prev_ann[1:] = ev["ann"][:-1]
    when_r = np.where(react & (when_r == 0) & prev_ann, prev, when_r)
    yrs = S.dates.astype("datetime64[Y]").astype(int) + 1970
    res = {}
    print("year   n    time known   P(<-1 ATR)  P(<-2)  P(<-3)   P(>+1)  P(>+2)   median ATR%")
    for y in range(2017, 2027):
        m = react & (yrs == y)[:, None]
        if m.sum() < 200:
            continue
        v = g[m]
        res[y] = {"n": int(m.sum()), "time_known": float((when_r[m] > 0).mean()), "lt-1": float((v < -1).mean()), "lt-2": float((v < -2).mean()),
                  "lt-3": float((v < -3).mean()), "gt+1": float((v > 1).mean()), "gt+2": float((v > 2).mean()),
                  "atr_pct": float(np.nanmedian((atr / c)[m]) * 100)}
        r = res[y]
        print(f"{y} {r['n']:>6d}   {100 * r['time_known']:5.1f}%      {100 * r['lt-1']:5.1f}%   {100 * r['lt-2']:5.1f}%  {100 * r['lt-3']:5.1f}%   {100 * r['gt+1']:5.1f}%  {100 * r['gt+2']:5.1f}%     {r['atr_pct']:.2f}")
    for lab, m in (("time known", react & (when_r > 0)), ("time unknown", react & (when_r == 0)), ("all, 2017-2026", react),
                   ("time known, 2020-2026", react & (when_r > 0) & (yrs >= 2020)[:, None])):
        v = g[m]
        res[lab] = {"n": int(m.sum()), "lt-1": float((v < -1).mean()), "lt-2": float((v < -2).mean()), "lt-3": float((v < -3).mean()),
                    "gt+1": float((v > 1).mean()), "gt+2": float((v > 2).mean()), "gt+3": float((v > 3).mean())}
        r = res[lab]
        print(f"{lab:<24s} n={r['n']:>6d}  down: {100 * r['lt-1']:.1f}% / {100 * r['lt-2']:.1f}% / {100 * r['lt-3']:.1f}%   up: {100 * r['gt+1']:.1f}% / {100 * r['gt+2']:.1f}% / {100 * r['gt+3']:.1f}%")
    log_trial("G60", "G60_post_lockbox", "earnings gap odds by year and by known time of day", "ALL", "descriptive", 0.0, note="after the lockbox; recalibration, not evidence")
    (Path(__file__).resolve().parents[1] / "results" / "g60_post_lockbox_earnings.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
