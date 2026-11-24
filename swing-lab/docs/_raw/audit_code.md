# Code audit before the validation look (auditor tag `auditc`)

12 Nov 2026. Development data only (DEV 2011-01-03..2018-06-29). No validation or lockbox price was
read: my script cuts every array at the last DEV row before computing anything, and the one
statement below about the validation period comes from `dates.npy` alone.

Script: `research/experiments/audit_code.py` (`python -m research.experiments.audit_code`, 30 s;
`--sim` runs the simulator checks). Tables: `research/results/audit_code.json`. Registry:
`registry/trials_auditc.jsonl` (26 distinct DEV cells; the script was run four times while being
written, so each cell appears up to four times; a bookkeeping line says so).

## Verdict

1. **The measurement engine is correct.** An independent re-implementation reproduces the four
   candidates to 0.1 bp, with identical event counts and t-statistics. Forward-return indexing,
   sample-end blanking, the volatility timing, the universe and the trade simulator do what the
   documents say.
2. **One blocker: the calendar.** The panel has rows for days on which the market was closed
   (8 in DEV, and 2020-02-17 in the validation period). On those rows every Yahoo-sourced security
   is a hole, and the volume features of the frozen candidates turn to NaN for the next 20 rows
   (E1, A1) or 50 rows (E2). By the same mechanism the validation run would blind E1 and A1 from
   18 Feb to 16 Mar 2020, and E2 until late April 2020, for every Yahoo-sourced security (the
   companies still listed in 2026), while delisted companies (DoltHub-sourced, which carry a stale
   bar on the holiday) stay eligible. I infer this from the date list and the DEV behaviour; I did
   not read validation prices to confirm it.
3. **E1 does not survive the repair intact**: +56.7 bp (t 2.07) becomes +47.1 bp (t 1.84) on the
   corrected calendar. A1, A4 and A8 move by less than 3 bp.
4. Seven minor defects and eleven notes follow. None changes a sign.

## 1. Independent re-implementation

Written from the research log (entry 4), `candidates.SPEC` and the docstring of `engine.vol_ewma`,
with pandas rolling functions; nothing imported from `study`, `candidates`, `pinelike` or `engine`.
The forward return is built a different way from the project's (rolling sums of log gross returns on
an array that physically ends on 2018-06-29, instead of a ratio of a total-return index).

Cross-sectional effect, DEV: each day, mean outcome of signal names minus mean outcome of all
universe names; then the mean over days.

| Candidate | h | Logged bp | Mine bp | t (mine / logged) | Events (mine / logged) | Difference |
|---|---|---|---|---|---|---|
| E1 episodic pivot | 10 | +56.7 | +56.7 | 2.07 / 2.07 | 943 / 943 | 0.0 |
| A1 shock down on volume | 20 | -49.3 | -49.4 | -2.56 / -2.56 | 6,228 / 6,228 | -0.1 (rounding) |
| A4 gap down, weak close | 20 | -40.1 | -40.1 | -3.75 / -3.75 | 25,266 / 25,266 | 0.0 |
| A8 pop fade | 5 | -9.7 | -9.7 | -3.35 / -3.35 | 218,162 / 218,162 | 0.0 |

