# Relative Volume: two external reviews, what was tested, v3 and v4

- **Date:** 24 Nov 2026.
- **Subject:** an external AI reviewer criticised `pine/relative_volume.pine` (v2) and the evidence
  behind it, without tools: no code execution, no data, no documentation access.
- **Second review, same day:** the reviewer audited v3 and the author's replies, this time with
  documentation access and code execution but without the project's data. Section 8.
- **This document:** each claim checked against data or sources, the experiments run, and the
  resulting design. Sections 3 to 6 record the first review and v3; section 8 the second review and
  v4, which is the current script. Specification of v4: `03_relative_volume.md`.

## 1. What is true now

1. **No volume reading tested predicts direction at swing horizons in 2018–2026.** That covers the
   former "absorption at lows" mark, a general high-volume premium, and continuation or reversal
   after strong moves on unusual volume.
2. **The "absorption" mark had a real, narrow effect until about 2017 and has none since.** With the
   bar's price action held fixed, heavy volume beat ordinary volume by about 0.1 risk units over 10
   bars against same-day peers in 2000–2017. On 2018–2026 the same test gives −0.009 [−0.050, +0.031].
   The new data source reproduces the old effect on 2006–2017 (+0.087 [+0.039, +0.138]), so the null
   result is about the period, not the source (E20). It is not a stress effect waiting to return
   either: in 2018–2026 the mark does nothing in stressed markets (−0.022 [−0.073, +0.034]; with the
   v3 definition +0.030 [−0.023, +0.084]; E21). v4 removes the mark.
3. **The reviewer's three statistical criticisms of the reference were right.** The arithmetic
   reference sat 10–15% too high, one extreme day distorted it for weeks, and the unclipped
   volatility was inflated for weeks after a shock. v3 fixes all three.
4. **Volume does not earn a place in position sizing.** After a bar at twice normal volume the next
   10 bars are 6–9% more volatile than the *previous* bar's ATR implied, and a stop two previous-ATRs
   away is hit 3–5 points more often. ATR recomputed at that bar's close already absorbs this. The
   rule is: use the ATR of the signal bar, add no extra widening. It also holds on bars with unusual
   volume and a narrow range, where the ATR does not rise: what follows is 5–6% calmer, not wilder,
   than after ordinary narrow bars (E22).
5. **Mechanical volume is large and concentrated.** In 2018–2026, 37–38% of stocks had unusual
   volume (zV ≥ 2) on quarterly expiry days and on the Russell reconstitution day, against 3.5% on
   other days: 17.7% of all flags on 2% of the days (E21).
6. **The time-of-day normalisation works on real intraday data** (13 months, cleaned): relative
   volume is centred in every slot (median 0.95–0.97), unusual volume is flagged at the design rate
   on 60-minute and 4-hour bars (3.8%), and an unprojected bar in progress understates relative
   volume by 25–91% depending on the hour (E19 re-run, E26).
7. **The public intraday source carries corrupted volume**, in episodes by listing group. It was
   found during E26. The first intraday run (49 sessions, September to November 2026) included
   three weeks of it: its figure of 8–12% of 60-minute bars flagged was an artefact.

## 2. Data

All sets hold only companies still listed at the end of their data (survivorship). Daily bars unless
stated.

| Set | Stocks | Evaluated period | Rows | Note |
|---|---|---|---|---|
| A | 231 S&P 500 | Sep 2014 – Feb 2018 | 192,823 | Development set |
| B | 258 other S&P 500 | Sep 2014 – Feb 2018 | 214,503 | Same dates as A |
| DJ | 31 Dow | Aug 2007 – Feb 2013 | 42,367 | Lies inside LH |
| LH | 459 S&P 500 names | Aug 2000 – Feb 2013 | 1,119,067 | |
| MS | 1,200 non-S&P, mostly mid and small caps | Aug 2006 – Nov 2017 | 2,776,862 | New (E10) |
| EM | 1,123 NASDAQ and NYSE stocks | Feb 2018 – Oct 2026 | 2,102,638 | New (E10b); no date shared with any other set |
| Intraday | 858 liquid stocks, 5-minute bars | 31 Aug – 6 Nov 2026 (49 sessions) | 4.6 million bars | New (E19); public 1-minute Yahoo bars |

