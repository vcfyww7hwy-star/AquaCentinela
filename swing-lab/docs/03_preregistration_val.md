# Pre-registration of the validation run

**Status: FINAL. Committed before `research/confirm/run_val.py` was executed on validation data;
the commit hash is recorded in the research log (entry 5).**

Written 11-12 Nov 2026 and revised after two independent audits
(`docs/_raw/audit_code.md`, `docs/_raw/audit_stats.md`). No outcome on the validation sample has
been computed. One fact about that sample was read during the audit: its list of dates.

## What is tested

Sample **VAL**: 2 July 2018 to 30 December 2022, the survivorship-free part of the panel, on a
calendar of days on which the market was open. It holds the fourth-quarter 2018 fall, the 2020
crash and rebound, 2021, and the 2022 bear market.

Everything is run once by `research/confirm/run_val.py`, which refuses to run a second time.
Signal definitions are the functions in `research/swinglab/candidates.py`; lists, thresholds and
development reference numbers are in `research/confirm/prereg_val.py`. The same code was dry-run
on DEV (`--sample DEV`) and reproduces the development numbers.

### Part D: seven directional candidates, one family

Outcome: total return from the open of *t*+1 to the close of *t*+*h*, dividends included, exit at
the last close (with a -30% haircut when the security stopped trading for cause).

| ID | Signal at the close of *t* | Control | h | Predicted | Development, day-weighted bp (t): DEV / CTX | Event-weighted, DEV |
|---|---|---|---|---|---|---|
| E1 | Opening gap >= +3 sigma, volume >= 3x the median of the prior 20 bars, close in the top third of the bar | universe | 10 | + | +47 (1.8) / +89 (2.9) | +51 (2.4) |
| A1 | One-day fall >= 3 sigma on volume >= 3x | universe | 20 | - | -49 (-2.7) / -78 (-3.4) | -28 (-2.3) |
| A2 | Close below the 200-day average and up >= 1.5 sigma over 5 bars | names below their 200-day | 10 | - | -30 (-2.4) / -22 (-1.9) | -22 (-2.1) |
| A3 | Low above the prior bar's high, and not an E1 event | universe | 5 | - | -16 (-3.5) / -21 (-4.2) | -8 (-2.5) |
| A4 | Opening gap <= -1 sigma and close below the open | universe | 20 | - | -37 (-3.6) / -36 (-2.6) | -21 (-2.6) |
| A5 | 20-bar sum of overnight log returns >= +5% and of intraday log returns <= -5% | universe | 5 | - | -23 (-2.3) / -14 (-2.0) | -11 (-1.4) |
| A8 | Up between 1 and 2 sigma over 3 bars | universe | 5 | - | -10 (-3.6) / -18 (-4.5) | -4 (-2.2) |

sigma is the robust EWMA volatility of `engine.vol_ewma`, taken before the move it scales. The gap
is `ln(open / close[1]) / sigma[1]`.

**Verdict "confirmed" requires both:**

1. *Day-weighted:* the mean over days of (signal mean minus control mean), Newey-West with 2*h*
   lags, one-sided p-value from Student's t with df = floor(days with a spread / 2*h*) - 1,
   significant under Holm's step-down at 5% across the seven.
2. *Event-weighted:* sum of n_t d_t over sum of n_t, date-clustered, with the predicted sign and
   one-sided p <= 0.10.

Other verdict words: **right sign, not significant**; **wrong sign**. With 1,134 validation days
against 1,894 in DEV, standard errors are about 1.3 times larger. If every development estimate
were exactly true, about three of the seven would be confirmed; if the truth is half of it, fewer
than one. "Right sign, not significant" is therefore the expected outcome for a real effect of
development size and is not a refutation.

Reported with the family, fixed here:

- **Label "material for a trend follower":** for an avoid state, the event-weighted effect inside a
  plain trend selection (close above the 200-day average and within 15% of the 252-bar high) is
  -20 bp or worse; for E1, the event-weighted effect net of protocol costs (5 bp a side at $50M
  median dollar volume and above, 10 bp a side below) is +20 bp or better.
- **A3 and A5, bars 2 to 5** (signal delayed one bar, *h* = 4). Without the predicted sign there,
  the wording is "not at the next open", not "avoid for a week".
- **Global test of the six avoid states:** the mean of their sign-adjusted t-statistics against a
  joint month-block bootstrap of recentred series, 1,000 draws, one-sided 5%. It asks whether the
  family as a whole exists.
- **E1 and take-overs.** The development samples contain almost no company that was later bought.
  Validation does. A take-over announcement is a gap up on heavy volume that closes high and then
  goes flat until the deal closes, so E1 is expected to be diluted. Declared diagnostic,
  descriptive only: E1 excluding names that stop trading within 126 bars of the event.
