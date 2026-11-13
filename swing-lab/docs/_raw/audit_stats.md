# Audit of the 14 frozen candidates: statistics (the skeptic's report)

11 Nov 2026. Development data only (DEV 2011-01..2018-06, CTX 1998..2010). No validation or lockbox
outcome was computed or read. Script: `research/experiments/audit_stats.py`; outputs
`research/results/audit_stats_{DEV,CTX,registry}.json`; every number looked at is logged under
registry tag `audits`, family `AUDIT_stats`.

## Verdict

1. **The logged numbers are right, but the statistic flatters most candidates.** All 28 logged
   values (14 candidates x 2 samples) reproduce to the decimal. They weigh every day equally,
   whatever the number of signals. When every signal event weighs the same (which is what a
   trader who sees the flag on a chart experiences), the effect falls by 43% to 67% for 11 of
   the 14 in DEV and changes sign for two in CTX (A4: -36 becomes +6; A7: -92 becomes +73). Only
   **E1, A1, A2, A3 and A8** keep the predicted sign at one-sided 5% under both weightings in
   both samples.
2. **The search explains part of the list.** 62,923 registry lines, 10,149 DEV-CTX pairs of
   cross-sectional cells. Between 2 and 5 of the 14 are expected to be selection noise. A3, A8,
   A4 and A1 stand clear of the search; A7, A6, A10 and A9 do not; the other six sit in a crowd
   of 47 to 121 logged cells that look at least as good.
3. **"Same sign in two decades" is weak protection.** Across all logged pairs the signs agree 61%
   of the time, and 80% of the time once |t| >= 2 in DEV. Both samples hold survivors only (15 of
   1,752 DEV names stop trading inside the sample; 0 of 1,282 in CTX), so they share their main bias.
4. **The avoid states are worth about 1 bp per position to a trend follower.** Three (A2, A7,
   A11) cannot occur in a trend-following selection by construction. The rest occur rarely or
   have effects of 2 to 18 bp inside it. Only A1 is material per event (-44 bp over 20 bars inside
   the selection, both samples), as an exit.
5. **The validation test as drafted is underpowered and too wide.** With 14 hypotheses under
   Holm, about 3 confirmations are expected if every development estimate is the exact truth,
   and fewer than one if the truth is half of it. Test 7, not 14; make the event-weighted
   estimate part of the verdict; fix the items in "Defects" first.

## 0. What was reproduced

| | Theirs (g30_attack.json) | Mine, day-weighted |
|---|---|---|
| All 14 candidates, DEV and CTX, bp and t | see tables below, column "logged" | identical in all 28 cells |

The frozen functions, `Study.fwd`, `engine.spread_series` and `engine.nw_mean` were used unchanged.

## 1. Inference

Versions, each at the candidate's frozen horizon h:
(a) day-weighted mean of (signal mean - control mean), Newey-West 2h lags (the reported one);
(b) event-weighted: sum of n_t d_t over sum of n_t, date-clustered through the daily sums as in
`Study._ts` but against the same-day control (the delta-method t differs by at most 0.3);
(c) median daily spread and share of days with the predicted sign;
(d) one sample day in h kept, for all h starting offsets: median t, range, observations per offset;
(e) circular block bootstrap over calendar months, 1,000 draws, block = max(2, ceil(2h/21)) months.

**DEV**

| ID | h | logged bp (t) | (a) day-weighted bp (t) | (b) event-weighted bp (t) | (c) median bp, days right | (d) non-overlapping: median t [min, max], obs | (e) 95% CI day-weighted | (e) 95% CI event-weighted |
|---|---|---|---|---|---|---|---|---|
| E1 | 10 | +56.7 (+2.07) | +56.7 (+2.07) | +57.8 (+2.61) | +38.0, 54% | +0.78 [-1.26, +2.09], 62 | +4 to +113 | +17 to +103 |
| E2 | 5 | +20.9 (+2.40) | +20.9 (+2.40) | +11.1 (+1.37) | +12.6, 52% | +0.86 [+0.74, +1.72], 218 | +2 to +37 | -4 to +25 |
| E3 | 60 | +41.8 (+1.94) | +41.8 (+1.94) | +36.2 (+1.34) | +21.8, 55% | +1.19 [-0.06, +1.97], 29 | +2 to +85 | -10 to +91 |
| A1 | 20 | -49.3 (-2.56) | -49.3 (-2.56) | -26.6 (-2.08) | -49.1, 55% | -0.59 [-3.30, +1.34], 73 | -93 to -13 | -54 to -2 |
| A2 | 10 | -28.8 (-2.27) | -28.8 (-2.27) | -22.1 (-2.07) | -28.2, 55% | -1.21 [-3.41, +0.60], 160 | -51 to -5 | -40 to -2 |
| A3 | 5 | -15.0 (-3.29) | -15.0 (-3.29) | -8.5 (-2.59) | -9.5, 54% | -1.70 [-2.38, -0.31], 359 | -23 to -6 | -14 to -2 |
| A4 | 20 | -40.1 (-3.75) | -40.1 (-3.75) | -21.4 (-2.61) | -40.6, 56% | -0.70 [-3.38, +1.66], 87 | -61 to -18 | -37 to -6 |
| A5 | 5 | -22.6 (-2.32) | -22.6 (-2.32) | -10.8 (-1.38) | -13.6, 54% | -1.85 [-2.09, -1.65], 368 | -42 to -4 | -25 to +4 |
| A6 | 20 | -26.9 (-1.41) | -26.9 (-1.41) | -9.0 (-0.78) | -16.7, 52% | -0.33 [-2.78, +1.29], 71 | -62 to +12 | -29 to +16 |
| A7 | 60 | -126.2 (-1.33) | -126.2 (-1.33) | -51.6 (-0.50) | -18.5, 51% | -1.08 [-1.93, -0.21], 26 | -329 to +57 | -288 to +138 |
| A8 | 5 | -9.7 (-3.35) | -9.7 (-3.35) | -3.7 (-2.02) | -6.4, 55% | -1.91 [-2.64, -0.90], 369 | -16 to -4 | -7 to -0 |
| A9 | 20 | -54.3 (-2.05) | -54.3 (-2.05) | -28.9 (-1.28) | -40.7, 56% | -1.67 [-2.56, -0.53], 91 | -109 to -4 | -68 to +15 |
| A10 | 60 | -26.4 (-0.55) | -26.4 (-0.55) | -8.8 (-0.21) | -1.0, 50% | -0.61 [-1.15, +0.64], 29 | -121 to +71 | -97 to +68 |
| A11 | 5 | -34.6 (-2.74) | -34.6 (-2.74) | -12.2 (-1.13) | -19.1, 53% | -1.01 [-2.35, -0.16], 195 | -62 to -7 | -34 to +11 |

