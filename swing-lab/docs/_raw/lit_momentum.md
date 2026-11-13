# Momentum, trend, 52-week high, stops: what the evidence supports for a long-only swing trader of US stocks

Research date: **2026-11-11** by the system clock (the project brief dates the day as 2026-11-10). Every URL below was accessed on 2026-11-11.
Scope: signals built on weeks-to-months of price history, used by a discretionary long-only trader who holds 5–10 US stocks for days to weeks and acts on bar-close alerts from TradingView (Pine v6, Premium).

## 0. How to read this file

| Tag | Meaning |
|---|---|
| [DOC] | Read today in a primary/official source. Includes **my own calculations on Ken French Data Library files downloaded today** (marked "own calc.") and the authors' own web page for a paper |
| [COMPILE] | Confirmed today with TradingView's compiler through `tools/pine_compile.py` (compile only, never runtime). 2 of 15 calls used |
| [PAPER] | Read today in the paper itself (PDF text) or in its abstract on the journal/RePEc/repository record |
| [SECONDARY] | Third-party page, or a search-tool summary of a page I could not open |
| [MEMORY] | Recalled from training, **not verified today**. Do not rely on it |

"Inference" marks a conclusion I drew; it is not a sourced fact. Returns are **percent per month** unless stated. t-statistics in parentheses.

Sources are listed with IDs (S1…S58) in section 10. Blocked today: SSRN (HTTP 403), Alpha Architect (403), the UPenn copy of Wilcox & Crittenden (TLS failure / HTTP 503), MIT DSpace PDFs (429). What that left unverified is in section 11.

---

## 1. Findings that change design decisions

| # | Finding | Tag / source |
|---|---|---|
| 1 | **Since 2000 the long-only large-cap momentum premium is statistically zero.** Fama–French "Big, high prior return" portfolio minus the market: 0.33 (t=5.1) in 1927–1999, **0.05 (t=0.39) in 2000–2026-09**, 0.04 (t=0.32) in 2010–2026-09. It beat the market in 15 of 27 calendar years. | [DOC] own calc., S1 |
| 2 | What is left in large caps is on the **loser side**: 2000–2026 CAGR was 9.0% for big winners, 9.9% for the big middle group, 8.5% for the market and **6.2% for big losers**. Winners minus middle = −0.05 (t=−0.33). | [DOC] own calc., S1 |
| 3 | The long-short factor also shrank: UMD 0.77 (t=5.0) in 1927–1999 → 0.21 (t=0.73) in 2000–2026. The post-2000 95% interval is wide (roughly −0.35 to +0.77), so "decayed by about 70%" is the point estimate, not a proven zero. | [DOC] own calc., S1 |
| 4 | Momentum depends on the market state, and the dependence survived out of sample: UMD after a non-negative 24-month market return 0.86 (t=7.8) vs −0.78 after a negative one (1929–2026); in 2000–2026 0.51 vs −1.05. For the long-only large-cap leg the gap is small and insignificant (0.14 vs −0.26 on a 12-month state, 2000–2026). | [DOC] own calc., S1; original claim [SECONDARY] S21 |
| 5 | Momentum crashes are **losers rallying, not winners falling**: "the crash performance is mostly attributable to the short side". A long-only holder sees relative underperformance in rebounds, not a collapse. Worst months of big-winners-minus-market since 1990: −9.5 (Jan 2001), −7.8 (Apr 2009), −7.8 (Nov 2002), −6.7 (Jan 2023), all after a negative 12-month market return and with the market up 4–10% that month. | [PAPER] S4; [DOC] own calc., S1 |
| 6 | Volatility scaling (Barroso & Santa-Clara) replicates and held up after publication **for the long-short factor** (Sharpe 0.14 → 0.41 in 2000–2026) but does **nothing for a long-only winner book** (0.59 → 0.63 full sample; 0.84 → 0.82 in 2010–2026). It cuts drawdown, not risk-adjusted return. | [DOC] own calc., S1; [PAPER] S5, S36 |
| 7 | Nearness to the 52-week high is mostly a short-side effect too: in George & Hwang's Table V the winner dummy is +0.16 (t=3.1) and the loser dummy −0.48 (t=−4.1). | [PAPER] S6 |
| 8 | At the trader's own horizon (one month and less) the unconditional effect is **reversal**, not continuation. Continuation at one month is documented only for **high-turnover** stocks, it is strongest in megacaps, and "generates all its profits on the long side" (Medhat & Schmeling: +0.42, t=4.9, in the largest 500 stocks, 1963–2018). This is the one result in the topic that matches both the horizon and the universe; it has no post-publication record yet. | [PAPER] S33, S6 |
| 9 | Tight stop-losses on individual US stocks lower returns ("tight stop-loss strategies tend to underperform the buy-and-hold policy due to excessive trading costs"); on the S&P 500 index "a change of trend is the best stop loss". The positive stop-loss results are either index-level with bonds as the alternative (Kaminski & Lo) or gross of costs with idealised fills (Han, Zhou & Zhu). | [PAPER] S16, S48, S15; [SECONDARY] S17 |
| 10 | Breakout trend-following on stocks earns its money from a small tail: "Less than 7% of trades generate the majority of cumulative profits", and the original author states the effect is inversely related to market capitalisation. A 5–10-name book cannot expect to hold the tail. | [DOC] S50; [SECONDARY] S49 |
| 11 | Trading costs are not this trader's binding constraint (project assumption 5 bp per side in liquid names). The binding constraint is **noise**: with 8 names, a premium of 0.3%/month would need about 30 years to show at t=2 (section 5). | Inference from S1 and project protocol |
| 12 | Post-publication decay is the base rate: across 97 predictors "Portfolio returns are 26% lower out-of-sample and 58% lower post-publication"; net of costs and publication effects "the average anomaly's expected return is a measly 4 bps per month". | [PAPER] S24, S25 |

---

## 2. First-hand evidence: Ken French Data Library, CRSP through September 2026

Files downloaded today from `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/` (each headed "created using the 202609 CRSP database"): `F-F_Momentum_Factor`, `6_Portfolios_ME_Prior_12_2`, `10_Portfolios_Prior_12_2`, `25_Portfolios_ME_Prior_12_2`, `F-F_Research_Data_Factors`, daily versions of the first three and of the factors, `49_Industry_Portfolios`, `12_Industry_Portfolios`. Definitions quoted from the file headers: prior return "is measured from month -12 to - 2"; "Big means a firm is above the median market cap on the NYSE"; high = "above the 70th NYSE percentile", low = "below the 30th NYSE percentile". [DOC] S1

All numbers in this section are **[DOC] own calc.** Value-weighted portfolios, monthly rebalancing, gross of costs, CRSP universe (survivorship-free). "Mkt" = Mkt-RF + RF. Not beta-adjusted.

### 2.1 Mean monthly return, % (t-statistic)

| Series | 1927–1999 | 1963-07–1999 | 2000–2026-09 | 2010–2026-09 |
|---|---|---|---|---|
| UMD factor | 0.77 (5.01) | 0.89 (5.53) | 0.21 (0.73) | 0.28 (1.08) |
| Decile 10 − decile 1 | 1.38 (5.52) | 1.70 (6.47) | 0.50 (0.97) | 0.65 (1.15) |
| Small high − small low | 0.89 (5.90) | 1.21 (8.08) | 0.32 (1.13) | 0.47 (1.99) |
| Big high − big low | 0.64 (3.76) | 0.58 (2.97) | 0.09 (0.30) | 0.09 (0.28) |
| Largest NYSE quintile, high − low (5×5 sort) | 0.71 (3.24) | 0.78 (3.17) | 0.24 (0.59) | 0.30 (0.65) |
| Smallest NYSE quintile, high − low | 1.04 (5.03) | 1.64 (9.68) | 0.41 (1.24) | 0.42 (1.40) |
| **Long-only views** | | | | |
| Big high − Mkt | 0.33 (5.08) | 0.33 (3.90) | **0.05 (0.39)** | 0.04 (0.32) |
| Largest quintile high − Mkt | 0.34 (3.74) | 0.37 (3.17) | 0.08 (0.49) | 0.13 (0.73) |
| Big high − big middle | 0.40 (4.26) | 0.49 (4.13) | −0.05 (−0.33) | −0.01 (−0.04) |
| Big middle − big low | 0.24 (2.25) | 0.09 (0.73) | 0.15 (0.71) | 0.10 (0.45) |
| Decile 10 (value-weighted) − Mkt | 0.66 (5.86) | 0.77 (5.25) | 0.29 (1.26) | 0.37 (1.36) |
| Decile 10 (equal-weighted) − Mkt | 0.93 (7.02) | 0.96 (5.45) | 0.33 (1.38) | 0.02 (0.07) |
| Small high − Mkt | 0.69 (5.77) | 0.70 (4.80) | 0.37 (1.88) | 0.14 (0.64) |
| Mkt − RF (for scale) | 0.72 (3.80) | 0.58 (2.76) | 0.62 (2.47) | 1.08 (3.57) |

Tail risk of the long-short series, 1927–2026: UMD worst month −52.6%, maximum drawdown −78%; decile 10 − decile 1 worst month −77.7%, maximum drawdown −96%. In 2000–2026: UMD worst month −34.4% (April 2009), drawdown −58%. The long-only relative series (big high − Mkt) had a worst month of −9.5% and a relative drawdown of −22% in 2000–2026.

Compound annual growth 2000-01 to 2026-09: Mkt 8.48%, big high 9.00%, big middle 9.94%, **big low 6.18%**, decile 10 10.86%. From 2010-01: Mkt 14.15%, big high 14.48%, big middle 14.83%, big low 12.26%, decile 10 17.79%.

Recent months in the file: UMD +9.51 (Apr 2026), +1.39, +4.62, **−12.21 (Jul 2026), −5.60 (Aug 2026)**, +6.70 (Sep 2026). The July–August 2026 loss came with a +22% trailing 12-month market return, so the bear-state filter in 2.2 would not have flagged it.

### 2.2 Market state, known at the end of month t−1; mean return in month t, % (t)