No difference above 3 bp when I use the project's calendar. Differences above 3 bp appear only
when I repair the calendar (rows on which the market was closed removed; volume median taken over
each security's own bars):

| Candidate | As coded | Median repaired only | Closed rows removed + median repaired | Events | Change |
|---|---|---|---|---|---|
| E1 | +56.7 (t 2.07) | +54.5 (t 2.14) | **+47.1 (t 1.84)** | 943 -> 1,013 | **-9.6** |
| A1 | -49.4 (t -2.56) | -49.5 (t -2.71) | -48.5 (t -2.65) | 6,228 -> 6,688 | +0.8 |
| A4 | -40.1 (t -3.75) | -40.1 | -37.3 (t -3.56) | 25,266 -> 25,289 | +2.8 |
| A8 | -9.7 (t -3.35) | -9.7 | -10.4 (t -3.60) | 218,162 -> 219,558 | -0.7 |

Explanation of E1's -9.6 bp. Two parts: -2.2 bp from the 65 events the volume blackout had
suppressed; -7.4 bp from removing the eight closed-market rows (windows that spanned one held 9
real bars instead of 10; 7 events on the day before a closed row had no outcome; the stale DoltHub
bars disappear). E1's daily spread has a standard deviation of about 680 bp over about 650 signal
days, so adding or altering about 50 signal-days moves the mean by this much through noise alone.
I read it as fragility, not as a directional bias: the estimate was sitting at t = 2.07 and a
neutral repair takes it to 1.84.

Two more facts about size that the logged table does not show:

- **Day-weighted versus event-weighted.** The logged figure gives every day equal weight, including
  days with a single event. The event-weighted excess over the same-day universe is about half:
  A1 -26.6 bp, A4 -21.4 bp, A8 -3.7 bp, E1 +57.8 bp. A trader who acts on every signal experiences
  the second number.
- **One event** (SRPT, signal 2016-09-14, +100% in ten bars on the FDA approval of 19 Sep) carries
  7.6 bp of E1's 56.7 bp. It is a real event, not a data error.

## 2. Look-ahead hunt

| Check | Result |
|---|---|
| (a) `engine.fwd_ret_open` indexing (engine.py:103-108) | Correct. Row t: `c[t+1]/o[t+1]` times `tri[t+h]/tri[t+1]`. A dividend with ex-date t+1 is excluded, as it should be. Confirmed by the replication and by a synthetic case. |
| (b) `Study.fwd` blanking (study.py:114-115) | Correct. Rows after `last_row - h` are NaN. My physically truncated array gives the same count of finite outcomes. |
| (c) `adv60` (05_panel.py:62) | Trailing, **includes** the current bar, at least 40 bars in the last 60 calendar rows. My pandas median matches the file on 5.0M cells (largest relative difference 6e-8); a version excluding the current bar differs on 54% of cells. Known at the close of t. The docstring's "previous 60 bars" is loose wording. |
| (d) volatility timing (engine.py:180-204, study.py:101-108, candidates.py:36-40) | Correct. `vol[t]` uses returns up to t; the cap uses the estimate before the update; `z(k)` divides by `vol[t-k]`; the gap divides by `vol[t-1]`. |
| (e) `pinelike.shift` and NaN cast to bool (pinelike.py:27-33; candidates.py:81-82, 100; g30_attack.py:80) | Direction correct. NaN becomes True only in the first k rows of the panel (bool arrays have no other NaN). No effect: the first universe row in DEV is row 39 (2011-03-01), rows outside a sample are False in `S.uni`, and in A6 the third factor is a NaN comparison (False). A latent trap, not a live one. |
| (f) `trades._sim` | Order of checks, entry bar, gap-through fill, intrabar stop, stop before target, time exit on the close of bar `max_hold`, dividends (entry-bar dividend excluded), delisting haircut: all as documented (7 synthetic scenarios, all match). Defects M5 below. |
| (g) levels of adjusted prices in `Feat` | None. Every feature is a ratio or a homogeneous comparison. The dollar-price filter uses the price as traded. Dollar volume is split-invariant: at 779 split dates the slope of the change in dollar volume on the change in adjustment factor is +0.2 (it would be -1 if volume were unadjusted). Adjusted prices are not rounded to cents (11% of strongly adjusted closes sit on a cent grid, against 99% of unadjusted ones). |
| (h) `relv` (candidates.py:41) | Median of the 20 rows before t, shifted by one: confirmed. But it needs all 20 rows to hold a bar: blocker B1. No zero medians, no infinite values in the universe. |
| (i) holes | 29,742 holes in DEV, of which 19,636 sit on the eight closed-market rows; only 166 others fall in names with dollar volume above $20M. See B1. |

## 3. Defects

### BLOCKER

**B1. Closed-market rows in the calendar, and volume windows that one hole disables.**

- `research/data_build/05_panel.py:48` builds the calendar as the union of all dates in both
  sources. DoltHub carries a bar on some market holidays: 2011-04-22, 2012-10-30, 2013-01-21,
  2013-02-18, 2013-03-29, 2013-07-04, 2014-09-01, 2014-11-27 in DEV (600-800 DoltHub bars each,
  94% of them a copy of the previous close; no Yahoo bar). Among NYSE holidays from 2018-07 to
  2022-12, `dates.npy` contains **2020-02-17**.
- `research/swinglab/candidates.py:32, 41, 101` with `pinelike.py:36-53` (`min_count = n`): one row
  without a bar makes `median(v, 20)[1]` NaN for the next 20 rows and `sma(v, 50)[1]` NaN for the
  next 50. E1, A1 and E2 cannot fire there.
- `research/swinglab/engine.py:106`: no bar at t+1 gives a NaN outcome, so every signal of a
  Yahoo-sourced name on the day before a closed row is dropped (signal cells on those eight days,
  both sources together: 7 E1, 17 A1, 49 A4, 1,084 A8).
- `research/swinglab/candidates.py:29-31, 66`: on a hole, high and low are set to the last close, so
  on the row after a closed row A3's "low above the prior high" becomes "low above the prior close":
  128 signal cells per row there against 36 normally.
- On the closed rows themselves the universe is 102-136 DoltHub names with stale bars; those rows
  produce a signal-minus-control observation like any other day.

Size in DEV: `relv` is NaN on 6.5% of universe stock-days (167 rows, 8.8% of the sample); inside
those rows E1 had 16 events and A1 76, **none from a Yahoo-sourced name**; E2's volume condition is
undefined on 15.0% of universe stock-days (355 rows fall inside a 50-row blackout). Effect on the
logged numbers: E1 -9.6 bp, A4 +2.8 bp, A1 +0.8 bp, A8 -0.7 bp; E2 and A3 not re-measured, expect
changes of the same order for E2.

Why it blocks: the validation run would test E1, A1 and E2 on a sample from which the weeks after
17 Feb 2020 are removed for survivors only. That is not the registered definition, it is the most
eventful month of the validation period for A1, and the exclusion is correlated with survival.

Fix: (1) in `05_panel.py` keep a date only if the market was open (for example: SPY has a bar, or at
least half of the Yahoo-sourced names have one) and drop DoltHub rows on other dates; (2) compute
volume medians and means over each security's own bars (`median_prev_bars` in my script does it in
five lines), which is also what TradingView does; (3) re-run the development table for all fourteen
candidates and freeze again before the look. The rule in (1) is mechanical and needs no validation
outcome.

