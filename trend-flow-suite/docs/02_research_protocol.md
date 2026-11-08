# Research protocol: how indicators get tested and accepted

Status: adopted Nov 2026. Applies to every module of the suite.

## 1. The question

> "Test the indicator(s) on the S&P, NASDAQ, DJI and Russell 2000 thousands or millions of times,
> refining after each run, until the backtest is the best possible."

**Short answer:** computationally trivial, statistically self-defeating.

- **Speed is not the problem.** 5,280 variants build and backtest in about 0.5 s per index on a
  laptop-class container, so a million runs take a few minutes.
- **Selection is the problem.** The best backtest found by such a loop is, by construction, the
  luckiest one. Experiment E02 measured this on real data.

## 2. Evidence: experiment E02 (`research/experiments/e02_overfitting.py`)

Search space: 5,280 variants of the VFI regime rule (length × dead band × volume cap × smoothing × rule).
Data: S&P 500 and NASDAQ Composite, daily. In-sample (IS) is 2001-03 to 2009 (two bear markets);
out-of-sample (OOS) is 2010–2018. Costs are 5 bp per switch.

| | S&P 500 | NASDAQ |
|---|---|---|
| Buy & hold Sharpe, IS / OOS | 0.11 / 0.68 | 0.21 / 0.78 |
| Best IS variant: Sharpe IS → OOS | 0.76 → 0.56 | 0.79 → 0.62 |
| Best IS variant vs buy & hold, OOS CAGR | 7.2% vs 9.4% | 8.8% vs 12.7% |
| Rank correlation of IS vs OOS Sharpe, all variants | 0.37 | 0.21 |
| **Probability of Backtest Overfitting** (CSCV, 12,870 splits) | **0.43** | **0.61** |
| Median IS → OOS Sharpe of the IS winner, across splits | 0.81 → 0.27 | 0.89 → 0.30 |
| **Null test:** best IS timing Sharpe, real vs median of 100 no-edge worlds | 0.61 vs 0.55 (**p = 0.40**) | 0.55 vs 0.53 (**p = 0.45**) |
| Deflated Sharpe of the winner (trial count assumed: all 5,280 / effective ≈ 3) | 0.14 / 0.92 | 0.48 / 0.96 |

How to read the table:

- **PBO.** A PBO of 0.43–0.61 means the in-sample champion lands in the bottom half
  out of sample about as often as a randomly chosen variant would.
- **Null test.** The same search run on synthetic histories with no exploitable structure finds
  equally good in-sample "winners" (p = 0.40–0.45). On this data, optimisation cannot separate
  skill from luck.
- **Deflated Sharpe.** The DSR is very sensitive to how many *independent* trials one assumes,
  because long/flat variants on the same index are highly correlated. It is reported as a range;
  PBO and the null test do not need that assumption.
- **What the search actually found.** Slow filters (length 160–200) that sat out 2001–02 and 2008.
  This is the well-known 200-day trend-filter effect. The volume-cap parameter was irrelevant:
  identical results for 1.5–5×.

Literature agrees:

- Aronson (2006) tested 6,402 technical rules on the S&P 500 (≈1980–2005); none was significant after
  adjusting for data-mining bias.
- McLean & Pontiff (2016, JF) found published return predictors earn 26% less out of sample and
  58% less after publication.

## 3. Why brute force fails (first principles)

1. **The maximum of noisy estimates is biased upward.** The expected best annualised Sharpe from
   pure luck grows with the number of independent trials N and falls only with √years:

   | Trials | 10 y | 20 y | 30 y |
   |---|---|---|---|
   | 100 | 0.80 | 0.57 | 0.46 |
   | 1,000 | 1.03 | 0.73 | 0.59 |
   | 1,000,000 | 1.54 | 1.09 | 0.89 |

   (Bailey & López de Prado 2014; formula in `tfs.validation.expected_max_sr`.)
   Buy-and-hold equity Sharpe is roughly 0.3–0.7.
2. **Low statistical power.** The standard error of an annualised Sharpe ratio is ≈ 1/√years.
   With 20 years, the 95% interval is about ±0.44.
3. **Few independent tests.** S&P 500 and NASDAQ daily returns correlate 0.89 (measured, 1999–2018).
   DJI and Russell 2000 are also highly correlated with them, so four indices are not four tests.
   A trend rule's result is dominated by a handful of episodes (2000–02, 2008, 2020, 2022).
