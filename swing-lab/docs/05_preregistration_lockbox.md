# Pre-registration of the lockbox run

**Status: FINAL. Committed and pushed before `research/confirm/run_lockbox.py` opened the sealed
data.** Written 11 Nov 2026 (UTC). The lockbox is 3 January 2023 to 9 November 2026,
survivorship-free. No return, price or event from that period has been read by any script of this
project except E03 (1-hour bars of 2023-12-14 to 2024-12-31, four non-P&L questions; protocol
amendment 1). It is opened once. The runner refuses to run a second time.

Frozen inputs: `research/confirm/prereg_lockbox.py`. Signal definitions:
`research/swinglab/candidates.py`. The same code, run on validation data
(`--sample VAL`), reproduces the validation results to the last digit
(`research/results/lockbox_dryrun_VAL.json`).

## The list (eight items; the protocol allows ten)

### Primary: these can become "demonstrated out of sample"

| ID | Claim | Criterion (all parts required) |
|---|---|---|
| **L1** | **How far a stock moves.** (a) R2 exactly as validated: 10-bar log return from the next open divided by 0.757 x ATR(14)/close x sqrt(10). (b) The bands the scripts display: ln(close[t+h]/close[t]) divided by ATR(14)/close x sqrt(h), chart prices, with the 5% / 25% / 75% / 95% lines at -1.23 / -0.40 / +0.45 / +1.10 (h = 5), -1.26 / -0.40 / +0.47 / +1.10 (h = 10), -1.28 / -0.40 / +0.49 / +1.11 (h = 20) | (a) R2's validation criteria unchanged (quantile ranges; coverage 87-93% pooled, 84-94% in each volatility tercile, 85-95% in at least 3 of the 4 blocks 2023, 2024, 2025, 2026). (b) At each of the three horizons the 90% band holds 87-93% of outcomes and the 50% band 46-54% |
| **L2** | **How often a stop is hit by noise.** Entry at the next open, stop k x ATR(14) below it, k = 1, 1.5, 2, 2.5, 3, 4, within 5, 10, 20 bars. (a) R3 as validated, against the development table. (b) Against the table the scripts display (mean of the development and validation tables; 2 ATR, 10 bars: 32.4%) | (a) R3's criteria unchanged: largest difference over the 18 cells <= 4 points; at 2 ATR and 10 bars, 8-20% of stop exits gap through and at most 1.92% of trades end worse than -1.5R. (b) Largest difference from the displayed table <= 4 points |
| **L3** | **Earnings nights.** Opening gap of the reaction bar in units of the previous bar's ATR(14). Displayed: worse than -1 ATR 17%, worse than -2 ATR 7.5%, worse than -3 ATR 3.5% | (a) R4 unchanged: P(gap worse than -2 ATR) on reaction bars at least 20 times that on ordinary nights. (b) Observed P(worse than -1 ATR) between 13% and 21%, P(worse than -2 ATR) between 5% and 10.5% |
| **L4** | **Market state is a risk state.** SPY above or below its 200-day average | R6 unchanged: SPY's daily volatility below the average at least 1.5 times that above it, and a universe stock more likely to lose 10% in 20 bars when SPY is below |
| **L5** | **E1.** Opening gap >= +3 sigma, volume >= 3 times the median of the prior 20 bars, close in the top third of the bar; return over 10 bars from the next open against the universe; predicted sign + | Protocol amendment 2: day-weighted estimate positive with one-sided Student-t p <= 0.05 (Newey-West, 20 lags) AND event-weighted estimate positive with one-sided p <= 0.10 |

### Secondary: these failed their validation criterion and can earn "suggestive" at most

| ID | Claim | What is computed | "Agrees in sign" means |
|---|---|---|---|
| S1 | PE1: earnings reaction bar with a close-to-close move >= +3 sigma; 20 bars; + | Same statistics as L5 | Day-weighted and event-weighted estimates both positive |
| S2 | R1: ATR(14)/close forecasts next-10-bar volatility better than EWMA(20) and Yang-Zhang(20) | R1 as in validation | ATR's QLIKE lower than both at h = 10 |
| S3 | R5: on random entries, holding 20 bars without a stop earns more per bar than a 2-ATR stop or an exit under the 20-day average; the 3-ATR stop is reported beside them | R5 as in validation | Both differences positive |

### Declared diagnostics (descriptive, no verdict)

E1: event-weighted return net of protocol costs; signals per month; without names that stop
trading within 126 bars; on and off earnings reaction bars; cross-section halves A and B (on
validation data the whole effect sat in half A: +102 bp against -21 bp, a warning). The slice
after the researcher's knowledge ends, 1 July to 9 November 2026: E1's mean daily spread and the
coverage of the displayed bands. R1b, the refitted ATR constant. Coverage of the displayed 90%
band by calendar block.

## How results map to labels (fixed now)

| Outcome | Label in the deliverable |
|---|---|
| L1-L4: every part passes | **Demonstrated out of sample** |
| L1-L4: the unchanged validation claim passes and a displayed constant misses its range, or the reverse | The part that passed keeps its label; the part that failed is reported as failed and the displayed constant is corrected to the pooled estimate and marked "recalibrated after the lockbox, untested" |
| L5 passes | **Demonstrated out of sample**, with the note "missed significance on validation" |
| L5 has the predicted sign in both weightings without passing | **Suggestive**. The script keeps the event marker and its alert, labelled as such |
| L5 has the wrong sign in either weighting | Dead. The scripts ship without a directional signal |
| S1-S3 agree in sign | **Suggestive** |
| S1-S3 do not | Dead (S1), or reported as unsupported (S2, S3) |

## What cannot be fixed

The researcher is a language model that has read about 2023-2026 (protocol section 2.4). It knows,
for instance, that markets fell sharply in April 2025. That knowledge could have shaped which
claims were kept. Mitigations: every claim above was fixed from 2011-2022 data or pre-2023
literature; the slice from July 2026 is reported separately; the forward test in the playbook is
the only fully clean one.
