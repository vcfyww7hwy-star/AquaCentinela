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

### 2.5 Results on the added long-history set (E08)

LH: 459 stocks, 2 Jan 1999 – 7 Feb 2013, 1.12 million stock-days, 150 months. Full output:
`research/results/e08_long_history.json`.

**Frozen confirmation tests**

| Test | LH result | Verdict |
|---|---|---|
| C1 dip in an uptrend, forward returns vs uptrend bars without a dip | f1 +0.11 [+0.04, +0.18]; f3 +0.11 [+0.03, +0.20]; **f5 +0.12 [+0.03, +0.20]**; f10 +0.01 [−0.07, +0.10]. Market-adjusted f5 +0.08 [+0.02, +0.13] | **Confirmed for 1–5 bars.** The bounce is over by bar 10 |
| C2 rule D as trades, 10-bar exit (primary) | +0.04R [−0.06, +0.13], 8,685 trades; random entries +0.04R, p = 0.76. Negative in 2001, 2002, 2007, 2008, 2010 | **Not confirmed** |
| C2 rule D with the 3-ATR chandelier (alternative) | +0.09R [−0.03, +0.21], 7,874 trades; random entries +0.07R (sd 0.01), p = 0.05 | Beats random entries; the interval still includes zero |
| C3 12-1 month momentum | Relative strength > +1σ: fx60 +0.02 [−0.03, +0.08]; ≤ −1σ: −0.02 [−0.09, +0.05]. Absolute momentum: ±0.00 | **Not confirmed** |
| C4 dips without an uptrend | Market-adjusted f5 +0.01 [−0.02, +0.04] | No bounce, as expected |

In risk units, +0.12 over 5 bars is about +0.26σ of daily volatility: roughly +0.3% to +0.5% for a
typical stock, before costs. That is real and small.

**Pre-registered questions (E05) repeated on LH**

| Question | LH result |
|---|---|
| Q1 Regime information | None: chart up vs rest +0.01 [−0.05, +0.07]; context up +0.01 [−0.06, +0.07]; market up +0.03 [−0.08, +0.15] |
| Q2 S1 rules | v2 −0.01 [−0.05, +0.03]; v1 −0.02 [−0.09, +0.04] |
| Q4 S2, S3 | S2 +0.02 [−0.08, +0.12]. **S3 −0.08 [−0.15, −0.00]: significantly negative** |
| Q5 Volume | Nothing in the predicted direction. Asymmetry regression −0.006 [−0.028, +0.014]. Absorption at lows: +0.02 [−0.11, +0.14] raw, +0.09 [+0.04, +0.15] market-adjusted (same sign as on A, B, DJ) |
| Q6 Stops | Close-based stops: +0.04R better on average [+0.01, +0.08], but 5.4% of trades lose more than 1.5R against 0.8% with intrabar stops. Worst single trade with an intrabar stop: −21R (a gap through the stop) |
| Q7 S1 vs random entries | +0.04R vs +0.03R, p = 0.43 |

### 2.6 H1: the trend filter as a risk switch (E09)

H1 was pre-registered in `04_trend_setups.md`: the regime filter improves the risk profile of holding
single stocks. Position decided at the close, 5 bp per switch, cash earns nothing. Output:
`research/results/e09_regime_risk.json`.

| Equal-weight portfolio | LH 1999–2013 | SP5 2014–2018 | DJ 2007–2013 |
|---|---|---|---|
| Buy and hold: Sharpe / max drawdown | 0.78 / −53% | 0.78 / −17% | 0.40 / −48% |
| Long unless the **weekly** trend is down | 0.80 / −33% | 0.78 / −12% | 0.44 / −29% |
| Long only while the weekly trend is up | 0.64 / −12% | 0.75 / −5% | 0.09 / −14% |
| Long unless the **daily** trend is down | 0.62 / −40% | 0.68 / −12% | 0.38 / −40% |
| Long unless the market's daily trend is down | 0.72 / −51% | 0.46 / −19% | 0.22 / −46% |
| Long while above the 200-day average | 0.58 / −24% | 0.71 / −8% | 0.34 / −23% |

- Per stock, no rule raises the Sharpe ratio for most stocks (8–39% improved). **H1's return
  criterion fails.**
- Drawdowns are smaller for most stocks (65–93% on LH), and at portfolio level the weekly "not down"
  rule cut the maximum drawdown by 29–40% (5 to 20 percentage points) at an unchanged Sharpe ratio,
  in all three sets. **H1's drawdown part holds.**
- The chart's own (daily) regime is worse than the weekly one on every measure.
- Survivorship inflates the buy-and-hold returns here, so the cost of the filter in lost return is,
  if anything, understated.

### 2.7 What the evidence supports, and the design decisions

Across four sets and about 1.7 million stock-days (1999–2018, daily bars, large US stocks):

1. **No rule tested has a confirmed, tradable directional edge.** That includes the trend state,
   pullback, breakout and reversal entries, every filter, and every volume signal.
2. **One regularity is confirmed:** dips inside long-term uptrends bounce for 1–5 bars. It is small,
   and as a complete stop-based trade rule it is not confirmed; it lost money in bear-market years.
3. **The higher-timeframe trend is a risk switch, not a predictor.** Standing aside while it is down
   cut drawdowns by 29–40% at the same risk-adjusted return.
4. **Stop orders cap losses** (about 1% of trades worse than −1.5R, against 5–9% with exits on the
   close), but a gap can jump any stop.

Decisions (v2 of the suite):

| Element | Decision | Basis |
|---|---|---|
| Long-term (context) trend | Main readout; chart shaded while it is Down; trades from setup D close when it turns Down | 2.6 |
| Chart-timeframe trend state | Kept as information only | Q1 |
| Setup D, dip in a long-term uptrend | Default setup, labelled as an unconfirmed candidate; entry at the dip's close, stop 2 ATR, 3-ATR trailing stop; optional time exit | C1 confirmed, C2 not; the chandelier beat random entries on A, B and LH |
| v1/v2 pullback entry (S1) | Removed from the TradingView script; kept in Python for the record | Q2, Q7 |
| Breakout (B) and reversal (R) | Off by default, labelled | Q4 |
| Context, market and strength filters | Shown as information; one optional market filter, off by default | Q3 |
| Stops | Stop orders by default; minimum distance 1 ATR; position capped at 25% of the account | Q6 |
| Volume pane | Reduced to relative volume and "absorption at lows"; flow lines, asymmetry tint, accumulation / distribution, divergences removed | Q5 |
| 12-month momentum | Not added | C3 |

Still untested: everything intraday (1h, 4h), weekly charts, small caps, other markets, and any
period after early 2018. A survivorship-free dataset would be needed to trust absolute return levels.