- **Diagnostics of survivor bias, no verdict:** A9 (4 or more ATR below the 50-day average, *h* 20;
  -59 in DEV, +138 in CTX, which holds only survivors) and E3 (60-bar skewness <= -1, *h* 60).

**Dropped before the look:** A6 failed breakout, A7 junk, A10 positive skew (now +20 bp in DEV
with the textbook statistic), A11 spike in a downtrend, E2 252-bar high on volume (does not pay a
round trip). Reasons: `audit_stats.md`, section 5.

### Part R: risk-engine claims (pass or fail)

| ID | Claim | Criterion |
|---|---|---|
| R1 | ATR(14)/close, rescaled by a constant fitted on 1998-2010, forecasts the realised volatility of the next bars better than EWMA(20) of squared returns and Yang-Zhang(20), each rescaled the same way | At h = 10: the daily mean of (competitor's QLIKE loss - ATR's) has Newey-West t (20 lags) >= 2.33 against each, ATR's QLIKE is at least 5% lower than each (development: 17% and 14%), and ATR is better in at least 3 of the 4 blocks 2018H2-2019, 2020, 2021, 2022. At h = 5 and 20: lower than both |
| R1b | The constant | The QLIKE-optimal scale refitted on validation at h = 10 lies in 0.68-0.83 (development 0.757) |
| R2 | Range calibration at h = 10 | 5% quantile in [-1.76, -1.36], 95% quantile in [+1.28, +1.68]; share of outcomes inside [-1.56, +1.48] between 87% and 93% pooled, between 84% and 94% in each tercile of forecast volatility, and between 85% and 95% in at least 3 of the 4 blocks |
| R3 | Stop-out table (random entries, stop k ATR below the next open, k = 1, 1.5, 2, 2.5, 3, 4; within 5, 10, 20 bars) | Largest absolute difference from the development table over the 18 cells <= 4 points; at k = 2, h = 10 the share of stop exits that gap through is between 8% and 20%, and the share of trades worse than -1.5R is at most 1.92% (twice development). Reported beside it: the same with a -100% delisting haircut |
| R4 | Earnings gap risk | P(gap worse than -2 ATR) on reaction bars is at least 20 times that on ordinary nights |
| R5 | Exits on the same random entries | Net bp per bar of "hold 20 bars, no stop" exceeds that of "2-ATR stop, 20 bars" and that of "exit on a close under the 20-day average", each with one-sided month-block-bootstrap p <= 0.05 |
| R6 | Market state | SPY's daily volatility below its 200-day average is at least 1.5 times that above it, and a universe stock is more likely to lose 10% in 20 bars |

## Changes made in response to the audits (all before the run)

| Finding | Action |
|---|---|
| **Blocker.** The calendar contained nine dates on which the market was closed (one in the validation period, 17 Feb 2020). On such a row every Yahoo-sourced security was a hole, which switched off 20- and 50-bar volume windows for weeks | Panel rebuilt on days on which SPY has a bar. Volume windows now tolerate a few missing bars (15 of 20, 40 of 50). All development numbers above recomputed; the auditor's independent repair gave the same E1 figure (+47.1 bp, t 1.84) |
| The data-error flag used the next bar's close and fed the universe at *t* | The universe no longer depends on it. Prices on flagged bars are still blanked: they are not prices anyone could trade |
| Day-weighting flatters: the event-weighted effect is about half for most candidates | Event-weighted condition added to the verdict; both are reported |
| Fourteen hypotheses were too many and included four that the development data did not support | Family cut to seven |
| Normal p-values overstate significance with overlapping windows | Student's t with the stated degrees of freedom |
| A3, A5: most of the effect is in the first session | Bars 2-5 endpoint registered |
| Risk criteria R1 and R5 would pass on any difference | Margins and tests added; R1b and the coverage conditions of R2 added |
| Skewness as coded was not the textbook statistic | Replaced by the textbook 60-bar skewness (E3 only a diagnostic now) |
| "First close above the high in 10 bars" fired on the first bar a high existed | Fixed (affects A6 and E2, both dropped) |
| The simulator kept stop-outs and dropped survivors among the last entries of a sample | Entries now stop one holding period before the sample ends; bars after the sample are never read |
| `Study.gap()` read one open from the next sample; `Study.mkt()` was not blanked | Fixed |
| Delisting branch never exercised by development data | Synthetic test added (`research/tests/test_delisting.py`), passes |
| Known and left: two renamed companies appear twice (COG/CTRA, CLNY/DBRG); one unadjusted split among 6,687 A1 events (QSII, Oct 2011); the truncation test proves the arithmetic is causal, not the data build | Stated here; none changes a sign |

## What happens next

- Confirmed directional candidates and passed risk claims go, unchanged, on the frozen list for
  the lockbox (at most ten items).
- Anything learned from this run that suggests a new definition is exploration on validation data
  and cannot be confirmed on it; it would need the lockbox or the forward test.