Independent evidence is thinner than the number of sets suggests: A and B share dates, DJ lies
inside LH, and LH and MS overlap in 2006–2013. EM is the only set after early 2018.
Metric for returns: `fzd10`, the 10-bar forward return minus the same-day average of the set, in
units of the stock's own volatility. Intervals are 95%, month-block bootstrap, 2,000 resamples.

## 3. The review, claim by claim

### Code

| Claim | Verdict | Evidence |
|---|---|---|
| Counting bars since the session's first bar breaks the slot when a bar is missing | Right as a mechanism; severity overstated | Routine with extended hours, rare on regular-hours 1h and 4h charts of liquid stocks (0 missing 60-minute bars in 858 stocks over 49 sessions). v3 keys the slot by clock time |
| The first loaded bar seeds the wrong slot | Right, harmless | The seed's weight is 13.5% after 20 sessions; nothing reaches the right edge of a 20,000-bar chart |
| "Premium loads about 10,000 bars" | Wrong | 20,000 (TradingView support article and Pine manual) |
| A clock-time key fixes half days | Wrong | The 12:30 bar of a half day has the same clock key as a normal 12:30 bar. v3 adds the bar's length to the key |
| A zero first value seeds the average at zero and inflates later ratios up to 1/α | Right | 25.5× on daily, 10.5× intraday, start of history only. v3 uses bias-corrected averages and a warm-up |
| Fix: skip every update with x ≤ 0 | Right for volume, wrong for squared returns | Dropping zero returns inflates σ (about 2–5% for stocks priced 10–20 dollars on 1h bars). v3 skips zeros for volume only |
| A gap up that is sold all day is marked as bullish absorption; require a close in the upper half | Pattern exists, fix useless | About 6% of marks. Marks closing in the upper half did no better than the rest (MS +0.015 [−0.034, +0.062]); the filter would drop 42–47% of marks |
| Table shows "NaN×"; no time stamp intraday; duplicate plot | Right | Fixed |
| The event cannot be filtered in the Pine Screener | Wrong | An `alertcondition` is a valid screener filter and the script had one |
| Without paid exchange data, live volume is Cboe-only and understated tenfold ("demonstrated") | Not demonstrated | The default US feed is Cboe One (four Cboe exchanges, about 9–10% of consolidated volume, not BZX alone at 3.7%). What the live daily bar and the intraday history show is undocumented. v3 adds a self-check; the owner must run the manual checks |
| The bar in progress is misleading | Right | E19: −92% at 10:00, −73% at 11:30, −56% at 13:00, −21% at 15:30 for the daily bar |
| `request.security_lower_tf` is a Premium feature | Wrong | Available on every plan (Premium: 100,000 intrabars) |

### Statistics and evidence

| Claim | Verdict | Evidence |
|---|---|---|
| The arithmetic average of a heavy-tailed variable is biased; one 10× day lifts the reference 35% | Right | E13: median volume ÷ reference is 0.89–0.90 in large caps and 0.85 in mid and small caps, below 1 in every stock. Bars 11–20 after a 5× day read about 11% low; a clipped average of log volume cuts that to 2–4% |
| Fixed multiples confuse dispersion with rarity | Right in mechanism, overstated in the example | 2× occurs on 2.7% of days in Dow stocks and 5.1% in mid and small caps; 1.5 times more often in the most erratic fifth of stocks. The reviewer's "σ = 0.25" stock is at the bottom of the real range (JNJ 0.31–0.33) |
| A z-score of log volume makes the flag comparable | True by construction; no trading benefit shown | zV ≥ 2 fires on 3.6–4.0% of days everywhere. It is as blunted after a spike as the old rule (21–40% fewer flags for about 30 bars) |
| The unclipped σ is inflated after a shock, making \|z\| ≤ 0.5 easier to meet | Right | E12: σ jumps 1.38–1.39× after a 5σ bar; for 20 bars P(\|z\| ≤ 0.5) is 50–54% against 43%. With clipping the excess is −1 to +2 points. 12–17% of old marks disappear, with no different forward return |
| The control group did not isolate volume | Right about the design, wrong about the consequence | E11: only 38–41% of the old control had \|z\| ≤ 0.5. With price action fixed the effect remains: LH +0.106 [+0.047, +0.160], MS +0.096 [+0.058, +0.135]; "price stopped" alone is worth nothing |
| Survivorship flatters the high-volume group | Not directly testable; the indirect test argues against it | No ticker disappears in any set. Bound: 6–21 unseen −60% outcomes per 1,000 marks would erase the raw 10-day edge. E20: the same calendar period gives the same effect whether the stocks had to survive 0–3 years or 9–12 years after the event, and stocks absent from the 2026 file show it as much as those present |
| The four sets are not four independent tests; 2018–2026 is missing | Right, and decisive | See E18 |
| Thirty comparisons, one pass; nothing after costs | Right in substance | After costs the historical peer-relative edge was about −0.2% to +0.3% per trade in recent data |
| Inverted accumulation and distribution signs "reflect exactly" Llorente et al. (2002) | Over-reading | That paper is about next-day returns. E18: no continuation or reversal after strong moves on unusual volume at 5 or 10 bars, in large or small caps |
| Volume's best-documented value is predicting volatility; use it to size positions and widen stops | Not supported | The cited papers concern same-day volume and variance. E14 and its audit: see point 4 of section 1 |
| Events cluster in market-wide sell-offs | Right | 28–42% of marks fall on the busiest 5% of dates; on large caps the whole historical effect sits in stressed markets (+0.17 against −0.02 in calm ones) |
| Replace relative volume by stock ÷ market | Not supported | It roughly halves the historical effect of the mark and predicts lower, not higher, volatility |

