# Relative Volume v3: specification

- **Script:** `pine/relative_volume.pine` (lower pane; title "Relative Volume v3", short title RVOL3).
- **Python twin:** `research/tfs/relvol.py`. Tests: `research/tests/test_relvol.py`.
- **Why it changed, and the evidence:** `07_relative_volume_review.md`.
- **Status:** rewritten 24 Nov 2026 after an external review. It passes a syntax parse and a line-by-line
  review. **It has not been compiled in TradingView.**

## 1. What the pane is for

It describes participation: how unusual this bar's volume is for this stock at this time of day, how
the session is running so far, and how liquid the stock is. It gives no buy or sell signal. On about
8.9 million stock-days (1999–2026) no volume reading predicted direction at swing horizons in
2018–2026, and relative volume added nothing to ATR for judging the next two weeks' volatility.

## 2. Definitions

Every reference value uses **earlier bars of the same slot only** and is updated on closed bars.

| Term | Definition |
|---|---|
| Slot | Intraday charts: the clock time of the bar's open (exchange time) together with the bar's length, so a short half-day bar never mixes with a full bar. Daily and higher, second-based and non-standard charts: one slot |
| Normal volume | exp(μ). μ is an exponentially weighted average of ln(volume): span 20 sessions per slot intraday, 50 bars on daily and higher. Each observation enters as μ + clip(ln(volume) − μ, ±3s). Zero-volume bars are skipped |
| Spread s | Square root of the same kind of average (span 100) of the clipped squared innovations |
| Relative volume | volume ÷ normal volume |
| zV | (ln(volume) − μ) ÷ s |
| Unusual / extreme | zV ≥ 2 / zV ≥ 3: about the busiest 4% / 1% of daily bars, for steady and erratic stocks alike |
| σ and bar move z | σ² is a clipped average of squared close-to-close returns (same slot and span; each squared return capped at 9σ²). z = return ÷ σ |
| Extension | (close − two-pole baseline equivalent to a 50-bar SMA) ÷ ATR(14) |
| Session pace | Intraday charts: volume of the session so far ÷ what is normal by this time of day (same robust reference, applied to cumulative volume). At the last bar it equals the day's relative volume |
| Day pace estimate | Daily chart, bar in progress: volume so far ÷ normal ÷ the usual share of a day's volume traded by this minute. Shown with a "likely" range. US 390-minute sessions only |
| Warm-up | Nothing is shown for a slot until it has 10 earlier observations (intraday) or 25 (daily and higher). Averages are bias-corrected, so no value is ever seeded by a single bar |

## 3. What is drawn

| Element | Meaning |
|---|---|
| Columns | Relative volume. Colour = direction of the close-to-close move; faint = ordinary, stronger = unusual, solid = extreme. Grey = bar in progress (partial volume, not comparable yet) |
| Grey step line | The level from which volume counts as unusual for this stock (and this time of day) |
| Orange step line | Session pace (intraday charts) |
| Tinted background | Quarterly option-expiry day (third Friday of March, June, September, December): heavy volume is mostly mechanical |
| **H** (off by default) | Heavy volume, small move, stretched low: zV ≥ 2, \|z\| ≤ 0.5, extension ≤ −1.5 ATR. Context only; see the evidence |
| Status table | Relative volume and zV; the unusual level; session pace or day estimate; bar move; 20-day dollar volume; last unusual bar; data feed check |

Column scale: multiples of normal, capped at 6× by default (a small triangle marks capped bars), or
log2 (1× = 0, 2× = +1).

## 4. Data feed check

TradingView's default US feed without paid exchange data is Cboe (about 9–10% of consolidated
volume). Whether the live bars and the intraday history it shows are partial is undocumented. The
status table therefore shows the symbol's feed prefix and, on intraday charts, the previous session's
volume summed from the chart's bars ÷ the previous daily bar. Near 1 is consistent; far below 1 means
the intraday bars carry only part of the market's volume. The manual checks are in the playbook.

## 5. Limits

- **Not compiled.** Verify in the Pine Editor first.
- Everything tested is daily bars of US stocks still listed today. The intraday logic was checked on
  49 real sessions (Aug–Nov 2026) only.
- The day pace estimate is rough before midday: the "likely" range at 10:30 is about ±65%.
- Regular trading hours are assumed. With extended hours the slots still work, but readings are not
  comparable with regular-hours charts.
- For about 30 bars after a day of 5× volume or more the unusual flag is less sensitive.
- The Trend & Setups overlay still uses the v2 volume reference for its optional breakout setup.

## 6. Verifying TradingView against Python

Export the chart data with the pane on the chart (after the close, so that no bar is partial), then
run from `research/`: `python3 -m tools.parity_check export.csv --script volume [--intraday]`.
The tool reads each bar's slot from the exported plot `dbg_key`.