### MINOR

**M1. The `bad` flag looks one bar ahead.** `data_build/04_merge.py:249`, `02_entities.py:269`,
`06_ctx_panel.py:73`: a bar is bad if the close jumps more than 50% (log) and the NEXT close is back
within 12%. It is consumed in the universe at t (`data.py:81`, `study.py:275`) and in every input
series (`engine.py:64-68`). Effect in DEV: 84 bars, 3 of them inside the universe filters, all MSGN
in Sept 2015 (spin-off artefacts); zero effect on the four candidates. Sign in general: it removes
crash-and-full-recovery and spike-and-full-reversal days, which favours continuation candidates
(E1, A1). Fix: do not let `uni[t]` depend on `bad[t]`; apply the flag from t+1 on, or report the
candidate with and without the flagged bars. One line; do it before the look because the count in
validation cannot be known without looking.

**M2. E3 / A10 do not compute the skewness that the log and the Pine recipe describe.**
`candidates.py:105-116`: the third moment is a 60-bar mean of cubed deviations from the 60-bar mean
*as it stood at each past bar* (119 bars of memory), divided by the current 60-bar standard
deviation; missing returns and the bars before listing are filled with zero. Against the textbook
60-bar skewness: E3 277,883 cells as coded, 237,780 textbook, 216,769 in common; A10 210,682 /
170,850 / 156,865. About 0.8% of coded signals come from names with fewer than 120 real bars, where
Pine would return `na`. No look-ahead. Fix: either change the text and recipe to describe the code,
or switch to the textbook statistic and re-run development before the look.

