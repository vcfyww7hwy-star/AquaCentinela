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
