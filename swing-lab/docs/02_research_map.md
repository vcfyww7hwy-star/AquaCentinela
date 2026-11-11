# The map: what was tried, how close each idea came, what is real

Final, 11 Nov 2026 (UTC). Every number below is in `RESEARCH_LOG.md` (entries 2-7) and in
`research/results/`. Units: basis points of return over the stated number of daily bars, measured
from the open after the signal, against the other stocks in the universe on the same day; t is a
date-clustered t-statistic.

## How to read the columns

| Column | Sample | What it is |
|---|---|---|
| CTX | 1998-2010 | Survivors only. Strongly biased. Development |
| DEV | 2011 - Jun 2018 | Companies alive in 2018. Biased. Development |
| VAL | Jul 2018 - 2022 | Survivorship-free. Looked at twice, with pre-registered tests |
| LOCK | 2023 - 9 Nov 2026 | Survivorship-free. Opened once, for a frozen list of eight items |

Universe: US-listed common stocks and ADRs, price at least $5, 60-day median dollar volume at least
$20M (about 900 names a day in 2011-18, 1,456 in 2018-22, 1,650 in 2023-26).
Trials logged: 64,213 (37,791 on DEV, 25,933 on CTX, 272 on the short-volume sample, 30 outcomes in
the two validation runs, 12 on the lockbox).

## 1. Rules that say which stock to buy, or when

| Family | Best representative | CTX | DEV | VAL | LOCK | Verdict |
|---|---|---|---|---|---|---|
| Event: gap up >= 3 sigma, volume >= 3x, close in the top third (E1), 10 bars | as stated | +89 (2.9) | +47 (1.8) | +68 (1.7) | **-7 (-0.2)** | **Dead.** The closest any rule came: same sign and size in three samples, zero in the fourth. By cross-section half it was +102 / -21 on VAL and +66 / -65 on LOCK: noise |
| Drift after a strong earnings reaction (>= +3 sigma), 20 bars | PE1 | no dates | +33 (1.1) | +71 (1.8) | +7 (0.2) | Dead in practice (agrees in sign at a tenth of the size) |
| Drift after a bad earnings reaction (<= -3 sigma), 20 bars | PE2 | no dates | -9 (-0.4) | +30 (0.8) | not tested | Dead: wrong sign on validation |
| Falling knives keep falling: fall >= 3 sigma on volume (A1), 20 bars | as stated | -78 (-3.4) | -49 (-2.7) | +3 (0.1) | not tested | Dead on validation |
| Gap down and weak close (A4), 20 bars | as stated | -36 (-2.6) | -37 (-3.6) | +28 (1.1) | not tested | Dead on validation, wrong sign |
| Bounce below the 200-day average (A2), 10 bars | as stated | -22 (-1.9) | -30 (-2.4) | +7 (0.3) | not tested | Dead on validation |
| Unfilled gap up (A3), 5 bars | as stated | -21 (-4.2) | -16 (-3.5) | -4 (-0.4) | not tested | Dead on validation |
| Overnight-driven rally (A5), 5 bars | as stated | -14 (-2.0) | -23 (-2.3) | -2 (-0.1) | not tested | Dead on validation |
| Do not chase: up 1-2 sigma in 3 bars (A8), 5 bars | as stated | -18 (-4.5) | -10 (-3.6) | -12 (-1.2) | not tested | Dead on validation (right sign, a tenth of a round trip) |
| The six "avoid" states as a family | global test | | | mean t 0.03, p 0.45 | | Dead |
| Dip buying in an uptrend, 5 bars | RSI(2) < 10; three down closes | +29 (6.1); +34 (8.1) | -3 (-0.7); -6 (-1.1) | | | Dead after 2010. Alive in 1998-2010, which is the finding |
| Dip buying, less liquid bucket ($5-20M a day), 5 bars | RSI(2) < 10 | +25 (3.2) | -11 (-1.5) | | | Dead, and the cost there is 50 bp a round trip |
| Breakouts, 20 bars | new 55-bar closing high against names near it | +25 (1.7) | -9 (-0.7) | | | Dead |
| Breakout to a 252-bar high on volume (E2), 5 bars | as stated | +21 (2.3) | +21 (2.4) | dropped before the look | | Too small for a round trip |
| Volume: high-volume premium, pocket pivots, accumulation counts, OBV divergence | high-volume premium, 20 bars | +25 (4.0) | -3 (-0.6) | | | Dead |
| Momentum and 52-week-high selection, 60 bars | 12-1 momentum above +50% | +89 (0.7) | +1 (0.0) | | | Dead in liquid names (40,350 cells searched) |
| Low volatility, lottery, skewness | 60-bar skewness <= -1 (E3), 60 bars | +100 (2.5) | +42 (1.9) | -62 (-1.5) | | Dead (diagnostic on validation) |
| Oversold: 4 ATR below the 50-day (A9), 20 bars | as stated | +138 (3.0) | -54 (-2.1) | +37 (0.7) | | No effect once the dead companies are in the sample |
| Volatility contraction ("squeeze", NR7, narrow Bollinger width) | direction of the next move | none | none | | | Dead; predicts neither direction nor, beyond 10-13%, size |
| Trend age, CUSUM alarm, variance-ratio and autocorrelation gates, efficiency ratio | | nothing consistent | nothing consistent | | | Dead |
| Stock against market residual reversal | | | nothing above costs | | | Dead |
| Round numbers | | large | large | | | Void: an artefact of split-adjusted price levels |
| FINRA daily short-sale volume, 5 bars (own sample Aug 2018 - Jun 2020) | short share >= 60%; <= 30% | | -4 (-1.0); +5 (1.1) | not carried forward | | Dead: published sign, 5-10 bp a week |
| Calendar: turn of the month (CRSP market, Kenneth French library) | extra return per day | +9.5 bp (2.2) in the 1990s | +2.7 bp (0.5) since 2010 | | | Dead |
| Short-term reversal, big stocks (Kenneth French library, % a year) | losers minus winners | +15.8 (2.1) in 2000-09 | +2.7 (0.6) in 2010-22 | | | Dead in large stocks |
| Momentum 12-2, big stocks (Kenneth French library, % a year) | winners minus losers | +2.2 (0.3) in 2000-09 | +1.6 (0.3) in 2010-22 | | | Dead in large stocks |