**CTX**

| ID | h | logged bp (t) | (a) day-weighted bp (t) | (b) event-weighted bp (t) | (c) median bp, days right | (d) non-overlapping: median t [min, max], obs | (e) 95% CI day-weighted | (e) 95% CI event-weighted |
|---|---|---|---|---|---|---|---|---|
| E1 | 10 | +88.8 (+2.93) | +88.8 (+2.93) | +69.1 (+2.78) | +35.9, 53% | +1.18 [-0.69, +2.89], 75 | +35 to +146 | +24 to +119 |
| E2 | 5 | +21.4 (+2.27) | +21.4 (+2.27) | +14.6 (+2.29) | +4.0, 51% | +0.92 [-0.00, +2.05], 401 | +3 to +41 | +2 to +28 |
| E3 | 60 | +99.9 (+2.45) | +99.9 (+2.45) | +80.9 (+2.34) | +72.8, 59% | +1.60 [+0.66, +3.27], 54 | +20 to +186 | +12 to +154 |
| A1 | 20 | -77.7 (-3.39) | -77.7 (-3.39) | -37.1 (-2.00) | -59.3, 54% | -1.16 [-2.77, +0.80], 121 | -120 to -35 | -71 to +3 |
| A2 | 10 | -21.9 (-1.90) | -21.9 (-1.90) | -37.4 (-3.84) | -28.7, 54% | -0.87 [-2.98, +0.84], 300 | -43 to -0 | -53 to -23 |
| A3 | 5 | -20.9 (-4.20) | -20.9 (-4.20) | -10.7 (-2.92) | -15.1, 54% | -2.16 [-3.37, -0.39], 632 | -31 to -11 | -18 to -4 |
| A4 | 20 | -36.4 (-2.56) | -36.4 (-2.56) | +5.9 (+0.54) | -30.6, 54% | -0.55 [-2.98, +1.12], 147 | -63 to -9 | -16 to +28 |
| A5 | 5 | -14.0 (-1.99) | -14.0 (-1.99) | -14.3 (-1.79) | -15.6, 54% | -1.73 [-2.10, -1.08], 653 | -26 to -1 | -28 to +0 |
| A6 | 20 | -32.2 (-2.03) | -32.2 (-2.03) | -16.8 (-1.22) | -21.8, 52% | -0.45 [-2.60, +1.54], 118 | -67 to +2 | -44 to +9 |
| A7 | 60 | -91.9 (-1.24) | -91.9 (-1.24) | +73.2 (+0.93) | -54.7, 53% | -1.06 [-1.57, -0.18], 54 | -249 to +56 | -83 to +195 |
| A8 | 5 | -18.3 (-4.50) | -18.3 (-4.50) | -13.6 (-5.65) | -11.7, 56% | -3.10 [-3.80, -1.10], 653 | -28 to -10 | -19 to -9 |
| A9 | 20 | +137.9 (+2.97) | +137.9 (+2.97) | +103.2 (+2.82) | +53.3, 44% | +2.32 [+1.61, +3.52], 161 | +54 to +232 | +37 to +177 |
| A10 | 60 | -123.5 (-3.37) | -123.5 (-3.37) | -72.7 (-3.03) | -72.1, 62% | -2.45 [-3.67, -0.45], 54 | -193 to -50 | -126 to -21 |
| A11 | 5 | -18.1 (-1.46) | -18.1 (-1.46) | -20.1 (-1.59) | -15.4, 52% | -0.63 [-2.09, +0.75], 331 | -41 to +6 | -41 to +0 |

**Do the conclusions agree?**

- **Weighting (a against b) is where they disagree.** Days with few signals carry larger effects
  than days with many (market-wide gap or shock days produce many flags and little stock-specific
  drift). The day-weighted mean is the return of a book that puts the same capital to work every
  day; no one who acts on flags trades that way.
  - Predicted sign at one-sided 5% (|t| >= 1.645) under both weightings in both samples: **E1,
    A1, A2, A3, A8**. A1 is the thinnest of the five (event-weighted t -2.08 and -2.00; CTX
    bootstrap interval -71 to +3).
  - Significance depends on the weighting: **A4** (CTX event-weighted +5.9, t +0.5), **A7** (CTX
    +73), **E2** (DEV t 1.37), **A5** (DEV t -1.38), **A11** (DEV t -1.13), **A9** (DEV t -1.28),
    **E3** (DEV t 1.34). A6 and A10 are not significant in DEV under either.