4. **Indices are not stocks.** Index returns have historically shown positive short-horizon
   autocorrelation, while individual stocks show reversal (Lo & MacKinlay 1988). Index volume is
   not tradable volume. Parameters tuned on indices do not transfer automatically to stocks.
5. **Iterating on the same data is data snooping.** Each "refine and re-run" leaks the test set into
   the design. An AI running the loop is the same process, only faster.

## 4. Protocol

1. **Pre-register.** Before any test, write down the hypothesis, metric, baseline and decision rule
   (see §5). Results never change a hypothesis retroactively.
2. **Partition the data in three dimensions, and touch each partition in order.**
   - *Time:* development ≤ 2014, validation 2015–2020, **lockbox 2021–2026** (opened once, at the end).
   - *Cross-section:* stocks split into halves A/B by a hash of the ticker. Develop on A, confirm on B.
   - *Instrument type:* ETFs (SPY, QQQ, DIA, IWM) are a separate sanity check, not the development set.
3. **Budget degrees of freedom.**
   - At most 3–5 free parameters per module.
   - Published defaults first.
   - Ensembles across lookbacks instead of picking one.
   - Coarse grids only to map sensitivity. Choose the centre of a stable plateau, never the peak.
4. **Optimise components on well-posed objectives with high statistical power, not on P&L:**
   - volatility estimators by out-of-sample forecast loss (QLIKE), measurable on every bar;
   - smoothing kernels by detection delay vs false-alarm rate on synthetic series with known breaks;
   - volume classification (bar-level BVC vs lower-timeframe delta) by agreement with intrabar data.

   P&L tests are reserved for a few final, pre-registered hypotheses.
5. **Register every trial.** Log config hash, code commit, data range and metrics. The trial count
   feeds DSR and the PBO family size.
6. **Statistics** (`research/tfs/validation.py`):
   - PBO via CSCV;
   - Deflated Sharpe with the logged trial count;
   - null-world permutation test (as in E02);
   - White's Reality Check or Hansen's SPA for rule families;
   - block-bootstrap confidence intervals.
7. **Acceptance criteria for a module.**
   - Out-of-sample improvement over its baseline in ≥ 2/3 of sub-periods *and* sectors.
   - Survives ±25% parameter perturbation.
   - PBO < 0.3.
   - Passes the family-wise test.
   - Engineering: Pine ↔ Python parity, and no repaint (replay = history).
8. **Lockbox, then forward test.** Run one lockbox evaluation. Then 3–6 months of paper trading on
   alerts, with every signal logged before the outcome is known.

## 5. Pre-registered hypotheses (initial)

| ID | Hypothesis | Metric | Baseline |
|---|---|---|---|
| H1 | The multi-horizon trend z-score regime filter improves risk-adjusted returns of stocks | Sharpe, max DD, per-stock win rate vs B&H | Buy & hold; close > SMA200 |
| H2 | Volume asymmetry adds information beyond the trend z-score | Incremental forward return / R in regression and setups | Same rule without the volume term |
| H3 | Pullback entries (S1) in uptrends beat random entries in the same uptrends | Expectancy in R, MAE/MFE | Random entries, matched holding time |
| H4 | Tapered kernels cut whipsaws at equal lag without hurting returns | Switches/yr; Sharpe difference with bootstrap CI | Boxcar |
| H5 | Time-of-day volume normalisation improves 1h/65-min flow signals | Same as H2, intraday | Raw volume |

## 6. Data plan

The Financial Datasets connector worked for AAPL but answered "Unauthorized" for SPY hourly, IWM and
^GSPC (likely a plan restriction). Through chat it also costs about 45 tokens per bar, so it suits
spot checks, not bulk research.

Options for the research harness, which reads files or APIs directly:

| Option | Covers | Notes |
|---|---|---|
| Financial Datasets REST API key, with `api.financialdatasets.ai` allowed in this environment's network settings | Stocks/ETFs per plan | Loader in `tfs.data.fetch_financial_datasets` (untested: host blocked) |
| Survivorship-free daily vendor (e.g. Norgate Data) | US stocks incl. delisted, index-constituent history | Gold standard for retail-level stock backtests |
| Intraday vendor (e.g. Polygon.io, Tiingo, FirstRate Data) | 1-min to 1-h bars, multi-year | Needed for H5 and 65/195-min tests |
| TradingView chart export | Any symbol, limited bars per plan | Also used for Pine ↔ Python parity checks |
