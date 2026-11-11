# Research log

Append-only. Newest entries at the bottom. Every hypothesis gets an ID, a status and a reason.
Machine-readable trial records are in `registry/trials.jsonl`; this file is the narrative.

Status words: **OPEN** (registered, not yet tested) · **DEV** (looked at on development data) ·
**VAL-PASS** / **VAL-FAIL** · **DESTROYED** (failed an attack) · **FROZEN** (on the lockbox list) ·
**LOCKBOX-PASS** / **LOCKBOX-FAIL** · **DROPPED** (with reason).

Running totals are restated at each milestone.

---

## 2026-11-10 — Session 2, entry 1: start, environment, data

**Inherited state** (`trend-flow-suite`, 9–10 Nov 2026): about 1.6 million stock-days of daily
large-cap US data, 1999–2018, survivors only. Findings carried forward as priors, not as facts:

- No entry rule (pullback, breakout, reversal) beat random entries in the same uptrends.
- No volume signal predicted direction.
- Dips inside long-term uptrends bounced for 1–5 bars (about +0.12 risk units over 5 bars);
  as a complete stop-based trade it was not confirmed. That test bought at the signal bar's close,
  which a trader working from a bar-close alert cannot do.
- A weekly trend filter cut drawdowns 29–40% at an unchanged Sharpe ratio.
- Its four Pine scripts had never been compiled.

**Done today**

1. Located the repository and branch (`AquaCentinela`, `claude/youthful-hopper-v9kozz`, draft PR 2).
   New work lives in `swing-lab/` on branch `claude/swing-lab`. `trend-flow-suite/` is untouched.
2. Probed the network. Yahoo, Hugging Face, DoltHub, Kenneth French, FRED and TradingView are
   reachable. Details in `01_data_inventory.md`.
3. **Found a free daily dataset that includes delisted companies** (DoltHub `stocks`, 2011 to
   9 Nov 2026) and measured that it is survivorship-free only from mid-2018. Found free earnings
   dates with before-open/after-close timing for 2020–2026.
4. **Compiler access.** TradingView's public lint endpoint compiles Pine v6 from here without a
   login and returns errors and warnings with positions (`tools/pine_compile.py`). Checked on a
   valid script, two broken ones, a v6-feature script and a strategy.
   Side result: the four `trend-flow-suite` scripts compile with 0 errors and 0 warnings.
5. Wrote the protocol (`00_protocol.md`) and froze the partitions **before computing any outcome**:
   DEV 2011-01 – 2018-06 (biased universe), VAL 2018-07 – 2022-12, LOCKBOX 2023-01 – 2026-11.
6. Asked the user, in one message: broker and costs, long/short, number of positions, universe,
   when orders can be placed, earnings policy, TradingView data feed, operating system; and for a
   free Alpaca API key (1-hour bars since 2016). Assumptions in force until answered are in
   protocol §5.
7. Launched a 16-topic parallel study (Pine capabilities from current documentation, literature by
   theme, data vendors), each with an independent verifier. Outputs: `docs/_raw/`,
   `01_pine_capabilities.md`, `02_research_map.md`.

**Trials so far: 0. Hypotheses registered: 0.** Nothing has been tested on market data yet.

**Open risks noted**

- The previous dip rule's entry at the close is not executable from a bar-close alert. Every test
  here enters at the next open unless stated.
- The model running this research has read about 2023–2026 markets (protocol §2.4).
- DoltHub prices are a community dataset. Bad ticks manufacture mean-reversion "edges". A
  cross-check against Yahoo is part of the build, and every reversal-type result is re-run on the
  cross-checked subset.

---

## 2026-11-11 - Session 2, entry 2: data built, first map, wave 1 launched

**Interruption.** The worker process restarted twice (once after an out-of-memory kill during the
first data build; once overnight). Files on disk survived; the literature workflows did not and
were relaunched. No results were lost.

**Data (details and counts in `01_data_inventory.md` section 5)**

- Research set = Yahoo for securities that still trade + cleaned DoltHub for those that stopped.
  6,927 ever-liquid securities x 3,997 dates; 1,710 stopped trading. On 4,551 survivors present in
  both sources, daily returns differ by more than 2% on 0.13% of days.