### Proposed complements

| Proposal | Verdict |
|---|---|
| Liquidity and volatility monitor (Amihud, stock-specific volume) for sizing | Not supported for sizing. Kept in the simplest form: 20-day dollar volume in the status table, as a liquidity gauge |
| Rolling per-stock continuation / reversal regime | No support at swing horizons (E18, S3); the literature result is a one-day effect from the 1990s. Not built |
| Anchored VWAP from earnings | No peer-reviewed evidence found; cannot be tested without an earnings calendar. Not built |
| Session-cumulative relative volume for the bar in progress | Built, in two forms (section 5) |

## 4. Experiments

| Id | Question | Result |
|---|---|---|
| E10, E10b | Shared panel for all tests | Reproduces every earlier count and result; adds MS and EM |
| E11 | Is the mark about volume once price action is fixed? | Yes historically: LH +0.106, MS +0.096 (Holm-significant), A +0.135, B +0.025, DJ +0.292 (60 marks). Dose-response from about 1.25× upward. Audit: every number reproduces; on large caps the effect exists only in stressed markets; recent data about +0.05; half of the LH gain arrives on day 1 |
| E12 | σ after shocks; hidden left tail | σ feedback confirmed; clipping fixes it. Left tail among survivors is not fatter under high volume (MS 4.84% against 4.85% for a 20-day loss beyond −22%) |
| E13 | Best definition of normal volume | Clipped average of log volume: centred at 0.96–0.98, 4–6% lower forecast error (all from centring), spike bias cut by 68–82% on bars 11–20. Audit: the reference change is supported; the z-score flag is a matter of design, not of evidence |
| E14 | Does volume predict volatility beyond price? | Raw: +11–15% over 10 bars after a 2× day. Beyond a price baseline that includes the day's range: at most ±2.5% per doubling. Audit and a re-check on EM: see section 1, point 4 |
| E18 | Old and new definitions on all six sets, including 2018–2026 | Old mark on EM −0.009 [−0.050, +0.031]. v3 mark: A +0.052, B +0.083, DJ +0.057, LH +0.069 [+0.010, +0.131], MS +0.083 [+0.040, +0.127], EM +0.034 [−0.006, +0.079]; EM by period +0.058 / +0.075 / +0.004. Heavy volume without a price move away from lows: nothing. High-volume premium (Gervais et al. design): +0.1% over 20 days before 2014, nil in 2018–2026. Strong moves on unusual volume: no continuation or reversal |
| E20 | Did the effect decay, or is it the source, or survivorship? | Same period, two snapshots: 2014-11 to 2017-10, +0.035 (stocks listed in 2017) against +0.027 (listed in 2026); 2006-08 to 2014-10, +0.127 against +0.115. Stocks of set MS present in the 2026 file +0.110, absent from it +0.093. 2018–2026 by period: +0.028, −0.142 (Feb–Jun 2020), −0.007, −0.026, +0.025. The calendar period decides the result; the years of survival required do not. Survivorship up to each snapshot itself remains untested |
| E19 | Real intraday data. Re-run on the cleaned 13-month sample (see E26); the first run used 49 sessions, 22 of them corrupted for NYSE names | Per-slot reference reads 0.95–0.97 in all seven 60-minute slots; a reference blind to the time of day reads 1.18 at the open, 0.69–0.75 at midday, 1.84 at the close and flags 18% of opening and 41% of closing bars at 2×. Volume share by slot: 17.4 / 12.8 / 10.8 / 9.8 / 10.6 / 13.8 / 24.8%. No 60-minute bar missing. The intraday bars sum to 0.81 of the daily volume. A daily bar in progress, unprojected, reads 91% low at 10:00, 71% at 11:30, 55% at 13:00, 25% at 15:30. Projection of the day from the volume so far, rank correlation with the final value: 0.62 at 10:30, 0.74 at 11:30, 0.84 at 13:00, 0.92 at 14:30 |
| Calendar check | Mechanical volume | Quarterly expiry days: median stock at 1.19× (LH), 1.31× (MS), 1.76× (EM); share of stocks at 2× or more: 8.9%, 21.3%, 39.9% against 3.6–5.1% on other days. Monthly expiries: no effect |

