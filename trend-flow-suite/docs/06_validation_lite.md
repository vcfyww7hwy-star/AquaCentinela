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
