# Protocol: how a finding earns the right to be traded

Written 10 Nov 2026, **before any outcome was computed on the data described here**. Changes after
this date are appended at the bottom with a date and a reason; nothing above is edited in place.

This protocol exists to hold two goals at once. The search must be wide: many ideas, some strange.
And nothing may be believed merely because it was the best of many. Every rule below serves one of
those two.

## 1. The three levels of claim

Every statement in the final deliverable carries exactly one label.

| Label | Meaning |
|---|---|
| **Demonstrated out of sample** | The exact rule, with frozen parameters, was written down before the lockbox was opened, and it passed its pre-stated criterion on the lockbox. |
| **Suggestive** | Passed on the validation partition after correction for the number of things tried, or agrees in sign with the lockbox without reaching the criterion. |
| **Untested** | Everything else, including anything that rests on literature alone or on simulated data. |

Simulated prices are used only to test code (a detector finds a planted break, two implementations
agree). They never support a statement about markets.

## 2. Data partitions

Frozen here. The loaders in `research/swinglab/data.py` enforce them: they refuse to return rows
after a partition's end unless the lockbox has been opened, and opening it writes a dated record to
`registry/lockbox.json`.

### 2.1 Daily data (the main body of evidence)

Source: DoltHub `post-no-preference/stocks`, daily bars for US-listed symbols as they traded,
3 Jan 2011 – 9 Nov 2026 (see `01_data_inventory.md` for defects).

| Partition | Dates | Universe quality | Use |
|---|---|---|---|
| **DEV** | 2011-01-03 – 2018-06-29 | **Biased**: only symbols still alive in 2018 | Exploration. Free to look, every look counted. Absolute returns here are overstated; only signal-versus-control differences are read. |
| **VAL** | 2018-07-02 – 2022-12-30 | Survivorship-free (delisted names present) | Confirmation of hypotheses registered from DEV. Looks are counted and corrected for. |
| **LOCKBOX** | 2023-01-03 – 2026-11-09 | Survivorship-free | **Opened once, at the end**, for a short frozen list of rules. |

Two further cuts are reported with every result:

- **Cross-section halves A/B** by `md5(symbol) mod 2`. Same dates, different companies: a check on
  whether a result belongs to a handful of names.
- **POST-CUTOFF slice, 2026-07-01 – 2026-11-09**, inside the lockbox. See §2.4.

### 2.2 Older daily data (context, not confirmation)

The 1999–2018 survivor sets used by `trend-flow-suite` and Yahoo history for today's listed
companies are survivor-biased throughout. They are used to see whether an effect behaves the same in
the 2000–02 and 2008 bear markets, and are labelled as such. A rule is never promoted on them alone.

The Kenneth French library (daily portfolio returns built from CRSP, which includes delisted
companies) is the survivorship-free long history we do have, at portfolio level only. It is cut at
2022-12-30 like everything else until the lockbox opens.

### 2.3 Intraday data

Yahoo gives 1-hour bars only for about the last two years (12 Dec 2023 onward) and only for
companies that still exist. That window lies entirely inside the daily lockbox. Rules:

- Until longer intraday history arrives, 1-hour data is used only for **non-P&L questions**:
  volatility forecasting, time-of-day volume normalisation, how well a signal computed before the
  close matches the one computed at the close, and the cost of trading at the open versus the close.
- Intraday P&L hypotheses get their own partitions: develop on 2023-12-12 – 2024-12-31, lockbox
  2025-01-02 – 2026-11-09. Anything concluded from them is labelled with the two-year limit and the
  survivor bias.
- If 1-hour data from 2016 becomes available, this section is replaced (appended below) with
  partitions that match the daily ones.

### 2.4 A contamination that cannot be removed, stated plainly

The researcher here is a language model whose training data runs to mid-2026. It has read about
the markets of 2023–2026: which sectors led, which crashes happened. The lockbox is therefore out
of sample for **computed outcomes** but not for the researcher's prior beliefs. Mitigations:

1. Every hypothesis must be justified from literature published before 2023 or from DEV/VAL
   evidence, in writing, before testing.
2. The slice after the model's knowledge ends (2026-07-01 onward) is reported separately. It is
   short (about 90 trading days) and it is the only window clean in both senses.
3. The real out-of-sample test is forward: alerts logged before outcomes are known. The delivery
   includes the logging template and the statistical stopping rule for it.

## 3. Counting what was tried

`registry/trials.jsonl` is append-only. One line per evaluated outcome: hypothesis ID, exact
definition, parameters, universe, partition, metric, result, timestamp, code commit.

