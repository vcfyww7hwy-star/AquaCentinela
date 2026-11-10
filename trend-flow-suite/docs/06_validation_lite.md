# Validation-lite on real stocks (E05): plan and results

**Part 1 (this section) was written and committed before any outcome was computed on the stock
data.** Part 2 holds the results and the design decisions they led to.

## Part 1: Plan (pre-registered, 10 Nov 2026)

### Why

Until now every design choice rested on three series (S&P 500 index, NASDAQ index, GOOG). That is
too little to decide which parts of the suite earn their place. Two public daily datasets are now
available, enough for a first, limited validation of single-stock behaviour.

### Data

| Set | Content | Source | Use |
|---|---|---|---|
| SP5 | 509 S&P 500 stocks, daily OHLCV, 8 Feb 2013 – 7 Feb 2018 | Kaggle "S&P 500 stock data" (C. Nugent), mirrored in the public repo `CNuge/kaggle-code` | Split by ticker into **A (development)** and **B (confirmation)** |
| DJ | 31 large caps (Dow 30 members of 2017, plus AABA, GOOGL, AMZN), daily OHLCV, 2006–2017 | Kaggle "DJIA 30 Stock Time Series" (szrlee), public repo `szrlee/Stock-Time-Series-Analysis` | **Second confirmation set, 3 Jan 2006 – 7 Feb 2013 only**, so it shares no dates with SP5 and contains the 2008–09 bear market |
| Benchmark | S&P 500 index close, 1999–2018 | bundled with the `arch` package | Market regime and relative strength |

Known limits, accepted and reported with every result:

- **Survivorship bias.** Both sets hold companies that were index members at the end of the sample.
  Absolute returns are overstated. Comparisons between a signal and a control drawn from the same
  stocks are affected much less, so every test below is such a comparison.
- **One market era in SP5** (a bull market). DJ adds the 2008 crash but only 31 stocks.
- **Daily bars only.** Nothing here validates 1h or 4h behaviour.
- **Prices are split-adjusted, not dividend-adjusted.**

### Splits and evaluation window

- SP5 tickers are split by `md5(ticker) mod 2` into A and B.
- All design decisions are made on **A**. B and DJ are used once, to confirm.
- The first 400 bars of every stock are warm-up (the weekly context needs them). Tests use the rest.

### Metrics