- **Overlap (d, e).** The month-block bootstrap standard error is 0.92 to 1.11 times the
  Newey-West one in all 28 cells, so 2h lags are not grossly short. The non-overlapping version
  discards real information for sparse events and is not a like-for-like test, but it shows how
  few independent windows there are: no candidate keeps |t| >= 2 in the median grid in DEV (best:
  A8 -1.91, A5 -1.85, A3 -1.70); in CTX only A3, A8 and A10 do (and A9, with the wrong sign). The 60-bar candidates rest on 29
  (DEV) and 54 (CTX) independent windows; validation would have 18.
- **Median and sign (c).** The share of days with the predicted sign is 50% to 56% in DEV for
  every candidate. These are small shifts in a noisy daily distribution, not regular effects.
- **Stability inside DEV.** Event-weighted, the second half (2015-01..2018-06) is near zero for
  A4 (-6, t -0.5), A5 (-1), A7 (-2), A9 (-1) and A8 (-3, t -1.0). E1 is the same in both halves
  (+55, +59). Survivor bias cannot explain the decay: it is stronger in the early years and
  pushes the other way.

| ID | DEV 2011-14 day | DEV 2015-18 day | DEV 2011-14 event | DEV 2015-18 event | CTX 1998-2004H1 event | CTX 2004H2-2010 event |
|---|---|---|---|---|---|---|
| E1 | +52 (+1.4) | +60 (+1.6) | +55 (+1.8) | +59 (+2.0) | +150 (+2.9) | +46 (+1.6) |
| E2 | +20 (+1.4) | +21 (+2.0) | +10 (+0.9) | +12 (+1.1) | +34 (+2.8) | +4 (+0.5) |
| E3 | +40 (+1.4) | +43 (+1.3) | +19 (+0.8) | +46 (+1.2) | +150 (+2.4) | +46 (+1.1) |
| A1 | -60 (-2.6) | -39 (-1.3) | -36 (-1.9) | -21 (-1.2) | -44 (-1.3) | -33 (-1.5) |
| A2 | -26 (-1.4) | -32 (-1.9) | -28 (-2.1) | -18 (-1.2) | -43 (-2.7) | -34 (-2.8) |
| A3 | -14 (-2.1) | -16 (-2.7) | -10 (-2.7) | -7 (-1.3) | -14 (-1.9) | -9 (-2.3) |
| A4 | -52 (-3.7) | -27 (-1.7) | -38 (-4.0) | -6 (-0.5) | +19 (+1.0) | +0 (+0.0) |
| A5 | -34 (-2.5) | -10 (-0.7) | -20 (-1.6) | -1 (-0.1) | -14 (-0.9) | -15 (-1.8) |
| A6 | -13 (-0.4) | -41 (-1.7) | +1 (+0.1) | -18 (-1.2) | -26 (-1.1) | -12 (-0.7) |
| A7 | -198 (-1.4) | -59 (-0.5) | -167 (-1.1) | -2 (-0.0) | +11 (+0.1) | +107 (+1.1) |
| A8 | -13 (-3.1) | -6 (-1.6) | -5 (-2.0) | -3 (-1.0) | -16 (-3.3) | -12 (-4.7) |
| A9 | -96 (-2.3) | -8 (-0.3) | -67 (-1.9) | -1 (-0.0) | +162 (+2.6) | +66 (+1.5) |
| A10 | +26 (+0.4) | -84 (-1.3) | +40 (+0.7) | -45 (-0.8) | -168 (-3.7) | -28 (-1.1) |
| A11 | -31 (-1.7) | -37 (-2.1) | -10 (-0.6) | -14 (-1.0) | -4 (-0.2) | -29 (-1.7) |

**Horizon profile, event-weighted bp (t).** The frozen horizon is not always where the effect is.

