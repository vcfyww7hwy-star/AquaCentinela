# Volume Flow v2 (Phase 1): specification, evidence, hypotheses

- **Script:** `pine/volume_flow_v2.pine` (lower pane).
- **Python twin:** `research/tfs/flow.py`.
- **Diagnostics:** `research/experiments/e03_flow_v2_diagnostics.py`.
- **Status:** built Nov 2026. The 27 unit tests pass. **Not yet compiled in TradingView**, and predictive value **not yet tested** (Phase 4).

## 1. Purpose

The pane answers one question that price cannot: **is volume adding information?** That means two things:

- whether participation leans to the buy or sell side;
- whether volume is concentrating on up bars or down bars *more than is normal for this symbol*.

It does not estimate the trend. In E01 the old VFI was ~90% price momentum, and that job belongs to the
trend engine (Phase 2).

## 2. Definitions (bar t)

```
r      = ln(C_t / C_{t-1})
slot   = bar number within the session (intraday); 0 on D/W/M
σ      = sqrt(EWMA of r² for this slot, previous sessions only)      span: 20 sessions / 50 bars
z      = r / σ                                                         standardised move
s      = 2Φ(z) − 1  ∈ (−1, 1)                                          bulk volume classification
         (optional: lower-timeframe up/down volume share, TradingView Volume Delta rule)
E[V]   = EWMA of volume for this slot, previous sessions only
RVOL   = V / E[V];   w = min(RVOL, 3)                                  capped relative-volume weight
F_n    = K_n(w·s) / K_n(w)  ∈ [−1, 1]                                  K = two-pole smoother; fast 40, slow 130
A      = F_slow − K_slow(s)                                            volume asymmetry
A_z    = (A − mean_250(A)) / sd_250(A)
ext    = (C − K_50(C)) / ATR14                                         extension in ATR units
```

The window sizes are SMA-equivalent bars. A two-pole span n = ⌊(window+1)/2⌋ has the same average lag as SMA(window).

## 3. Design decisions and the evidence for each