| Sample | State variable | Series | State "up" | State "down" |
|---|---|---|---|---|
| 1929–2026 | Market return over prior 36 months ≥ 0 | UMD | 0.77 (6.47), n=986 | −0.44 (−0.72), n=180 |
| 1929–2026 | prior 24 months ≥ 0 | UMD | 0.86 (7.79), n=982 | −0.78 (−1.25), n=191 |
| 1929–2026 | prior 12 months ≥ 0 | UMD | 0.83 (7.76), n=882 | −0.11 (−0.24), n=291 |
| 1929–2026 | Market index ≥ its 10-month average | UMD | 0.74 (6.68), n=852 | 0.21 (0.52), n=321 |
| 2000–2026 | prior 24 months ≥ 0 | UMD | 0.51 (1.91), n=259 | −1.05 (−1.10), n=62 |
| 2000–2026 | prior 12 months ≥ 0 | UMD | 0.55 (2.32), n=248 | −0.96 (−1.02), n=73 |
| 1929–2026 | prior 12 months ≥ 0 | Big high − Mkt | 0.33 (5.55) | −0.05 (−0.33) |
| 2000–2026 | prior 12 months ≥ 0 | Big high − Mkt | 0.14 (1.19) | −0.26 (−0.78) |
| 2010–2026 | prior 12 months ≥ 0 | Big high − Mkt | 0.10 (0.80), n=179 | −0.47 (−1.12), n=22 |
| 1929–2026 | prior 12 months ≥ 0 | Decile 10 − Mkt | 0.63 (5.47) | 0.20 (0.88) |
| 2000–2026 | prior 12 months ≥ 0 | Decile 10 − Mkt | 0.36 (1.35) | 0.05 (0.11) |
| 1929–2026 | Index ≥ 10-month average | Mkt − RF | 0.75 (5.19) | 0.42 (0.99) |
| 2000–2026 | Index ≥ 10-month average | Mkt − RF | 0.78 (3.53) | 0.17 (0.22) |
| **2010–2026** | Index ≥ 10-month average | Mkt − RF | 0.82 (3.01), n=167 | **2.36 (2.01), n=34** |
| 2010–2026 | prior 12 months ≥ 0 | Mkt − RF | 0.92 (3.04), n=179 | 2.42 (1.91), n=22 |

Reading: the state variable separates long-short momentum returns in every sample. It does **not** reliably separate market returns after 2010: the months below the 10-month average were followed by higher, not lower, market returns (V-shaped recoveries). A market trend filter is a drawdown control with a measurable cost in the last 16 years, not a return enhancer.

### 2.3 Volatility scaling

Method as in Barroso & Santa-Clara: realised variance of the previous 126 daily returns, scaled to a monthly figure, exposure = target / forecast, target 12% a year. The scaling uses only data up to the end of month t−1.

| Series | Sample | Sharpe raw → scaled | Worst month raw → scaled | Max drawdown raw → scaled | Skew raw → scaled |
|---|---|---|---|---|---|
| UMD | 1927-07–2026-09 | 0.45 → 0.87 | −52.6 → −29.0 | −78% → −43% | −3.01 → −0.41 |
| UMD | 1927–1999 | 0.58 → 1.01 | | | |
| UMD | 2000–2026 | 0.14 → 0.41 (t 0.73 → 2.12) | −34.4 → −20.6 | −58% → −25% | −1.43 → −0.32 |
| UMD | 2010–2026 | 0.26 → 0.47 | −16.2 → −9.7 | −25% → −19% | |
| Decile 10 − 1 | 1927-07–2026-09 | 0.49 → 0.92 | −77.7 → −24.2 | −96% → −44% | −2.09 → −0.29 |
| Decile 10 − 1 | 2000–2026 | 0.19 → 0.42 | −45.2 → −13.6 | −81% → −28% | |
| **Long-only, no leverage** (exposure = min(1, 15% / 63-day realised vol)) | | | | | |
| Big high − RF | 1927-07–2026-09 | 0.59 → 0.63 | −26.3 → −24.0 | −79% → −63% | |
| Big high − RF | 2000–2026 | 0.50 → 0.56 | −15.1 → −10.0 | −49% → −35% | |
| Big high − RF | 2010–2026 | 0.84 → 0.82 | −11.4 → −9.7 | −25% → −19% | |
| Mkt − RF | 2000–2026 | 0.48 → 0.52 | −17.2 → −12.6 | −54% → −41% | |
| Mkt − RF | 2010–2026 | 0.87 → 0.83 | | −25% → −20% | |

Reading: the published result (Sharpe 0.53 → 0.97 for 1927–2011, [SECONDARY] S5b) is reproduced on the extended sample and survives after 2011. The gain comes from shrinking exposure before loser rallies, which is a short-leg event. For a long-only book the Sharpe ratio is unchanged within noise; drawdown falls by about a quarter at the price of roughly 15% lower average exposure.

### 2.4 Industry momentum (equal weight across industries, one-month hold, no costs)

| Universe, formation | Long-short | 1928–1999 | 2000–2026 | 2010–2026 |
|---|---|---|---|---|
| 12 industries, 1 month, top 3 − bottom 3 | | 0.77 (6.36) | 0.27 (1.08) | 0.41 (1.34) |
| 12 industries, 1 month, top 3 − average of all | long-only view | 0.38 (5.51) | 0.11 (0.81) | 0.21 (1.18) |
| 12 industries, 6 months, top 3 − bottom 3 | | 0.45 (3.72) | 0.27 (1.04) | 0.16 (0.51) |
| 12 industries, 12 months, top 3 − bottom 3 | | 0.64 (5.04) | 0.35 (1.31) | 0.42 (1.38) |
| 12 industries, 12 months, top 3 − average | long-only view | 0.37 (5.04) | 0.19 (1.28) | 0.24 (1.33) |
| 49 industries, 12 months, top 5 − bottom 5 | | 0.97 (4.30) | 0.72 (1.79) | 0.87 (2.07) |
| 49 industries, 12 months, top 5 − average | long-only view | 0.53 (4.94) | 0.37 (1.57) | 0.23 (0.94) |
| 49 industries, 6 months, top 5 − average | long-only view | 0.24 (2.38) | 0.35 (1.55) | 0.24 (1.02) |
| 49 industries, 1 month, top 5 − average | long-only view | 0.16 (1.55) | 0.19 (0.96) | 0.14 (0.60) |

Reading: point estimates stay positive after 2000 (0.1–0.4 a month for the long-only tilt). No long-only cell reaches t = 2 after 2000; among the long-short cells only one does (49 industries, 12 months, 2010–2026: 2.07), which is what one expects by chance from this many cells. The one-month effect on broad sectors, the original headline of Moskowitz & Grinblatt (published 1999), fell from 0.77 to 0.27.

---

## 3. Findings by topic

Column key: **Size** = effect, universe, period. **After** = replication, post-publication, recent period. **Costs** = survives realistic costs in liquid US stocks? **Why / who** = mechanism and who is on the other side. **Pine** = computable at bar close from TradingView data? (formulas in section 7).

### 3.1 Cross-sectional momentum

| Item | Content | Tag |
|---|---|---|
| Claim | Stocks ranked high on past 3–12-month return outperform those ranked low over the next 3–12 months | [PAPER] S2 |
| Size | 12-month formation / 3-month hold: 1.31 per month, 1.49 with a one-week skip; 6-month formation: "about 1% per month regardless of the holding period"; 6/6 strategy: "compounded excess return of 12.01% per year". Sample 1965–1989, NYSE and AMEX stocks, equally weighted decile portfolios | [PAPER] S2 |
| Decay | "With the exception of the first month, this portfolio realizes positive returns in each of the 12 months after the formation date"; "half of their excess returns in the year following the portfolio formation date dissipate within the following 2 years" | [PAPER] S2 |
| Where | "the subsample with the largest firms generates lower abnormal returns than the other two subsamples". Hong, Lim & Stein: "once one moves past the very smallest stocks, the profitability of momentum strategies declines sharply with firm size" and is larger with low analyst coverage. Fama & French 2012: "spreads in average momentum returns also decrease from smaller to bigger stocks". **Contested:** Israel & Moskowitz: "Momentum profits, however, exhibit no reliable relation with size" | [PAPER] S2, S32, S39, S20 |
| After | 1990s out-of-sample: "momentum profits have continued in the 1990s" (J&T 2001). After 2000: section 2.1, premium down ~70% in the factor and to about zero in the long-only large-cap leg | [PAPER] S3; [DOC] own calc. S1 |
| Long vs short | Israel & Moskowitz (86 years of US data): long positions make up "half of momentum profits". In French data after 2000 big winners − big middle is −0.05 and big middle − big losers +0.15, so the remaining large-cap spread is all on the loser side | [PAPER] S20; [DOC] own calc. S1 |
| Costs | J&T: turnover 84.8% semi-annually; after "a 0.5% one-way transaction cost" 9.29% a year. Novy-Marx & Velikov (1963–2013, value-weighted deciles): gross 1.33, turnover 34.5% a month per side, cost 0.65, **net 0.68 (t=2.45)**; with a 10%/20% buy/hold spread net 0.85 (t=3.35). Lesmond et al.: "an illusion of profit opportunity when, in fact, none exists". Patton & Weller: all-in costs for typical mutual funds "7.2%–7.6% per year, which eliminates most profits accruing to momentum", "About half of this cost is due to mutual funds' inability to short" | [PAPER] S2, S18, S23, S26 |
| Why / who | Under-reaction to firm-specific news (J&T: "consistent with delayed price reactions to firm-specific information"; Hong, Lim & Stein: "firm-specific information, especially negative information, diffuses only gradually"). Other side: holders anchored on old prices who sell winners early and hold losers; Remorov's survey: "most institutional investors expect to exhibit highly contrarian reactions to past returns" while individual investors are "on average, extrapolative". Alternative reading: momentum "is not a distinct risk factor—it times other factors" (Ehsani & Linnainmaa) | [PAPER] S2, S32, S16, S35 |
| Pine | Own 12-1 return and return relative to SPY: yes [COMPILE]. A true cross-sectional rank over hundreds of stocks cannot be computed inside one chart script (40 `request.*` calls on Premium per the sibling report `pine_requests.md`); it needs the Pine Screener or thresholds calibrated offline | [COMPILE] m1; sibling doc not re-verified by me |
| **Verdict** | **CONTEXT.** Use as an exclusion filter (do not buy 12-1 losers); do not treat "is a 12-1 winner" as an edge in large caps | |