Not run at the time (the session's usage limit stopped them): a full study of the per-stock
continuation regime, the attention premium by company size, and a full market-relative
decomposition. E18 covers their main questions in a simpler form. The continuation regime was
tested later (E25), and the market reference for alerts in E21: section 8.

## 5. What v3 changes

| Element | v2 | v3 | Reason |
|---|---|---|---|
| Normal volume | Arithmetic EWMA of volume | Clipped, bias-corrected average of log volume | E13 |
| Unusual flag | 2× normal | zV ≥ 2 (the fixed multiple remains visible in the columns) | Comparable across stocks; a design choice |
| σ for the bar move | Unclipped | Clipped | E12 |
| Slot | Bar count since the session's first bar | Clock time and bar length | Missing bars, half days |
| Seeding | First observation | None: warm-up of 10 (intraday) or 25 (daily) earlier observations | Zero and outlier seeds |
| Bar in progress | Shown like a closed bar | Grey; "so far" in the table | E19 |
| Intraday | Bar-by-bar only | Adds session pace (cumulative volume against normal by this time) | E19 |
| Daily, bar in progress | Nothing | Estimate of the day with the range that held two days in three; US sessions, minute 30 to 360, not on half days | E19 |
| Mark "A, absorption at lows" | On | Renamed "H, heavy volume, small move, stretched low"; **off** | E18 |
| Quarterly expiry days | Not distinguished | Tinted; unusual-volume alert skipped by default | Calendar check |
| Status table | Relative volume, move, last mark | Adds the unusual level, pace, 20-day dollar volume, last unusual bar, data feed check | Review |
| Climax marks | Optional | Removed | No information (E05, E08) |

## 6. Review of the v3 script before release

Two reviewers read the first v3 script line by line, one as the compiler and one against the Python
twin (a literal transcription of the Pine functions agrees with the twin to 1e-12). Defects found
and fixed:

| Defect | Fix |
|---|---|
| The session pace of a bar in progress divided partial volume by the normal for the end of the bar (a normal day read 0.6 at 10:35) | The pane shows the last closed bar's pace while a bar is in progress |
| The pace alert compared with the previous session's last value and missed a second heavy day | Compared within the session |
| The day estimate overshot when it read high, and ran on half days and non-US sessions | Fitted slope, tighter gate (see E19) |
| Quarterly-expiry tint and alert skip were documented but not coded | Coded |
| "20-day" dollar volume was wrong on multi-day charts; Heikin Ashi lost its time-of-day slots; the feed ratio was wrong with extended hours | Fixed |
| Header and tooltips quoted the old mark's figures and "8.9 million" stock-days | Corrected: 6.4 million evaluated; mark H 0.05–0.08 in 2000–2017 |
| 14 of 29 single-line mutants of the twin survived the tests | Tests added for marks, warm-up, half days, counting rules, the estimate, and script-twin constants |

## 7. Not verified (v3; the current list is in section 8)

- Compilation in TradingView, the data feed, the behaviour of `time_close` on half days, the bar
  state at load, survivorship in every return result, and trading costs. The v3 list also named the
  thin intraday history (49 sessions); E26 replaced it with 13 months.

## 8. The second review (24 Nov 2026) and v4

The reviewer read the v3 script and the author's report with access to TradingView's documentation
and a Python interpreter. Every claim was checked again, with the project's data where the claim
was about markets and with a local copy of the Pine manual where it was about the platform.

### 8.1 Code

| Reviewer's claim | Verdict | Evidence |
|---|---|---|
| E1. A bar still open when the chart loads is treated as closed | **Correct.** The manual: the last bar "is still considered a historical bar because no realtime updates have been received", and `barstate.isconfirmed` "is true on all historical bars". Events, the state update and Screener filters used it unguarded | v4: `conf` excludes that bar. The reviewer's own fix (`conf = isconfirmed and not live`) would lose a bar whose closing update arrives a moment before `time_close`; the guard is applied to historical bars only |
| E2. The exported pace plot is the raw value of the bar in progress | Correct | The exported plot is the displayed value |
| E3. Pine Screener loads the first ten plots and two alert conditions, and computes on 500 bars | Correct (TradingView support page, search extract) | Numeric plots come first. 500 bars change zV by 0.00 (daily) and 0.01 (60-minute) at the median; flags agree on 99.6–100% of bars (E26) |
| E4. Weekly chart: a lower-timeframe request and no dollar volume | Correct | The request uses the chart's timeframe on daily and higher charts; weekly charts show the last 4 weeks ÷ 5 |
| E5. The quarterly expiry of June 2026 fell on Thursday 18 (Juneteenth); "last unusual volume" ignores the skip; non-US symbols are tinted | **Correct.** 19 June 2026 has no bars; on the 18th 29.7% of stocks traded at 2× or more | Coded, with the 2027 case the reviewer did not see: Juneteenth observed on Friday 18 June 2027 (NYSE calendar), expiry on Thursday 17. US-listed stocks and funds only |
| E6. `syminfo.prefix` cannot show that the data come from Cboe | Plausible; not verifiable here. The manual gives "NASDAQ" or "BATS" for AAPL, depending on the symbol loaded | The row no longer presents the prefix as a check |
| E7. The first, partial session seeds the pace reference; pre-market volume enters the pace | First part immaterial: one observation carries a weight below 0.1% after 70 sessions. Second part correct in substance | Session pace is shown with regular trading hours only |
| E8. Clipping starts after 20 observations but values show after 10 on intraday charts | True, immaterial: it concerns bars 10–19 of the loaded history of each slot | No change |
| E9. Cap triangle on the live bar; repeated pace alerts; level line stuck at the cap | Correct | Fixed; the pace alert fires once per session |
| "alertcondition() cannot carry computed values" | **Wrong.** The manual: `{{plot_0}}` to `{{plot_19}}` and `{{plot("title")}}` | Both routes are offered: placeholders in the three alert conditions, and one formatted line through `alert()` |

### 8.2 Objections to the author's conclusions

| Objection | Verdict | Evidence |
|---|---|---|
| 1a. E20 cannot exclude survivorship up to each snapshot | Correct, and already stated as untested. The reviewer's arithmetic (1.5% against 0.3% of marks followed by a fatal delisting would create +0.07) shows it is possible, not that it happened | Needs a data set with delisted companies. Moot for the script: the mark is removed |
| 1b. The mark did not decay; it is conditional on market stress and will return | **Refuted** by the reviewer's own test | E21, same definition as the first audit (trailing 21-day volatility of the set's mean return above its past-only expanding median). Stressed against calm: LH +0.170 against −0.024; MS +0.116 against +0.068; EO +0.112 against +0.057; **EM 2018–2026: −0.022 [−0.073, +0.034] against +0.017**. With the v3 definition on EM: +0.030 [−0.023, +0.084] against +0.042 |
| 2. A market reference (zV of SPY) would spare an alerts-only user the broad days | **Fails the reviewer's own criterion** (keep at least 85% of idiosyncratic jumps) | E21. Flags are moderately clustered: outside expiry days the busiest 5% of days hold 20% of the flags. SPY's zV tracks breadth weakly (rank correlation 0.42; it reads 2 or more on 26% of the broadest days). The filter "zV − market zV ≥ 1.5" keeps 45% of the flags on broad days but removes 16% on ordinary days and 18% of the idiosyncratic jumps. The calendar does better: expiry and Russell days are 2% of days and 17.7% of flags |
| 3. The day estimate is biased low because it was calibrated on intraday volume that lacks the close | **Correct**, and larger than the reviewer computed | E24. The intraday bars sum to 0.82 of the daily volume on ordinary days and 0.42–0.52 on expiry and index-rebalance days: the missing part is the closing auction. Judged as the pane uses it, the v3 estimate read 6% low at 10:00, 13% at 11:30, 18% at 13:00, 22% at 15:30, and reached 2× on 2.1% of days when 4.5% ended there. Removed |
| 4. Averaging hides the per-stock regimes of Llorente et al. | **Tested and nil** | E25. A rolling c2 does not persist (rank correlation with itself one window later: 0.03 and 0.01 with 250 bars, 0.02 and 0.01 with 750). Top against bottom fifth by c2, next-bar product of returns on unusual volume: MS −0.065 [−0.18, +0.06], EM −0.022 [−0.13, +0.10]; signed forward return after strong moves on unusual volume, 1 to 10 bars: every interval includes zero in both sets |
| 5. ATR understates risk after heavy volume on a narrow bar | **Refuted** | E22, bars with true range ≤ previous ATR, unusual against ordinary volume at equal range: next-10-bar range relative to the bar's ATR −5.9% [−7.5, −4.3] (EM), −6.0% (MS), −4.7% (LH); a 2-ATR stop is touched 2 to 4 points less often |
| 6. The 8–12% of 60-minute bars flagged came from the window, not from intraday bars | Right that it was an artefact, wrong about the cause | E26: the source's volume was corrupted from 6 Oct 2026 for NYSE names. On the cleaned 13 months, with at least 100 earlier sessions per slot: 3.8% of 60-minute bars and 3.9% of 4-hour bars at zV ≥ 2, 1.1% and 1.2% at zV ≥ 3, the same in every slot and quarter. A control with daily bars and a 49-bar history gives 4.9%: short history alone was never the cause |