| ID | frozen h | DEV h=1 | DEV h=5 | DEV h=10 | DEV h=20 | DEV h=60 | CTX h=1 | CTX h=5 | CTX h=10 | CTX h=20 | CTX h=60 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 10 | +19 (+2.3) | +48 (+2.7) | +58 (+2.6) | +62 (+2.1) | +67 (+1.1) | +35 (+3.9) | +49 (+2.5) | +69 (+2.8) | +91 (+3.1) | +58 (+1.1) |
| E2 | 5 | +4 (+1.0) | +11 (+1.4) | +10 (+0.9) | -3 (-0.2) | -23 (-0.7) | +8 (+2.6) | +15 (+2.3) | +25 (+2.9) | +46 (+3.0) | +52 (+1.9) |
| E3 | 60 | -0 (-0.3) | +2 (+0.8) | +6 (+1.3) | +13 (+1.4) | +36 (+1.3) | -2 (-2.1) | +2 (+0.7) | +10 (+1.6) | +21 (+1.8) | +81 (+2.3) |
| A1 | 20 | -7 (-1.5) | -25 (-3.2) | -19 (-1.8) | -27 (-2.1) | -22 (-1.0) | -13 (-2.6) | -15 (-1.2) | -28 (-1.8) | -37 (-2.0) | +16 (+0.4) |
| A2 | 10 | -3 (-1.4) | -12 (-1.8) | -22 (-2.1) | -33 (-2.3) | -74 (-2.5) | -13 (-4.3) | -32 (-4.4) | -37 (-3.8) | -44 (-3.0) | -93 (-4.3) |
| A3 | 5 | -6 (-4.7) | -8 (-2.6) | -10 (-2.2) | -13 (-2.2) | -14 (-1.1) | -5 (-3.9) | -11 (-2.9) | -14 (-2.5) | -14 (-1.3) | -14 (-0.5) |
| A4 | 20 | -2 (-1.0) | -8 (-1.8) | -13 (-1.9) | -21 (-2.6) | -17 (-1.0) | -4 (-1.5) | -6 (-1.1) | -3 (-0.4) | +6 (+0.5) | +25 (+1.0) |
| A5 | 5 | -5 (-3.0) | -11 (-1.4) | -16 (-1.1) | -11 (-0.4) | -36 (-0.8) | -15 (-9.0) | -14 (-1.8) | -19 (-1.3) | -5 (-0.2) | +5 (+0.1) |
| A6 | 20 | -0 (-0.0) | -5 (-1.1) | -12 (-1.8) | -9 (-0.8) | -16 (-0.7) | +6 (+2.6) | +12 (+2.1) | +3 (+0.3) | -17 (-1.2) | -41 (-1.6) |
| A7 | 60 | +0 (+0.2) | +3 (+0.2) | +4 (+0.2) | -5 (-0.1) | -52 (-0.5) | +2 (+0.9) | +9 (+1.0) | +17 (+1.0) | +32 (+0.9) | +73 (+0.9) |
| A8 | 5 | -1 (-2.4) | -4 (-2.0) | -5 (-1.6) | -5 (-1.1) | -2 (-0.3) | -3 (-4.3) | -14 (-5.7) | -18 (-5.2) | -20 (-4.1) | -26 (-2.3) |
| A9 | 20 | +2 (+1.1) | +2 (+0.3) | -12 (-1.0) | -29 (-1.3) | -83 (-1.2) | +3 (+1.2) | +40 (+3.3) | +70 (+3.3) | +103 (+2.8) | +170 (+2.0) |
| A10 | 60 | +0 (+0.6) | +1 (+0.3) | +0 (+0.1) | -1 (-0.1) | -9 (-0.2) | +1 (+1.7) | -2 (-0.8) | -6 (-1.1) | -14 (-1.3) | -73 (-3.0) |
| A11 | 5 | -14 (-2.4) | -12 (-1.1) | -22 (-1.6) | -34 (-2.0) | -29 (-0.8) | -17 (-2.3) | -20 (-1.6) | -19 (-1.3) | -29 (-1.1) | -61 (-1.4) |

- **A3, A5 and A11 are one-session effects registered as five-bar effects.** A3: -6 of the -8.5
  bp falls in the first session (day-weighted: -9 of -15, t -4.5). A5 in CTX: -15 on day one,
  -14 after five. A11 in DEV: -14 on day one, -12 after five. The first-bar outcome is the next
  session's open-to-close return. g30's own one-bar delay shows the same thing (A3 -4.1, t -0.9;
  A11 -9.9, t -0.85): the sign survives, the effect does not.
- **A1's day-weighted h=20 is a peak** (h=10: -23, t -1.4; h=20: -49, t -2.6; h=60: -37). The
  event-weighted effect arrives within 3 to 5 bars (-25, t -3.2) and is flat afterwards.
- **E1 is a plateau** from 5 to 20 bars in both samples. E2 in DEV is gone by 20 bars.

**The candidates are not 14 separate bets** (share of the row's events that are also the column's, DEV):
A1 in A4 58%, A1 in E3 64%, A9 in E3 55%, A7 in E3 28%, A11 in A2 44%, A11 in A8 42%, A3 in A8 37%,
E1 in A10 78%, E2 in A3 33%. E3 ("select") therefore covers most of the stock-days that A1 and A9
("avoid") flag, with the opposite prediction.

## 2. Multiple testing

**What was searched** (`registry/*.jsonl`, excluding the audit and dry-run files): 62,923 lines in
25 family labels. Cross-sectional cells with a t-statistic: 28,504, in 15,898 distinct
definitions. Largest families (all lines / XS cells): F03_momentum_selection 40,350 / 21,825;
F09_map 5,631 / 0; F05_volume 4,164 / 2,076; F06_breakouts 3,191 / 1,568; E01_anatomy 2,881 /
1,440; F09_port 2,624 / 0; G02_shocks 792 / 396; F09_stock 646 / 285; G12_risk 419 / 16;
G03_selection 408 / 204; G13_strange 240 / 120; G01_dips 228 / 114; G10_earnings 224 / 112;
G05_volume 192 / 96; G06_breakouts 192 / 96; G30_attack 182; G07_gaps 156 / 78; G14_resid 156 /
78; G09_regime 94; E02_french 62; G11_exits 60; E03_intraday 17; three probe families 14.

**(ii) Distribution of |t| over logged XS cells with at least 100 events.**

| | cells | robust sd of t | median abs t | abs t >= 2 | abs t >= 3 | abs t >= 4 |
|---|---|---|---|---|---|---|
| Standard normal | | 1.00 | 0.67 | 4.6% | 0.27% | 0.006% |
| DEV | 14,237 | 1.10 | 0.75 | 8.3% | 1.6% | 0.4% |
| CTX | 10,219 | 1.37 | 1.03 | 14.3% | 2.8% | 1.0% |

The search found about twice (DEV) and three times (CTX) as many |t| >= 2 cells as noise would.
In the main-loop families the candidates came from, the excess is larger: G02 24% of DEV cells at
|t| >= 2, G07 33%, G13 20%; in CTX G01 49%, G02 41%, G07 44%. That excess is real structure plus
shared bias; the registry cannot separate them.

**(i) Sign agreement between the two samples.** 10,149 pairs (same family, id, definition,
parameters; at least 100 events in both).

