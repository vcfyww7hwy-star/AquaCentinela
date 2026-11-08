"""Pine <-> Python parity check for Volume Flow v2.

Proves that what TradingView plots is the same maths that the tests and experiments validated.

Steps
1. In TradingView, add "Volume Flow v2" to a chart (symbol and timeframe you want to verify).
2. Export the chart data to CSV (chart layout menu -> "Export chart data..."). The export carries
   OHLCV plus one column per plot, including the hidden diagnostic series "dbg_*".
3. From research/:  python3 -m tools.parity_check path/to/export.csv [--intraday]

The script recomputes every series from the exported OHLCV and compares it with TradingView's
values after a warm-up. Exit code 0 = parity, 1 = mismatch (details printed).
Recursive filters converge from the first bar, so parity is exact only when the export starts
at the first bar the script calculated on (TradingView exports all loaded bars).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from tfs.data import COLS, load_tradingview_export
from tfs.flow import volume_flow_v2

SERIES = {"dbg_z": "z", "dbg_s": "s", "dbg_rvol": "rvol", "dbg_f_fast": "f_fast",
          "dbg_f_slow": "f_slow", "dbg_asym_z": "asym_z", "dbg_asym": "asym", "dbg_ext": "ext",
          "dbg_persist_c": "persist_c"}


def _find(columns, key: str):
    hits = [c for c in columns if c.lower().endswith(key.lower())]
    return hits[0] if hits else None


def compare(tv: pd.DataFrame, intraday: bool, warmup: int, rtol: float, atol: float) -> tuple[bool, list[dict]]:
    ours = volume_flow_v2(tv[COLS], intraday=intraday)
    rows, ok_all = [], True
    for key, col in SERIES.items():
        src = _find(tv.columns, key)
        if src is None:
            rows.append({"series": key, "status": "missing in export"})
            continue
        a = pd.to_numeric(tv[src], errors="coerce").to_numpy()[warmup:]
        b = ours[col].to_numpy()[warmup:]
        both = ~np.isnan(a) & ~np.isnan(b)
        nan_mismatch = int((np.isnan(a) != np.isnan(b)).sum())
        diff = np.abs(a[both] - b[both])
        tol = atol + rtol * np.abs(b[both])
        ok = nan_mismatch == 0 and bool((diff <= tol).all())
        ok_all &= ok
        rows.append({"series": key, "status": "OK" if ok else "MISMATCH", "bars": int(both.sum()),
                     "max_abs_diff": float(diff.max()) if diff.size else 0.0,
                     "nan_pattern_mismatches": nan_mismatch})
    return ok_all, rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--intraday", action="store_true", help="chart timeframe is below 1D")
    ap.add_argument("--tz", default="America/New_York", help="exchange time zone (session detection)")
    ap.add_argument("--warmup", type=int, default=600)
    ap.add_argument("--rtol", type=float, default=1e-6)
    ap.add_argument("--atol", type=float, default=1e-9)
    a = ap.parse_args(argv)
    tv = load_tradingview_export(a.csv)
    idx = tv.index if tv.index.tz is not None else tv.index.tz_localize("UTC")
    tv.index = idx.tz_convert(a.tz).tz_localize(None)
    ok, rows = compare(tv, a.intraday, a.warmup, a.rtol, a.atol)
    print(pd.DataFrame(rows).to_string(index=False))
    print("\nPARITY OK" if ok else "\nPARITY FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
