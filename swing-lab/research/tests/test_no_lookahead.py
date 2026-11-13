"""Every frozen candidate must give the same signal whether or not the future exists.

Build each candidate on a Study truncated at row t_cut and on the full Study; the signals must be
identical on every row before t_cut. Run: python -m research.tests.test_no_lookahead
"""
from __future__ import annotations

import sys

import numpy as np

from research.swinglab import candidates as C
from research.swinglab.study import Study


def main() -> int:
    bad = 0
    for smp, cuts in (("DEV", (900, 1500)), ("CTX", (1200, 2600))):
        S = Study(smp)
        F = C.Feat(S)
        full = {k: v["fn"](F) for k, v in C.SPEC.items()}
        for t_cut in cuts:
            T = S.truncated(t_cut)
            FT = C.Feat(T)
            for name, spec in C.SPEC.items():
                sig_t, ctl_t = spec["fn"](FT)
                sig_f, ctl_f = full[name]
                same = np.array_equal(sig_t, sig_f[:t_cut])
                if ctl_t is not None:
                    same &= np.array_equal(ctl_t, ctl_f[:t_cut])
                n = int(sig_t.sum())
                if not same:
                    bad += 1
                    diff = int((sig_t != sig_f[:t_cut]).sum())
                    print(f"LOOK-AHEAD  {smp} cut={t_cut} {name}: {diff} cells differ of {n} signals")
            print(f"{smp} cut at row {t_cut} ({S.dates[t_cut]}): {len(C.SPEC)} candidates compared")
        del S, F
    print("RESULT:", "no candidate depends on future rows" if bad == 0 else f"{bad} FAILURES")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