### 8.3 Proposals

| Proposal | Decision | Reason |
|---|---|---|
| Remove mark H and its price series | Done | E21 |
| Remove the day estimate | Done | E24 |
| Remove the debug plots | The slot key stays (the parity check needs it), as the last plot | |
| Add the zV of SPY to the table and the alert | Not added | E21, objection 2 |
| Alerts with the numbers | Done, both ways | |
| Optional alert filter: the bar moved | Done, off by default | 53% of flags come with a move of 1.5σ or more, 42% with 2σ. It thins alerts; it carries no information (E18) |
| Scale of the z-score from absolute deviations (L1) or median/MAD | Not changed | E23, injection of a 5× day into real series: the shipped scale loses 20% of the flags of the next 30 bars and 11% of the following 30; the L1 scale 17% and 9%. Skipping the spike in the scale halves the loss but raises the flag rate to 5.4% and widens it across stocks |
| Complement: continuation regime | Retired | E25 |
| Complement: liquidity and volatility monitor | Retired by the reviewer; the stop rule stands | E14, E22 |
| Complement: VWAP anchored at shocks | Not tested | A study of a price setup, outside the volume pane; open for the owner to decide |

### 8.4 Experiments of the second round

| Id | Question | Result |
|---|---|---|
| E21 | Stress or decay; clustering of flags; market reference | See 8.2. Share of stocks at zV ≥ 2 by kind of day, 2018–2026: quarterly expiry 37.1%, Russell reconstitution 36.9%, last trading day of February, May and November about 10%, other month ends 4.8%, monthly expiries 3.8%, other days 3.5%. Extreme volume (zV ≥ 3): 15.5% and 18.2% on the two mechanical kinds against 1.0%. Second Friday of November 2026: 1.9%, no sign of a second reconstitution |
| E22 | Heavy volume on narrow bars and later volatility | See 8.2 |
| E23 | Other scale estimators after a spike | See 8.3 |
| E24 | Missing intraday volume; the v3 day estimate | See 8.2 |
| E25 | Per-stock continuation regime | See 8.2 |
| E26 | Intraday behaviour on 13 months (273 sessions, 29 Aug 2025 to 5 Oct 2026; 170 liquid stocks with a clean record) | Flag rates: see 8.2. Centring: median 0.95–0.97 in every slot. **Session pace alert:** at a fixed 2× it fires on 12 stocks in 100 per day and 26% of those days end with unusual volume on the daily chart, because the first hour is erratic (75% of the crossings happen there). In units of its own spread: zV ≥ 2 gives 7 in 100 and 43%, announcing 90% of the days that end unusual (70% before 11:30); zV ≥ 2.5 gives 4 in 100 and 63%, announcing 75% (56% before 11:30). Half days (28 Nov and 24 Dec 2025): the short last bar stays in warm-up, earlier bars read 0.6–0.7. Expiry and index-rebalance days on 60-minute bars: 12–14% of opening and closing bars flagged, midday bars normal |
| Source check | Corrupted prints in the public intraday data | Single one-minute bars of several hundred thousand or million shares, so that the intraday sum exceeds the official daily volume: 9.3% of checked ticker-days; NASDAQ names from late Sep 2025 to mid Mar 2026, NYSE names in Jan, May and Aug 2026 and on 40–58% of ticker-days from 6 Oct 2026. Cleaning: `research/experiments/intraday_common.py` |

