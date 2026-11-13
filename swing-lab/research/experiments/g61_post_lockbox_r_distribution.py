"""G61 - After the lockbox: what does one trade look like in R units? (descriptive, all data)

Random entries at the next open, stop k x ATR(14) below the fill, exit at the close of bar h,
protocol costs (5 bp a side at $50M median dollar volume and above, 10 bp below), 2018-07..2026-11
(the survivorship-free years). Used by the playbook to size the forward test. Not evidence.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ["SWINGLAB_REGISTRY_TAG"] = "g61"
os.environ["SWINGLAB_OPEN_LOCKBOX"] = "I-HAVE-FROZEN-THE-RULES"

import numpy as np

from research.swinglab import trades as TR
from research.swinglab.data import PARTITIONS, open_lockbox
from research.swinglab.registry import log_trial
from research.swinglab.study import Study


def main():
    panel = open_lockbox("post-evaluation description of trade outcomes in R units for the playbook (descriptive, G61)", ["none: descriptive"])
    PARTITIONS["LOCKBOX"] = ("2018-07-02", "2026-11-09")
    S = Study("LOCKBOX", panel=panel)
    rng = np.random.default_rng(12)
    rnd = S.uni & (rng.random(S.uni.shape) < 0.02)
    atr = S.atr(14)
    res = {}
    print("k   h    trades   mean R   sd R   median   P(R<-1)  P(R<-1.5)  P(R>+1)  P(R>+2)  win%   stopped  mean bars  mean ret bp")
    for k, h in ((2.0, 10), (3.0, 5), (3.0, 10), (3.0, 20), (4.0, 20)):
        tr = TR.simulate(S.P, rnd, atr, rows=S.rows, stop_k=k, max_hold=h, cost_bp=7.5, stop_extra_bp=10.0)
        R = tr["R"].to_numpy()
        r = {"trades": int(len(R)), "mean_R": float(R.mean()), "sd_R": float(R.std()), "median_R": float(np.median(R)), "p_lt_-1": float((R < -1).mean()),
             "p_lt_-1.5": float((R < -1.5).mean()), "p_gt_1": float((R > 1).mean()), "p_gt_2": float((R > 2).mean()), "win": float((R > 0).mean()),
             "stopped": float(tr["reason"].isin(["stop", "gap_stop"]).mean()), "bars": float(tr["bars"].mean()), "ret_bp": float(1e4 * tr["ret"].mean())}
        res[f"k{k}_h{h}"] = r
        print(f"{k:<3.1f} {h:<3d} {r['trades']:>8d}   {r['mean_R']:+.3f}   {r['sd_R']:.3f}   {r['median_R']:+.3f}   {100 * r['p_lt_-1']:5.1f}%   {100 * r['p_lt_-1.5']:5.2f}%    {100 * r['p_gt_1']:5.1f}%   {100 * r['p_gt_2']:5.2f}%   {100 * r['win']:.1f}   {100 * r['stopped']:5.1f}%   {r['bars']:.1f}      {r['ret_bp']:+.1f}")
    log_trial("G61", "G61_post_lockbox", "R distribution of random entries", "ALL", "descriptive", 0.0, note="after the lockbox; description, not evidence")
    (Path(__file__).resolve().parents[1] / "results" / "g61_post_lockbox_r_distribution.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
