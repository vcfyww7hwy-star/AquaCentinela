"""Synthetic check of what happens to a position when a security stops trading.

Simulated prices test code only (protocol section 1). Three securities over 40 bars:
  0  trades throughout, flat at 100
  1  stops after bar 20 at 45 following a slide from 100 ("for cause": lost more than half in 60 bars)
  2  stops after bar 20 at 100 (a take-over: not for cause)
Expected: a forward return whose window crosses the last bar exits at the last close, with a -30%
haircut only for security 1; the trade simulator does the same; no outcome is produced for entries
after the last bar.
Run: python -m research.tests.test_delisting
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from research.swinglab import engine as E
from research.swinglab import trades as TR


class Fake:
    def __init__(self):
        T, N = 40, 3
        c = np.full((T, N), 100.0)
        c[:21, 1] = np.linspace(100, 45, 21)
        c[21:, 1] = np.nan
        c[21:, 2] = np.nan
        self.c = c.astype(np.float32)
        self.o, self.h, self.l = self.c.copy(), self.c.copy(), self.c.copy()
        self.v = np.where(np.isfinite(c), 1e6, np.nan).astype(np.float32)
        self.c_raw = self.c.copy()
        self.div = np.zeros((T, N), dtype=np.float32)
        self.bad = np.zeros((T, N), dtype=np.int8)
        self.dates = np.arange(T)


def main() -> int:
    P = E.prepare(Fake())
    ok = True
    def check(name, got, want, tol=1e-6):
        nonlocal ok
        good = (np.isnan(got) and np.isnan(want)) or abs(got - want) <= tol
        ok &= bool(good)
        print(f"{'ok  ' if good else 'FAIL'} {name}: got {got:.6f}, expected {want:.6f}")
    check("alive flags (0 alive, 1 and 2 ended)", float(P.alive[0]) + 10 * float(P.alive[1]) + 100 * float(P.alive[2]), 1.0)
    check("cause flags (only 1)", float(P.cause[0]) + 10 * float(P.cause[1]) + 100 * float(P.cause[2]), 10.0)
    f = E.fwd_ret_open(P, 10)
    # signal at bar 15: entry at the open of 16, window ends at bar 25, beyond the last bar (20)
    e16_1 = float(P.o[16, 1])
    check("security 1, window crosses the end: exit at last close with -30%", float(f[15, 1]), 45.0 / e16_1 * 0.7 - 1)
    check("security 2, window crosses the end: exit at last close, no haircut", float(f[15, 2]), 0.0)
    check("security 1, window inside its life (signal bar 5, h=10)", float(f[5, 1]), float(P.c[15, 1] / P.o[6, 1] - 1))
    check("security 1, signal on its last bar: no entry possible", float(f[20, 1]), np.nan)
    check("security 0, ordinary", float(f[15, 0]), 0.0)
    sig = np.zeros((40, 3), dtype=bool)
    sig[15, :] = True
    atr = np.full((40, 3), 2.0)
    tr = TR.simulate(P, sig, atr, rows=np.arange(40) < 39, stop_k=1e6, max_hold=10, cost_bp=0, stop_extra_bp=0)
    by = {int(r.col): r for r in tr.itertuples()}
    check("simulator, security 1: delisting exit with haircut", float(by[1].ret), 45.0 / e16_1 * 0.7 - 1)
    check("simulator, security 2: delisting exit without haircut", float(by[2].ret), 0.0)
    check("simulator, security 0: time exit", float(by[0].ret), 0.0)
    print("reasons:", {k: v.reason for k, v in by.items()})
    print("RESULT:", "delisting handled as documented" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
