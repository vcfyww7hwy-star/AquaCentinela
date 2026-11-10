# Relative Volume pane: specification and evidence

- **Script:** `pine/relative_volume.pine` (lower pane). It replaces "Volume Flow v2".
- **Python twin:** `research/tfs/flow.py` (series `rvol`, `z`, `ext`, `absorb_bottom`, `climax_up`, `climax_dn`, `dryup`).
- **Status:** rebuilt 10 Nov 2026 after the tests in `06_validation_lite.md`. Not yet compiled in TradingView.

## Why it shrank

Volume Flow v2 showed flow lines, an accumulation / distribution tint, climax, absorption and
divergence marks. Tested on about 1.7 million stock-days (E05, E08):

| Signal | 10-bar forward return vs control (risk units), sets A / B / DJ / LH |
|---|---|
| Accumulation state (asymmetry ≥ +2σ), predicted positive | −0.06 / −0.02 / −0.02 / −0.03 |
| Distribution state (asymmetry ≤ −2σ), predicted negative | +0.08 / +0.05 / +0.08 / +0.02 |
| Buying climax, predicted negative | +0.01 / −0.09 / +0.02 / +0.01 |
| Bearish divergence, predicted negative | +0.01 / +0.01 / −0.05 / −0.02 |
| Bullish divergence, predicted positive | +0.07 / +0.03 / −0.02 / −0.11 |
| **Absorption at lows**, predicted positive | **+0.22** / +0.13 / +0.02 / +0.02 (market-adjusted on LH: +0.09, significant) |

Only the first figure in the last row is significant on its own, and with about 30 comparisons one
such pass is what chance would give. Its sign is at least consistent across all four sets. Nothing
else carries directional information, and several signals point the wrong way.

The flow lines were also about 80% correlated with plain price momentum (E03), so they repeated what
the trend overlay already measures.

## What the pane shows

| Element | Definition | Use |
|---|---|---|
| Columns | Volume ÷ normal volume for this bar. Normal = EWMA of previous bars in the same time-of-day slot (20 sessions) on intraday charts; EWMA of the previous 50 bars on daily and higher | Descriptive: how unusual is today's participation? 1.0 is normal |
| Column colour | Direction of the close-to-close move; solid when volume is at least 2× normal | — |
| **A** | Absorption at lows: relative volume ≥ 2, move within ±0.5σ, price ≥ 1.5 ATR below its baseline | Weak support only. Context for a dip; a caution for shorts |
| Optional marks | Climax (volume ≥ 3×, move ≥ 2σ, extension ≥ 2.5 ATR) and dry-up (volume ≤ 0.6×) | Information only; no predictive value found |

The time-of-day normalisation is verified on synthetic intraday data only (unit test); no real
intraday data was available.

## Verifying TradingView against Python

Export the chart data with the pane on the chart, then run from `research/`:
`python3 -m tools.parity_check export.csv --script volume [--intraday]`.