- A **trial** is any (definition x parameters x universe x partition) whose outcome was looked at.
  Changing a threshold and re-running is a new trial. So is looking at a new sub-period.
- A **family** is a set of trials that answer the same question (for example all variants of
  "dip depth"). Families are declared before their first run.
- The running totals (trials, families, hypotheses alive, dead) are printed at every milestone.

How the count is used:

- **DEV:** no correction; nothing on DEV is evidence.
- **VAL:** within a family, the Romano–Wolf step-down or, where impractical, Benjamini–Hochberg at
  q = 0.10. Across families a discovery needs |t| >= 3.0 on date-clustered statistics (Harvey, Liu
  & Zhu 2016). A pre-registered replication of a published effect with the published sign needs
  |t| >= 2.0.
- **LOCKBOX:** at most ten frozen rules. Each has a one-sided test with the sign fixed in advance;
  Holm correction across the ten.

## 4. Statistics

Stock returns on the same day are correlated, so stock-days are not independent observations.

- The unit of inference is the **date**. Signal-minus-control differences are computed each day
  across stocks, giving one number per day; inference is on that daily series with Newey–West
  standard errors (lag = 2 x holding period) and, as a check, a block bootstrap over calendar months.
- Forward returns are measured **from the first price the trader could have obtained** (§5), in
  basis points and in units of the stock's own forecast volatility.
- Every result is shown gross and net of costs, by sub-period, by liquidity bucket, and for the A/B
  halves.
- An effect is "stable" only if it survives: +/-25% changes to each parameter, removal of the best
  month, removal of the 20 most influential symbols, doubling of costs, and a one-bar delay in
  execution.

## 5. Fills, costs, gaps, delistings

The trader acts on alerts and cannot watch the screen. The base case is therefore:

| Item | Base assumption | Stress |
|---|---|---|
| Signal time | Close of bar *t*, computed only from data up to *t* | – |
| Entry | **Open of bar *t*+1** (market-on-open) | Close of *t* reported separately as "needs action before the close", never as the base case |
| Exit by rule | Open of the bar after the exit signal | – |
| Stop-loss | Resting stop order. If the bar's low is at or below the stop: fill at the stop, or at the open if the bar opened below it (gap-through) | Extra 10 bp on every stop fill |
| Limit entry | Filled only if the low trades strictly below the limit; at the open if the bar opens below it | – |
| Cost per side, commission + half-spread + slippage | 5 bp if median daily dollar volume >= $50M; 10 bp for $20–50M; 25 bp for $5–20M | Doubled |
| Dividends | Signals use split-adjusted prices (TradingView's default chart). P&L includes dividends | – |
| Universe at date *t* | Common stocks, ADRs and ETFs with 60-day median dollar volume >= $20M and price >= $5, judged with data up to *t* only | $5M floor as a wider universe; $50M as a narrower one |
| Delisting | A position held when a symbol stops trading exits at the last close. If the last close is under $2 or the final 60 bars lost more than 50%, a further −30% is applied (delisting for cause; Shumway 1997) | −100% |
| Costs paid on | Every entry and every exit, including stops and delistings | – |

These are assumptions until the questions put to the user on 10 Nov 2026 (broker, commissions,
order types, when orders can be placed) are answered. They are deliberately on the expensive side.

## 6. Destruction before belief

A candidate that passes VAL is handed to an attempt to break it before it may enter the frozen
lockbox list. The attempt includes, at minimum:

1. **Leak audit.** Recompute every input with data truncated at *t* and confirm identical signals.
   Shift the signal one bar late and confirm the edge does not *improve*.
2. **Placebo.** Random entries matched on date, liquidity bucket and trend state; the candidate
   must beat the placebo distribution, not zero.
3. **Data-error audit.** Re-run without the 1% most extreme input bars and on the subset of symbols
   whose prices agree with an independent source (Yahoo). Mean-reversion "edges" are often bad ticks.
4. **Decomposition.** How much of the return is market beta, sector, the overnight gap that the
   trader cannot capture, or the one best month.
5. **Capacity and cost.** Break-even cost per side; turnover; fraction of signals in names where
   the assumed cost is optimistic.
6. **Same mathematics.** The Pine script reproduces the research signal bar for bar (§7).

Results of the attempt are logged whether or not the candidate survives.

## 7. Pine verification ladder

A script is "verified to level *n*":

1. **Compiles** under TradingView's compiler (`tools/pine_compile.py`), zero errors, warnings read.
2. **Executes** in an open-source Pine runtime on the same bars as the research code and matches
   it within tolerance (useful only as far as that runtime is itself shown to match TradingView).
3. **Matches on TradingView:** the user's CSV export of the script's plots on named symbols and
   timeframes matches the research code bar for bar (`tools/parity_check.py`). This is the level
   required for delivery.
4. **Does not repaint:** an export taken on a later day reproduces the earlier export's values for
   all bars closed at the time of the first export.
5. **Strategy twin agrees:** the Strategy Tester's trade list on a symbol matches the research
   backtest of the same symbol trade for trade.

## 8. Forward test

Delivery includes a log sheet and a sequential test (SPRT on per-trade outcomes against the
lockbox estimate) with stopping boundaries fixed in advance, so that "the edge has stopped working"
is a computed event, not a feeling.

---

## Amendments


### Amendment 1 - 11 Nov 2026 (before any validation outcome was computed)

Reason: three data sets turned out to begin or end at awkward places. Nothing above changes.

1. **Context sample CTX.** Yahoo daily history of today's survivors, 1998-2010, was added as a
   second development sample because DEV (2011-2018) holds no bear market. It is strongly
   survivor-biased and is never evidence; it shows whether an effect behaves the same in 2000-02
   and 2008 before a validation look is spent.
2. **Earnings.** Announcement dates begin in January 2017. The earnings family therefore develops
   on DEV restricted to 2017-01..2018-06 and has no CTX. Its hypotheses are taken from the
   published literature, so that the short development window is a sanity check, not a search.
3. **Short-sale volume.** FINRA's consolidated daily file, the series TradingView exposes, begins
   on 2018-08-01, inside the validation window. That family alone uses its own split:
   exploration `DEV_S` 2018-08-01..2020-06-30, confirmation `VAL_S` 2020-07-01..2022-12-30.
   Consequence, stated plainly: for that family the researcher sees returns from the first third
   of the validation window, conditioned on short-volume features. No other family may be
   explored there.
4. **Intraday.** E03 used 1-hour bars from 2023-12-14 to 2024-12-31 for four non-P&L questions
   (volume profile, agreement of a 15:30 decision with the close, realised-variance forecasting,
   timing of the day's extremes), as section 2.3 allows. Those dates lie inside the daily lockbox;
   no return of any trading rule was computed on them. Later 1-hour bars stay unread.
5. **Kenneth French library** data are cut at 2022-12-30 (E02).

### Amendment 2 - 12 Nov 2026 (after the validation run, before the lockbox)

Section 3 said that only confirmed candidates go to the lockbox. The validation run confirmed no
directional candidate. One, E1, had the predicted sign and a similar size in all three samples
without reaching significance on validation. Rather than leave the question open, E1 is placed on
the lockbox list as the single directional hypothesis, with its definition, horizon and sign
unchanged, and the criterion fixed now: day-weighted one-sided p <= 0.05 (Student's t as in the
validation run) AND event-weighted estimate with the predicted sign and one-sided p <= 0.10.
If it passes, it is reported as "confirmed on the lockbox after missing significance on
validation"; if it fails, it is removed. No other directional rule may be added to the list.
Risk claims R2, R3, R4 and R6 go to the lockbox with their validation criteria unchanged.

### Amendment 3 - 11 Nov 2026 UTC (before the earnings look at validation data; lockbox sealed)

1. **Erratum.** The validation run was executed on 11 Nov 2026 at 22:57 UTC (registry
   timestamps). Entry 5 of the research log, the pre-registration and amendment 2 give the date
   as 12 Nov 2026; that is wrong by a few hours.
2. **Short-sale volume.** The family was explored on `DEV_S` (G40, 34 cells). The published sign
   appears, but the effects are 5-10 bp over a week, well below a round trip. Nothing is carried
   to `VAL_S`, which stays unread.
3. **Earnings drift.** One further pre-registered family of two hypotheses is tested on VAL
   (`docs/04_preregistration_earnings.md`) under section 3's rule for replications of published
   effects. It is the last look at that sample.
4. **Lockbox list.** Amendment 2 said that no directional rule other than E1 may be added. That
   sentence was written to shut out the failed candidates and variants of E1 invented after the
   validation run, and it stays in force for those. It is narrowed in one respect: a hypothesis
   of the earnings family that is *confirmed* under its pre-registered criterion may join the
   list. Directional rules on the list are then tested with Holm's correction among themselves,
   which can only make E1's criterion stricter than amendment 2 stated, never looser.