| Subset | Pairs | Same sign |
|---|---|---|
| All | 10,149 | 61.2% (family-weighted 57.1%) |
| abs t DEV < 1 | 6,714 | 56.4% |
| abs t DEV >= 1 | 3,435 | 70.7% |
| abs t DEV >= 2 | 710 | 80.4% |
| abs t DEV >= 3 | 146 | 77.4% |

Rank correlation of t between DEV and CTX: 0.30. Of the 710 pairs with |t| >= 2 in DEV, 170 are
also |t| >= 2 in CTX with the same sign and 5 with the opposite sign. So the requirement "same
sign in a second decade" removes about one cell in five among those already significant in DEV,
not one in two. Independent sampling noise is not the main risk (5 against 170). The main risk is
anything the two samples share: survivor-only universes, the same construction, the same control.

**How unusual is each candidate among everything logged.** "As strong" means the same sign in both
samples with |t| at least the candidate's in each. The empirical null uses the robust spread of the
logged t's (1.10, 1.37) and the 61.2% agreement rate; "share of noise" is expected / observed.

| ID | t DEV | t CTX | combined z | logged pairs at least as strong, same sign (all / main loop) | opposite sign, as strong | expected by chance, N(0,1) | expected by chance, empirical null | estimated share of noise (all pairs / main loop) |
|---|---|---|---|---|---|---|---|---|
| E1 | +2.07 | +2.93 | 3.54 | 47 / 22 | 0 | 0.66 | 12.07 | 0.26 / 0.03 |
| E2 | +2.40 | +2.27 | 3.30 | 58 / 21 | 1 | 1.93 | 17.64 | 0.30 / 0.05 |
| E3 | +1.94 | +2.45 | 3.10 | 101 / 36 | 2 | 3.8 | 35.62 | 0.35 / 0.06 |
| A1 | -2.56 | -3.39 | 4.21 | 18 / 11 | 0 | 0.04 | 1.65 | 0.09 / 0.01 |
| A2 | -2.27 | -1.90 | 2.95 | 121 / 28 | 2 | 6.76 | 40.14 | 0.33 / 0.08 |
| A3 | -3.29 | -4.20 | 5.30 | 6 / 4 | 0 | 0.0 | 0.04 | 0.01 / 0.00 |
| A4 | -3.75 | -2.56 | 4.46 | 4 / 4 | 0 | 0.01 | 0.25 | 0.06 / 0.00 |
| A5 | -2.32 | -1.99 | 3.05 | 103 / 24 | 1 | 4.81 | 31.76 | 0.31 / 0.08 |
| A6 | -1.41 | -2.03 | 2.43 | 328 / 75 | 34 | 34.08 | 171.85 | 0.52 / 0.14 |
| A7 | -1.33 | -1.24 | 1.82 | 869 / 112 | 162 | 200.2 | 514.36 | 0.59 / 0.27 |
| A8 | -3.35 | -4.50 | 5.55 | 4 / 4 | 0 | 0.0 | 0.01 | 0.00 / 0.00 |
| A9 | -2.05 | +2.97 | signs disagree | | | | | 1 |
| A10 | -0.55 | -3.37 | 2.77 | 117 / 50 | 21 | 2.22 | 53.27 | 0.46 / 0.06 |
| A11 | -2.74 | -1.46 | 2.97 | 88 / 18 | 5 | 4.5 | 22.68 | 0.26 / 0.07 |

- **Expected number of the 14 that are noise** (sum of the shares, A9 counted as 1): 1.6 under a
  standard-normal null, 1.9 under the empirical null over the 596 main-loop pairs, 4.5 under the
  empirical null over all pairs. Honest range: **2 to 5**. This is on the day-weighted t's; part
  1 lowers most of them.
- **Clear a bar that accounts for the search** (Bonferroni 5% on the combined z): over the 596
  main-loop pairs the bar is 3.93: **A8, A3, A4, A1** clear it. Over all 10,149 pairs it is 4.57:
  **A8, A3**. Rescaled by the empirical null (combined z divided by 1.42) none clears either bar
  (A8 3.91, A3 3.73, A4 3.14, A1 2.96). On event-weighted t's A4 would not be in this group.
- **Most likely noise:** A7, A6, A10 (shares 0.46 to 0.59; 21 to 162 opposite-sign pairs just as
  extreme), and A9, whose prediction is contradicted by one of its two samples. E3, A2, A5, E2,
  E1, A11 sit at 0.26 to 0.35 on the all-pairs basis: each has 47 to 121 logged cells at least as
  good, which is what one in three being noise looks like.

## 3. Direction of the survivor bias

Measured: 15 of 1,752 DEV universe names stop trading inside 2011-2018H1, none of 1,282 in CTX.
The draft pre-registration reports 399 of 2,625 in validation. Two kinds of company are missing,
and they bias in different directions:

- **Failures** (delisted for cause, or collapsed and died later). Missing returns are very
  negative and concentrated after loser states. Signal means for loser states are biased up, more
  than the control. Each 0.1% of events ending in a for-cause delisting inside the window, at
  about -60% including the haircut, moves the event-weighted effect by about -6 bp.
- **Takeover targets** (the majority of disappearances among liquid names). Missing returns are
  one large up-gap on heavy volume, then a flat line at the deal price until delisting.