What this says. In liquid US stocks, at holding periods of one to four weeks, from price, volume
and the other series a chart can show, there is no stock-picking or timing rule in this search
that survives data it has not seen. Most of the textbook rules worked before 2010 and stopped.
The rules that looked strongest on two decades of development data (t-statistics of 3 to 4)
failed on the first fresh sample. This agrees with the published record on the decay of anomalies
after publication and in liquid stocks (McLean & Pontiff 2016; Chordia, Subrahmanyam & Tong 2014;
Martineau 2022 on earnings drift), which was read before the tests and is cited from the
literature reports in `_raw/` (citations not independently re-verified).

## 2. The arithmetic of risk

| Claim | CTX | DEV | VAL | LOCK | Verdict |
|---|---|---|---|---|---|
| Close-to-close move over h bars, in units of ATR(14) x sqrt(h): the 90% band holds 90%, the 50% band 50% (h = 5, 10, 20) | 90.5-90.8% / 49.7-50.8% | calibration | calibration | **89.6-89.9% / 48.8-50.0%** | **Demonstrated out of sample** |
| Same, from the next open, with development constants (R2) | calibration | calibration | 89.9% | 89.6% | **Demonstrated out of sample** (passed twice) |
| Stop k ATR below the next open is hit within h bars (18 cells); 2 ATR, 10 bars | 31.6% | 31.5% | 33.2% | **31.6%**; largest gap over the table 1.7 points | **Demonstrated out of sample** (passed twice) |
| Share of stop exits that gap through the stop; trades worse than -1.5R (2 ATR, 10 bars) | 9-17% | 11-17% | 15.9%; 0.81% | 15.1%; 1.02% | **Demonstrated out of sample** |
| Earnings night against an ordinary night: gap worse than -2 ATR | no dates | 79 times | 48 times | **104 times** | **Demonstrated out of sample** (criterion: 20 times) |
| The exact odds of that gap | | 9.7% | 7.5% | 12.3% | Failed as displayed (too low). Now shown as the 2017-2026 pool: 20% / 10% / 5% for 1 / 2 / 3 ATR; by year 15-27%, 5-15%, 3-8%. **Untested** |
| Index volatility with SPY below its 200-day average, as a multiple of above | 1.9 | 1.9 | 2.2 | 2.4 | **Suggestive** (the lockbox claim was a conjunction and failed on its other half) |
| A stock is likelier to lose 10% in 20 bars when SPY is below its 200-day average | 18.1% v 9.7% | 11.2% v 6.8% | 15.6% v 14.7% | **9.8% v 13.3%** | **Failed** on the lockbox |
| Mean index return above and below the 200-day average | same | same | +2 v +5 bp a day | +5 v +24 bp a day | The state forecasts risk, not return; after 2018 it has been a contrary signal if anything |
| Net return per bar held, random entries: no stop / 3-ATR stop / 2-ATR stop / exit under the 20-day average | 3.97 / 2.92 / 2.57 / 0.96 | 4.28 / 3.37 / 2.66 / 0.49 | 1.95 / 2.24 / 1.39 / 0.94 | 5.71 / 5.10 / 4.67 / 3.73 | **Suggestive**: same order in four samples, never significant |
| ATR(14) forecasts next-10-bar volatility better than an EWMA of squared returns | yes | yes, 17% | 15%, t 1.7 | 15%, t 4.4 | **Suggestive** |
| ... and better than range estimators (Yang-Zhang) | yes | yes, 14% | 9%, t 4.3 | tie | Unsupported |
| The constant that turns ATR into a daily sigma | 0.757 | (applied) | 0.879 | 0.85 | Not a constant; the scripts never quote a sigma |
| Market-level 200-day rule, 1926-2022 (Kenneth French library): Sharpe 0.88 against 0.61, worst drawdown -40% against -84% | | | | | Context, **untested** here; gave up 3-5 points a year in 2010-18 |

## 3. Intraday (Yahoo 1-hour bars, Dec 2023 - Dec 2024, survivors, no P&L)

| Question | Answer | Status |
|---|---|---|
| Does a decision taken at 15:30 agree with the one taken at the close? | About 90% of the time | Suggestive, one year |
| Does 1-hour realised variance improve the daily volatility forecast? | Yes, modestly | Suggestive, one year |

No intraday trading rule was tested: free 1-hour history is two years of surviving companies,
which cannot carry a conclusion. An Alpaca key (free tier, 1-minute bars from 2016) would allow
it; given the daily results the prior that it changes the picture is low.

## 4. What would change the conclusion

| If | Then |
|---|---|
| A data source with information the chart does not carry (point-in-time fundamentals, analyst revisions, options, order flow) | A different search. None of it is available to a Pine script, except fundamentals without point-in-time history |
| Less liquid stocks (under $20M a day) | French's small-stock reversal is still +10% a year after 2010, but the only test here (dips in the $5-20M bucket) was negative before a 50 bp round trip |
| Longer holding periods (months) | Outside the brief. Momentum and trend-following live there, at index and sector level more than in single liquid stocks |
| The trader's own selection has skill | Measurable: the playbook's forward test tells a +0.2R edge from none in about 100-150 trades |
