# Relative Volume v4: specification

- **Script:** `pine/relative_volume.pine` (lower pane; title "Relative Volume v4", short title RVOL4).
- **Python twin:** `research/tfs/relvol.py`. Tests: `research/tests/test_relvol.py`.
- **Why it looks like this, and the evidence:** `07_relative_volume_review.md` (two external reviews,
  experiments E10–E26).
- **Status:** revised 24 Nov 2026 after a second external review. It passes a syntax parse and two
  line-by-line reviews. 111 project tests pass. **It has not been compiled in TradingView.**

## 1. What the pane is for

Triage and hygiene, not signals:

1. **Where to look.** Which stocks of a watchlist traded unusual volume for that stock and that time
   of day, on a day when the volume is not mechanical.
2. **Liquidity.** The stock's average dollar volume per day.
3. **No false readings.** A bar in progress is never shown as closed; expiry and index-rebalance days
   are marked.

It gives no buy or sell signal. On about 6.4 million evaluated stock-days (2000–2026) no volume
reading predicted direction at swing horizons in 2018–2026. After a bar of unusual volume the ATR
recomputed at that bar already reflects the volatility that follows; no extra stop distance is
warranted, also when the bar's own range was small (E14, E22).

## 2. Definitions

Every reference value uses **earlier bars of the same slot only** and is updated on closed bars.

| Term | Definition |
|---|---|
| Slot | Minute-based charts, standard or Heikin Ashi: the clock time of the bar's open (exchange time) together with the bar's length, so a short half-day bar never mixes with a full bar. Daily and higher, second-based, Renko, range and similar charts: one slot |
| Normal volume | exp(μ). μ is an exponentially weighted average of ln(volume): span 20 sessions per slot intraday, 50 bars on daily and higher. Each observation enters as μ + clip(ln(volume) − μ, ±3s). Zero-volume bars are skipped |
| Spread s | Square root of the same kind of average (span 100) of the clipped squared innovations |
| Relative volume | volume ÷ normal volume |
| zV | (ln(volume) − μ) ÷ s |
| Unusual / extreme | zV ≥ 2 / zV ≥ 3: about the busiest 4% / 1% of daily bars, for steady and erratic stocks alike |
| Bar move | Close-to-close return ÷ σ. σ² is a clipped average of squared returns (same slot and span; each squared return capped at 9σ²) |
| Session pace | Intraday charts with regular trading hours: volume of the session so far ÷ what is normal by this time of day (same robust reference, applied to cumulative volume), and its zV: the same figure in units of its usual spread at that time of day. While a bar is in progress the pane shows the values of the last closed bar |
| Closed bar | `barstate.isconfirmed`, except on a bar that is still open when the chart loads: TradingView processes that bar as historical and reports it as confirmed until the first live update, so the script also requires `timenow ≥ time_close` there (plus 20 minutes on a delayed feed; a forming bar of a tick or Renko chart never counts) |
| Expiry and index-rebalance day | US-listed stocks and funds. Quarterly expiry: third Friday of March, June, September, December; the Thursday before when that Friday in June is the Juneteenth holiday or its observance (18 June 2026, 17 June 2027). Russell reconstitution: fourth Friday of June |
| Warm-up | Nothing is shown for a slot until it has 10 earlier observations (intraday) or 25 (daily and higher). Averages are bias-corrected, so no value is ever seeded by a single bar |
| Dollar volume per day | Average of close × volume over 20 days (intraday and daily charts); the last 4 weeks ÷ 5 on weekly charts. In the currency of the prices; the label names it when it is not the dollar |

## 3. What is drawn

| Element | Meaning |
|---|---|
| Columns | Relative volume. Colour = direction of the close-to-close move; faint = ordinary, stronger = unusual, solid = extreme. Grey = bar in progress (partial volume, not comparable yet) |
| Grey step line | The level from which volume counts as unusual for this stock (and this time of day) |
| Orange step line | Session pace (intraday charts, regular trading hours) |
| Tinted background | Expiry or index-rebalance day: heavy volume is mostly mechanical |
| Status table | Relative volume and zV; the unusual level; session pace; bar move; dollar volume per day; last unusual bar; check of the intraday history |