| ID | Bias in DEV / CTX | Validation, if the effect is real |
|---|---|---|
| A1 | Failures missing after 3-sigma falls: effect biased toward zero in both. Yet CTX, the more biased sample, is the more negative (-78 against -49 day-weighted), which the bias does not produce | **Stronger** (more negative). A weaker result would be evidence against it |
| A4 | Same direction as A1, smaller (a 1-sigma gap down is an ordinary bad day); the bias falls on signal and control almost alike | Slightly stronger. The CTX event-weighted +6 is not a bias signature (the day-weighted is -36 on the same names); it is the weighting |
| A7 | Failures concentrate here. Biased toward zero in DEV, to the wrong sign in CTX (event-weighted +73; +107 in 2004H2-2010) | **Stronger**, clearly negative. If it is near zero with the failures present, the idea is dead |
| A9 | The same, most extreme: CTX +138 is survivors bouncing. DEV's own second half is already zero (-1 event-weighted) | Negative if the DEV sign is real. A positive result means the DEV number was the artefact. Zero is what DEV 2015-18 predicts |
| E1 | Biased **up** in both. Takeover announcements are 3-sigma gaps on 3x volume that close near the high: they pass every E1 filter, and none is in DEV or CTX. In validation they enter with about zero drift (the name is pinned at the deal price), so each contributes roughly minus the universe's 10-bar return. Names that gapped up and later failed are also missing | **Weaker.** If deals are 15% to 30% of validation E1 events, +57 becomes roughly +40 to +48 with the earnings-type effect fully intact |
| E3 | Past crashers that survived: biased up, more in CTX (+100 against +42; +150 in 1998-2004H1) | Weaker, possibly zero |
| E2 | Deal announcements also make new highs on volume; older deals sit flat in the control | Slightly weaker |
| A2, A11 | Both sides are downtrend names. A bid for a beaten-down company is a 3-sigma up day below the 200-day (an A11 event), flat afterwards, while the control gains the failures | A11 **weaker** (toward zero or positive) for a mechanical reason; A2 little changed |
| A3 | Deal gaps that miss the E1 thresholds enter with zero drift | Slightly weaker |
| A10 | Announced targets keep a +1 skew for 60 bars and earn a cash-like return: they lag the universe in rising markets and lead it in falling ones | Not interpretable: the sign will follow the market's direction in 2018-2022 |
| A5, A6, A8 | No clear direction | Unchanged |

## 4. Economic meaning

**Avoid states inside a plain trend-following selection** (close above the 200-day average and
within 15% of the 252-bar high; 52% of DEV universe stock-days, 46% in CTX). Effect inside =
state-and-selection against the selection, same day, at the frozen horizon. "Worth per position"
= frequency x event-weighted effect: what skipping the state adds to the h-bar return of a
randomly chosen selection name.

| ID | h | DEV: share of trend-selection stock-days in the state | DEV: share of the state's events inside the selection | DEV effect inside, day bp (t) | DEV effect inside, event bp (t) | DEV worth per position (bp) | CTX share of selection days | CTX effect inside, event bp (t) |
|---|---|---|---|---|---|---|---|---|
| A1 | 20 | 0.18% | 27% | -32.3 (-1.30) | -44.4 (-2.13) | 0.08 | 0.15% | -43.4 (-1.97) |
| A2 | 10 | 0.00% | 0% | none | none | 0 | 0.00% | none |
| A3 | 5 | 4.07% | 55% | -7.0 (-1.81) | -6.3 (-2.14) | 0.26 | 3.94% | -7.5 (-2.44) |
| A4 | 20 | 1.04% | 37% | -21.5 (-2.04) | -17.7 (-1.94) | 0.18 | 0.78% | +1.7 (+0.14) |
| A5 | 5 | 2.45% | 34% | -13.3 (-1.26) | -9.2 (-1.21) | 0.23 | 4.17% | -7.3 (-1.14) |
| A6 | 20 | 0.61% | 68% | -12.4 (-0.87) | -5.9 (-0.71) | 0.04 | 0.65% | -2.7 (-0.29) |
| A7 | 60 | 0.00% | 0% | none | none | 0 | 0.00% | none |
| A8 | 5 | 14.36% | 60% | -3.5 (-1.45) | -2.5 (-1.58) | 0.36 | 15.04% | -9.4 (-5.77) |
| A9 | 20 | 0.14% | 1% | +18.1 (+0.43) | +16.0 (+0.41) | -0.02 | 0.08% | -36.7 (-0.88) |
| A10 | 60 | 16.95% | 74% | -0.5 (-0.01) | +1.9 (+0.06) | -0.32 | 14.84% | -14.7 (-0.84) |
| A11 | 5 | 0.00% | 0% | none | none | 0 | 0.00% | none |

- A2, A7 and A11 require a close below the 200-day average: a trend follower never holds them.
  A9 is 0.14% of his stock-days. These four "avoid" rules tell him nothing.
- Summed over the states that can occur and have the predicted sign there (A1, A3, A4, A5, A6,
  A8), avoiding all of them is worth about **1.1 bp per position** in DEV. A round trip costs 10
  to 20 bp.
- The only state with a material effect inside the selection is **A1**: -44 bp over 20 bars in
  both samples (t about -2). It is rare (one selection stock-day in 550), so it is an exit
  trigger for a held name, not a filter.
- A10 occupies 17% of the selection's stock-days and has no effect there (-0.5 bp).

**Enter states.** Costs: 10 bp round trip as in the guide; the protocol's table (10 bp a side for
$20-50M names) gives 14 bp on average in DEV because 40% of events are in those names.