- Lessons kept in the code: splits are applied only when the price confirms them; the first split
  detector mistook 20-25% falls for 5:4 and 4:3 splits (4,537 false detections) and was restricted
  to ratios of 3:2 and above with a volume test; a single day of disagreement between sources (a
  spin-off) must not be read as a change of company.
- Context sample `CTX`: Yahoo survivors 1998-2010 (1,581 securities). Strongly biased; development
  use only; has the 2000-02 and 2008 bear markets.
- Earnings events 2017-2022 from two sources whose dates agree on the same day in 90% of matched
  cases; 93,572 events. Time of day known from 2020. Lockbox-period events are in a sealed file.
- Partitions are enforced in code: experiments read a copy that physically ends on 2022-12-30, and
  the `Study` object blanks every outcome outside the chosen development sample.

**E01 - what follows a k-day move (descriptive, DEV 2011-2018 and CTX 1998-2010)**

Signal: k-day return in units of the volatility known before the move. Outcome: total return from
the next open. 1,440 cells per run. The first run was invalid (the volatility estimate could stick
at zero and filled the ">3 sigma" bucket with garbage); recorded in the registry, fixed, rerun.

| Finding (cross-sectional view, stock-specific) | DEV 2011-2018 | CTX 1998-2010 |
|---|---|---|
| Down 3 sigma or more in one day: next 10 bars | -25 bp (t -2.1) | -55 bp (t -5.0) |
| Down 3 sigma or more in one day: next 20 bars | -39 bp (t -2.9) | -57 bp (t -3.3) |
| Down 1-2 sigma over 3 bars: next 5 bars | +5 bp (t 1.5) | +19 bp (t 5.2) |
| Up 1-2 sigma over 3 bars: next 5 bars | -10 bp (t -3.3) | -18 bp (t -4.5) |
| Up more than 3 sigma over 252 bars: next 20 bars | +83 bp (t 1.7) | +135 bp (t 1.6) |

| Finding (time-series view, includes market-wide moves) | DEV | CTX |
|---|---|---|
| Down 3 sigma or more over 21 bars: next 5 bars | +93 bp (t 2.0) | +78 bp (t 1.1) |

Reading, all on biased development data and therefore **untested**:

1. There is no stock-specific bounce to capture from the next open after a sharp fall. A crash day
   is followed by further underperformance. This is the opposite of the "buy the capitulation"
   habit, and it appears even though both samples contain only companies that survived.
2. The classic short-term reversal after moderate dips was 13-19 bp per week before 2010 and is
   about 0-5 bp after 2011: decayed below costs.
3. The bounce after market-wide selloffs is large on average and statistically weak: it comes from
   a handful of episodes. Date-matched random entries earn the same as a "2-sigma dip" entry
   (+34 bp versus +29 bp per trade, 10-bar hold): it is market exposure, not selection.
4. Long-horizon momentum has the right sign and is weak in liquid names.

**Wave 1 (running): 14 families**, each explored on DEV and CTX by one agent and then attacked by
an independent auditor who must reproduce the numbers, prove the absence of look-ahead and issue
PROMOTE / WEAK / DEAD verdicts: regime (f09), momentum and 52-week high (f03), one-day shocks
(f02), dips in trends (f01), volatility forecasting and stop calibration (f12), stops and exits
(f11), lottery/low-volatility (f04), earnings (f10), stock versus market (f14), breakouts (f06),
overnight versus intraday (f07), volume (f05), calendar (f08), imports from other fields (f13).

**Trials so far: 2,881** (E01: 1,440 invalid + 1,440 valid + 1 correction record), all on
development data. Validation looks: 0. Lockbox: sealed.

---

## 2026-11-11 - Session 2, entry 3: E02, ninety-six years without survivor bias

Source: Kenneth French data library, daily value-weighted portfolios built from CRSP (delisted
companies included), cut at 2022-12-30. Portfolio level only: this cannot test a chart rule, but
it says which published effects are still alive in the kind of stocks this project trades.
Script `research/experiments/e02_french_context.py`; 50 logged cells.

