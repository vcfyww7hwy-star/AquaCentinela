# Relative Volume: the external review, what was tested, and v3

- **Date:** 24 Nov 2026.
- **Subject:** an external AI reviewer criticised `pine/relative_volume.pine` (v2) and the evidence
  behind it, without tools: no code execution, no data, no documentation access.
- **This document:** each claim checked against data or sources, the experiments run, and the
  resulting v3 design. Specification of v3: `03_relative_volume.md`.

## 1. What is true now

1. **No volume reading tested predicts direction at swing horizons in 2018–2026.** That covers the
   former "absorption at lows" mark, a general high-volume premium, and continuation or reversal
   after strong moves on unusual volume.
2. **The "absorption" mark had a real, narrow effect until about 2017 and has none since.** With the
   bar's price action held fixed, heavy volume beat ordinary volume by about 0.1 risk units over 10
   bars against same-day peers in 2000–2017. On 2018–2026 the same test gives −0.009 [−0.050, +0.031].
   The new data source reproduces the old effect on 2006–2017 (+0.087 [+0.039, +0.138]), so the null
   result is about the period, not the source (E20).
3. **The reviewer's three statistical criticisms of the reference were right.** The arithmetic
   reference sat 10–15% too high, one extreme day distorted it for weeks, and the unclipped
   volatility was inflated for weeks after a shock. v3 fixes all three.
4. **Volume does not earn a place in position sizing.** After a bar at twice normal volume the next
   10 bars are 6–9% more volatile than the *previous* bar's ATR implied, and a stop two previous-ATRs
   away is hit 3–5 points more often. ATR recomputed at that bar's close already absorbs this. The
   rule is: use the ATR of the signal bar, add no extra widening.
5. **Mechanical volume is large and growing.** On quarterly option-expiry days in 2018–2026, 40% of
   stocks traded at twice normal volume or more, against 5% on other days.
6. **The time-of-day normalisation works on real intraday data**, and an unprojected bar in progress
   understates relative volume by 21–92% depending on the hour.

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
| E19 | Real intraday data | Per-slot reference reads 1.01–1.04 in all seven 60-minute slots; a reference blind to the time of day reads 1.33 at the open, 0.74 at midday, 1.74 at the close and flags 25–37% of opening and closing bars. Volume share by slot: 17.5 / 13.1 / 11.4 / 10.5 / 11.5 / 14.2 / 21.8%. Projection of the day from the volume so far, rank correlation with the final value: 0.63 at 10:30, 0.71 at 11:30, 0.81 at 13:00, 0.91 at 14:30. A plain projection (volume so far ÷ usual share) overshoots when it reads high: the day ended lower in 72–88% of the cases where it read 2× or more. The pane's estimate uses a fitted slope below 1; on hold-out sessions its error (in logs) is 0.40 at 10:30, 0.33 at 11:30, 0.25 at 13:00, 0.16 at 14:30, lower than the plain projection at every hour |
| Calendar check | Mechanical volume | Quarterly expiry days: median stock at 1.19× (LH), 1.31× (MS), 1.76× (EM); share of stocks at 2× or more: 8.9%, 21.3%, 39.9% against 3.6–5.1% on other days. Monthly expiries: no effect |

Not run (the session's usage limit stopped them): a full study of the per-stock continuation regime,
the attention premium by company size, and a full market-relative decomposition. E18 covers their
main questions in a simpler form.

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

## 7. Not verified

- **Compilation in TradingView.** The script passes a syntax parse. Two independent line-by-line
  reviews found no compile error and estimated about 85% that it compiles as written.
- **The data feed.** Run the four checks in the playbook before trusting any live reading.
- **Half days.** Whether `time_close` reports the early close: read the 12:30 bar of a 1h chart on
  27 Nov 2026 (13:00 close). The plot `dbg_key` should read 7500030 for that bar (7500060 on a normal
  day).
- **Bar state.** That the last bar is drawn grey while it is in progress and not after the close.
- **Intraday history.** 49 sessions from one source; unusual-volume flags fired on 8–11% of 60-minute
  bars in that sample (earnings season, short history) against 4% on daily bars.
- **Survivorship**, in every return result.
- **Trading costs**: daily bars hold no quotes or fills.