Column scale: multiples of normal, capped at 6× by default (a small triangle marks capped bars), or
log2 (1× = 0, 2× = +1).

## 4. Alerts

All alerts fire at the close of a bar.

| Alert | Fires when | Notes |
|---|---|---|
| RVOL4 unusual volume | zV ≥ 2 | Not on expiry and index-rebalance days (input). Optional: only if the bar moved at least a chosen number of σ |
| RVOL4 extreme volume | zV ≥ 3 | Same two filters |
| RVOL4 session pace | The zV of the session's volume so far reaches a level (default 2.5) | Once per session; intraday charts with regular hours; not on expiry and index-rebalance days. On 60-minute bars about 4 stocks in 100 alert on a day; 63% of those days end with unusual volume on the daily chart, and 3 in 4 such days are announced, 56% before 11:30 (E26). At 2.0: 7 in 100, 43%, 9 in 10 |
| Any alert() function call | The events chosen in the inputs | One formatted line: relative volume, zV, the bar's move in % and σ, close, dollar volume per day |

The messages of the three alert conditions carry the numbers through the placeholders `{{plot_0}}`
(relative volume), `{{plot_1}}` (zV), `{{plot_2}}` (bar move in σ), `{{plot_3}}` (session pace) and
`{{plot_4}}` (its zV).

**Pine Screener.** The numeric series are the script's first plots, in this order: RVOL, zV, Move,
Pace, Pace z, Bars since unusual, Turnover per day. The Screener computes on the last 500 bars only:
at the median that changes zV by 0.00 on daily and 0.01 on 60-minute bars, and flags agree on 99.6%
of bars or more (E26); on 5-minute charts and below, 500 bars are fewer than the 10 sessions of
warm-up and nothing is shown. "Bars since unusual" counts from the latest closed unusual bar: 0 when
the latest bar closed unusual, 1 when a bar is in progress and the one before it was unusual. While
the market is open, filter on it and not on the live bar's own values.

## 5. Checks before trusting live readings

The script cannot see which data feed it runs on. The status table shows, on intraday charts with
regular hours, the previous session's volume summed from the chart's bars ÷ the previous daily bar.
The daily bar includes the closing auction and late prints, so 0.6 to 1 is normal (about 0.45 on a
quarterly expiry); below 0.3 means the intraday history is partial. This says nothing about bars in
progress or about a bar at the moment it closes. The manual checks are in the playbook.

## 6. Limits

- **Not compiled.** Verify in the Pine Editor first.
- Everything about returns was tested on daily bars of US stocks still listed at the date of each
  data file.
- **The flag is blunt after a spike.** In the 30 bars after an isolated day at 5× normal the
  unusual flag is about 20% less likely, and about 11% in the following 30 (E23). No estimator
  tested removed this without making the flag fire more often and less evenly across stocks.
- **The live daily bar reads low.** The volume of a daily bar in progress excludes the closing
  auction, which the normal includes. The pane shows it as "so far" and makes no estimate of the
  day: the v3 estimate ran 6–22% low against the final daily volume (E24).
- **A bar at the moment it closes may also read low** if the feed adds late prints afterwards
  (TradingView's manual says some trades reach the end-of-day feed only). Alerts on daily bars would
  then fire less often than the next day's chart suggests. Check 5 of the playbook measures it.
- Session pace needs regular trading hours. With extended hours the columns still work, but
  readings are not comparable with regular-hours charts.
- On a half day the short last bar has its own slot and stays in warm-up (two such days a year);
  on a 4-hour chart that is the whole session.
- On a 4-hour chart the session pace is empty until the first bar closes (13:30 New York).
- Other mechanical days are not marked: the last trading day of February, May and November (index
  reviews) had about 10% of stocks at unusual volume, against 3.5% on ordinary days.
- The Trend & Setups overlay still uses the v2 volume reference for its optional breakout setup.

## 7. Verifying TradingView against Python

Export the chart data with the pane on the chart (after the close, so that no bar is partial), then
run from `research/`: `python3 -m tools.parity_check export.csv --script volume [--intraday]`.
The tool reads each bar's slot from the exported plot `dbg_key` and compares RVOL, zV, Move, Pace
and Pace z. Export from a minute-based chart with regular trading hours, or from a daily chart.