| Effect (percent per year; Newey-West t) | 1963-1989 | 1990-1999 | 2000-2009 | 2010-2022 |
|---|---|---|---|---|
| Short-term reversal, BIG stocks: last month's losers minus winners | +18.4 (8.8) | +15.9 (4.1) | +15.8 (2.1) | **+2.7 (0.6)** |
| Same, SMALL stocks | +43.0 (21.4) | +63.8 (19.5) | +16.8 (2.9) | +10.0 (2.6) |
| Momentum 12-2, BIG stocks: winners minus losers | +5.6 (2.3) | +7.7 (1.8) | +2.2 (0.3) | **+1.6 (0.3)** |
| Momentum, BIG winners minus the market (the long side) | +3.0 (2.5) | +3.9 (2.7) | +1.9 (0.7) | +1.1 (0.6) |
| Same, SMALL stocks: winners minus losers | +11.7 (6.0) | +18.6 (6.7) | +2.1 (0.3) | +5.8 (1.4) |
| Turn of the month: extra return per day on the last and first three days, bp | +12.2 (4.8) | +9.5 (2.2) | +5.5 (0.8) | +2.7 (0.5) |

| Market-level risk rules, 1926-2022 (next-day execution, 5 bp per switch) | CAGR | Sharpe | Max drawdown |
|---|---|---|---|
| Buy and hold | 9.4% | 0.61 | -84% |
| In the market only above its 200-day average (71% of the time) | 9.7% | 0.88 | -40% |
| Volatility-managed (15% target, weight capped at 1.5) | 10.7% | 0.75 | -68% |

By era the trend filter raised the Sharpe ratio in 1926-62, 1963-89 and 2000-09, matched it in
2010-22 (0.72 both, CAGR 8.3% against 12.1%, drawdown -21% against -34%) and lowered it in the 1990s.

**Reading.** The two best-known stock-level effects at these horizons, reversal and momentum, have
faded to statistical zero in large US stocks since 2010. So has the turn of the month. This agrees
with E01 on our own panel and is the base rate against which every "edge" in liquid names should be
judged: the prior that a simple published pattern still pays there is low. What has held for a
century is the market-level trend filter as a way to cut drawdowns, at a cost in bull decades.
Status: literature-level context, **untested** as a product claim.

**Trials so far:** 2,931 on development or context data, plus the wave-1 families in progress
(their own registry files). Validation looks: 0. Lockbox: sealed.

---

## 2026-11-11/12 - Session 2, entry 4: usage limit, change of method, the wide map on development data

**What went wrong.** Twelve research agents running in parallel exhausted the account's 5-hour
usage limit; all six workflows stopped. Kept: four Pine reports, five literature reports (none
independently verified), and partial scripts from four experiment families. From here the
exploration is done in the main loop with compact scripts (`g*.py`), and agents are reserved for
independent audits of finalists. The delegated `f03/f05/f06/f09` files are kept as an unaudited
cross-check; `f09`'s SPY benchmark matches mine to the basis point.

**A trap caught.** A "round number" signal built on the split-ADJUSTED price level showed a large,
significant effect in both samples. It is an artefact: the level of an adjusted price encodes
future splits (a future reverse split inflates past adjusted prices, so "high adjusted price"
selects future losers). Rule added to `candidates.py`: only ratios of adjusted prices, never
levels. The signal is void and is not carried forward.

### Results by family (development data only: DEV 2011-2018, CTX 1998-2010; all UNTESTED)

Numbers are cross-sectional (signal minus control on the same day), from the next open, in basis
points, with date-clustered t-statistics, as "DEV / CTX".

**Risk engine (G12)** - the strongest, most stable results of the project so far.