### 3.2 Momentum crashes and market states

| Item | Content | Tag |
|---|---|---|
| Claim | Momentum has rare, clustered, large losses; "They occur in panic states, following market declines and when market volatility is high, and are contemporaneous with market rebounds" | [PAPER] S4 |
| Size | Decile winners-minus-losers (Table 2, 1927–2013): August 1932 −74.36% (market +36.49% that month, −67.77% over the prior two years); July 1932 −60.98%; January 2001 −49.19% (prior two-year market return **+10.74%**, so not every crash follows a bear market); April 2009 −45.52%; March 2009 −42.28%. "over the three-month period from March to May of 2009, the past-loser decile rose by 163%, while the decile portfolio of past winners gained only 8%" | [PAPER] S4 |
| Which leg | "the crash performance is mostly attributable to the short side"; losers "are 'crashing up' rather than down" | [PAPER] S4 |
| State variable | Bear indicator = 1 "if the cumulative CRSP VW index return in the past 24 months is negative"; volatility = variance of daily market returns over the preceding 126 days | [PAPER] S4 |
| Dynamic strategy | "approximately doubles the alpha and Sharpe ratio of a static momentum strategy" | [PAPER] S4 |
| Market states | Cooper, Gutierrez & Hameed: 1929–1995 mean momentum profit 0.93 after a non-negative three-year market return, −0.37 after a negative one. My replication through 2026: 0.77 vs −0.44 (36 months) | [SECONDARY] S21; [DOC] own calc. S1 |
| Liquidity states | "momentum profits are markedly larger in liquid market states"; "momentum strategies have been unconditionally unprofitable in the United States, in Japan, and in the Eurozone countries in the last decade" (paper published 2016) | [PAPER] S34 |
| After | Bear-state effect held in 2000–2026 in sign (section 2.2). It did not flag July–August 2026 | [DOC] own calc. S1 |
| For a long-only trader | Winners do not crash in absolute terms in these episodes; they lag a rebounding market by 5–10% in the worst months. The practical rule is "after a bear market, do not expect winners to lead the rebound" | Inference from S4 and S1 |
| Pine | SPY 12- and 24-month return, 126-day realised volatility of SPY: yes | [COMPILE] m1 |
| **Verdict** | **CONTEXT** (risk input: switch off momentum-style entries when SPY's 12- or 24-month return is negative). Expected benefit for long-only is small and not significant; treat it as tail control | |

### 3.3 Volatility scaling

| Item | Content | Tag |
|---|---|---|
| Claim | "the risk of momentum is highly variable over time and predictable. Managing this risk virtually eliminates crashes and nearly doubles the Sharpe ratio" | [PAPER] S5 |
| Size | Sharpe 0.53 → 0.97, 1927–2011 | [SECONDARY] S5b (number not read in the paper) |
| After | Reproduced and extended in section 2.3: 0.45 → 0.87 full sample; 0.14 → 0.41 after 2000 | [DOC] own calc. S1 |
| Contested | Moreira & Muir generalise it to other factors (abstract not available on RePEc today). Cederburg et al., 103 equity strategies: "Volatility-managed portfolios do not systematically outperform their corresponding unmanaged portfolios in direct comparisons"; out-of-sample versions "generally earn lower certainty equivalent returns and Sharpe ratios" | [PAPER] S36; Moreira–Muir [MEMORY] |
| Long-only | No Sharpe gain for big winners or for the market (section 2.3). Drawdown reduction of about a quarter | [DOC] own calc. S1 |
| Why / who | Volatility clusters and momentum's worst losses come after high volatility; the short leg carries option-like exposure to a rebound (S4). Not an information edge | [PAPER] S4 |
| Pine | `ta.stdev` of log returns × √252; exposure = min(1, target / vol): yes | [COMPILE] m1 |
| **Verdict** | **CONTEXT** for position sizing and for a "high-volatility state" warning. **REJECT** as a source of return for a long-only book | |

### 3.4 52-week-high proximity

| Item | Content | Tag |
|---|---|---|
| Claim | "Nearness to the 52-week high dominates and improves upon the forecasting power of past returns (both individual and industry returns) for future returns. Future returns forecast using the 52-week high do not reverse in the long run." | [PAPER] S6 |
| Definition | "ratio of price level in month t – j to the maximum price achieved in months t – j – 12 to t – j"; winners/losers = top/bottom 30%; 6-month hold; equal-weighted; July 1963–December 2001 | [PAPER] S6 |
| Size | Table I (all months): J&T momentum 0.48, industry momentum 0.45, 52-week high 0.45. Table II (January excluded): 1.07 vs 1.23. Table V regression, controlling for the other two: 52-week high winner − loser 0.65 (t=4.08) vs J&T 0.38 vs industry 0.25; excluding January 1.06 vs 0.46 vs 0.22 | [PAPER] S6 |
| Which leg | Table V, raw, January included: **winner dummy +0.16 (t=3.06); loser dummy −0.48 (t=−4.07)**. Three quarters of the spread is "far from the high underperforms" | [PAPER] S6 |
| One-month reversal in the same table | Coefficient on last month's return −6.50 (t=−14.9). The regressions skip a month "To abstract from bid-ask bounce" | [PAPER] S6 |
| Extensions | Recency: stocks whose 52-week high is recent beat those whose high is distant; top vs bottom decile on recency 0.70 a month; the nearness strategy "is about twice as large for stocks with recent 52-week high price". Risk-based reading: price-to-high captured by the q-factor model, "consistent with the investment CAPM" | [PAPER] S37, S38 |
| After | No post-2001 US large-cap replication read today. The French data show the related 12-2 sort lost its long-side premium after 2000 | Gap; [DOC] own calc. S1 for the related sort |
| Costs | Not reported in S6. Turnover of a price-level signal is lower than a return-rank signal (inference) | |
| Why / who | Anchoring: "traders use the 52-week high as a reference point"; "traders are reluctant to bid the price of the stock higher even if the information warrants it". Other side: holders who sell into the old high (the paper cites Finnish evidence that investors are "much more likely to sell ... a stock whose price is near a historical high") | [PAPER] S6 |
| Pine | `close / ta.highest(high, 252)`; bars since the high via `ta.highestbars`: yes. Whether the paper used closes or intraday highs is not stated in the passages I read; test both | [COMPILE] m1 |
| **Verdict** | **CANDIDATE**, in two forms: (a) exclusion of names far below the high; (b) recency of the high as a ranking input. Expect a small long-side effect | |

### 3.5 Residual (idiosyncratic) momentum

| Item | Content | Tag |
|---|---|---|
| Claim | Ranking on residual returns (after removing Fama–French factor exposure) gives "risk-adjusted profits that are about twice as large as those associated with total return momentum; is more consistent over time; and less concentrated in the extremes of the cross-section of stocks" | [PAPER] S11 |
| Follow-up | "crash risk, and investor overconfidence and overreaction linked to market states and dynamics cannot explain idiosyncratic momentum profits"; "robust returns across a range of developed and emerging markets" | [PAPER] S12 |
| Size | Monthly Sharpe 0.48 vs 0.25 for conventional momentum, US 1925–2015; "weakens after the early 2000s"; absorbs part of the 2009 crash | [SECONDARY] S12b |
| Costs | Listed among mid-turnover anomalies by Novy-Marx & Velikov (appears in their table headings); row not read | [PAPER] S18 (partial) |
| Why / who | Under-reaction to firm-specific news ("long-term return dynamics ... support the underreaction hypothesis") | [PAPER] S12 |
| Pine | Three-factor residuals are not available. A one-factor version (rolling beta to SPY, residual return scaled by residual volatility) compiles; adding a sector ETF as a second factor is possible | [COMPILE] m1 |
| **Verdict** | **CANDIDATE**, low priority. The one-factor Pine version is not the published signal; a test must be on the Pine-computable definition | |

### 3.6 Industry momentum

| Item | Content | Tag |
|---|---|---|
| Claim | "momentum investment strategies ... are significantly less profitable once we control for industry momentum"; industry strategies "appear highly profitable" | [PAPER] S7 |
| Contested | George & Hwang, same horizon and period: industry 0.25 vs 52-week high 0.65 vs individual 0.38 in a joint regression | [PAPER] S6 |
| After | Section 2.4: one-month broad-sector effect 0.77 → 0.27 after 2000; 12-month versions 0.35–0.72 with t below 2 | [DOC] own calc. S1 |
| Costs | One-month industry momentum, stock-level implementation: gross 0.93, turnover 90.1% a month, cost 1.22, **net −0.29**; with a 10%/50% buy/hold rule net −0.02 | [PAPER] S18 |
| Practitioner version | Zarattini & Antonacci, 48 industry portfolios 1926–2024, channel-based long-only timing: 18.5% average annual return, Sharpe 1.46 vs 0.63 for the market, costs included per the authors' page. Not peer-reviewed; rules and cost levels not on the page | [DOC] S51 (authors' page, summary only) |
| Why / who | Slow diffusion of industry news across related firms [MEMORY]; alternatively factor momentum (S35) | |
| Pine | Sector ETF return relative to SPY via `request.security`; mapping from `syminfo.sector` compiles, but the sector strings I used are from memory and `syminfo.sector` is a current snapshot | [COMPILE] m2; strings [MEMORY] |
| **Verdict** | **CONTEXT.** A 6–12-month sector tilt is defensible as a tie-breaker; the one-month version is **REJECT** (decayed, and negative net of costs at stock level) | |

### 3.7 Intermediate-horizon momentum ("echo")

| Item | Content | Tag |
|---|---|---|
| Claim | "Momentum is primarily driven by firms' performance 12 to seven months prior to portfolio formation"; recent-performance strategies "are less profitable ... especially among the largest, most liquid stocks" | [PAPER] S8 |
| Contested | "In 37 countries excluding the United States, there is no robust evidence of such an echo"; "Any echo in the United States appears to be driven largely by a carryover of short-term reversals from month − 2" | [PAPER] S9 |
| Size | Specific monthly figures not verified today | Gap |
| Pine | `close[126] / close[252] − 1`: yes | [COMPILE] m1 |
| **Verdict** | **REJECT** as a separate signal: contested, US-only, and it adds a free parameter. Keep the standard 12-1 window | |

