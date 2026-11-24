"""Compact family runner: one line per signal, DEV and CTX side by side.

    def build(S): return {"name": sig_bool, "name2": (sig_bool, control_bool), ...}
    run("g03", "G03_selection", build, hs=(5, 20, 60))

Each cell is XS bp (t): signal mean minus control mean on the same day, from the next open
(protocol sections 4-5). The control defaults to the whole universe. Everything is logged.
"""
from __future__ import annotations

import gc
import json
import os
from pathlib import Path

import numpy as np

from research.swinglab.study import Study


def run(tag: str, family: str, build, hs=(5, 20, 60), samples=("DEV", "CTX"), view: str = "xs", extra=None) -> dict:
    os.environ["SWINGLAB_REGISTRY_TAG"] = tag
    res: dict = {}
    order: list[str] = []
    for smp in samples:
        S = Study(smp)
        sigs = build(S)
        for name, v in sigs.items():
            sig, ctrl = (v if isinstance(v, tuple) else (v, None))
            t = S.event(tag.upper(), family, name, sig, control=ctrl, hs=hs)
            res.setdefault(name, {})[smp] = t
            if name not in order:
                order.append(name)
        if extra is not None:
            res.setdefault("_extra", {})[smp] = extra(S)
        del S, sigs
        gc.collect()
    head = "".join(f"  {smp}: " + " ".join(f"h={h:<2d} bp (t)   " for h in hs) + "      n" for smp in samples)
    print(f"\n== {family} ({view.upper()} view, from the next open){head}")
    for name in order:
        row = f"{name[:54]:<54s}"
        for smp in samples:
            t = res[name].get(smp)
            if t is None:
                row += " " * 60
                continue
            for h in hs:
                b, tt = t[h][f"{view}_bp"], t[h][f"{view}_t"]
                row += f" {b if b is not None else float('nan'):+7.1f}({tt if tt is not None else float('nan'):+5.1f})"
            row += f" {t[hs[0]]['events']:>8d}"
        print(row)
    out = Path(__file__).resolve().parents[1] / "results" / f"{tag}_{family.split('_', 1)[-1]}.json"
    out.write_text(json.dumps(res, indent=0, default=str))
    return res