- **Forward return in risk units:** `fz_h = (ln C[t+h] − ln C[t]) / (σ_t·√h)` for h = 5, 10, 20 bars,
  with σ_t the engine's own volatility estimate known at t. **Primary: h = 10.** A market-adjusted
  version (minus the benchmark's log return over the same bars) is reported alongside.
- **Trade results:** R-multiples from the trade engine, with its real stop and exit rules.
- **Uncertainty:** bootstrap over calendar months (2,000 resamples). All observations from a month
  stay together, which respects the fact that stocks move together. "Significant" means the 95%
  interval excludes zero.

### Questions and decision rules

Every signal is tested as *raw detection*, before filters, against a control drawn from the same set.

| ID | Question | Test | Decision rule |
|---|---|---|---|
| Q1 | Does the regime carry information? | `fz` on up-regime bars vs other bars; same for context, market and relative strength | Report only |
| Q2 | Which pullback rule for S1: v1 "near the baseline" or v2 "after a confirmed swing high"? | `fz` of each rule's signals vs all up-regime bars; direct difference between the two | Adopt v2 (fewer parameters, tied to structure) unless v1 is significantly better on A |
| Q3 | Do the S1 filters help: context, market, relative strength, light pullback volume? | Among S1 signals: `fz` where the filter passes vs where it fails | A filter is **on by default** only if pass − fail is significantly positive on A **and** has the same sign on B and DJ. Otherwise it is shown as information and off by default |
| Q4 | Do S2 (compression breakout) and S3 (confirmed reversal) have an edge? | `fz` of signals vs control (S2: bars with regime not down; S3: bars with regime not up) | **On by default** only if significantly positive on A and same sign on B and DJ; otherwise off by default |
| Q5 | Does the volume pane predict anything? | Accumulation / distribution (events and states), climax, absorption, divergences: `fz` vs control, with the predicted sign stated in the code | Keep in the default display only if the predicted sign is significant on A and repeated on B and DJ; otherwise remove from the default display |
| Q6 | Stops and exits | Trade-level R: intrabar vs close-based stops; chandelier (3 ATR) vs structure trail (last confirmed swing low) | Intrabar stays the default unless its average R is significantly lower on A and B. Chandelier stays unless the structure trail is significantly better on A with the same sign on B and DJ |
| Q7 | Does S1's timing beat random entries in the same uptrends? | Average R of S1 trades vs 20 runs of random entries on up-regime bars (same count per stock, same stop distances, same exits) | Report only |

Adopted on first principles regardless of these results, and reported for their effect:

- robust (winsorised) volatility in the trend score;
- a minimum stop distance of 1 ATR and a cap on position size;
- setups detected independently of the simulated position.

### Trial count

The plan holds about 30 pre-specified comparisons. No parameter is tuned: every threshold keeps the
value it had before this experiment (trend thresholds ±1.0/0.3, swing size 2 ATR, trail 3 ATR,
breakout 20 bars, and so on). Anything explored beyond this plan will be labelled *exploratory*.

## Part 2: Results and what they changed

### 2.1 Pre-registered results (E05)

Run on 489 S&P 500 stocks (A: 231, B: 258; evaluation Sep 2014 – Feb 2018) and 31 Dow-set stocks
(evaluation Aug 2007 – Feb 2013). Full output: `research/results/e05_validation_lite.json`.
`fz10` is the 10-bar forward return in risk units; brackets are 95% intervals.

| Question | Result | Decision |
|---|---|---|
| Q1 Regime information | None. Chart regime up vs rest: +0.01 (A), +0.01 (B), −0.03 (DJ), all intervals span zero. Context, market and strength: also not significant. "Market down" was followed by *better* returns on A and B (+0.35, significant) | The chart-timeframe regime is descriptive, not predictive |
| Q2 S1 rule | Neither rule beats ordinary up-regime bars: v2 −0.03 / −0.02 / −0.13; v1 −0.05 / +0.01 / −0.14. Both are slightly negative over 5 bars | Neither is kept as a default entry |
| Q3 S1 filters | No filter passes. The "not down" filters almost never bind, and where they do the sign is wrong | All off by default |
| Q4 S2, S3 | S2: −0.13 / −0.17 / +0.16. S3: +0.04 / −0.04 / +0.03. Nothing significant, signs inconsistent | Both off by default |
| Q5 Volume | Asymmetry, accumulation/distribution, climaxes and divergences: nothing significant in the predicted direction; several point the other way. Regression coefficient of asymmetry ≈ −0.02 / −0.01 / 0.00. One pass: absorption at lows, +0.22 [+0.02, +0.38] on A, same sign on B (+0.13) and DJ (+0.02) | Only "absorption at lows" stays in the default display; with about 30 comparisons one pass is what chance alone would give |
| Q6 Stops and exits | Close-based vs intrabar stops: no significant difference in average R, but 8.5% of close-based trades lose more than 1.5R against 1.4% with intrabar stops. Structure trail: not better than the chandelier | Intrabar stops and the chandelier stay |
| Q7 S1 vs random entries | Average R of S1 trades vs random entries in the same uptrends: +0.09 vs +0.08 (A, p = 0.43), +0.11 vs +0.07 (B, p = 0.05), −0.07 vs +0.06 (DJ, p = 0.95) | S1's timing adds nothing reliable |

Trade level, all v1/v2 setups, no filters: average R +0.10 [−0.03, +0.22] (A), +0.09 [−0.06, +0.24]
(B), −0.01 [−0.20, +0.19] (DJ), before costs. **No detectable edge.**

The consistent hint in these tables is short-term mean reversion: conditions that look bad are
followed by slightly better returns. The v1/v2 entry waits for a close above the prior bar's high,
which gives that effect away.

### 2.2 Exploratory analysis on the development half only (E06, E06b; not pre-registered)

A short menu of effects from the literature, looked at on set A only:

- **Dips in long-term uptrends bounce.** With the weekly context up and the 5-bar return at or
  below −1.5σ, forward returns exceed other context-up bars: f5 +0.20 [+0.01, +0.35],
  f10 +0.25 [+0.08, +0.41]. The effect is a plateau across dip depths (−1 to −2σ), dip windows
  (3, 5, 10 bars) and trend definitions (weekly context, 12-month momentum, relative strength),
  and it grows with depth. Without an uptrend there is no bounce. Market-adjusted, the effect is
  about zero: these are market-wide dips, so the edge is market timing inside uptrends, not stock picking.
- **The bounce lasts about 10 bars.** Cumulative excess: +0.4σ after 3–5 bars, +0.8σ after 10, flat to 20.
- **Long-horizon momentum** (12 months, skipping the last month) is strong and orderly on A, also
  after removing the market: relative strength above +2σ gives fx60 +0.26 [+0.09, +0.41]; at or
  below −1σ, −0.21 [−0.32, −0.09].
- **As a trade rule** (buy the dip's close, stop 2 ATR): a 10-bar time exit averages +0.16R with a
  54% win rate and 8 bars held; a 3-ATR chandelier averages +0.17R with 37% and 17 bars. Random
  entries in the same uptrends: +0.05R and +0.10R.

### 2.3 Confirmation plan (frozen 10 Nov 2026, before B and DJ were looked at for these effects)

**Candidate rule D ("dip in an uptrend").** Context regime up, and the 5-bar return in risk units
at or below −1.5 on the first bar of the dip. Buy at that close. Stop: 2 ATR below, as an intrabar
stop order. Exit: at the close 10 bars later (primary), or a 3-ATR chandelier (alternative). Exit
also if the context turns down.

| ID | Test on B and on DJ, run once | Counts as confirmed if |
|---|---|---|
| C1 | f5 and f10 of rule-D bars minus context-up bars without a dip | Positive on B and DJ, and the interval excludes zero on DJ for f5 or f10. Same sign but not significant on DJ = "partly confirmed" |
| C2 | Rule D as trades, primary exit: average R, and vs 20 runs of random entries under the same context | Average R above zero and above the random runs (p ≤ 0.10) on B and on DJ |
| C3 | Long-horizon momentum: 60-bar market-adjusted return for relative strength (12-1) above +1σ vs the rest, and at or below −1σ vs the rest; the same for absolute momentum with the raw 60-bar return | Same signs on B and DJ, significant on at least one |
| C4 | Dips without an uptrend: market-adjusted 5-bar return vs other no-uptrend bars | Supportive only: not positive |

B covers the same dates as A, so for C1 and C2 it replicates across stocks, not across time. **DJ
(2007–2013, including 2008) is the independent test.**

### 2.4 Confirmation results (E07) and an added independent set

**Result on the planned sets.** Rule D replicated on B (other stocks, same years) and was **not
confirmed** on DJ (2007–2013):

| Test | B | DJ |
|---|---|---|
| C1 f5 / f10 vs context-up bars without a dip | +0.18 [+0.03, +0.33] / +0.23 [+0.08, +0.37] | +0.06 [−0.16, +0.27] / −0.12 [−0.32, +0.11] |
| C2 average R, 10-bar exit (random entries) | +0.11 [−0.08, +0.28] (random +0.05, p = 0.05) | −0.04 [−0.24, +0.19] (random +0.02, p = 0.95) |
| C3 relative strength ≤ −1σ, fx60 | −0.24 [−0.37, −0.11] | +0.17 [−0.00, +0.33] |
| C3 relative strength > +1σ, fx60 | +0.05 [−0.06, +0.16] | +0.05 [−0.11, +0.20] |

By the frozen criteria C1, C2 and C3 are **not confirmed**. DJ has only 31 stocks and 333 trades,
so its intervals are wide: it fails to confirm, it does not refute.

**Added set LH (decided 10 Nov 2026 after the DJ result, before any outcome on LH was computed).**
The dip effect is market-wide, so the question needs more independent *years*, not more stocks
from the same years. A public mirror of the Kaggle "Huge Stock Market Dataset" (B. Marjanovic;
repo `masaok/kaggle-boris-huge-stock-market-dataset`) holds daily data back to each listing date.

- Universe: the same S&P 500 tickers as SP5 (503 found).
- Period: 2 Jan 1999 – 7 Feb 2013. This shares no dates with SP5 and holds two bear markets.
- Tests: the frozen C1–C4, rule unchanged, plus the pre-registered Q1–Q7 of E05 as a further check.
- Extra caveat: the universe is "members in 2018, traced back", which adds look-ahead in stock
  selection on top of survivorship. Average returns are overstated; signal-vs-control differences
  are affected much less. Prices here are also dividend-adjusted.

How the outcome will be used:

- Rule D becomes the default entry only if C1 and C2 hold on LH by the same criteria as in 2.3.
- Otherwise it ships as an *unconfirmed candidate*, labelled as such, and no setup is presented
  as validated.