| ID | Sample | Signals per month in the universe | Days with a signal | Event-weighted bp (t) | Net of 10 bp, day-weighted bp (t) | Net of 10 bp, event-weighted bp (t) | Net of protocol costs, event-weighted |
|---|---|---|---|---|---|---|---|
| E1 (10 bars) | DEV | 10.7 | 33% | +57.8 (+2.61) | +46.7 (+1.70) | +47.8 (+2.16) | +43.8 |
| E1 | CTX | 6.8 | 23% | +69.1 (+2.78) | +78.8 (+2.60) | +59.1 (+2.38) | +38.5 |
| E2 (5 bars, vs names near the high) | DEV | 38.7 | 58% | +11.1 (+1.37) | +10.9 (+1.25) | +1.1 (+0.14) | -3.2 |
| E2 | CTX | 39.0 | 65% | +14.6 (+2.29) | +11.4 (+1.21) | +4.6 (+0.72) | -16.9 |
| E3 (60 bars, a state: 16% of stock-days) | DEV | 3,088 | 94% | +36.2 (+1.34) | +31.8 (+1.48) | +26.2 (+0.97) | +22.2 |
| E3 | CTX | 1,454 | 100% | +80.9 (+2.34) | +89.9 (+2.20) | +70.9 (+2.05) | +49.8 |

- **E1** leaves about +45 bp per trade over 10 bars after costs, about 11 signals a month across
  roughly 970 names (about one a month on a 100-name watchlist). It is the only entry with a
  margin over costs. Without its best month DEV falls to +40.7 (t 1.83, from g30).
- **E2** does not pay a round trip: +1 bp net event-weighted in DEV, negative at protocol costs.
  Against the whole universe in CTX it is +4 bp (t 0.5). Even confirmed at its development size
  it is not a trade.
- **E3** has no effect inside 10 bars; it is a three-month tilt, outside the swing horizon.

## 5. Recommendation

**Test seven in one confirmatory family.** Horizon and sign as frozen.

| ID | h | Sign | Why it earns a look | Known weakness |
|---|---|---|---|---|
| E1 | 10 | + | Robust to weighting, plateau over 5-20 bars, stable across DEV halves, pays costs | Takeover gaps absent from development; expect dilution |
| A1 | 20 | - | Clears the search bar; -44 bp inside a trend selection in both samples | Event-weighted t only about -2; day-weighted h=20 is a peak |
| A2 | 10 | - | Event-weighted t -2.1 and -3.8; grows smoothly with horizon | Irrelevant to trend followers |
| A3 | 5 | - | Strongest joint evidence with A8 | One-session effect of 6-9 bp |
| A4 | 20 | - | Best day-weighted t in DEV | Event-weighted nothing in CTX and in DEV 2015-18; 58% of A1 is inside it |
| A5 | 5 | - | Published mechanism; steady non-overlapping t (-1.85, -1.73) | One-session effect; zero in DEV 2015-18 |
| A8 | 5 | - | Strongest joint evidence | 2.5 to 3.7 bp event-weighted in DEV |

**Criterion, fixed before the run:**

1. *Primary:* day-weighted mean spread at the frozen h, Newey-West 2h lags, one-sided p in the
   predicted direction from Student's t with df = floor(days with a spread / 2h) - 1 (112, 55,
   27 for h = 5, 10, 20 when there is a signal every day; fewer for E1, which fires on about a
   third of days), Holm at 5% across the seven. First bar: p <= 0.00714, t >= 2.49 (h=5), 2.53
   (h=10), 2.62 (h=20); then 0.05/6, 0.05/5 and so on.
2. *Also required for "confirmed":* event-weighted estimate (sum n_t d_t / sum n_t, date-clustered,
   same lags) with the predicted sign and one-sided p <= 0.10 (|t| >= 1.28), uncorrected.
3. *Label, not a test:* "material for a long-only trend follower" only if the event-weighted
   effect inside the trend selection is <= -20 bp (avoid) or, for E1, the event-weighted effect
   net of protocol costs is >= +20 bp. On development data only A1 and E1 would get the label.
4. *A3 and A5:* also report bars 2-5 (signal delayed one bar, h=4). Predicted sign there is
   needed for the wording "avoid for a week"; otherwise the wording is "not at the next open".
5. *One global test, outside Holm:* mean of the sign-adjusted t's of the six avoid states, null
   distribution from a joint month-block bootstrap (recentred), one-sided 5%. It asks whether
   the avoid family as a whole exists, with far more power than any single test.
6. *E1 diagnostic, declared now, descriptive only:* E1 excluding names that stop trading within
   126 bars of the event. It cannot be traded; it separates dilution by deals from failure.
7. Verdict words as drafted. "Right sign, not significant" is the expected outcome for a true
   effect of development size in most of these tests and must not be read as refutation.

**Power, so the result is read correctly.** Validation has 1,134 days against DEV's 1,894:
standard errors about 1.29 times larger. If each development estimate were the exact truth, the
chance of clearing the first Holm bar is A4 0.67, A8 0.56, A3 0.54, A1 0.32, A5 0.26, A2 0.24,
E1 0.20: 2.8 expected confirmations of 7. With all 14 in the family it is 3.1 of 14. If the truth
is half the development estimate (the usual shrinkage after selection), 0.6 either way.

**Drop now** (no validation look):

| ID | Reason |
|---|---|
| A7 | t -1.3 and -1.2; event-weighted +73 in CTX; 869 logged cells as good; never held by a trend follower; 18 independent windows in validation |
| A10 | Nothing in DEV (t -0.55; -0.5 bp inside the trend selection); the CTX effect is 1998-2004 only; contaminated by deal stocks in validation |
| A6 | t -1.4 / -2.0 day-weighted, -0.8 / -1.2 event-weighted; positive for the first 5 bars in CTX; nothing inside the trend selection, where 68% of its events are |
| A11 | 44% inside A2 with the same control; DEV event-weighted t -1.1; one-session effect that dies with a one-bar delay; biased toward zero in validation by takeover bids |
| E2 | +1 bp after costs event-weighted in DEV, negative at protocol costs; a confirmation would not make it tradable |
| E3 | Not a swing horizon; DEV event-weighted t 1.3, non-overlapping 1.2 on 29 windows; overlaps A1/A9/A7 with the opposite prediction; the bias pushes it up |
| A9 | Not a hypothesis: its two samples contradict each other |

