# E01: VFI diagnostics (Nov 2026)

These are the scripts behind the numbers in `docs/01_vfi_critique.md`. They are kept as run.

| Script | Measures |
|---|---|
| `vfi_diag.py` | Faithful replication; change decomposition; information content; illustrative regime tests |
| `vfi_diag2.py` | Big Swing mechanics; kernel comparison and hysteresis; lag at major S&P turns |
| `vfi_diag3.py` | Volume-free copy regime test; step responses |
| `vfi_diag4.py` | Kernel/hysteresis effect on regime outcomes |
| `vfi_diag5.py` | Buy/Sell band width and repeated signals |

Run: `python3 vfi_diag.py`. Scripts 2–5 take the path of `vfi_diag.py` as an argument.