### 8.5 What v4 changes

| Element | v3 | v4 | Reason |
|---|---|---|---|
| Closed bar | `barstate.isconfirmed` | Excludes a bar that is still open at load (historical, `timenow` before its close; forming bars of non-time charts; 20 minutes of margin on delayed feeds) | 8.1, E1 |
| Mark H, extension, ATR, quiet-bar dots | Optional | Removed | E21 |
| Daily bar in progress | Estimate of the day | "So far" only | E24 |
| Mechanical days | Third Friday of the quarter month | Adds the holiday shift (Thursday 17 or 18 June) and the Russell reconstitution; US stocks and funds only; left out of "last unusual volume"; applies to the extreme and pace alerts too | E21 |
| Session pace alert | Pace ≥ 2×, re-armed whenever it fell below | zV of the pace ≥ 2.5, once per session | E26 |
| Session pace | Any session | Regular trading hours only | 8.1, E7 |
| Alerts | Fixed text | Numbers in the message (placeholders), one formatted line through `alert()`, optional minimum move | Review |
| Plots | Visual plots first | Numeric series first, for the Pine Screener and the placeholders | 8.1, E3 |
| Liquidity | Dollar volume, intraday and daily charts | Adds weekly charts; labelled with the currency of the prices | 8.1, E4; script review |
| Feed row | Prefix shown as a check | "Intraday history": yesterday's bars ÷ daily bar, alarm below 0.3 (it is 0.42–0.52 after an expiry day) | 8.1, E6; E24 |