A9 and E3 may be **reported as diagnostics of survivor bias**, declared as such in advance,
outside the confirmatory family and without a verdict word.

**Risk-engine claims: criteria to fix in advance.** The drafted R1 and R5 are point comparisons
without a margin; a difference of 0.001 would pass.

| Claim | Pass criterion |
|---|---|
| Volatility forecast ranking (ATR14/close against EWMA20 and Yang-Zhang20, constants frozen from CTX) | At h=10: the daily cross-sectional mean of (competitor QLIKE loss - ATR loss) has Newey-West t (20 lags) >= 2.33 against each competitor, and ATR's QLIKE is at least 5% lower (DEV: 17% and 14%). At h=5 and 20: lower. Same sign in at least 3 of the 4 blocks 2018H2-2019, 2020, 2021, 2022 |
| The constant | QLIKE-optimal scale refitted on validation at h=10 lies in 0.68-0.83 (0.757 +/- 10%) |
| Range calibration | Pooled 5% and 95% quantiles inside the drafted bands; coverage of [-1.56, +1.48] between 87% and 93% pooled, between 84% and 94% in each tercile of forecast volatility, and between 85% and 95% in at least 3 of the 4 blocks (2020 is expected to fail and should be shown) |
| Stop-out table | Largest absolute difference over the 18 cells <= 4 points (as drafted); share of stop exits that gap through between 8% and 20%; share of 2-ATR, 10-bar trades worse than -1.5R no more than twice the DEV value. Report the table with the -100% delisting stress beside it |
| Exits (R5) | Difference in net bp per bar, same random entries, clustered by entry date: one-sided t >= 1.645 for each of the two comparisons; otherwise "not shown" |

The development tables for all of these come from survivors. Validation is the first time the
delisting branch of `engine.fwd_ret_open` and `trades._sim` carries weight (15 names in DEV, 399
in validation); it should be exercised on a synthetic delisted series before the run.

## Defects to fix before the validation run

1. `research/confirm/run_val.py` lines 50-77 and `docs/03_preregistration_val.md` lines 48-49
   ("does not change the verdict"): the verdict uses the day-weighted statistic alone. On development data
   that statistic confirms A4 and A7 in CTX while the average flagged stock-day shows +6 and +73
   bp. Add the event-weighted condition (criterion 2).
2. `research/confirm/prereg_val.py` lines 7-22: 14 hypotheses in the Holm family, including A9
   (signed against CTX), A10 (DEV t -0.55), A7 and A6. Raises the first bar to t 2.69 and leaves
   about 3 expected confirmations even if everything is true. Cut to the seven above.
3. `research/confirm/run_val.py` line 64: `norm_sf(sgn * t)`. Normal p-values with 2h lags; at
   h=20 there are about 28 independent windows in validation (first bar 2.62, not 2.45), at h=60
   about 9 (3.12). Use Student's t with the stated df, or the bootstrap p.
4. `research/swinglab/candidates.py` lines 133, 136, 145 (h=5 for A3, A5, A11): the claim "avoid
   for five bars" is not what the data show. The next session alone holds 60% to 71% of A3's
   effect, 61% to all of A11's, and all of A5's in CTX (40% to 46% in DEV). Register the bars
   2-5 endpoint or reword the claim before the run.
5. `docs/03_preregistration_val.md` lines 55 and 59, `run_val.py` lines 92 and 139 (`R1_pass`,
   `R5_pass`): pass on any difference, however small. Add the margins and tests above.
6. E1 (`candidates.py` line 52): development samples contain no takeover announcement. State in
   the pre-registration how a diluted validation result is read, and add diagnostic 6.

Smaller points:

- `candidates.py` lines 105-116: the skew is `sma((r - sma(r,60))^3, 60) / stdev(r,60)^3`, each
  day's deviation taken from that day's trailing mean, spanning 119 bars, with missing returns
  set to 0. The Pine line in SPEC says "skewness of the last 60 daily log returns", which is a
  different number. Matters only if E3 or A10 is kept.
- `engine.spread_series`: the control includes the signal names. For states covering 12% to 16%
  of the universe (A8, A10, E3) the effect is understated by that fraction.
- `engine.nw_mean` drops days without a signal and treats the remaining days as consecutive.
  Harmless here (bootstrap agrees), but lags are then not calendar lags for sparse signals (E1
  has a signal on 33% of days).
- `g30_attack.py` line 78: the liquidity split compares each half with the whole universe, not
  with names of the same liquidity.
- `g30_attack.py` line 13 states that a candidate goes forward only if it keeps its sign through
  every attack. A3 and A11 kept the sign under a one-bar delay and lost 73% and 71% of the
  effect; the rule let that through.
- The protocol (section 5) charges 10 bp a side for $20-50M names; the guide and g30 use 10 bp a
  round trip for all. 40% of DEV entry events are in the dearer bucket.

## How to rerun

```
cd swing-lab
python -m research.experiments.audit_stats registry   # part 2, under a second
python -m research.experiments.audit_stats DEV        # parts 1 and 4, about 20 s
python -m research.experiments.audit_stats CTX        # about 12 s
python -m research.experiments.audit_stats tables     # prints everything above
```

Bootstrap seed 20261111. Sub-period splits: DEV at 2015-01-01, CTX at 2004-07-01.
