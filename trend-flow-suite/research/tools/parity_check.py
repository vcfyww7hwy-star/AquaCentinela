"""Pine <-> Python parity check.

Proves that what TradingView plots is the same maths that the tests and experiments used.

Steps
1. In TradingView, add the script to a chart (symbol and timeframe you want to verify).
2. Export the chart data to CSV (chart layout menu -> "Export chart data..."). The export carries
   OHLCV plus one column per plot, including the hidden diagnostic series "dbg_*".
3. From research/:
     python3 -m tools.parity_check export.csv --script trend  [--intraday] [--tick 0.01]
     python3 -m tools.parity_check export.csv --script volume [--intraday]

The script recomputes every series from the exported OHLCV and compares it with TradingView's
values after a warm-up. Exit code 0 = parity, 1 = mismatch (details printed).

Notes
- Recursive filters converge from the first bar, so parity is exact only when the export starts at
  the first bar the script calculated on (TradingView exports all loaded bars).
- `--script trend` takes the long-term trend state from the export itself (dbg_ctx_dir), because the
  higher-timeframe bars are not in the file. Leave "D and B need the market trend not down" off.
- `--tick` must be the symbol's minimum price step (0.01 for most US stocks).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from tfs.data import COLS, load_tradingview_export
from tfs.flow import volume_flow_v2
from tfs.trend import TrendParams, trend_setups

SERIES = {
    "volume": {"dbg_z": "z", "dbg_rvol": "rvol", "dbg_ext": "ext"},
    "trend": {"dbg_ts": "ts", "dbg_dir": "dir", "dbg_dip_z": "dip_z", "dbg_ext": "ext",
              "dbg_last_sh": "last_sh", "dbg_last_sl": "last_sl", "dbg_avwap_low": "avwap_low",
              "dbg_sig": "sig", "dbg_sig_stop": "sig_stop", "dbg_entry": "entry",
              "dbg_exit_reason": "exit_reason"},
}


def _find(columns, key: str):
    hits = [c for c in columns if c.lower().endswith(key.lower())]
    return hits[0] if hits else None


def compare(tv: pd.DataFrame, script: str, intraday: bool, warmup: int, rtol: float, atol: float,
            tick: float = 0.01) -> tuple[bool, list[dict]]:
    if script == "volume":
        ours = volume_flow_v2(tv[COLS], intraday=intraday)
    else:
        ctx_col = _find(tv.columns, "dbg_ctx_dir")
        if ctx_col is None:
            return False, [{"series": "dbg_ctx_dir", "status": "missing in export (needed as input)"}]
        ctx = pd.to_numeric(tv[ctx_col], errors="coerce").fillna(0).round().astype(int).to_numpy()
        ours, _ = trend_setups(tv[COLS], intraday=intraday, p=TrendParams(tick=tick), htf_dir=ctx)
    rows, ok_all = [], True
    for key, col in SERIES[script].items():
        src = _find(tv.columns, key)
        if src is None:
            rows.append({"series": key, "status": "missing in export"})
            continue
        a = pd.to_numeric(tv[src], errors="coerce").to_numpy()[warmup:]
        b = ours[col].to_numpy().astype(float)[warmup:]
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
    ap.add_argument("--script", choices=sorted(SERIES), required=True)
    ap.add_argument("--intraday", action="store_true", help="chart timeframe is below 1D")
    ap.add_argument("--tz", default="America/New_York", help="exchange time zone (session detection)")
    ap.add_argument("--tick", type=float, default=0.01, help="minimum price step of the symbol")
    ap.add_argument("--warmup", type=int, default=600)
    ap.add_argument("--rtol", type=float, default=1e-6)
    ap.add_argument("--atol", type=float, default=1e-9)
    a = ap.parse_args(argv)
    tv = load_tradingview_export(a.csv)
    idx = tv.index if tv.index.tz is not None else tv.index.tz_localize("UTC")
    tv.index = idx.tz_convert(a.tz).tz_localize(None)
    ok, rows = compare(tv, a.script, a.intraday, a.warmup, a.rtol, a.atol, a.tick)
    print(pd.DataFrame(rows).to_string(index=False))
    print("\nPARITY OK" if ok else "\nPARITY FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