**M3. E1's Pine recipe does not match its code.** `candidates.py:125` writes the gap as a simple
return, `candidates.py:38-40` uses a log return. The simple version gives 992 cells against 960
(32 extra). Fix the text.

**M4. Two helpers read past the sample.** `study.py:150-153`: `gap()` on the last DEV row uses the
open of 2018-07-02. `g30_attack.py:56, 91` ("overnight_gap_bp") includes that row;
`f06_breakouts.py:535` also calls `gap()`. One row of 1,894: no visible effect, but it is a
validation price.
`study.py:119-121`: `mkt()` returns SPY's forward return with no blanking at all; nothing calls it.
Fix: blank the last sample row in `gap()`; route `mkt()` through `self.fwd`.

**M5. Simulator, end of sample.** `trades.py:145` keeps a trade only if its exit lies inside the
sample. For entries in the last `max_hold` bars that keeps the stop-outs and drops the survivors
(shown in `--sim`). Effect, estimated and not measured: mean trade return biased down by roughly
0.5 to 1 bp (0.5% of entries are affected).
The simulator also walks through bars after the sample before the trade is dropped; nothing from
them is reported. `trades.py:42`: a signal with no bar on the next row is discarded, not deferred.
Fix: drop every trade whose entry is later than `row_hi - max_hold`, and bound the walk at `row_hi`.

**M6. Splice artefacts between the two sources.**
- Stale bars in DoltHub names: 5,452 on the closed rows, 640 universe stock-days elsewhere (0.23%
  of DoltHub universe cells; 3 in Yahoo names).
- The same company twice in the universe: COG = CTRA on 1,204 days, CLNY = DBRG on 685 days
  (renames not de-duplicated; 0.11% of universe stock-days).
- One apparent unadjusted 2:1 split among the extreme A1 events: NXGN (then QSII) 2011-10-27,
  86.70 -> 41.82, share volume two to four times higher from then on. This matches my memory of a
  2-for-1 split that month; I did not check an outside source. Effect on A1: one spurious event of
  6,322.

**M7. The truncation test proves less than the log says.** `tests/test_no_lookahead.py` with
`study.py:84-98` slices `uni`, `adv60` and the prepared arrays from the full-sample objects. It
shows that the indicator arithmetic is causal. It cannot see M1 or anything else in the data build.
Fix the sentence in the log, or rebuild the inputs from truncated raw data in the test.

### NOTES

- **N1.** Day-weighted against event-weighted size (section 1). State which one is the registered
  criterion and print both.
- **N2.** "First close above the high in 10 bars" (`candidates.py:81, 100`) is true on the first bar
  where the high exists (bar 56 or 253 of a security) whatever happened before. In DEV this clusters
  in early January 2012 for E2, because the panel starts on the sample's first day.
- **N3.** DEV has no warm-up. Universe from 2011-03-01; 200- and 252-bar features from late 2011 /
  2012. The 2011 "year" is thin for E2, A2, A7, A11.
- **N4.** `05_panel.py:64-68`: inclusion needs 20 liquid days over the whole history, lockbox years
  included, and the `suspect` flag is also full-history. A security liquid for fewer than 20 days
  before disappearing is excluded with hindsight. Very few names.
- **N5.** `02_entities.py:199-222`: the split detector uses volume after the candidate date. Data
  cleaning with hindsight; harmless unless it misfires (see NXGN, where it did not fire).
- **N6.** `g30_attack.py:78-79`: the liquidity split restricts the signal but not the control. And
  the day-weighted effect is not additive across subsets: A1 is -62 and -52 in the two halves and
  -49 overall.
- **N7.** A1 by data source, corrected calendar, control inside the same source: Yahoo names
  -35.7 bp (t -2.08, 5,506 events), DoltHub names -42.4 bp (t -1.12, 1,182 events). The sign holds
  in both; the headline is not produced by the splice. DoltHub names (gone by 2026) earn 44 bp per
  20 bars against 99 bp for Yahoo names, the known survivor tilt of DEV.