| Decision | Why | Evidence |
|---|---|---|
| Two-pole kernel instead of a 130-bar sum | Same lag, no artifact from bars leaving the window | E01: zero-line whipsaws 36 vs 112 (S&P, 2000–18). E03: slow flow crosses zero 1.4–1.9×/yr vs 6.5–7.3×/yr for the VFI |
| Continuous direction weight (Φ) instead of up/down/zero | Keeps magnitude; standard method (Easley, López de Prado & O'Hara 2012) | E01: the old ±0.2σ dead band zeroed only ~16% of bars and discarded magnitude on the rest |
| **Relative** volume as the weight, not raw volume | Raw volume lets the busy open/close dominate intraday flow, and a time-of-day return pattern then shows up as fake "accumulation" | Unit test: with an up-drifting, high-volume opening bar and no volume information, raw weighting reports asymmetry > 1.2%; relative weighting < 0.6% |
| Normalise per time-of-day slot (intraday) | Removes the U-shape in volume and volatility, and the short last bar | Unit test: RVOL median per slot 0.85–1.15 and z std per slot 0.8–1.25, despite a 3× raw U-shape |
| Centre the asymmetry on its own rolling mean | Asymmetry has a structural negative baseline (volume heavier on down bars) | E03, before centring: median A_z −0.4 to −2.6. After: median ≈ 0, signals balanced |
| Events on closed bars only; pivots flagged at confirmation | No repaint, no look-ahead | Unit test: truncation invariance (values on data cut at bar k equal full-history values) |

## 4. E03 results (descriptive, daily)

Read the full output in `research/results/e03_flow_v2_diagnostics.json`.

| | S&P 500 | NASDAQ | GOOG |
|---|---|---|---|
| Std of standardised move z / median RVOL | 1.04 / 1.00 | 1.03 / 0.99 | 1.08 / 0.87 |
| Flow slow, 5–95% range | −5.7% … +10.0% | −6.4% … +10.6% | −10.5% … +14.5% |
| Correlation of flow slow with VFI / with the 130-bar return | 0.82 / 0.76 | 0.85 / 0.80 | 0.86 / 0.83 |
| Correlation of asymmetry with the VFI's volume component | 0.79 | 0.81 | 0.66 |
| Correlation of asymmetry with the 130-bar return | 0.00 | −0.06 | 0.48 |
| Zero crosses per year: flow slow / flow fast / VFI | 1.4 / 6.7 / 7.3 | 1.9 / 6.0 / 6.5 | 1.6 / 5.9 / 4.9 |
| Accumulation / distribution signals per year | 0.6 / 0.5 | 0.5 / 0.6 | 0.3 / 0.5 |
| Bearish / bullish divergences per year | 2.8 / 0.9 | 3.0 / 0.6 | 1.1 / 1.0 |
| Climax / absorption events per year | 0 / 0 | 0 / 0 | 0.7 / 1.5 |

**What the results mean:**

- **Asymmetry is genuinely about volume.** It tracks the VFI's volume component (r ≈ 0.8) and is
  uncorrelated with price momentum on the indices. On GOOG it is moderately correlated (0.48);
  this is to be re-checked across many stocks.
- **Climax and absorption never fire on indices.** Aggregate index volume is too smooth. These
  events are designed for single stocks.
- **Persistence (experimental) is not stable.** The 500-bar estimate of whether high-volume moves
  continue or reverse swung in sign. Median t-statistics over the sample were 0.17 (S&P), 0.53
  (NASDAQ) and 0.35 (GOOG). It stays off by default and is never used as a signal.

## 5. How to read the pane (until Phase 4 says otherwise)

- **Lines.**
  - Slow flow above zero means buying pressure dominates at the swing horizon.
  - The fast line shows the current push.
  - Use them as confirmation of the trend engine, not on their own.
- **Tint.**
  - Green (accumulation) means volume is heavier on up bars than is normal for this symbol.
  - Purple (distribution) is the opposite. It is most informative when price is still rising.
- **Marks.** Climax, absorption and divergence marks are *warnings*. Use them to manage open
  positions (tighten stops, take partial profits), not to enter against the trend. Phase 3 combines
  them with structure for confirmed reversals.

## 6. Pre-registered hypotheses (tested in Phase 4 on a stock universe)

Every hypothesis is subject to the rules of `02_research_protocol.md`: development / validation /
lockbox periods, a ticker split, every trial logged, PBO < 0.3, and DSR.

| ID | Hypothesis | Test | Accept if |
|---|---|---|---|
| H2 | A_z predicts 10- and 20-bar forward returns beyond the trend score and unweighted flow | Panel regression on returns in σ units, standard errors clustered by date | Incremental t ≥ 3 in development; same sign and t ≥ 2 in validation; same sign in ≥ 2/3 of sectors |
| H5 | Time-of-day normalisation improves intraday A_z | H2's test on 65-min/1h bars, relative vs raw weights | Out-of-sample difference > 0 with 95% bootstrap CI |
| H6 | Climax/absorption at an extension precede short-term mean reversion | Forward 5/10/20-bar returns vs matched controls (same extension, no event) | Predicted sign; CI excludes 0 in development and validation |
| H7 | Divergences raise the odds of a structural break | P(lower low within 20 bars) after a bearish divergence vs matched controls; R-multiple impact of stop-tightening | CI-significant hit-rate gain, or ≥ 0.1R expectancy gain in validation |

Features that fail are removed or set off by default. The pane must earn its place on the chart.

## 7. Verifying TradingView against Python

1. Add the script to a chart.
2. Export the chart data.
3. Run `python3 -m tools.parity_check export.csv [--intraday]` from `research/`.

The hidden `dbg_*` plots carry the internal series. Parity is exact when the export starts at the
first bar the script calculated on.

## 8. Known uncertainties

- **Not yet compiled in TradingView.** The script passes a syntax parse only.
- **Lower-timeframe mode.** It places a `request.security_lower_tf()` call inside a conditional,
  relying on v6 dynamic requests. If it fails to compile, the fix is to move the call to global scope.
- **Exports.** Whether "Export chart data" includes `display.data_window` plots is unverified. If a
  `dbg_*` column is missing, set that plot's display to *all* temporarily.
- **Intraday behaviour** was verified on synthetic data only. No real intraday data was reachable from
  the development environment.
