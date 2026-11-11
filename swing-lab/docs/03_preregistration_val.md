# Pre-registration of the validation run

**Status: DRAFT until the independent audit (`docs/_raw/audit_code.md`, `audit_stats.md`) is
answered. The final version is committed before `research/confirm/run_val.py` is executed, and
the commit hash is recorded in the research log.**

Written 11-12 Nov 2026. No outcome on the validation sample has been computed.

## What is tested

Sample **VAL**: 2 July 2018 to 30 December 2022, the survivorship-free part of the panel (2,625
names passed through the $20M universe; 399 of them had stopped trading by the end of 2022). It
holds the fourth-quarter 2018 fall, the 2020 crash and rebound, 2021, and the 2022 bear market.

Everything is run once by `research/confirm/run_val.py`, which refuses to run a second time.
Definitions are the functions in `research/swinglab/candidates.py`; constants are in
`research/confirm/prereg_val.py`. The same code path was dry-run on DEV and reproduced the
development numbers.

### Part D: directional candidates

For each: the signal at the close of *t*, the control, the horizon *h*, the predicted sign.
Outcome: total return from the open of *t*+1 to the close of *t*+*h*. Statistic: the mean over
days of (signal mean minus control mean), Newey-West t with 2*h* lags, one-sided p-value in the
predicted direction. Family-wise error is controlled with Holm's step-down at 5% across the list.

| ID | Signal | Control | h | Predicted | Why it should exist |
|---|---|---|---|---|---|
| E1 | Opening gap >= +3 sigma, volume >= 3x the median of the prior 20 bars, close in the top third of the bar | universe | 10 | + | Under-reaction to news; drift measured by announcement return and volume (Chan, Jegadeesh & Lakonishok 1996; Garfinkel & Sokobin 2006) |
| E2 | First close above the 252-bar closing high in 10 bars, volume >= 1.5x its 50-bar average | names within 3% of that high | 5 | + | Anchoring on the 52-week high (George & Hwang 2004) |
| E3 | Skewness of the last 60 daily log returns <= -1 | universe | 60 | + | Lottery preference: positively skewed stocks are overpriced (Boyer, Mitton & Vorkink 2010) |
| A1 | One-day fall >= 3 sigma on volume >= 3x | universe | 20 | - | Slow diffusion of bad news; information shocks continue (Savor 2012) |
| A2 | Close below the 200-day average and up >= 1.5 sigma over 5 bars | names below their 200-day | 10 | - | Short-covering rallies in downtrends fade |
| A3 | Low above the prior bar's high, and not an E1 event | universe | 5 | - | Attention-driven buying at the open (Berkman et al. 2012) |
| A4 | Opening gap <= -1 sigma and close below the open | universe | 20 | - | As A1 |
| A5 | Sum of overnight log returns over 20 bars >= +5% and sum of intraday log returns <= -5% | universe | 5 | - | Overnight-driven rallies reverse (Lou, Polk & Skouras 2019; Aboody et al. 2018) |
| A6 | First close above the 55-bar high two bars ago, close now back below that level | universe | 20 | - | Failed breakouts trap late buyers |
| A7 | 12-1 momentum < 0, more than 30% below the 252-bar high, below the 200-day | universe | 60 | - | Momentum and 52-week-high effects, loser side |
| A8 | Up between 1 and 2 sigma over 3 bars | universe | 5 | - | Short-term reversal, winner side |
| A9 | Close 4 or more ATR(14) below the 50-day average | universe | 20 | - | Development samples disagree (-54 in DEV, +138 in CTX, which holds only survivors); VAL includes the ones that did not survive |
| A10 | Skewness of the last 60 daily log returns >= +1 | universe | 60 | - | As E3 |
| A11 | Close below the 200-day average and a one-day rise >= 3 sigma | names below their 200-day | 5 | - | As A2 |

sigma is the robust EWMA volatility of `engine.vol_ewma`, taken before the move it scales.

Verdict words: **confirmed** (predicted sign and significant after Holm), **right sign, not
significant**, **wrong sign**. A candidate that is not confirmed is not sent to the lockbox as a
directional claim. The event-weighted estimate is reported beside the primary one and does not
change the verdict.

### Part R: risk-engine claims (pass or fail)

| ID | Claim | Criterion fixed here |
|---|---|---|
| R1 | ATR(14)/close, rescaled by a constant fitted on 1998-2010, forecasts the realised volatility of the next 5, 10 and 20 bars better than EWMA(20) of squared returns and Yang-Zhang(20), each rescaled the same way | QLIKE lower than both at all three horizons |
| R2 | The 10-bar return from the next open divided by 0.757 x ATR(14)/close x sqrt(10) has the same 5% and 95% quantiles as in development (-1.56, +1.48) | 5% quantile in [-1.76, -1.36] and 95% quantile in [+1.28, +1.68] |
| R3 | The share of random entries stopped within 5, 10, 20 bars by a stop 1, 1.5, 2, 2.5, 3, 4 ATR below the next open matches the development table | largest absolute difference over the 18 cells <= 4 percentage points |
| R4 | A gap worse than -2 ATR is far more likely on an earnings reaction bar than on an ordinary night | ratio of the two probabilities >= 20 |
| R5 | For random entries, holding 20 bars without a stop earns more per bar than a 2-ATR stop, and more than exiting on a close under the 20-day average | both inequalities hold, net of costs |
| R6 | SPY is at least 1.5 times as volatile below its 200-day average as above it, and a universe stock is more likely to lose 10% in 20 bars | both hold |

Development values for each claim are in `research/results/g12_risk_engine.json`,
`g11_exits.json`, `g02_events.json`, `g09_regime.json`.

## What happens next

- Confirmed directional candidates and passed risk claims go, unchanged, on the frozen list for
  the lockbox (at most ten items in total).
- Anything learned from this run that suggests a *new* definition counts as exploration on
  validation data and cannot be confirmed on it; it would need the lockbox or the forward test.

## Changes made in response to the audit

*(to be filled before the run)*