- **N8.** `trades.py:125`: a signal on the exit bar is ignored. Conservative.
- **N9.** `adv60` and every `ta.*` window count calendar rows, not bars. After B1 the difference is
  negligible (166 holes in liquid names).
- **N10.** The context panel's calendar is clean (no row with under half the usual bars), so CTX
  numbers are not touched by B1's closed rows; the hole-intolerant median still applies there.
- **N11.** `study.py:271-276` and `data.py:76-82` duplicate the universe rule. They agree today.

## 4. Data sanity for E1 and A1

One-day moves beyond 40% on the signal bar: **E1 12 of 960; A1 25 of 6,322.** I recognise all 12 E1
events as real (ILMN 2012-01-25 Roche bid, VRTX 2012-05-07, PBYI 2014-07-23 +295%, SNAP 2018-02-07,
MDGL 2018-05-31 and so on). Of the 25 A1 events, 24 are real crashes (RMBS 2011-11-16, SRPT
2013-11-12, CLVS 2015-11-16, BHC 2016-03-15, ISEE 2016-12-12 ...) and one is the unadjusted split of
M6. A scan of A1 events whose opening gap equals a split ratio found eleven, all real falls of about
a third (CROX 2011-10-18, FOSL 2016-05-11, GEN 2018-05-11 ...) except SBSW 2017-05-19, which is
probably a rights issue going ex. These judgements rest on my memory of the events, not on a second
data source. Outcomes: E1 1%/99% quantiles -14% / +18%, one beyond 50%; A1 -26% / +28%,
16 beyond 50%.

Fifteen random E1 events (seed 20261111; prices split-adjusted; `fwd10` from the next open, percent).
All fifteen look like earnings or deal gaps (for example NFLX and FDX earnings, the Roche bid for
ILMN, the Unisplendour stake in WDC); prices, ranges and volumes are coherent and none looks like a
data error.

| Symbol | Date | Prev close | Open | High | Low | Close | Volume | Rel. vol | fwd10 % |
|---|---|---|---|---|---|---|---|---|---|
| STX | 2012-02-01 | 21.14 | 23.59 | 26.15 | 23.56 | 25.53 | 75,403,800 | 7.2 | +3.9 |
| BIG | 2012-02-02 | 39.55 | 42.81 | 43.10 | 41.27 | 42.82 | 3,471,793 | 3.0 | +1.8 |
| ILMN | 2012-03-29 | 48.52 | 50.63 | 51.22 | 50.24 | 50.97 | 15,157,860 | 10.6 | -10.4 |
| CCK | 2013-10-31 | 40.62 | 42.83 | 44.08 | 41.95 | 43.60 | 7,951,800 | 6.1 | -0.2 |
| HAS | 2015-02-09 | 55.74 | 58.40 | 60.66 | 57.20 | 59.66 | 4,926,600 | 3.7 | +1.9 |
| WDC | 2015-09-30 | 52.43 | 59.55 | 61.03 | 57.70 | 60.05 | 15,468,516 | 5.1 | +4.2 |
| ARMK | 2015-11-18 | 21.39 | 22.20 | 23.57 | 21.99 | 23.57 | 9,706,496 | 4.8 | +2.6 |
| ENDP | 2016-08-09 | 18.19 | 20.27 | 23.34 | 19.63 | 22.16 | 37,981,432 | 9.2 | +8.9 |
| MKTX | 2017-01-25 | 158.36 | 170.66 | 178.00 | 166.00 | 175.99 | 616,000 | 3.1 | +6.1 |
| NFLX | 2017-07-18 | 16.17 | 17.61 | 18.50 | 17.42 | 18.36 | 415,873,984 | 7.5 | -0.5 |
| JWN | 2017-09-13 | 45.05 | 47.90 | 48.11 | 46.94 | 47.74 | 9,565,321 | 6.6 | -0.5 |
| GRMN | 2017-11-01 | 56.61 | 57.62 | 60.44 | 57.61 | 59.80 | 3,488,700 | 4.3 | +1.0 |
| FDX | 2017-12-20 | 195.44 | 203.55 | 204.06 | 198.71 | 202.31 | 7,319,542 | 3.8 | +4.8 |
| LUMN | 2018-05-10 | 18.04 | 18.95 | 19.75 | 17.98 | 19.40 | 27,892,000 | 3.2 | -4.6 |
| LOW | 2018-05-23 | 85.75 | 90.70 | 95.14 | 90.52 | 94.69 | 26,304,800 | 5.5 | +5.8 |