| Finding | DEV | CTX |
|---|---|---|
| Forecast of next-10-bar volatility, QLIKE (lower is better): ATR(14)/close, rescaled | 0.402 | 0.364 |
| Same: EWMA(20) of squared returns | 0.485 | 0.429 |
| Same: Yang-Zhang(20), Garman-Klass(20) | 0.465 | 0.417 |
| Daily sigma for the next 10 bars as a multiple of ATR(14)/close | 0.757 (fitted on CTX, applied to DEV) | |
| 5% / 95% quantile of the 10-bar return divided by forecast x sqrt(10) (normal: -1.64 / +1.64) | -1.56 / +1.48 | -1.51 / +1.46 |
| Random entry, stop 2 ATR below the next open: stopped within 10 bars | 31.8% | 31.6% |
| Same, stop 3 ATR | 16.0% | 15.3% |
| Same, stop 1 ATR within 5 bars | 45.2% | 46.5% |
| Share of stop exits that gapped through the stop | 11-17% | 9-17% |
| Nights with a gap worse than -1 ATR / -2 ATR | 1.29% / 0.32% | 1.04% / 0.20% |

ATR lengths 10 to 50 are a plateau. ATR wins because it uses the day's range, averages absolute
rather than squared moves (one earnings gap does not dominate), and remembers about 27 bars.
Volatility contraction ("squeeze", NR7, Bollinger width at a 126-bar low) predicts neither direction
nor, beyond 10-13%, size.

**Earnings (G10, DEV 2017-01..2018-06 only, 6,279 reaction bars; low power).** Risk table: on the
reaction bar the opening gap is worse than -1 ATR in 17.7% of cases against 0.68% on ordinary
nights, worse than -2 ATR in 9.7% against 0.12% (79 times), worse than -3 ATR in 5.3%. Reaction
bars are 1.4% of stock-days and 23% of all days with a move of 3 sigma or more. Drift after the
reaction is noisy in six quarters; no pre-announcement premium (-4.5 bp a day in the ten bars
before).

**Market regime (G09, SPY 1993-02..2018-06, next-open execution, 5 bp per switch).** Buy and hold:
9.5% a year, Sharpe 0.59, worst drawdown -55%. 200-day rule with a 2% band: 8.2%, 0.73, -20%.
Ten-month rule decided at month-end: 9.8%, 0.82, -19%, one switch a year. In 2010-2018 every rule
gave up 3-5 points a year of return. The reason the rules work at all: SPY's next-day volatility
is 13.8% a year above its 200-day average and 26.5% below it, while the mean daily return is the
same (+3.5 bp and +3.4 bp). The trend state forecasts risk, not return. For single stocks the
probability of a loss worse than 10% in 20 bars is 6.8% (DEV) and 9.7% (CTX) with SPY above its
200-day average, 11.2% and 18.1% below.

**Exits (G11).** For random entries and for trend entries, in both samples, every tight stop,
trailing stop and moving-average exit LOWERED the net return per bar held:

| Exit (random entries) | DEV bp per bar | CTX bp per bar |
|---|---|---|
| Hold 20 bars, no stop | +4.28 | +3.97 |
| Stop 3 ATR, 20 bars | +3.37 | +2.92 |
| Stop 2 ATR, 20 bars | +2.66 | +2.57 |
| Stop 1.5 ATR, 20 bars | +2.09 | +1.94 |
| Stop 2 ATR, trail 3 ATR | +1.89 | +1.47 |
| Exit on a close under the 20-day average | +0.49 | +0.96 |

A stop is insurance against the tail (with a 3-ATR stop about 0.5-1% of trades lose more than
1.5R), not a source of return. Profit targets change little.

**Events (G02).** Large one-day falls on heavy volume keep falling; large gaps up on heavy volume
that close strong keep rising; everything else about big days is noise or fades.

**Dead on 2011-2018 data** (most were alive in 1998-2010, which is itself the finding):

| Idea | DEV | CTX |
|---|---|---|
| Buy RSI(2)<10 in an uptrend, 5 bars | -3 (t -0.7) | +29 (t 6.1) |
| Three down closes in an uptrend, 5 bars | -6 (t -1.1) | +34 (t 8.1) |
| Any dip definition, uptrend, versus other uptrend names | none above +10 | +23 to +52 |
| New 55-bar closing high versus names near the same high, 20 bars | -9 (t -0.7) | +25 (t 1.7) |
| Volume: high-volume premium, 20 bars | -3 (t -0.6) | +25 (t 4.0) |
| Pocket pivot, accumulation/distribution counts, OBV divergence | zero or negative | negative |
| Momentum 12-1 above +50%, 60 bars | +1 (t 0.0) | +89 (t 0.7) |
| Within 5% of the 252-bar high, 60 bars | +39 (t 1.1) | -78 (t -1.0) |
| Trend age, CUSUM alarm, variance-ratio and autocorrelation gates, efficiency ratio | nothing consistent | |
| Calendar: turn of the month (E02, CRSP market) | +2.7 bp a day (t 0.5) since 2010 | |