### 3.8 "Frog in the pan": information discreteness

| Item | Content | Tag |
|---|---|---|
| Claim | "continuous information induces strong persistent return continuation that does not reverse in the long run" | [PAPER] S10 |
| Definition | `ID = sgn(PRET) × [%neg − %pos]`, with PRET "a firm's cumulative return over the past twelve months after skipping the most recent month" and %pos, %neg the shares of positive and negative daily returns in that window | [PAPER] S10 |
| Size | Six-month holding: momentum "increases monotonically from –2.07% in the discrete information portfolio to 5.94% in the continuous information portfolio" (sequential double sort). "Momentum following continuous information persists for eight months, while the momentum profit following discrete information becomes insignificant after two months" | [PAPER] S10 |
| Where | Stronger where attention is scarce: "low institutional ownership ... small market capitalizations, low analyst coverage, and low media coverage" | [PAPER] S10 |
| After | Sample "ends in 2007". No post-2007 large-cap evidence read today | [PAPER] S10; gap |
| Costs | Not quantified in the passages read | Gap |
| Why / who | Limited attention to small, frequent signals. Other side: investors who react only to large moves | [PAPER] S10 |
| Pine | Count of up and down days over bars t−252…t−21 with `math.sum`: yes | [COMPILE] m1 |
| **Verdict** | **CANDIDATE** as a quality filter on trend ("smooth winner" vs "one-gap winner"). The stated mechanism predicts a weaker effect in heavily covered large caps | |

### 3.9 Momentum acceleration