Fifteen random A1 events (`fwd20` percent). All look like real events (earnings, guidance, offerings,
the August 2011 sell-off); none looks like a data error.

| Symbol | Date | Prev close | Open | High | Low | Close | Volume | Rel. vol | fwd20 % |
|---|---|---|---|---|---|---|---|---|---|
| OBE | 2011-08-08 | 136.92 | 126.77 | 129.29 | 123.69 | 124.60 | 1,026,900 | 4.5 | -0.9 |
| SPWR | 2013-08-01 | 27.65 | 27.61 | 27.70 | 23.51 | 23.90 | 13,343,989 | 3.3 | -11.2 |
| SPLK | 2014-05-30 | 50.04 | 46.92 | 47.00 | 41.05 | 41.86 | 19,324,936 | 4.9 | +30.2 |
| VTR | 2014-06-02 | 76.28 | 73.56 | 75.27 | 73.18 | 74.15 | 6,223,162 | 4.7 | -0.1 |
| HPR | 2015-01-28 | 541.00 | 531.00 | 533.60 | 433.50 | 449.00 | 110,582 | 3.2 | +12.3 |
| SHW | 2015-07-16 | 94.05 | 85.36 | 88.90 | 83.42 | 87.08 | 21,494,100 | 12.4 | +5.9 |
| RGLD | 2015-07-20 | 56.85 | 53.88 | 54.37 | 50.94 | 51.22 | 1,634,300 | 3.2 | +7.0 |
| PII | 2015-07-22 | 153.38 | 144.84 | 148.31 | 143.50 | 147.71 | 3,131,000 | 5.1 | -8.6 |
| SNY | 2016-04-29 | 42.85 | 41.74 | 41.76 | 40.72 | 41.10 | 4,760,800 | 3.5 | +3.4 |
| ACIA | 2017-04-26 | 54.13 | 54.02 | 54.37 | 47.96 | 48.08 | 3,515,305 | 3.6 | -0.3 |
| BKD | 2017-08-01 | 14.20 | 14.20 | 14.25 | 12.94 | 12.97 | 6,129,200 | 3.2 | -12.2 |
| MUSA | 2017-08-03 | 76.19 | 78.00 | 79.98 | 73.01 | 73.44 | 1,394,600 | 4.2 | -11.5 |
| BC | 2017-08-17 | 55.61 | 55.66 | 55.86 | 51.35 | 51.49 | 3,562,600 | 3.4 | +6.6 |
| SBRA | 2017-09-26 | 22.33 | 20.90 | 21.21 | 20.85 | 20.92 | 17,563,300 | 11.2 | -0.1 |
| MD | 2018-04-26 | 52.69 | 47.91 | 51.22 | 46.38 | 46.52 | 2,720,900 | 3.9 | -0.0 |

HPR and OBE show adjusted prices far above the price as traded ($8.98 and $17.80) because of later
reverse splits; the ratios are unaffected.

## 5. Not checked

- The other ten candidates' numbers, and all CTX numbers, were not re-derived.
- The validation period: only its dates were read. Holes inside it (other than the 2020-02-17 row)
  are unknown; the fix in B1 handles them without looking.
- Pine parity, the earnings data, and the download scripts (`00`, `03`, `07`-`09`).
- Another process (`research.data_build.09_yahoo_sectors`, a background download I did not start)
  was running during my runs; mine were single processes of 30 s or less.