### Candidates frozen for validation (`research/swinglab/candidates.py`)

Attacked on development data (`g30_attack.py`): cross-section halves, liquidity split, years with
the predicted sign, one-bar delay, best month removed, 6-sigma bars removed, share in the overnight
gap. All kept their sign except A9 across samples. A truncation test
(`research/tests/test_no_lookahead.py`) shows no candidate depends on future rows.

| ID | Definition (at the close of t) | Use | h | DEV bp (t) | CTX bp (t) | Years right |
|---|---|---|---|---|---|---|
| E1 | Gap up >= 3 sigma, volume >= 3x its 20-bar median, close in the top third of the bar | enter | 10 | +57 (2.1) | +89 (2.9) | too few per year |
| E2 | First close above the 252-bar high in 10 bars on volume >= 1.5x; control: names within 3% of that high | enter | 5 | +21 (2.4) | +21 (2.3) | 15/20 |
| E3 | Skewness of the last 60 daily returns <= -1 | select | 60 | +42 (1.9) | +100 (2.5) | 14/21 |
| A1 | Daily fall >= 3 sigma on volume >= 3x | avoid, exit | 20 | -49 (-2.6) | -78 (-3.4) | 18/21 |
| A2 | Below the 200-day average and up >= 1.5 sigma over 5 bars; control: below the 200-day | avoid | 10 | -29 (-2.3) | -22 (-1.9) | 16/21 |
| A3 | Unfilled gap up (low above the prior high), not an E1 event | avoid | 5 | -15 (-3.3) | -21 (-4.2) | 19/21 |
| A4 | Gap down >= 1 sigma and close below the open | avoid, exit | 20 | -40 (-3.8) | -36 (-2.6) | 18/21 |
| A5 | 20-bar overnight return >= +5% and intraday return <= -5% | avoid | 5 | -23 (-2.3) | -14 (-2.0) | 16/21 |
| A6 | First close above the 55-bar high two bars ago, now back below it | exit | 20 | -27 (-1.4) | -32 (-2.0) | 16/21 |
| A7 | 12-1 momentum negative, more than 30% below the 252-bar high, below the 200-day | avoid | 60 | -126 (-1.3) | -92 (-1.2) | 13/20 |
| A8 | Up 1 to 2 sigma over 3 bars | do not chase | 5 | -10 (-3.4) | -18 (-4.5) | 19/21 |
| A9 | 4 or more ATR below the 50-day average | avoid | 20 | -54 (-2.1) | +138 (3.0) | 9/21 |
| A10 | Skewness of the last 60 daily returns >= +1 | avoid | 60 | -26 (-0.6) | -124 (-3.4) | 14/21 |
| A11 | Below the 200-day average and a daily rise >= 3 sigma; control: below the 200-day | avoid | 5 | -35 (-2.7) | -18 (-1.5) | 14/20 |

A9 is kept on purpose: the two samples disagree, CTX contains only survivors (crushed stocks that
survived bounced), and validation data include the ones that did not survive. It is the cleanest
test here of how much survivor bias distorts "oversold" rules.

**Reading.** In liquid US stocks after 2010 the published entry edges are gone. What the development
data still show is (1) one event with upward drift, (2) a family of states after which a stock
underperforms and which a trader can avoid or exit, (3) a risk engine with stable, checkable
numbers, and (4) market regime as a forecast of risk. That is a different product from a signal
indicator: it tells the trader what not to buy, how much to risk, and when the odds have shifted.
Nothing above is evidence yet.

**Trials so far** (all on development or context data): see `registry/`; validation looks: 0;
lockbox: sealed.