### 8.6 Review of the v4 script

Two reviewers read the v4 script line by line with the local copy of the Pine manual: one as the
compiler (no finding; its estimate that the script compiles as written: 92%), one as the runtime and
the user (no blocker; on a US stock at 1h, 4h, daily and weekly with real-time data, no wrong number,
colour, table row or alert). Their findings, all applied: the June 2027 expiry (Thursday 17);
"dollar volume" shown for prices in other currencies; a possible "NaN" in the alert text on the
first eligible bar of a fresh listing; forming bars of tick and Renko charts and of delayed feeds
counted as closed at load; the pace alert not covered by the mechanical-day switch; the calendar
rule applied to US futures; the parity tool failing on extended-hours exports.

### 8.7 Not verified

- **Compilation in TradingView.** Syntax parse and two line-by-line reviews only.
- **The data feed.** What TradingView shows in a bar in progress, and in a bar at the moment it
  closes, without paid exchange data and with it. The manual says some trades reach the end-of-day
  feed only; if that is so on the user's feed, alerts on daily bars fire on a volume that is too
  low. The playbook has five checks; the fifth measures this.
- **`time_close` on daily bars and on half days.** The manual's countdown example relies on it for
  intraday and daily charts; whether it reports an early close is not documented. Read the 12:30
  bar of a 1h chart on 27 Nov 2026 (13:00 close): the plot `dbg_key` should read 7500030 for that
  bar (7500060 on a normal day).
- **Bar state in the Pine Screener.** Assumed to be that of a chart at load.
- **Number format of the alert placeholders.**
- **Intraday bars on TradingView.** One public source, 13 months, 170 stocks after cleaning; whether
  TradingView's last intraday bar includes the closing auction is unknown, and decides how much
  expiry days show on intraday charts.
- **Survivorship**, in every return result, and **trading costs**.