| Item | Content | Tag |
|---|---|---|
| Claim A | "changes of momentum, i.e. 'acceleration', defined as the first difference of successive returns, provide better performance and higher explanatory power than momentum" (working paper, not a journal article) | [PAPER] S53 |
| Claim B | US 1962–2014: "Winners with accelerated historical price increases deliver higher future expected returns"; long accelerated winners / short accelerated losers earns more "than the momentum profit by 51.47%" | [PAPER] S52 |
| Cautions | Gross of costs; many curvature and horizon variants tried on one sample (reviewer's caution) | [SECONDARY] S52b |
| Tension | Acceleration favours convex, speeding-up price paths; frog-in-the-pan favours smooth, steady paths; Claim A's own abstract attributes the profits to "transient non-sustainable accelerating" prices | Inference from S10, S52, S53 |
| Pine | Difference of two sub-period returns: yes | [COMPILE] m1 |
| **Verdict** | **REJECT** for now: weakest evidence in the set, no cost analysis, and the mechanism conflicts with 3.8 | |

### 3.10 Short-horizon continuation and reversal (the trader's holding period)

| Item | Content | Tag |
|---|---|---|
| Claim | "double sorting on the previous month's return and share turnover reveals significant short-term reversal among low-turnover stocks, whereas high-turnover stocks exhibit short-term momentum" | [PAPER] S33 |
| Size | Winner-minus-loser on last month's return: **lowest-turnover decile −1.41 (t=−7.13); highest-turnover decile +1.37 (t=4.74)**. By size: microcaps −0.34 (t=−1.21); megacaps +0.53 (t=2.53); **500 largest stocks +0.42 (t=4.91)** from a 2×2 sort, about 129 long and 121 short names. July 1963–December 2018 | [PAPER] S33 |
| Which leg | "On average, the STMOM strategy generates all its profits on the long side." | [PAPER] S33 |
| Persistence / costs | "persists for 12 months"; "survives transaction costs and is strongest among the largest, most liquid, and most extensively covered stocks" | [PAPER] S33 |
| Weekly horizon | After extreme weekly returns a brief reversal is "followed by an opposing and long-lasting stream of continuation" strong enough "to produce a significant momentum effect over the full year" | [PAPER] S31 |
| After | Published 2022, sample to 2018. No post-2018 evidence read. A China replication found only reversal | Gap; [SECONDARY] S33b |
| Why / who | "some traders underappreciating the information conveyed by prices": high volume marks informed trading that the rest under-react to; low volume marks liquidity-driven moves that revert. Other side in high-turnover winners: sellers supplying stock into heavy demand | [PAPER] S33 |
| Pine | Last-21-day return: yes. Share turnover needs shares outstanding through time; Pine exposes only a current snapshot (`syminfo.shares_outstanding_float`, per `pine_requests.md`). Proxy: 21-day volume relative to the stock's own 252-day average volume. **This proxy is not the published variable** (it measures abnormal volume, not the level of turnover) | Sibling doc; inference |
| **Verdict** | **CANDIDATE, highest priority in this report**: right horizon, right universe, long-side. Must be re-tested with the Pine-computable proxy and on post-2018 data | |

### 3.11 Time-series momentum on single stocks

| Item | Content | Tag |
|---|---|---|
| Origin | Time-series momentum was documented on 58 futures, not stocks: "persistence in returns for one to 12 months that partially reverses over longer horizons" | [PAPER] S27 |
| Single stocks | "strong time-series momentum effects in individual stocks in the US markets from 1927 to 2017 ... not specific to sub-periods, firm sizes"; effects "conditional on the market state, the information discreteness of the constituent stocks and investor sentiment" | [PAPER] S30 |
| Contested | "For individual stocks, the difference between the performances of TS and CS strategies is largely due to this time-varying net long investment" (i.e. it is market exposure). "asset-by-asset time series regressions reveal little evidence of TSM"; performance "is virtually the same as that of a similar strategy that is based on historical sample mean" | [PAPER] S28, S29 |
| Pine | Sign of the stock's own 12-month return: yes | [COMPILE] m1 |
| **Verdict** | **CONTEXT.** "Own 12-month return positive" is a reasonable long-only precondition; the evidence says its payoff is mostly equity beta taken at better times, not stock selection | |

### 3.12 Moving-average timing on stocks

| Item | Content | Tag |
|---|---|---|
| Claim | Applying a moving-average timing rule to volatility-sorted portfolios "substantially outperform[s] the buy-and-hold strategy"; for high-volatility portfolios the abnormal returns "are greater than those from the well-known momentum strategy" | [PAPER] S13 |
| Details | 10-day average, deciles by prior-year daily volatility, switch to T-bills with a one-day delay; gross annualised abnormal returns 8.42%–18.70%; break-even cost 0.29% (decile 8, 10-day rule) to 1.12% (decile 1, 50-day rule); reviewer: frictions "high compared to breakeven during much of the sample period" | [SECONDARY] S13b |
| Trend factor | Moving averages of several lengths combined: "more than doubling" the Sharpe ratios of reversal, momentum and long-term reversal factors; during the financial crisis +0.75 a month vs −3.88 for momentum | [PAPER] S14 |
| Contested | Glabadanidis's strong results: "due to simulating trading with look-ahead bias"; without it "indistinguishable from the performance of the buy-and-hold strategy". On US stocks 1990–2004 moving-average and range-breakout rules "are rarely profitable", "more profitable for smaller, less liquid stocks". Dow Jones 1897–2011: rule performance "completely offset by the introduction of low transaction costs" and no rule selectable in advance. The original supportive study used the Dow index 1897–1986 | [PAPER] S47, S46, S45, S43; data-snooping method S44 |
| After (index level) | S&P 500 timing by the 10-month average did not help in 2010–2026 (section 2.2) | [DOC] own calc. S1 |
| Why / who | If real: slow diffusion under information uncertainty (S13). The portfolio-level results rest on daily autocorrelation of small, volatile, illiquid stocks, which a trader in liquid names does not get (inference) | |
| Pine | `close > ta.sma(close, n)`: yes | [COMPILE] m1 |
| **Verdict** | **REJECT** as an edge in liquid stocks. Keep moving averages as a trend-state display and as an exit trigger ("change of trend") | |

### 3.13 Breakouts with ATR stops (trend-following on stocks)

| Item | Content | Tag |
|---|---|---|
| Original | Wilcox & Crittenden (Blackstar Funds, Nov 2005; not peer-reviewed): buy at a new all-time high, exit on an ATR trailing stop (10 ATR is one point of a tested range); NYSE/AMEX/NASDAQ incl. delisted, 1983–2004; 0.5% round-trip cost | [SECONDARY] S49b. **Paper not readable today** |
| Critique | Niederhoffer (Nov 2005): no statistical significance shown; "Small stocks performed much better than big stocks during the latter part of the period"; a random or 10%-off-high entry "would have come up with as good results"; "We have tested similar strategies on big groups of stocks like the S&P500 and found it produces random results". Crittenden's reply on the same page: "When restricted to the S&P 500 we found an inverse relationship between the tendency to have substantial and prolonged % moves and market capitalization"; "being stopped out of almost 90% of our positions during the crash of 1987". A third commenter: most outperformance came in 2003–2005 and tracks an equal-weighted index | [SECONDARY] S49 (page read today; quotes are the critics' and the author's own words) |
| Update | Zarattini, Pagani & Wilcox (2025, SSRN, not peer-reviewed): all liquid US stocks 1950–Nov 2024, survivorship-free, "more than 66,000 long-only trend trades"; "Less than 7% of trades generate the majority of cumulative profits"; portfolio 1991–2024 "15.19% compound annual growth rate", "6.18% annualized alpha", gross of fees; "difficult to implement for portfolios with assets under management below $1 million" without their turnover-control step | [DOC] S50 (authors' page) |
| Rule details | Entry at next open after a close at an all-time high; stop from the all-time high and 42-day ATR, ratchets up only; liquidity filter price > $10 and 42-day dollar volume > $1M (inflation-adjusted); sizing to a 30% portfolio volatility target, leverage up to 200%; 15.0% gross CAGR vs 11.2% for the cap-weighted market, Jan 1991–Oct 2024 | [SECONDARY] S50b |
| Costs | Authors: costs "significantly reduce net returns" for small accounts. For this trader the issue is not cost per trade but number of positions | [DOC] S50 |
| Why / who | A right-skewed payoff: many small losses, few very large winners. The return is the mean of a fat right tail and needs breadth to be collected. Benchmark problem: part of the gross alpha is an equal-weight / small-cap tilt (critique above) | Inference from S49, S50 |
| Pine | `ta.max(high)` for the all-time high within loaded history, `ta.atr`, ratcheting stop in `var` state: yes. Limitation: the all-time high is only as deep as the chart's loaded history | [COMPILE] m2 |
| **Verdict** | **REJECT** as a stand-alone system for a 5–10-name book (profits from under 7% of trades; effect weakest in large caps). **CANDIDATE** only as an event definition to be tested against matched random entries (hypothesis H8) | |

### 3.14 Stop-loss rules

| Item | Content | Tag |
|---|---|---|
| Theory | "under the Random Walk Hypothesis, simple 0/1 stop-loss rules always decrease a strategy's expected return, but in the presence of momentum, stop-loss rules can add value" | [PAPER] S15 (working paper abstract) |
| Index evidence | US equities with long-term government bonds as the stop asset, monthly, 1950–2004: "certain stop-loss rules add 50 to 100 basis points per month to the buy-and-hold portfolio during stop-out periods". Published version: "At longer sampling frequencies, certain stop-loss policies can increase expected return while substantially reducing volatility" | [PAPER] S15 |
| Single stocks | Large sample of US stocks: "tight stop-loss strategies tend to underperform the buy-and-hold policy due to excessive trading costs. Outperformance is possible for stocks with sufficiently high serial correlation in returns. Certain strategies succeed at reducing downside risk, but not substantially." | [PAPER] S16 (thesis abstract containing the paper) |
| Details | 1964–2014; daily stops 0 to −6% and 10-day stops 0 to −14%; cost 0.2% half-spread; return autocorrelation "Positive over the first half of the sample, significantly negative over the second half"; wide 10-day stops about equal to buy-and-hold risk-adjusted; one-day delayed execution better "because of return reversion during the one-day delay" | [SECONDARY] S16b |
| Stop-loss momentum | Han, Zhou & Zhu (working paper): 10% stop cuts the worst month of equal-weighted momentum from −49.79% to −11.36% (1926–2013). With a 15% stop: mean 0.99 → 1.93, monthly Sharpe 0.17 → 0.40. **Gross of costs; assumes a limit order near the stop level fills intramonth; turnover rises 39% → 49% (winners)** | [SECONDARY] S17 |
| Index, trend plus stops | S&P 500, July 1988–June 2011: trailing stops of 3–15% and purchase-price stops on top of a 200-day rule: "stop-loss rules would seem to make performance worse"; "a change of trend is the best stop loss"; "monthly end of month investment decision rules are superior to those which trade more" frequently | [PAPER] S48 |
| Why / who | A stop pays only if losses predict further losses (positive serial correlation). Daily and weekly stock returns after 1990 show reversal on average, so the stop sells to a liquidity provider who collects the bounce (inference from S16b, S33) | |
| Pine | Fixed, ATR-trailing, Donchian and time exits in one state machine evaluated on confirmed bars: yes. A close-based stop cannot protect against an overnight gap | [COMPILE] m2 |
| **Verdict** | Tight stops as a return source: **REJECT**. Stops as risk control: **CONTEXT**: one wide, catastrophic stop (it bounds single-name damage in a 5–10-name book), plus a time exit and a trend-change exit. The cost of the stop in expectancy must be measured, not assumed away | |

### 3.15 Trading costs of momentum

| Study | Finding | Tag |
|---|---|---|
| Lesmond, Schill & Zhou 2004 | "those stocks that generate large momentum returns are precisely those stocks with high trading costs" | [PAPER] S23 |
| Korajczyk & Sadka 2004 | "Equal-weighted strategies perform the best before trading costs and the worst after trading costs"; liquidity-weighted strategies break even at "$5 billion or more (relative to December 1999 market capitalization)" | [PAPER] S22 |
| Novy-Marx & Velikov 2016 | Momentum net 0.68 (t=2.45), 0.85 with a buy/hold spread; "Introducing a buy/hold spread ... is the most effective cost mitigation technique"; "Most anomalies with turnover less than 50% per month generate significant net spreads ...; few with higher turnover do"; capacity "slightly more than $5 billion" | [PAPER] S18 |
| Frazzini, Israel & Moskowitz (2012 draft) | Live institutional trades 1998–2011: "actual trading costs are less than a tenth as large as ... previous studies suggest"; average market impact 11.21 bp for large-cap trades, 21.27 bp for small-cap; momentum break-even size $52 billion in the US. 2018 version: abstract not readable today (SSRN 403) | [PAPER] S19 |
| Patton & Weller 2020 | "typical mutual funds earn low returns to value and no returns to momentum"; smallest funds earn "5%–6% more per unit momentum beta than the largest funds" | [PAPER] S26 |
| Chen & Velikov 2023 | 204 anomalies, net of spreads and publication effects, post-2000s trading technology: "a measly 4 bps per month"; "The strongest anomalies net, at best, 10 bps after controlling for data mining" | [PAPER] S25 |
| McLean & Pontiff 2016 | "26% lower out-of-sample and 58% lower post-publication"; declines larger for predictors with higher in-sample returns | [PAPER] S24 |
| Replication debate | "65% of the 452 anomalies ... cannot clear the single test hurdle" with NYSE breakpoints and value weights (Hou, Xue & Zhang) vs "The majority of asset pricing factors (i) can be replicated" (Jensen, Kelly & Pedersen) vs 98% of clearly significant originals reproduce (Chen & Zimmermann) | [PAPER] S40, S41, S42 |

For this trader (inference): position sizes of thousands to tens of thousands of dollars in stocks trading over $50M a day have no market impact; the project's 5 bp per side is the right order. The lessons that transfer are structural: (1) costs scale with turnover, so use a **buy/hold hysteresis** (stricter rule to enter than to stay); (2) the studies agree that gross premia are concentrated where trading is expensive, which is the same statement as "the premium is small in liquid large caps".

---

## 4. What the trader's horizon does to these results

| Published design | Trader's reality | Consequence |
|---|---|---|
| Portfolios of 100+ stocks per leg | 5–10 names | Premium is swamped by single-name noise (section 5) |
| Long-short | Long-only | Half or more of every spread is unavailable; after 2000 the large-cap long half is about zero (S1) |
| Monthly rebalance, 1–12-month hold, skip the latest month | Hold days to weeks, enter on the latest bar | The first month after formation is the weakest: J&T report positive returns in every month "With the exception of the first month" [PAPER] S2; one-month reversal is strong in broad samples [PAPER] S6; it turns into continuation only for high-turnover stocks, and among megacaps the low-turnover reversal is still −0.74 (t=−4.27) [PAPER] S33 |
| Equal weights including small and micro caps | Liquid stocks only | Effect sizes from equal-weighted CRSP studies (S2, S6, S10, S13) overstate what liquid names offer |
| Rank across the whole market | One chart at a time in Pine | Signals must be absolute or relative to SPY / a sector ETF, or run through the Pine Screener |

So the momentum literature answers "which stocks should be on the watchlist this quarter" better than "should I buy this bar". The swing-entry question is closer to the short-horizon literature (3.10) and to event studies outside this report's scope.

---

## 5. How much can 5–10 names capture? (arithmetic; inference)

Assumptions, stated so they can be changed: idiosyncratic volatility of a liquid US stock 30% a year [MEMORY, order of magnitude]; N = 8 equal positions; residual volatility of the book ≈ 30% / √8 ≈ 10.6% a year.

| Assumed long-only premium | Source of the number | Per year | Information ratio | Years for t = 2 |
|---|---|---|---|---|
| 0.33 a month | Big high − Mkt, 1927–1999 (S1) | 4.0% | 0.38 | ≈ 28 |
| 0.29 a month | Decile 10 − Mkt, 2000–2026 (t=1.26) (S1) | 3.5% | 0.33 | ≈ 37 |
| 0.05 a month | Big high − Mkt, 2000–2026 (S1) | 0.6% | 0.06 | > 1,000 |

Even at pre-2000 strength the tilt could not be confirmed inside a trading lifetime with eight names. Consequences for the indicator: momentum-family signals belong in **filters and context panels** (what not to buy, what state the market is in, how large to size), and any claim of entry edge must come from tests with thousands of events, not from the trader's own trade log.

---

## 6. Where the literature and the practitioners are wrong or contested

| Topic | Position A | Position B | My reading |
|---|---|---|---|
| Does momentum depend on size? | "no reliable relation with size" [PAPER] S20 | Declines with size [PAPER] S2, S32, S39; French data after 2000: smallest quintile 0.41 vs largest 0.24, both insignificant [DOC] S1 | Before 2000 it existed in large caps (0.58–0.78, t≈3). After 2000 it is not distinguishable from zero in any size group; point estimates are larger in small caps |
| Is half of momentum on the long side? | Yes, 86 years [PAPER] S20 | After 2000 big winners ≈ big middle [DOC] S1 | The long side is what decayed |
| Industries explain momentum | Yes [PAPER] S7 | Industry effect is the weakest of three in a joint test [PAPER] S6 | Treat sector strength as a minor tilt |
| Intermediate-horizon "echo" | [PAPER] S8 | Not outside the US; an artefact of month −2 reversal [PAPER] S9 | Do not tune the look-back window |
| Volatility management | Doubles Sharpe [PAPER] S5 | Not out of sample across 103 strategies [PAPER] S36 | Both right: works for long-short momentum specifically; not for long-only [DOC] S1 |
| Time-series momentum | Pervasive [PAPER] S27, S30 | Net-long exposure / not statistically reliable [PAPER] S28, S29 | Beta timing, not selection |
| Moving-average timing | Large abnormal returns [PAPER] S13 | Look-ahead bias in a prominent study; rules rarely profitable on US stocks; nothing after costs on the Dow [PAPER] S47, S46, S45 | No edge in liquid stocks |
| Trading costs | "illusion" [PAPER] S23; no returns to momentum for funds [PAPER] S26 | Costs a tenth of earlier estimates [PAPER] S19 | Costs depend on who trades; irrelevant at retail size in liquid names; the gross premium is the problem |
| "Buy new highs" (practitioner) | Positive expectancy on all stocks [SECONDARY] S49b | Author: weakest in large caps; critic: random on the S&P 500 [SECONDARY] S49; under 7% of trades carry the profits [DOC] S50 | Needs breadth the trader does not have |
| "Cut losses short" (practitioner) | Stops improve momentum [SECONDARY] S17; index with bonds [PAPER] S15 | Tight stops hurt on single stocks and on the index [PAPER] S16, S48 | Stops are insurance with a premium; size the premium |
| Smooth vs accelerating trends | Smooth is better [PAPER] S10 | Accelerating is better [PAPER] S52, S53 | Unresolved; only the first has a stated mechanism that the second does not contradict by its own account |
| Replication | Most anomalies fail [PAPER] S40 | Most replicate [PAPER] S41, S42 | In-sample momentum replicates; the open question is its size after 2000 |

Practitioner systems that combine these ideas (new highs above rising 50/150/200-day averages; regression-slope rankings) have, to my knowledge, no survivorship-free published test; I did not search for one today. [MEMORY]

---

## 7. Pine computability

Both probes compile with zero errors and zero warnings under the current compiler. [COMPILE] `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/lit_momentum/pine/m1_signals.pine` and `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/lit_momentum/pine/m2_stops.pine`. Compilation proves the functions, parameters and types exist; it proves nothing about runtime limits or numerical parity.

| Signal | Bar-close formula (daily series `c`, `h`; market proxy `m`) | Confirmed names | Caveats |
|---|---|---|---|
| 12-1 momentum | `c[21] / c[252] - 1` | series history operator | Price return, not total return, if dividends are not in the adjustment. Pin with `ticker.new(syminfo.prefix, syminfo.ticker, session.regular, adjustment.splits)` |
| 12-7 and 6-2 | `c[126]/c[252]-1`, `c[21]/c[126]-1` | | |
| Relative strength vs market | `(c[21]/c[252]) / (m[21]/m[252]) - 1` | `request.security`, `input.symbol` | One request per extra symbol; 40-call budget (sibling report) |
| Price-to-52-week-high | `c / ta.highest(h, 252)` | `ta.highest` | Test closes vs highs |
| Recency of the high | `-ta.highestbars(h, 252)` | `ta.highestbars` | |
| New 52-week high event | `h >= ta.highest(h, 252)[1]` | | |
| Information discreteness | `math.sign(mom) * (pctNeg - pctPos)`, with `math.sum(r > 0 ? 1.0 : 0.0, 231)[21] / 231` | `math.sum`, `math.sign` | Needs ≥ 253 daily bars |
| Residual momentum, one factor | `beta = ta.correlation(r, rm, 252) * ta.stdev(r, 252) / ta.stdev(rm, 252)`; `resid = r - beta[21]*rm`; `math.sum(resid, 231)[21] / (ta.stdev(resid, 231)[21] * math.sqrt(231))` | `ta.correlation`, `ta.stdev` | Not the three-factor published version |
| Market state | `m/m[252]-1 >= 0`; `m/m[504]-1 < 0` | | 504 daily bars of SPY needed |
| Realised volatility, sizing | `ta.stdev(math.log(c/c[1]), 63) * math.sqrt(252)`; `math.min(1, target/vol)` | `math.log`, `math.sqrt`, `math.min` | |
| Moving-average state | `c > ta.sma(c, n)` | `ta.sma` | |
| Donchian | `ta.highest(h, 55)[1]`, `ta.lowest(low, 20)[1]` | `ta.lowest` | |
| All-time high | `ta.max(high)` | `ta.max` | Bounded by loaded history |
| ATR trailing stop | `var` state; `trail := math.max(trail, hiSince - k * ta.atr(42))` | `ta.atr`, `var`, `barstate.isconfirmed` | Close-based; gaps pass through |
| Sector ETF relative strength | `switch syminfo.sector` → ETF symbol → `request.security(etf, "D", close[1], lookahead = barmerge.lookahead_on)` | `syminfo.sector`, `switch` with string cases, `barmerge.lookahead_on` | Sector label strings from memory; snapshot value, no history |
| Daily values on intraday charts | `request.security(sym, "D", src[1], lookahead = barmerge.lookahead_on)` | | Pattern taken from the sibling report; yields the last completed day |
| Alerts | `alertcondition(barstate.isconfirmed and cond, ...)` | `alertcondition` | |
| Share turnover (for 3.10) | **Not computable historically**; proxy `ta.sma(volume, 21) / ta.sma(volume, 252)` | | Proxy differs from the published variable |
| Cross-sectional rank | **Not computable in one script** for a broad universe | | Pine Screener or offline thresholds |

---

## 8. Verdict table

| # | Idea | Verdict | Reason in one line |
|---|---|---|---|
| 1 | 12-1 momentum as a buy signal in large caps | CONTEXT | Long-only premium ≈ 0 since 2000 (S1) |
| 2 | Exclude 12-1 losers / names far below the 52-week high | CANDIDATE | The surviving large-cap spread is on the loser side (S1, S6) |
| 3 | Market-state gate (SPY 12/24-month return) | CONTEXT | Separates long-short momentum; small for long-only |
| 4 | Market 10-month-average timing | CONTEXT (drawdown only) | Reversed sign in 2010–2026 (S1) |
| 5 | Volatility-scaled sizing | CONTEXT | Cuts drawdown, no Sharpe gain long-only (S1) |
| 6 | 52-week-high nearness, long side | CANDIDATE | +0.16 a month in 1963–2001 equal-weighted; untested recently |
| 7 | Recency of the 52-week high | CANDIDATE | 0.70 a month decile spread (S37); untested in large caps |
| 8 | Residual momentum (one-factor) | CANDIDATE (low) | Published version not computable in Pine |
| 9 | Sector/industry strength, 6–12 months | CONTEXT | Positive, insignificant since 2000 (S1) |
| 10 | Industry momentum, 1 month | REJECT | Decayed; negative net of costs (S18) |
| 11 | 12-7 "echo" window | REJECT | Contested, adds a parameter |
| 12 | Frog-in-the-pan smoothness | CANDIDATE | Clear mechanism; sample ends 2007; predicted weaker in large caps |
| 13 | Acceleration | REJECT | Weak, gross-only, conflicts with 12 |
| 14 | One-month winners with high turnover (short-term momentum) | **CANDIDATE (first)** | Long-side, megacap, right horizon (S33); needs proxy and post-2018 test |
| 15 | Own 12-month return > 0 (time-series momentum) | CONTEXT | Beta timing (S28) |
| 16 | Moving-average timing on stocks | REJECT as edge | Costs, look-ahead controversy, large-cap nulls |
| 17 | All-time-high / Donchian breakout system with wide ATR stop | REJECT as system; CANDIDATE as event | Profits from < 7% of trades; weakest in large caps |
| 18 | Tight stops | REJECT as return source | S16, S48 |
| 19 | Wide catastrophic stop + time exit + trend-change exit | CONTEXT | Risk control; measure its cost |
| 20 | Buy/hold hysteresis in any ranking rule | CONTEXT (design rule) | Most effective cost mitigation (S18) |

---

## 9. Hypotheses to test

Common settings, so the tests are comparable. Universe: stocks and ADRs with price ≥ $5 and 60-day median dollar volume ≥ $20M (project panel), reported separately for ≥ $50M. Signals are computed on the close of day t; entry at the open of t+1; costs per the project protocol (5/10/25 bp per side by liquidity, doubled as a stress). Forward returns at 5, 10 and 20 trading days, **in excess of the equal-weighted universe return over the same days** (so a market move is not mistaken for an edge) and also raw. Survivorship-free evidence only from 2018-07; 2011–2018 is biased and is development data. Each hypothesis fixes its parameters before testing; the variants listed are the only ones allowed. "Prior" is my probability that the stated effect is found with the stated sign and at least half the stated magnitude, net of costs, in the survivorship-free period.

| # | (a) Signal at the close of t | (b) Comparison / control | (c) Expected sign and size | (d) Data | (e) How it could fail | (f) Prior |
|---|---|---|---|---|---|---|
| H1 | **Loser exclusion.** `mom12_1 = c[21]/c[252]−1` in the bottom 30% of the universe that day, or `c / highest(h,252) < 0.70` | Same-day stocks in the middle 40%; matched on sector and volatility tercile | Losers earn −0.15 to −0.30% per 20 days relative to the middle group; no difference between top 30% and middle | Daily OHLCV panel | Rebound regimes (2020-04, 2023-01) dominate a short sample and flip the sign; effect confined to names under $50M a day | 45% |
| H2 | **New 52-week high event.** `h ≥ highest(h,252)[1]`, first occurrence in 21 bars, with SPY 12-month return ≥ 0 | Same stock, random dates in the same calendar quarter with no new high; and same-day stocks at 85–95% of the high | +0.1 to +0.3% per 20 days excess; nothing at 5 days | Daily OHLCV, SPY | Excess is a volatility or beta artefact (new highs cluster in rising markets); disappears against the same-day control | 25% |
| H3 | **Recency of the high.** Among stocks with `c/highest(h,252) ≥ 0.90`: bars since the high ≤ 21 | Same filter, bars since the high > 126 | Recent group better by 0.15–0.30% per 20 days | Daily OHLCV | Recent-high group is just higher 1-month return, which reverses in low-volume names | 30% |
| H4 | **Smooth winners.** Among the top 30% on `mom12_1`: bottom third of `ID = sign(mom)·(%neg − %pos)` over bars t−252…t−21 | Top third of ID within the same winners, matched on `mom12_1` quintile | Smooth better by 0.15–0.35% per 20 days; difference persists to 60 days | Daily OHLCV | Attention mechanism implies little effect in liquid, covered names; sample too short for a 60-day horizon | 30% |
| H5 | **Short-term momentum.** 21-day return in the top quintile **and** turnover proxy `sma(volume,21)/sma(volume,252)` in the top quintile, within the 500 most liquid names | (i) Top return quintile with bottom-quintile volume proxy (should reverse); (ii) universe average; (iii) where shares outstanding are available offline, the published turnover variable, to measure what the proxy loses | Long side +0.2 to +0.4% per 20 days excess; control (i) negative | Daily OHLCV with volume; shares outstanding for (iii) | Proxy captures earnings-volume spikes rather than turnover level; effect decayed after 2018 or after 2022 publication; earnings dates drive it (then it belongs to the earnings researcher) | 35% |
| H6 | **Market-state gate.** For the entries of H2 and H5: SPY 252-day return ≥ 0 | Same entries when SPY 252-day return < 0 | Excess return higher by 0.2–0.5% per 20 days in the up state | SPY daily; H2/H5 events | Only two or three down-state episodes since 2018 (2020, 2022); cannot be distinguished from noise | 35% |
| H7 | **Tight stop vs time exit.** For H2/H5 entries held to 20 bars: exit at next open after `close < entry − 2·ATR(14)` | Same entries with a 20-bar time exit only; and with a 3·ATR stop | Tight stop **lowers** mean net return per trade by 0.1–0.5% and lowers the win rate by ≥ 10 points; the 5th-percentile trade improves by ≥ 30% | Daily OHLCV incl. gaps; delisting returns | Positive serial correlation after losses in this event set would make the stop add return (that would be a finding in favour of stops) | 60% that the mean falls; 55% that the tail improves by ≥ 30% |
| H8 | **Breakout expectancy against matched random entries.** Close ≥ prior all-time high (within panel history, minimum 3 years) or close > `highest(h,55)[1]`; exit on a ratcheting `10·ATR(42)` trailing stop or `close < lowest(low,20)[1]` | Random entry dates in the same stocks and years with the same exit rules; split by dollar-volume tercile | Excess expectancy over random entry ≤ 0.5 R in the top liquidity tercile, larger in the bottom tercile; ≥ 50% of total profit from ≤ 10% of trades | Daily OHLCV, long history preferred | Panel too short for trades that last years; all-time high undefined before 2011 in this data | 25% that the top-tercile excess is positive and significant |
| H9 | **Volatility sizing.** Position weight = min(1, 15% / 63-day realised volatility of the stock), applied to H1-filtered baskets | Equal weights, same baskets | Sharpe ratio change within ±0.05; maximum drawdown lower by ≥ 20% | Daily OHLCV | Low-volatility names underperform in momentum regimes, lowering return more than risk | 15% that Sharpe rises ≥ 0.1; 60% that drawdown falls ≥ 20% |
| H10 | **Sector tilt.** Stock's sector ETF in the top 3 of 11 on 126-day return relative to SPY | Stocks whose sector is in the bottom 3; stock-level controls for `mom12_1` | +0.1 to +0.25% per 20 days | Sector ETF daily bars; sector membership through time (current snapshot only in Pine) | Sector classification today differs from the past (snapshot bias); effect already captured by the stock's own momentum | 25% |
| H11 | **Residual vs raw momentum.** Top tercile on one-factor residual momentum (formula in section 7) | Top tercile on raw `mom12_1`; overlap removed | Equal mean; relative drawdown in rebound months (SPY +5% or more after a negative 12-month return) smaller by ≥ 30% | Daily OHLCV, SPY | One-factor residual is too crude; too few rebound months since 2018 | 30% |
| H12 | **Moving-average timing null.** Hold a stock only while `close > sma(close, n)`, n ∈ {50, 200}, top volatility tercile | Buy and hold the same stocks; costs charged on every switch | Net Sharpe difference ≤ +0.1 and not significant; drawdown lower | Daily OHLCV | If the timed version wins net by more than 0.1 Sharpe out of sample, the rejection in 3.12 is wrong for this universe | 15% that timing wins by > 0.1 |

Order of work if time is short: H5, H1, H7, H4, H3, then the rest. H7 and H12 are stated so that the expected outcome is the unexciting one; they exist to stop a stop-loss or a moving-average rule from being added to the indicator on faith.

---

## 10. Sources (all accessed 2026-11-11)

| ID | Reference | URL | What I read |
|---|---|---|---|
| S1 | Kenneth R. French Data Library (files listed in section 2) | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/ | Data files; own calculations |
| S2 | Jegadeesh & Titman (1993), *J. Finance* 48(1) 65–91 | https://ideas.repec.org/a/bla/jfinan/v48y1993i1p65-91.html ; full text copy https://floridapsc.com/library/filings/2013/07457-2013/Support/Gulf's%20response%20to%20OPC's%201st%20POD,%20No.%2057/Jegadeesh%20and%20Titman%201993%20(140-167).pdf | Abstract and paper text |
| S3 | Jegadeesh & Titman (2001), *J. Finance* 56(2) 699–720 | https://ideas.repec.org/a/bla/jfinan/v56y2001i2p699-720.html | Abstract |
| S4 | Daniel & Moskowitz (2016), *JFE* 122(2) 221–247; NBER WP 20439 | https://ideas.repec.org/a/eee/jfinec/v122y2016i2p221-247.html ; https://www.nber.org/system/files/working_papers/w20439/w20439.pdf | Abstract; working-paper text |
| S5 | Barroso & Santa-Clara (2015), *JFE* 116(1) 111–120 | https://ideas.repec.org/a/eee/jfinec/v116y2015i1p111-120.html | Abstract |
| S5b | Search-tool summary citing ETF.com for the 0.53 → 0.97 figure | https://www.etf.com/node/94292.md | Not opened by me |
| S6 | George & Hwang (2004), *J. Finance* 59(5) 2145–2176 | https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf | Paper text, Tables I, II, V |
| S7 | Moskowitz & Grinblatt (1999), *J. Finance* 54(4) 1249–1290 | https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html | Abstract |
| S8 | Novy-Marx (2012), *JFE* 103(3) 429–453 | https://ideas.repec.org/a/eee/jfinec/v103y2012i3p429-453.html | Abstract |
| S9 | Goyal & Wahal (2015), *JFQA* 50(6) 1237–1267 | https://ideas.repec.org/a/cup/jfinqa/v50y2015i06p1237-1267_00.html | Abstract |
| S10 | Da, Gurun & Warachka (2014), *RFS* 27(7) 2171–2218 | https://ideas.repec.org/a/oup/rfinst/v27y2014i7p2171-2218..html ; https://www3.nd.edu/~zda/Frog.pdf | Abstract; paper text |
| S11 | Blitz, Huij & Martens (2011), *J. Empirical Finance* 18(3) 506–521 | https://ideas.repec.org/a/eee/empfin/v18y2011i3p506-521.html | Abstract |
| S12 | Blitz, Hanauer & Vidojevic (2020), *Int. Rev. Economics & Finance* 69, 932–957 | https://econpapers.repec.org/RePEc:eee:reveco:v:69:y:2020:i:c:p:932-957 | Abstract |
| S12b | Search-tool summary of CXO Advisory on S12 | https://www.cxoadvisory.com/momentum-investing/idiosyncratic-pure-or-residual-momentum-as-a-stock-return-predictor | Not opened by me |
| S13 | Han, Yang & Zhou (2013), *JFQA* 48(5) 1433–1461 | https://ideas.repec.org/a/cup/jfinqa/v48y2013i05p1433-1461_00.html | Abstract |
| S13b | Search-tool summary of CXO Advisory on S13 | https://www.cxoadvisory.com/volatility-effects/combining-realized-volatility-and-simple-moving-averages | Not opened by me |
| S14 | Han, Zhou & Zhu (2016), "A trend factor", *JFE* 122(2) 352–375 | https://ideas.repec.org/a/eee/jfinec/v122y2016i2p352-375.html | Abstract |
| S15 | Kaminski & Lo (2014), *J. Financial Markets* 18, 234–254; SIFR WP 63 (2008) | https://ideas.repec.org/a/eee/finmar/v18y2014icp234-254.html ; https://econpapers.repec.org/RePEc:hhs:sifrwp:0063 | Both abstracts |
| S16 | Lo & Remorov (2017), *J. Financial Markets* 34, 1–15; Remorov, MIT thesis "Dynamic trading and behavioral finance" | https://dspace.mit.edu/handle/1721.1/107017 | Thesis abstract (its first part is the paper). Journal abstract not reached |
| S16b | CXO Advisory review of the 2015 working paper | https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth | Page read |
| S17 | Han, Zhou & Zhu, "Taming Momentum Crashes: A Simple Stop-Loss Strategy" (SSRN 2407199), via CXO Advisory | https://www.cxoadvisory.com/technical-trading/stop-losses-to-avoid-stock-momentum-crashes/ | Review page read; SSRN blocked |
| S18 | Novy-Marx & Velikov (2016), *RFS* 29(1) 104–147 | https://ideas.repec.org/a/oup/rfinst/v29y2016i1p104-147..html ; https://mysimon.rochester.edu/novy-marx/research/ToAatTC.pdf | Abstract; August 2015 version, Tables 3 and 6 |
| S19 | Frazzini, Israel & Moskowitz, "Trading Costs of Asset Pricing Anomalies" (Dec 2012 draft); "Trading Costs" (2018) | https://conference.nber.org/conf_papers/f68262/f68262.pdf ; https://papers.ssrn.com/abstract=3229719 | 2012 draft text; 2018 not readable |
| S20 | Israel & Moskowitz (2013), *JFE* 108(2) 275–301 | https://ideas.repec.org/a/eee/jfinec/v108y2013i2p275-301.html | Abstract |
| S21 | Cooper, Gutierrez & Hameed (2004), *J. Finance* 59(3) 1345–1365 | Search-tool summary of aggregator copies of the abstract | Not opened by me |
| S22 | Korajczyk & Sadka (2004), *J. Finance* 59(3) 1039–1082 | https://www.kellogg.northwestern.edu/faculty/korajczy/htm/korajczyk%20sadka.jf2004.pdf | Abstract in the paper |
| S23 | Lesmond, Schill & Zhou (2004), *JFE* 71(2) 349–380 | https://www.bauer.uh.edu/rsusmel/phd/Lesmond_et%20al%20_2004_JFE.pdf | Abstract in the paper |
| S24 | McLean & Pontiff (2016), *J. Finance* 71(1) 5–32 | https://gwern.net/doc/economics/2016-mclean.pdf | Abstract in the paper |
| S25 | Chen & Velikov (2023), *JFQA* 58(3) 968–1004 | https://ideas.repec.org/a/cup/jfinqa/v58y2023i3p968-1004_2.html | Abstract |
| S26 | Patton & Weller (2020), *JFE* 137(2) 515–549 | https://econpapers.repec.org/RePEc:eee:jfinec:v:137:y:2020:i:2:p:515-549 ; https://public.econ.duke.edu/~ap172/Patton_Weller_MF_28nov18.pdf | Abstract; Nov 2018 version text |
| S27 | Moskowitz, Ooi & Pedersen (2012), *JFE* 104(2) 228–250 | https://ideas.repec.org/a/eee/jfinec/v104y2012i2p228-250.html | Abstract |
| S28 | Goyal & Jegadeesh (2018), *RFS* 31(5) 1784–1824 | https://ideas.repec.org/a/oup/rfinst/v31y2018i5p1784-1824..html | Abstract |
| S29 | Huang, Li, Wang & Zhou (2020), *JFE* 135(3) 774–794 | https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html | Abstract |
| S30 | Lim, Wang & Yao (2018), *J. Banking & Finance* 97, 283–296 | https://ideas.repec.org/a/eee/jbfina/v97y2018icp283-296.html | Abstract |
| S31 | Gutierrez & Kelley (2008), *J. Finance* 63(1) 415–447 | https://econpapers.repec.org/article/blajfinan/v_3a63_3ay_3a2008_3ai_3a1_3ap_3a415-447.htm | Abstract |
| S32 | Hong, Lim & Stein (2000), *J. Finance* 55(1) 265–295 | https://econpapers.repec.org/article/blajfinan/v_3a55_3ay_3a2000_3ai_3a1_3ap_3a265-295.htm | Abstract |
| S33 | Medhat & Schmeling (2022), *RFS* 35(3) 1480–1526 | https://openaccess.city.ac.uk/id/eprint/31278/1/MS_short_term_mom_v27.pdf | Accepted version text |
| S33b | Search-tool summary mentioning a China replication | – | Not opened by me |
| S34 | Avramov, Cheng & Hameed (2016), *JFQA* 51(6) 1897–1923 | https://econpapers.repec.org/RePEc:cup:jfinqa:v:51:y:2016:i:06:p:1897-1923_00 | Abstract |
| S35 | Ehsani & Linnainmaa (2022), *J. Finance* 77(3) 1877–1919 | https://econpapers.repec.org/RePEc:bla:jfinan:v:77:y:2022:i:3:p:1877-1919 | Abstract |
| S36 | Cederburg, O'Doherty, Wang & Yan (2020), *JFE* 138(1) 95–117 | https://econpapers.repec.org/RePEc:eee:jfinec:v:138:y:2020:i:1:p:95-117 | Abstract |
| S37 | Bhootra & Hur (2013), *J. Banking & Finance* 37(10) 3773–3782 | https://econpapers.repec.org/RePEc:eee:jbfina:v:37:y:2013:i:10:p:3773-3782 | Abstract |
| S38 | George, Hwang & Li (2018), *JFE* 128(1) 148–163 | https://www.bauer.uh.edu/tgeorge/papers/GHL-52WHQ.pdf | Abstract in the working paper |
| S39 | Fama & French (2012), *JFE* 105(3) 457–472 | https://econpapers.repec.org/RePEc:eee:jfinec:v:105:y:2012:i:3:p:457-472 | Abstract |
| S40 | Hou, Xue & Zhang (2020), *RFS* 33(5) 2019–2133 | https://econpapers.repec.org/RePEc:oup:rfinst:v:33:y:2020:i:5:p:2019-2133. | Abstract |
| S41 | Jensen, Kelly & Pedersen (2023), *J. Finance* 78(5) 2465–2518 | https://econpapers.repec.org/RePEc:bla:jfinan:v:78:y:2023:i:5:p:2465-2518 | Abstract |
| S42 | Chen & Zimmermann (2022), *Critical Finance Review* 11, 207– | https://econpapers.repec.org/RePEc:now:jnlcfr:104.00000112 | Abstract |
| S43 | Brock, Lakonishok & LeBaron (1992), *J. Finance* 47(5) 1731–1764 | https://econpapers.repec.org/RePEc:bla:jfinan:v:47:y:1992:i:5:p:1731-64 | Abstract |
| S44 | Sullivan, Timmermann & White (1999), *J. Finance* 54(5) 1647–1691 | https://econpapers.repec.org/RePEc:bla:jfinan:v:54:y:1999:i:5:p:1647-1691 | Abstract |
| S45 | Bajgrowicz & Scaillet (2012), *JFE* 106(3) 473–491 | https://econpapers.repec.org/RePEc:eee:jfinec:v:106:y:2012:i:3:p:473-491 | Abstract |
| S46 | Marshall, Qian & Young (2009), *Applied Financial Economics* 19(15) 1213–1221 | https://ideas.repec.org/a/taf/apfiec/v19y2009i15p1213-1221.html | Abstract |
| S47 | Zakamulin (2018), *Int. Review of Finance* 18(2) 317–327 | https://econpapers.repec.org/RePEc:bla:irvfin:v:18:y:2018:i:2:p:317-327 | Abstract |
| S48 | Clare, Seaton, Smith & Thomas (2013), *J. Asset Management* 14(3) 182–194 | https://openaccess.city.ac.uk/17842/8/BLACKBOX%20%20%20SSRN-id2126476.pdf | Accepted version text |
| S49 | Niederhoffer's review of Wilcox & Crittenden, with Crittenden's reply (25 Nov 2005) | https://dailyspeculations.com/vic/trend.html | Page read |
| S49b | Wilcox & Crittenden (2005), "Does Trend Following Work on Stocks?" | https://www.cis.upenn.edu/~mkearns/finread/trend.pdf | **Not readable today**; details from search-tool summaries |
| S50 | Zarattini, Pagani & Wilcox (2025), "Does Trend-Following Still Work on Stocks?" (SSRN 5084316), authors' page | https://concretumgroup.com/does-trend-following-still-work-on-stocks/ | Page read; paper not read |
| S50b | CXO Advisory review of S50 (7 Feb 2025) | https://www.cxoadvisory.com/momentum-investing/all-time-high-trend-following | Free part of the page read |
| S51 | Zarattini & Antonacci, "A Century of Profitable Industry Trends", authors' page | https://concretumgroup.com/a-century-of-profitable-industry-trends/ | Page read; paper not read |
| S52 | Chen, Yu & Wang (2018), *J. Financial Markets* 37, 120–135 | https://econpapers.repec.org/RePEc:eee:finmar:v:37:y:2018:i:c:p:120-135 | Abstract |
| S52b | Search-tool summary of CXO Advisory on the 2013 working paper | https://www.cxoadvisory.com/momentum-investing/stock-price-acceleration-as-a-momentum-investing-enhancement/ | Not opened by me |
| S53 | Ardila-Alvarez, Forrò & Sornette (2015), Swiss Finance Institute RP 15-30 | https://ideas.repec.org/p/chf/rpseri/rp1530.html | Abstract |
| S54 | Lee & Swaminathan (2000), *J. Finance* 55(5) 2017–2069 | https://econpapers.repec.org/RePEc:bla:jfinan:v:55:y:2000:i:5:p:2017-2069 | Abstract (background: "price momentum effects reverse over the next five years, and high (low) volume winners (losers) experience faster reversals") |
| S55 | Wiest (2023), *Financial Markets and Portfolio Management* 37(1), review | https://ideas.repec.org/a/kap/fmktpm/v37y2023i1d10.1007_s11408-022-00417-8.html | Abstract |
| S56 | Sibling reports | `docs/_raw/pine_requests.md`, `docs/_raw/pine_language.md` | Read for Pine limits; not re-verified |
| S57 | Project protocol | `docs/00_protocol.md` §5 (costs), `docs/01_data_inventory.md` | Read |
| S58 | Compile probes and calculation scripts | `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/lit_momentum/pine/m1_signals.pine`, `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/lit_momentum/pine/m2_stops.pine`; `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/lit_momentum/ff_analysis.py`, `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/lit_momentum/ff_vol_ind.py`, `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/lit_momentum/ff_extra.py` (session scratchpad, not permanent) | Written and run today |

Calculation notes for section 2, for anyone re-running it: monthly percent returns as published; t = mean / (sd / √n); Sharpe = mean / sd × √12 on the series shown (long-short series are already excess returns); drawdown from compounding the monthly series; state variables use data to the end of month t−1 only; industry portfolios with missing codes (−99.99) are dropped for that month; volatility scaling uses the last 126 (factor) or 63 (long-only) daily returns ending on the last trading day of month t−1.

---

## 11. Not verified today

| Item | Status |
|---|---|
| Wilcox & Crittenden (2005) paper text: entry and exit rules, trade counts, win rate, CAGR | Could not open the PDF (TLS failure with curl, HTTP 503 with the fetch tool). Everything about it here is second-hand |
| Barroso & Santa-Clara figures 0.53 → 0.97 and their skew/kurtosis numbers | Sharpe pair from a search-tool summary only; other figures not found. My own replication stands in for them |
| Han, Zhou & Zhu stop-loss paper: abstract, exact rules, publication status | SSRN blocked; numbers from one review page and a search-tool summary |
| Lo & Remorov (2017) journal abstract and tables | Only the thesis abstract and a review of the 2015 working paper |
| Frazzini, Israel & Moskowitz (2018) "Trading Costs" abstract and numbers | SSRN blocked, AQR page returned no abstract. The 2012 draft was read instead |
| Cooper, Gutierrez & Hameed (2004) abstract (0.93 vs −0.37) | Search-tool summary only; my replication on French data is independent support |
| Novy-Marx (2012) effect sizes; Gutierrez & Kelley weekly magnitudes; Moreira & Muir (2017) abstract; Grinblatt & Han (2005) | Not read; any statement about them beyond the abstracts quoted is [MEMORY] |
| Han, Yang & Zhou (2013) return and break-even figures | Search-tool summary of a review |
| Post-2001 large-cap evidence on the 52-week high; post-2007 evidence on information discreteness; post-2018 evidence on short-term momentum | Not found today; these are the gaps the hypotheses are meant to close |
| TradingView sector label strings used in `m2_stops.pine` | From memory; they compile as strings but may not match `syminfo.sector` values |
| Whether George & Hwang's 52-week high uses closing prices or intraday highs | Not stated in the passages read |
| The 30% idiosyncratic volatility used in section 5 | Assumption, order of magnitude only |
| Practitioner "trend template" systems | No survivorship-free test known to me; not searched |
| Pine runtime behaviour of the probes (history depth, request limits, repainting) | Compile-checked only |
