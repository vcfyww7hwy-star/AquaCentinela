# Short-horizon reversal and liquidity provision (1 day to 1 month): literature, practitioner rules, and what a Pine script can use

Research date: **2026-11-11 UTC** by the system clock (the project brief calls this working day 2026-11-10). Every URL below was accessed on that date.
Scope: individual US stocks, horizons of 1 day to 1 month; large and liquid names first; what survives costs; what Pine can compute at a bar close.
This report gives no trading recommendation. Nothing in it has been tested on the project's own stock-level data.

## 0. How to read this file

| Tag | Meaning |
|---|---|
| [PAPER] | Read today in the paper itself: "(abs)" = abstract only, "(full)" = full text of the version named in section 2 (often the working-paper version, which can differ from the journal version) |
| [DOC] | Read today in a primary/official source (TradingView documentation; Kenneth French Data Library files). Where marked "own arithmetic", the number is my computation on that primary file |
| [COMPILE] | Confirmed today with TradingView's compiler through `tools/pine_compile.py` (compile only, never runtime). 4 of 15 calls used |
| [SECONDARY] | Third-party page: blog, vendor, summary site, or a sibling report of this project that I did not re-verify |
| [MEMORY] | Recalled from training, **not verified today**; do not rely on it |

"Inference" marks a conclusion I drew; it is not a sourced fact.
Cost yardstick used throughout: the project protocol (`docs/00_protocol.md` §5): 5 bp per side for names with median daily dollar volume of $50M or more, so 10 bp per round trip, 20 bp under the doubled-cost stress; entry at the open of the bar after the signal.

## 1. Bottom line

| # | Finding | Tag |
|---|---|---|
| 1 | **Unconditional short-term reversal in large US stocks has been close to zero, gross, since about 2005–2010.** Top size quintile, value-weighted, 20-day losers minus winners, next-day return: 9–14 bp/day in every block from 1963 to 2004, 4 bp/day in 2005–09, 1–2 bp/day in 2010–19, −1.5 bp/day in 2020–22 (none of the post-2005 blocks is statistically different from zero). The monthly version in the same size quintile is +0.04%/month (t = 0.15) for 1990–2022. | [DOC] French library, own arithmetic (section 3) |
| 2 | Published papers agree once microcaps are removed: one-month reversal earns −0.26%/month (t = −1.31) as a winner-minus-loser decile with NYSE breakpoints and value weights, and is listed among variables that "do not survive our replication" (Hou, Xue, Zhang, 1967–2014); 0.31%/month (t = 1.68) for 1973–2021 and 0.18%/month (t = 0.62) after decimalization (Dai et al.); −2 bp/month among the 500 largest stocks even inside low turnover (Medhat, Schmeling). | [PAPER] (full, WP versions) |
| 3 | What still shows up in large stocks is **conditional**: (a) reversal measured against the industry and with earnings-announcement returns removed (1.08%/month 1973–2021, 0.58%/month, t = 3.29, after decimalization, gross, long-short, about 90% monthly turnover per side); (b) reversal when VIX is high (large, liquid stocks: about zero at low VIX, about 0.1%/day at the 95th percentile of VIX, 1998–2010); (c) short formation and holding windows: 20 bp per 5 days, gross, long-short, top size quintile, 2001–2020. | [PAPER] (full, WP versions): Dai et al.; Nagel; Drechsler, Moreira, Savov |
| 4 | At the protocol's 10 bp round trip, result (c) leaves nothing for a long-only trader in calm markets: 20 bp is the gross long-short spread, so each leg earns roughly 10 bp per 5-day hold before costs. | Inference from [PAPER] figure and protocol cost |
| 5 | **High-turnover large caps continue, they do not reverse, at the one-month horizon.** Winner-minus-loser within the highest-turnover decile: +1.37%/month (t = 4.74), 1963–2018; among the 500 largest stocks +0.42%/month (t = 4.91); megacap version net of half-spreads 0.59%/month (t = 3.10). The reversal in high-turnover names is over within one to two weeks. Fading a month-long, heavily traded move in a large cap is the losing side of this effect. | [PAPER] (full): Medhat, Schmeling (accepted manuscript); Dai et al. |
| 6 | Moves that contain earnings news do not reverse: reversal among firms that announced earnings in the formation month is 0.06%/month (t = 0.30) against 0.51%/month (t = 2.54) for non-announcers. Any "oversold" rule should drop bars inside an earnings window. | [PAPER] (full, WP): Dai et al. Table 1 |
| 7 | The large-cap reversal premium is priced as volatility risk: after adjusting for exposure to VIX changes its pricing error falls from 17 bp to −2 bp per 5 days. Dip-buying is a short-volatility position: it loses when VIX keeps rising after entry, and the loss does not come back within 20 days. | [PAPER] (full, Sept 2021 draft): Drechsler, Moreira, Savov |
| 8 | Practitioner "oversold in an uptrend" rules (Connors RSI(2) and relatives): independent tests show a shrinking edge. Russell 3000, RSI(2) crossing below 1: 0.89% per trade in 2003–07, 0.52% in 2010–18, 0.33% in 2017–18, gross, not drift-adjusted. S&P 500 members 2006–2025, RSI(2) < 10 above the 200-day average: 14.2%/year gross becomes 8.8% at 5 bp per side and 3.6% at 10 bp per side, against 8.4% for SPY price-only; 20 days after a dip the average return in excess of SPY is +0.06% (all dips), +0.49% when VIX ≥ 20, −0.08% when VIX < 20. No peer-reviewed out-of-sample test of these rules on survivorship-free single-stock data was found. | [SECONDARY] Alvarez; QuanterLab |
| 9 | Pine can compute time-series versions of all the conditioning variables on one chart (residual versus a sector ETF, earnings-bar exclusion, overnight/intraday split, relative volume, VIX state, RSI(2), IBS, ConnorsRSI by hand). It cannot compute cross-sectional ranks inside a script; `ta.crsi` does not exist; float is a current snapshot, so historical turnover on a chart is not point-in-time. | [COMPILE]; [SECONDARY] sibling report for request limits and `syminfo.*` |
| 10 | Verdict for the project: reversal is **not** a stand-alone edge in liquid stocks. It is a conditional setup (non-news, industry-relative, short hold, high-VIX state, sized as a short-volatility bet) with a low prior, plus two filters of general use: exclude earnings-window moves; do not fade high-turnover month-long moves. | Inference |

## 2. Sources

Academic. "Read" says exactly what I opened today.

| ID | Authors, year, venue | Read today | URL |
|---|---|---|---|
| A1 | Jegadeesh 1990, J. Finance 45(3) 881–898 | abs | https://ideas.repec.org/a/bla/jfinan/v45y1990i3p881-98.html |
| A2 | Lehmann 1990, QJE 105(1) 1–28 | abs; NBER WP 2533 (scan) for sample dates | https://ideas.repec.org/a/oup/qjecon/v105y1990i1p1-28..html ; https://www.nber.org/system/files/working_papers/w2533/w2533.pdf |
| A3 | Lo, MacKinlay 1990, RFS 3(2) 175–205 | abs | https://ideas.repec.org/a/oup/rfinst/v3y1990i2p175-205.html |
| A4 | Campbell, Grossman, Wang 1993, QJE 108(4) 905–939 | abs | https://ideas.repec.org/a/oup/qjecon/v108y1993i4p905-939..html |
| A5 | Conrad, Hameed, Niden 1994, J. Finance 49(4) 1305–1329 | abs | https://ideas.repec.org/a/bla/jfinan/v49y1994i4p1305-29.html |
| A6 | Cooper 1999, RFS 12(4) 901–935 | abs | https://ideas.repec.org/a/oup/rfinst/v12y1999i4p901-35.html |
| A7 | Llorente, Michaely, Saar, Wang 2002, RFS 15(4) 1005–1047 | abs | https://ideas.repec.org/a/oup/rfinst/v15y2002i4p1005-1047.html |
| A8 | Chan 2003, JFE 70(2) 223–260 | no abstract on IDEAS; search-engine summary of the abstract only | https://ideas.repec.org/a/eee/jfinec/v70y2003i2p223-260.html |
| A9 | Avramov, Chordia, Goyal 2006, J. Finance 61(5) 2365–2394 | abs | https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html |
| A10 | Khandani, Lo 2007, "What Happened to the Quants in August 2007?", draft of 20 Sept 2007 | full | https://web.mit.edu/Alo/www/Papers/august07.pdf |
| A11 | Kaniel, Saar, Titman 2008, J. Finance 63(1) 273–310 | abs | https://ideas.repec.org/a/bla/jfinan/v63y2008i1p273-310.html |
| A12 | Gutierrez, Kelley 2008, J. Finance 63(1) 415–447 | abs | https://ideas.repec.org/a/bla/jfinan/v63y2008i1p415-447.html |
| A13 | Hameed, Kang, Viswanathan 2010, J. Finance 65(1) 257–293 | abs | https://ideas.repec.org/a/bla/jfinan/v65y2010i1p257-293.html |
| A14 | Tetlock 2010, RFS 23(9) 3520–3557; Tetlock 2011, RFS 24(5) 1481–1512 | abs (both) | https://ideas.repec.org/a/oup/rfinst/v23y2010i9p3520-3557.html ; https://ideas.repec.org/a/oup/rfinst/v24y2011i5p1481-1512.html |
| A15 | Nagel 2012, "Evaporating Liquidity", RFS 25(7) 2005–2039 | abs; full text of NBER WP 17653 (Dec 2011) | https://ideas.repec.org/a/oup/rfinst/v25y2012i7p2005-2039.html ; https://www.nber.org/system/files/working_papers/w17653/w17653.pdf |
| A16 | de Groot, Huij, Zhou 2012, J. Banking & Finance 36(2) 371–382 | abs; full text of the 2011 WP | https://ideas.repec.org/a/eee/jbfina/v36y2012i2p371-382.html ; https://repub.eur.nl/pub/25718/AnotherLook_2011.pdf |
| A17 | Berkman, Koch, Tuttle, Zhang 2012, JFQA 47(4) 715–741 | abs | https://ideas.repec.org/a/cup/jfinqa/v47y2012i04p715-741_00.html |
| A18 | Blitz, Huij, Lansdorp, Verbeek 2013, J. Financial Markets 16(3) 477–504 | abs | https://ideas.repec.org/a/eee/finmar/v16y2013i3p477-504.html |
| A19 | Da, Liu, Schaumburg 2014, Management Science 60(3) 658–674 | abs; full text of NY Fed Staff Report 513 (Sept 2011) | https://ideas.repec.org/a/inm/ormnsc/v60y2014i3p658-674.html ; https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr513.pdf |
| A20 | So, Wang 2014, JFE 114(1) 20–35 | abs only (MIT DSpace full text returned HTTP 429 four times) | https://ideas.repec.org/a/eee/jfinec/v114y2014i1p20-35.html |
| A21 | Hendershott, Menkveld 2014, "Price pressures", JFE 114(3) 405–423 | abs; one sentence quoted in A35 footnote 12 | https://ideas.repec.org/a/eee/jfinec/v114y2014i3p405-423.html |
| A22 | Chordia, Subrahmanyam, Tong 2014, J. Accounting & Economics 58(1) 41–58 | abs | https://ideas.repec.org/a/eee/jaecon/v58y2014i1p41-58.html |
| A23 | Hameed, Mian 2015, JFQA 50(1–2) 89–117 | abs | https://ideas.repec.org/a/cup/jfinqa/v50y2015i1-2p89-117_00.html |
| A24 | McLean, Pontiff 2016, J. Finance 71(1) 5–32 | published first page (abstract) | https://gwern.net/doc/economics/2016-mclean.pdf |
| A25 | Novy-Marx, Velikov 2016, RFS 29(1) 104–147 | abs; full text of NBER WP 20721 (Dec 2014) | https://ideas.repec.org/a/oup/rfinst/v29y2016i1p104-147..html ; https://www.nber.org/system/files/working_papers/w20721/w20721.pdf |
| A26 | Cheng, Hameed, Subrahmanyam, Titman 2017, JFQA 52(1) 143–173 | abs | https://ideas.repec.org/a/cup/jfinqa/v52y2017i01p143-173_00.html |
| A27 | Ben-David, Franzoni, Moussawi 2018, J. Finance 73(6) 2471–2535 | abs | https://ideas.repec.org/a/bla/jfinan/v73y2018i6p2471-2535.html |
| A28 | Aboody, Even-Tov, Lehavy, Trueman 2018, JFQA 53(2) 485–505 | abs | https://ideas.repec.org/a/cup/jfinqa/v53y2018i02p485-505_00.html |
| A29 | Lou, Polk, Skouras 2019, JFE 134(1) 192–213 | abs | https://ideas.repec.org/a/eee/jfinec/v134y2019i1p192-213.html |
| A30 | Baltussen, van Bekkum, Da 2019, JFE 132(1) 26–48 | abs | https://ideas.repec.org/a/eee/jfinec/v132y2019i1p26-48.html |
| A31 | Hou, Xue, Zhang 2020, "Replicating Anomalies", RFS 33(5) 2019–2133 | abs; full text of NBER WP 23394 | https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2019-2133..html ; https://www.nber.org/system/files/working_papers/w23394/w23394.pdf |
| A32 | Bogousslavsky 2021, JFE 141(1) 172–194 | abs | https://ideas.repec.org/a/eee/jfinec/v141y2021i1p172-194.html |
| A33 | Brown, Davies, Ringgenberg 2021, Review of Finance 25(4) 937–972 | abs | https://ideas.repec.org/a/oup/revfin/v25y2021i4p937-972..html |
| A34 | Drechsler, Moreira, Savov, "Liquidity and Volatility", draft of Sept 2021 (NBER WP 27959 is the 2020 version) | full (Sept 2021 draft) | https://pages.stern.nyu.edu/~asavov/alexisavov/Alexi_Savov_files/DMS_Liquidity_and_Volatility.pdf |
| A35 | Medhat, Schmeling 2022, "Short-term Momentum", RFS 35(3) 1480–1526 | abs; full text of the accepted manuscript (v27) | https://ideas.repec.org/a/oup/rfinst/v35y2022i3p1480-1526..html ; https://openaccess.city.ac.uk/id/eprint/31278/1/MS_short_term_mom_v27.pdf |
| A36 | Akbas, Boehmer, Jiang, Koch 2022, JFE 145(3) 850–875 | abs | https://ideas.repec.org/a/eee/jfinec/v145y2022i3p850-875.html |
| A37 | Barardehi, Bogousslavsky, Muravyev 2022, "What Drives Momentum and Reversal? Evidence from Day and Night Signals", working paper | abstract excerpts on the Illinois Experts page; conference slides (figures not machine-readable) | https://experts.illinois.edu/en/publications/what-drives-momentum-and-reversal-evidence-from-day-and-night-sig/ ; https://jacobslevycenter.wharton.upenn.edu/wp-content/uploads/2022/09/Bogousslavsky.pdf |
| A38 | Dai, Medhat, Novy-Marx, Rizova 2024, "Reversals and the Returns to Liquidity Provision", Financial Analysts Journal 80(2) 122–151 | abs; full text of the WP dated 26 Jan 2023 | https://ideas.repec.org/a/taf/ufajxx/v80y2024i2p122-151.html ; https://mysimon.rochester.edu/novy-marx/research/RRLP.pdf |
| A39 | Della Corte, Kosowski, Wang, "Market Closure and Short-Term Reversal", Nov 2015 draft marked "incomplete, please do not distribute" | full | https://www.cicfconf.org/sites/default/files/paper_357.pdf |
| A40 | Gervais, Kaniel, Mingelgrin 2001, J. Finance 56(3) 877–919 | abs | https://ideas.repec.org/a/bla/jfinan/v56y2001i3p877-919.html |
| A41 | Kenneth French Data Library: `25_Portfolios_ME_Prior_1_0` (monthly and daily), `10_Portfolios_Prior_1_0`, `F-F_ST_Reversal_Factor` (files state "created using the 202609 CRSP database") | files downloaded and processed | https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/25_Portfolios_ME_Prior_1_0_Daily_CSV.zip (and the same folder for the other three names with `_CSV.zip`) |

Practitioner and documentation.

| ID | Source | URL |
|---|---|---|
| P1 | StockCharts ChartSchool, "RSI(2)" (describes Connors' rules) | https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2 |
| P2 | TradingView Help Center, "Connors RSI (CRSI)" | https://www.tradingview.com/support/solutions/43000502017-connors-rsi-crsi/ |
| P3 | Cesar Alvarez (co-author of Connors' 2008 book), Alvarez Quant Trading blog, posts of 19 Aug 2015 and 13 Mar 2019 | https://alvarezquanttrading.com/blog/the-health-of-stock-mean-reversion-dead-dying-or-doing-just-fine/ ; https://alvarezquanttrading.com/blog/how-is-mean-reversion-doing-dead-shrinking-or-doing-just-fine/ |
| P4 | Empirica Lab (Substack), note EL-R-2026-302 dated 11 Oct 2026, RSI(2) on SPY | https://empiricalab.substack.com/p/connors-rsi2-spy |
| P5 | QuanterLab, S. Girgin, "Navigating Mean Reversion: Breaking Down the Base Mechanism", compiled 26 Sept 2026 | https://quanterlab.com/research/navigating-mean-reversion-breaking-down-the-base-mechanism |
| P6 | StatOasis, "Mean Reversion: 40 Ways to Buy the Dip, and the 16 That Held Up", 5 Nov 2026 | https://statoasis.com/overfit/research/mean-reversion-buy-the-dip-ranked |
| P7 | Quantpedia strategy pages (summaries of A16 and A20) | https://quantpedia.com/strategies/short-term-reversal-in-stocks ; https://quantpedia.com/strategies/reversal-during-earnings-announcements |
| P8 | Sibling reports of this project (Pine limits, symbols, earnings fields) | `docs/_raw/pine_requests.md`, `docs/_raw/pine_language.md` |
| P9 | Compile tests for this report | `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/lit_reversal/rev_proto.pine`, `rev_proto2.pine`, `neg_crsi.pine` |

## 3. Own check on primary data: the Kenneth French short-term-reversal portfolios

Why: the French library is the project's survivorship-free long record (protocol §2.2). It answers the brief's central question (large stocks, recent decades) without relying on any author's sample choice.
Protocol note: per §2.2 the data was **cut at 2022-12-30**; nothing after that date was read into a statistic. These are descriptive replications of a published factor, at portfolio level. They are not stock-level trials, but the orchestrator may want them noted in `RESEARCH_LOG.md`.
Method: value-weighted returns from the files in A41. "Big" is the top market-cap quintile of the 5×5 sort (file header: "intersections of 5 ME portfolios and 5 prior return portfolios"); that the quintile breakpoints are NYSE breakpoints is the library's usual convention and was not re-read today [MEMORY]. Daily file header: "The portfolios are constructed daily. ME is market cap at the end of the previous day. PRIOR_RET is from − 20 to − 1." So the daily numbers are: sort every day on the return of the previous 20 trading days, hold one day, close to close. t-statistics on daily series use Newey–West with 5 lags. Scripts: `/tmp/claude-0/-home-user-aquacentinela/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/lit_reversal/french_stats.py`, `french_stats2.py`, `french_stats3.py`.

### 3.1 Daily-rebalanced 20-day reversal, next-day return, loser quintile minus winner quintile, by size quintile (bp per day, gross) [DOC, own arithmetic]

| Period | ME1 small | ME2 | ME3 | ME4 | ME5 big |
|---|---|---|---|---|---|
| 1963-07 to 1989-12 | 31.5 (t 29.1) | 17.4 (17.5) | 15.3 (15.4) | 14.5 (14.3) | 11.0 (9.6) |
| 1990-01 to 2001-04-06 | 64.0 (30.5) | 15.2 (7.5) | 7.1 (3.2) | 6.0 (2.5) | 12.4 (5.2) |
| 2001-04-09 to 2010-12 | 17.8 (7.0) | 5.2 (2.2) | 3.6 (1.4) | 4.9 (1.7) | 7.6 (2.0) |
| 2011-01 to 2022-12 | 6.6 (3.2) | 3.7 (1.7) | 1.9 (0.9) | 2.6 (1.2) | **0.6 (0.2)** |

### 3.2 Big quintile only, shorter blocks (bp per day, gross) [DOC, own arithmetic]

| Block | Losers − winners | Losers − middle quintile (long-leg proxy) |
|---|---|---|
| 1963–1969 | 12.9 (t 7.1) | 7.0 (5.4) |
| 1970–1979 | 11.8 (6.8) | 5.3 (3.8) |
| 1980–1989 | 9.1 (4.3) | 4.7 (3.0) |
| 1990–1994 | 10.9 (4.3) | 5.4 (2.8) |
| 1995–1999 | 12.2 (3.6) | 6.5 (2.7) |
| 2000–2004 | 14.5 (3.0) | 6.5 (1.7) |
| 2005–2009 | 4.2 (0.7) | 1.5 (0.3) |
| 2010–2014 | 1.1 (0.4) | 0.4 (0.2) |
| 2015–2019 | 2.2 (0.9) | 0.6 (0.3) |
| 2020–2022 | −1.5 (−0.2) | −1.3 (−0.2) |

Reading: for 40 years the big-stock loser quintile beat the middle quintile by about 5–7 bp on the next day. Since 2005 the estimate is 0–2 bp and indistinguishable from zero. A long-only "buy the 20-day loser" rule in large caps has had no measurable next-day edge for roughly two decades, before any cost.

### 3.3 Monthly formation, monthly holding (% per month, gross) [DOC, own arithmetic]

| Period | F-F ST_Rev factor | Big quintile, losers − winners | Small quintile, losers − winners | Deciles D1−D10, value-weighted | Deciles D1−D10, equal-weighted |
|---|---|---|---|---|---|
| 1926-07 to 1962-12 | 1.04 (t 5.6) | 0.42 (1.5) | 3.81 (11.1) | 1.72 (5.3) | 3.77 (10.6) |
| 1963-07 to 1989-12 | 0.76 (5.3) | 0.40 (1.8) | 1.75 (9.9) | 0.72 (3.0) | 2.38 (11.3) |
| 1990-01 to 2000-12 | −0.02 (−0.1) | −0.31 (−0.7) | 0.41 (1.2) | −0.48 (−0.9) | 1.85 (4.1) |
| 2001-05 to 2010-12 | 0.31 (1.0) | 0.56 (1.1) | 0.23 (0.6) | 0.18 (0.3) | 1.03 (2.1) |
| 2011-01 to 2022-12 | 0.15 (0.6) | −0.31 (−0.8) | 0.20 (0.6) | −0.04 (−0.1) | 0.37 (0.8) |
| 1990-01 to 2022-12 | 0.22 (1.2) | 0.04 (0.15) | 0.38 (1.7) | not computed | not computed |

Reading: the monthly effect in the top size quintile was never statistically reliable (t below 2 in every period, including 1926–1989). The headline numbers of the early literature come from equal weighting and small stocks, and even the equal-weighted spread has faded to 0.37%/month (t = 0.8) in 2011–2022.

Limits of this check: portfolio level only; quintile, not decile, sorts in the size-split files; formation windows are 20 days (daily file) and one calendar month (monthly file), so it says nothing direct about 1-day or 5-day formation windows or about conditional versions; close-to-close returns starting at the formation close, which a trader entering at the next open does not get.

## 4. Findings

Each block: claim; effect size, universe, period; source; later evidence; costs for liquid US stocks; mechanism and who is on the other side; Pine; verdict.

### F1. Monthly reversal (Jegadeesh 1990)

| Item | Content |
|---|---|
| Claim | Last month's losers beat last month's winners next month. |
| Effect size | "The difference between the abnormal returns on the extreme decile portfolios over the period 1934-87 is 2.49 percent per month." [PAPER] (abs) A1. Hou, Xue, Zhang describe the original as "−1.99% (t = −12.55) reported in Jegadeesh (1990) based on NYSE-Amex-NASDAQ breakpoints and equal-weighted returns" [PAPER] (full, WP) A31. |
| Later evidence | With NYSE breakpoints and value weights the winner-minus-loser decile "earns on average only −0.26% per month (t = −1.31)"; it is named among "prominent variables that do not survive our replication" (Jan 1967–Dec 2014 in the WP version) [PAPER] (full, WP) A31. 0.31%/month (t = 1.68), 1973–2021, value-weighted NYSE quintiles; 0.18%/month (table t = 0.62; the text prints 0.18, a typo) for May 2001–Dec 2021 [PAPER] (full, WP) A38. Sample of analyst-covered stocks ("roughly 75% of the entire US equity market capitalization"), Jan 1982–Mar 2009: 0.67%/month (t = 2.53), three-factor alpha 0.33% (t = 1.37) [PAPER] (full, WP) A19. French library: section 3.3 [DOC]. |
| Costs | Short-run reversals, all stocks, value-weighted NYSE deciles, July 1963–Dec 2012: gross 0.37%/month (t = 1.71), turnover 90.9%/month per side, trading cost 1.65%/month (Hasbrouck effective spreads), net −1.28%/month (t = −6.02). Large caps (above the NYSE median), in the cost-mitigated form that enters at the extreme decile and holds until a stock leaves the top half: gross 0.18% (t = 0.88), net −0.51% (t = −2.54) [PAPER] (full, WP) A25 Tables 3 and 13. "The average cost of the conventional STREV strategy is 0.56% per month, which subsumes its average gross return" [PAPER] (full) A35 fn 18. Does not survive. |
| Mechanism, other side | Original reading: overreaction. Current majority reading: price concession to whoever demanded immediacy; the reversal is the liquidity provider's pay (F4). |
| Pine | Trivial (`close/close[21]-1`), but only as a per-symbol number. |
| Verdict | **REJECT** as a trade in liquid stocks (no gross effect since 1990 in the top size quintile; negative net everywhere). CONTEXT: do not treat "down a lot this month" as an edge by itself. |

### F2. Weekly reversal (Lehmann 1990) and the claim that it survives costs in large caps

| Item | Content |
|---|---|
| Claim | Last week's losers beat last week's winners next week, by more than plausible costs. |
| Effect size | "'winners' and 'losers' one week experience sizeable return reversals the next week in a way that reflects apparent arbitrage profits which persist after corrections for bid-ask spreads and plausible transactions costs" [PAPER] (abs) A2. Sample: NYSE and AMEX stocks, July 1962–December 1986 [PAPER] (WP scan) A2. Exact weekly profit figures were not legible in the scan; not quoted. |
| Large caps, 1990–2009 | Quintile long-short on one-week return, rebalanced daily. 1,500 largest US stocks: gross 61.7 bp/week, turnover 677%/week, net −66.1 bp/week (Keim–Madhavan costs) and −103.7 bp/week (Nomura costs). 500 largest: net −3.0 bp/week with Nomura costs, which "consume roughly 75 basis points of the strategy's gross return". With a turnover-reducing construction ("smart"): net +30.5 bp/week (500 largest) and +53.1 bp/week (100 largest); in 2000–2009 alone 22.1 and 59.0 bp/week [PAPER] (full, WP) A16. |
| Later evidence | None found that extends A16 past 2009. The French big-quintile series (section 3.2, 20-day formation) drops to about zero from 2005–2010 on [DOC]. Top size quintile, 1-day formation, 5-day hold, April 2001–May 2020: 20 bp per 5 days [PAPER] (full) A34, far below A16's roughly 70 bp/week gross for the 500 largest. Inference: the A16 result is a 1990–2009 result. |
| Costs | A16's net figures rest on institutional cost models; the Keim–Madhavan estimates are negative for the most liquid volume deciles (Table 1 of A16 shows −20 bp for the top decile) and the authors floor them at zero [PAPER] (full, WP) A16. At the protocol's 10 bp round trip, a daily-rebalanced weekly strategy with 300–700% weekly turnover is not something an alert-driven trader can run. |
| Mechanism, other side | As F4. Lo and MacKinlay add that part of contrarian profit is lead-lag between stocks, not own-stock reversal: "the returns of large stocks lead those of smaller stocks" [PAPER] (abs) A3. |
| Pine | 5-bar return on a daily chart, or 1-bar return on a weekly chart. |
| Verdict | Unconditional: **REJECT** for liquid stocks. The 5-day window is kept as the formation window for the conditional hypotheses (H2–H4), because that is where the remaining large-cap evidence sits (A34, A38). |

### F3. Daily reversal and its decline after the 1990s

| Item | Content |
|---|---|
| Claim | A one-day contrarian portfolio earned very high gross returns in the 1990s, almost all of it in small stocks, and decayed steadily. |
| Effect size | Lo–MacKinlay contrarian weights, all US stocks, average daily return by year: 1.38% (1995), 0.44% (2000), 0.26% (2005), 0.13% (2007 to 31 Aug). Largest market-cap decile: 0.04% (1995), 0.02% (1996), 0.14% (1997), 0.10% (1998), 0.06% (1999), 0.03% (2000), −0.11% (2001), 0.09% (2002), 0.05% (2003), −0.01% (2004), 0.02% (2005), 0.00% (2006), −0.04% (2007). Smallest decile: 3.57% (1995) to 0.57% (2007) [PAPER] (full) A10 Table 2. The authors: "this return is unrealistic because it ignores a number of market frictions". |
| Other measurements | Jan 1998–Dec 2010, five overlapping daily lags: 0.30%/day with transaction prices, 0.18%/day with quote midpoints; "the mean returns are only about half as big when quote-midpoints are used", so about half is bid-ask bounce [PAPER] (full, WP) A15 Table 1. S&P 500 and S&P 100 members, 1993–2014, close-to-close daily reversal: annualised Sharpe "slightly above 1.00" and 0.47, gross [PAPER] (full, incomplete draft) A39. |
| Why it declined | "the majority of the anomalies have attenuated and the average returns from a portfolio strategy based on prominent anomalies have approximately halved after decimalization", linked to "hedge fund assets under management, short interest and aggregate share turnover" [PAPER] (abs) A22. Khandani and Lo name "increased competition, changes in market structure, improvements in trading technology and electronic connectivity, the growth in assets devoted to this type of strategy" [PAPER] (full) A10. Across 97 predictors, "Portfolio returns are 26% lower out-of-sample and 58% lower post-publication" [PAPER] (abs) A24. |
| Costs | For the largest decile the gross daily figure is 0–10 bp against a 10 bp round trip. Does not survive. |
| Mechanism, other side | Market-making. Half-life of price pressure on NYSE: 0.92 days on average, 0.49% in size [PAPER] (abs) A21; "Price pressure for the quintile of largest stocks is 17 basis points with a half life of 0.54 days. For the smallest-stocks quintile, it is 118 basis points with a half life of 2.11 days" (A21 p. 406 as quoted in A35 fn 12) [PAPER] (full) A35. Inference: with a half-life of about half a trading day in the largest stocks, much of the pressure can be gone before an order placed for the next open is filled. |
| Pine | Trivial. |
| Verdict | **REJECT** as a trade. CONTEXT: one-day pops and drops in liquid names are not a signal. |

### F4. Reversal as pay for liquidity provision; it rises with VIX and after market declines

| Item | Content |
|---|---|
| Claim | Reversal returns proxy the return to supplying liquidity; that return is strongly predictable with VIX. |
| Effect size | Daily reversal return regressed on VIX five days earlier, Jan 1998–Dec 2010: coefficient 0.22 (s.e. 0.02) per one point of "normalized" VIX (VIX divided by √250, so one point is about 16 points of quoted VIX); daily adjusted R² 0.07; monthly adjusted R² 56% (transaction prices), 25% (midquotes), 7% (industry portfolios). Conditional annualised Sharpe ratio rises by 0.13 per VIX point [PAPER] (full, WP) A15. |
| Large, liquid stocks | "for large, liquid, low-volatility stocks, reversal strategy profits are very close to zero when VIX is low … In times of high VIX, however, even the largest, most liquid, lowest-volatility stocks exhibit statistically and economically significant reversal strategy returns. The magnitude of the return is on the order of about 0.1% per day" (fitted values at the 5th and 95th percentiles of VIX) [PAPER] (full, WP) A15 Fig. 4. |
| Replication | Top size quintile, April 2001–May 2020: correlation of 46% between VIX and the next 60 days' average reversal return; predictive R² 3.45% at a 5-day horizon; "the main result in Nagel (2012) holds for large stocks" [PAPER] (full) A34. Intra-industry reversals "are stronger following aggregate market declines and volatile times" [PAPER] (abs) A23. "economically significant returns to supplying liquidity following periods of large drops in market valuations" [PAPER] (abs) A13. S&P 500 members 2006–2025: 20 days after an RSI(2) dip the excess over SPY is +0.49% when VIX ≥ 20 and −0.08% otherwise; the page reports that the VIX-gated book's advantage is concentrated in 2020–2022 and that without those years the two books grew at the same pace [SECONDARY] P5. |
| Risk reading | The large-cap strategy "has an average five-day return of 20 bps, or about 10% per year, and an annual Sharpe ratio of 0.5"; "a one-point increase in VIX induces a 20-bps drop in the strategy's return"; after pricing that exposure with the option-market variance premium the large-cap pricing error "drops from 17 to −2 bps"; a VIX shock one day after formation costs 17 bp and "settles at 19 bps after twenty trading days", i.e. it is not recovered [PAPER] (full) A34. The unit of "one point" of VIX or VIX-squared differs between passages of the draft; I could not pin the scaling down, so use these as signs and orders of magnitude only. |
| Costs | High-VIX large-cap figure of about 0.1%/day is a long-short spread across five overlapping one-day lags, gross. Halved for one leg and held about five days it is of the order of 25 bp per trade against a 10–20 bp round trip. Marginal, and available on only a small share of days. Inference. |
| Mechanism, other side | "withdrawal of liquidity supply … consistent with theories of liquidity provision by financially constrained intermediaries" [PAPER] (abs) A15. Liquidity provision "is a bet against private information: if private information turns out to be higher than expected, liquidity providers lose" [PAPER] (full) A34. The counterparty of a dip-buyer is whoever needs to sell now: institutions under redemption or risk limits ("fire sales more likely demand liquidity", A19 abs), index and ETF arbitrage flow (F13). Competing on the same side: market makers, statistical-arbitrage funds, and individuals, who "tend to buy stocks following declines … consistent with the notion that risk-averse individuals provide liquidity to meet institutional demand for immediacy" [PAPER] (abs) A11. When VIX is low the competition is enough that "the expected return from liquidity provision is close to zero for all but the lowest quality stocks" [PAPER] (full, WP) A15. |
| Pine | `request.security("CBOE:VIX", "1D", close[1], lookahead = barmerge.lookahead_on)` compiles [COMPILE] P9. `CBOE:VIX` daily history from 1990-01-03 [SECONDARY] P8. |
| Verdict | **CANDIDATE** as a gate (H2) and **CONTEXT** as a risk input (H12): size dip positions as short-volatility exposure; several simultaneous dip positions are one bet. |

### F5. Size: where the effect lives

| Item | Content |
|---|---|
| Claim | Reversal is much larger in small, illiquid stocks; among the rest it varies little with size. |
| Evidence | "while reversals are much larger among microcap stocks (bottom NYSE size quintile), there are almost no differences across the other size quintiles, which together account for 97% of market capitalization … the larger microcap spreads are primarily driven by strong first-day effects" [PAPER] (full, WP) A38. Five-day returns of the extreme-decile strategy by size quintile, 2001–2020: 78, 40, 15, 16, 20 bp (small to big); Sharpe 0.90, 0.72, 0.32, 0.37, 0.50 [PAPER] (full) A34 Table 3. Low-turnover reversal: −2.04%/month in microcaps, −0.74%/month in megacaps, −2 bp/month in the 500 largest [PAPER] (full) A35. French library: section 3.1 [DOC]. "The largest reversals … occur in high turnover, low liquidity stocks … the contrarian trading strategy profits are smaller than the likely transactions costs" [PAPER] (abs) A9. |
| Contested | A16 states reversal profits "appear to be the highest" among the largest stocks (1990–2009). A38 reports that outside the US "the largest stocks surprisingly exhibit the strongest reversals". |
| Costs | The small-stock effect does not survive: "contrarian trading strategy profits are smaller than the likely transactions costs" [PAPER] (abs) A9; microcap high-turnover strategies turn "severely negative" net [PAPER] (full, WP) A25. Part of it is bid-ask bounce, which "does not impact large stocks whose bid-ask spreads are very small" [PAPER] (full) A34 fn 19. |
| Mechanism, other side | Fewer and more capital-constrained liquidity providers in small names; in large names competition among providers removes the premium in calm markets (F4). |
| Pine | Size itself is not needed on a chart; the protocol's dollar-volume buckets (`close × volume`, 60-bar median) are the practical proxy. |
| Verdict | **CONTEXT**. Any backtest whose result leans on names below the protocol's $20M–$50M dollar-volume buckets should be read as the small-cap effect, which costs remove. |

### F6. Industry-relative, residual and announcement-adjusted reversal

| Item | Content |
|---|---|
| Claim | The raw reversal is weak because it is short two continuation effects: one-month industry momentum and post-earnings drift. Remove both and the liquidity-driven part is large. |
| Effect size | Value-weighted, NYSE quintiles, Jan 1973–Dec 2021, %/month: raw reversal 0.31 (t 1.68); industry-relative (stock minus its Fama–French 49 industry) 0.74 (5.40); industry-relative with the three-day earnings-announcement abnormal return removed ("IRRX") 1.08 (9.35). Raw reversal regressed on IRRX, PEAD and industry momentum: alpha 0.13 (1.73), R² 87%. May 2001–Dec 2021: raw 0.18 (0.62), industry-relative 0.20 (0.94), IRRX 0.58 (3.29); "the returns to IMOM are negligible post-decimalization", so the gain now comes from removing announcement returns [PAPER] (full, WP) A38 Tables 2, A2. |
| Related | Within-industry reversal 1.20%/month (t 5.87), three-factor alpha 0.92%; reversal on the part of return not explained by analyst-forecast revisions 1.57%/month (t 9.48), alpha 1.34%; profit "accrues mainly during the first month … 0.40% (t-value = 2.51) during the second month. Beyond that … essentially zero"; Jan 1982–Mar 2009 [PAPER] (full, WP) A19. A38 fn 5 notes that A19's results "are for equal-weighted portfolio returns". "intra-industry return reversals that are larger in magnitude, consistently present over time, and prevalent across subgroups of stocks, including large and liquid stocks" [PAPER] (abs) A23. Residual reversal (residual to Fama–French factors) earns "risk-adjusted returns that are twice as large" and is profitable net of costs "even when we restrict our sample to large-cap stocks over the post-1990 period" [PAPER] (abs) A18. |
| Costs | A19's own estimate: 80.5 bp/month from quoted spreads of 46 and 43 bp and about 90% turnover, leaving alpha of about 0.54%/month (t 3.9) [PAPER] (full, WP) A19. Independent estimate, July 1963–Dec 2012: industry-relative reversals gross 0.98%/month, cost 1.78%, net −0.80% (t −4.73); large caps (cost-mitigated buy/hold-spread form) gross 0.61% (t 4.08), net −0.12% (t −0.85). Restricted to low-volatility stocks: gross 1.25%, cost 1.06%, net 0.19% (t 1.41); large caps gross 0.92% (t 7.83), net 0.31% (t 2.73) [PAPER] (full, WP) A25 Tables 3, 13. A38 reports no net figures and says "Actively exploiting these reversals is certainly less profitable … investors can benefit from incorporating short-run reversals into their rebalancing process". So: as a monthly long-short portfolio, net is zero to slightly positive in large caps; as an entry-timing input it costs nothing extra. |
| Mechanism, other side | Returns relative to peers with no news attached are the cleanest proxy for order-flow pressure; "the public information component in returns adds noise unrelated to inventory imbalances" (Nagel, quoted in A38 fn 3). Long side: liquidity shocks; short side: sentiment and short-sale limits [PAPER] (abs) A19. A long-only trader uses only the liquidity side. |
| Pine | One `request.security` for a sector ETF on the chart timeframe, daily residual `r − r_ETF`, sum over the window with announcement bars set to zero, scale by the 63-bar standard deviation of the daily residual: compiles [COMPILE] P9 (`rev_proto2.pine`). Limits: 11 SPDR sector ETFs are a much coarser peer group than 49 industries; `syminfo.sector` uses TradingView's own taxonomy, so mapping a stock to an ETF needs a hand-made table or a user input [SECONDARY] P8; a beta of 1 to the ETF is assumed unless a rolling beta is added. |
| Verdict | **CANDIDATE** (H3), and the default definition of "dip" for every other hypothesis here. |

### F7. Reversal conditional on trading volume (one day to one week)

| Item | Content |
|---|---|
| Claim | Volume tells liquidity-driven moves from information-driven ones. |
| Evidence | "For both stock indexes and individual large stocks, the first-order daily return autocorrelation tends to decline with volume … a stock price decline on a high-volume day is more likely than a stock price decline on a low-volume day to be associated with an increase in the expected stock return" [PAPER] (abs) A4. "returns generated by risk-sharing trades tend to reverse themselves, while returns generated by speculative trades tend to continue themselves"; the volume effect on autocorrelation depends on "the extent of informed trading" [PAPER] (abs) A7. Weekly, Lehmann-type strategy: "high-transaction securities experience price reversals, while the returns of low-transactions securities are positively autocovarying" [PAPER] (abs) A5. Weekly, large-cap NYSE/AMEX: "decreasing-volume stocks experience greater reversals. Increasing-volume stocks exhibit weaker reversals and positive autocorrelation" [PAPER] (abs) A6. "The largest reversals … occur in high turnover, low liquidity stocks" [PAPER] (abs) A9. |
| Contested | A5 and A6 point in opposite directions at the same weekly horizon. A38 explains part of A9: "Skipping a day prior to formation … ignoring the large first-day effects observed for the least liquid stocks is misleading". A7 implies the sign is stock-specific. Effect sizes for large caps after 2000 were not found. |
| Related, other direction | "stocks experiencing unusually high (low) trading volume over a day or a week tend to appreciate (depreciate) over the course of the following month" [PAPER] (abs) A40: a volume effect that does not depend on the sign of the day's return. |
| Costs | Unknown for liquid stocks; no net figure found. |
| Mechanism, other side | High volume with no news: someone needed to trade, so the price concession is larger and reverts (A4). High volume with private information: the move continues (A7). The trader cannot see which, hence F10 and F11 as tie-breakers. |
| Pine | `volume / ta.sma(volume, 63)`; `ta.sma(volume, n) / ta.sma(volume, 63)` for a window: compiles [COMPILE] P9. Whether a chart's daily volume is consolidated or primary-exchange volume depends on the data feed [MEMORY]; not checked here. |
| Verdict | **CANDIDATE**, low prior, sign to be established first (H6). |

### F8. Short-term momentum in high-turnover stocks (Medhat, Schmeling 2022)

| Item | Content |
|---|---|
| Claim | Sorting on last month's return and last month's share turnover: reversal in low-turnover stocks, continuation in high-turnover stocks. |
| Effect size | All common non-financial NYSE/AMEX/NASDAQ shares, July 1963–Dec 2018, value-weighted, NYSE-breakpoint double deciles. Winner minus loser within the lowest-turnover decile: −1.41%/month (t −7.13). Within the highest-turnover decile: +1.37%/month (t 4.74). "On average, the STMOM strategy generates all its profits on the long side." Skipping the last three days of the formation month: +1.83%/month. Large caps (above NYSE median): +0.62%/month (t 3.01). Megacaps (top NYSE quintile): +0.53%/month (t 2.53). 500 largest stocks, 2×2 sort: +0.42%/month (t 4.91), while low-turnover reversal there "yields just −2 basis points per month". International (22 developed markets): +1.39%/month [PAPER] (full) A35. |
| Costs | Benchmark: turnover 89–90%/month per side, half-spreads 0.17% and 0.24%, cost 0.37%/month, net 1.00%/month (t 3.47). Megacaps, excluding end-of-month days: gross 0.72%, cost 0.13%, net 0.59%/month (t 3.10). Half-spreads are computed from 1983. The low-turnover reversal costs 1.94%/month, more than its gross return [PAPER] (full) A35 Table VII. Survives the authors' costs; these are long-short portfolio numbers from a sample ending 2018. |
| Later evidence | A38 reproduces the pattern and reframes it: in high-turnover stocks reversal exists but "end[s] after a single week" and the portfolio is "well into the short-run momentum" by one month. No post-2018 out-of-sample test was found. |
| Mechanism, other side | "an explanation based on some traders underappreciating the information conveyed by prices" [PAPER] (abs) A35. The losing side is whoever fades heavily traded month-long moves in large caps, which is what a dip-buying or "overbought" rule does. |
| Pine | Return over bars t−20 to t−3; turnover needs shares outstanding. `syminfo.shares_outstanding_float` compiles but is a current snapshot with no history [COMPILE] P9; [SECONDARY] P8. So the chart value is usable live, not for a Pine backtest; the research backtest needs point-in-time shares. Without a cross-section, "top decile" must be replaced by per-symbol thresholds (relative volume and a fixed turnover level) or by ranking in the Pine Screener [SECONDARY] P8. |
| Verdict | **CANDIDATE** for continuation (H7) and **CONTEXT** as a veto on fading (H8). |

### F9. Volatility sets the speed and size of a reversal; turnover sets how long it lasts

| Item | Content |
|---|---|
| Claim | "Higher volatility is associated with faster, initially stronger reversals, while lower turnover is associated with more persistent, ultimately stronger reversals." [PAPER] (abs) A38 |
| Effect size | 5-day industry-relative, announcement-adjusted signal, NYSE quintiles, 1973–2021: "Two weeks after formation, the spread is more than twice as large for high-volatility stocks as it is for low-volatility stocks, but the spreads converge after two months." By turnover: "The reversal is over after only two weeks for high-turnover stocks, but continues to grow for almost three months for low-turnover stocks." 21-day signal: "past performance only predicts reversals out to two weeks among high-volatility stocks, but out to almost three months among low-volatility stocks." Industry-relative reversal one month after a 21-day signal: 106 bp (low volatility) against 39 bp (high volatility); two weeks after a 5-day signal in high-volatility stocks: 116 bp. The patterns "hold in both sub-samples" around April 2001, though "reversals are weaker in the post-decimalization sample" [PAPER] (full, WP) A38. |
| Costs | Not reported. |
| Mechanism | Volatility is the liquidity provider's inventory risk; turnover is how fast inventory can be unwound (A38). |
| Pine | 63-bar standard deviation of daily returns; turnover as in F8. |
| Verdict | **CONTEXT** for the exit clock: in liquid, heavily traded stocks the bounce, if any, is a matter of days to two weeks; holding a dip longer moves into continuation territory (H8). |

### F10. News versus no-news moves

| Item | Content |
|---|---|
| Claim | Price moves with public news attached tend to continue; moves without news tend to reverse. |
| Evidence | Announcers 0.06%/month (t 0.30) versus non-announcers 0.51%/month (t 2.54) for the standard reversal, 1973–2021 [PAPER] (full, WP) A38. "Stock returns unexplained by 'fundamentals,' such as cash flow news, are more likely to reverse" [PAPER] (abs) A19. Monthly returns after headlines: drift after bad news, reversal after extreme moves with no public news, both mainly in smaller, more illiquid stocks [SECONDARY] search-engine summary of A8's abstract; the paper itself was not read. Stale news: "a firm's return on the day of stale news negatively predicts its return in the following week … significantly larger in stocks with above-average individual investor trading activity" [PAPER] (abs) A14 (2011). News "increas[es] their willingness to accommodate a persistent liquidity shock" [PAPER] (abs) A14 (2010); the size of the news-day effect on reversal that I recall (roughly a third less reversal) is [MEMORY]. |
| Contested | "an opposing and long-lasting continuation in returns follows the well-documented brief reversal … Our findings extend to weekly price movements with and without public news" [PAPER] (abs) A12. So at the weekly horizon the news split may not matter, and a week's reversal is followed by continuation. |
| Costs | A filter, not a strategy: it removes trades. |
| Pine | No news feed in Pine: "`request.news`" is rejected by the compiler [SECONDARY] P8. Proxies that compile: earnings report bars from `request.earnings(..., gaps = barmerge.gaps_on)` [COMPILE] P9; overnight gaps as a news proxy (F11). The exact bar on which an after-close report appears on history versus real time is unresolved [SECONDARY] P8. |
| Verdict | **CANDIDATE as a filter** (H5): highest prior of anything in this report. |

### F11. Overnight versus intraday components

| Item | Content |
|---|---|
| Claim | The part of a past return earned during trading hours behaves differently from the part earned overnight. |
| Evidence | Signals split by day and night, 1926–2019: portfolios sorted on past intraday returns show short-term reversal and momentum; "Portfolios formed on past overnight returns display only long-term reversal"; premise "Overnight returns are mostly driven by news, whereas intraday returns are mostly driven by investors' trading" [PAPER] (abstract excerpts) A37. The slides add that results hold "Excluding stocks in the bottom 20% of market capitalization and … dropping the 3-day windows around earning announcements", and "Weaker value-weighted returns also support liquidity effects" [PAPER] (slides) A37. Where profits are realised: "profits are either earned entirely overnight (for reversal and a variety of momentum strategies) or entirely intraday" [PAPER] (abs) A29. "a strong tendency for positive returns during the overnight period followed by reversals during the trading day … concentrated among stocks that have recently attracted the attention of retail investors … The additional implicit transaction costs for retail traders who buy high-attention stocks near the open frequently exceed the effective half spread" [PAPER] (abs) A17. "stocks with high (low) overnight returns underperform (outperform) over the longer term" [PAPER] (abs) A28. Frequent positive overnight returns followed by daytime reversals predict "higher future returns in the cross section" [PAPER] (abs) A36. |
| Extreme version | Buy overnight losers at the open, sell at the close: 1.68%/day gross for US stocks 1993–2014; annualised Sharpe 4.07 in S&P 100 members [PAPER] (full, incomplete draft) A39. Not usable here: the signal exists only at the open, the draft is marked incomplete, opening prints are noisy, and no costs are applied. |
| Costs | The component split is a filter. The realisation result matters for execution: if reversal profits accrue overnight (A29), an entry at the next open gives up the first night. Size of that give-up in liquid stocks today: not found. |
| Mechanism, other side | Overnight: news and retail attention; intraday: institutional trading and its price pressure (A37, A17). |
| Pine | `open/close[1]-1` and `close/open-1`, summed over the window; on 1h and 4h charts the daily open and close come from a `"1D"` request with `[1]` and `lookahead_on`: compiles [COMPILE] P9. |
| Verdict | **CANDIDATE** as a composition filter (H4) and **CONTEXT** for execution (H10): avoid market-on-open buys after a gap up in attention names; test what the first night costs a dip entry. |

### F12. Reversal ahead of earnings announcements (So, Wang 2014)

| Item | Content |
|---|---|
| Claim | "a six-fold increase in short-term return reversals during earnings announcements relative to non-announcement periods … market makers demand higher expected returns prior to earnings announcements because of increased inventory risks" [PAPER] (abs) A20 |
| Effect size | Formation on returns over days t−4 to t−2, holding t−1 to t+1 around announcement day t; losers minus winners "yielded an average 3-day return … of 1.45% during the 1996-2011 sample period" against 0.22% in "random pseudo-announcement periods"; for the largest size quintile the page shows 6.5% per year "assuming 10 rebalances per quarter" [SECONDARY] P7. Inference: 6.5% over about 40 events is roughly 16 bp per three-day event, long-short, in large stocks. The paper's tables were not read (see section 9). |
| Later evidence | None verified. |
| Costs | P7: "No trading-cost deduction is applied to reported reversal-strategy returns." At 16 bp long-short per event in large caps the protocol's costs exceed the effect, and the position is held through the announcement. |
| Mechanism, other side | Market makers charging more to hold inventory through a known event; the other side is anyone who must trade in the days just before earnings. |
| Pine | `earnings.future_time` compiles; per the sibling report it is fetched once at the script's first calculation and is valid on the last bar only, so it supports a live alert, not a Pine backtest [COMPILE] P9; [SECONDARY] P8. Historical announcement dates with before-open/after-close timing are needed for research. |
| Verdict | **REJECT as a trade** for liquid stocks (too small, event risk); **CONTEXT**: do not sell into weakness in the three days before a report; treat pre-earnings dips as a separate class (H9 keeps a small test). |

### F13. ETF and index-related effects

| Item | Content |
|---|---|
| Claim | Index products transmit non-fundamental flow to their constituents and have made index returns mean-revert. |
| Evidence | "stocks with higher ETF ownership display significantly higher volatility. ETF ownership increases the negative autocorrelation in stock prices … a significant risk premium of up to 56 basis points monthly" [PAPER] (abs) A27. Index-level serial dependence "switches to negative since the 2000s" across 20 indexes and "links to the increasing popularity of index products" [PAPER] (abs) A30. "A portfolio that is short high-flow ETFs and long low-flow ETFs earns excess returns of 1.1–2.0% per month" [PAPER] (abs) A33. |
| Practitioner counterpart | RSI(2) < 10 with close above the 200-day average on SPY, exit above the 5-day average, 2 bp per side: 0.79% per trade and Sharpe 0.97 for 1993–2008 (buy and hold 0.42); 0.51% per trade and Sharpe 0.68 for 2009–Sept 2026 (buy and hold 0.87); in the market about one day in ten [SECONDARY] P4. Edge over drift for the same entry on SPY in three equal thirds of 1993–2026: +0.549%, +0.198%, +0.096% per trade, frictionless [SECONDARY] P6. |
| Costs | Index ETFs trade at 1–2 bp, so costs are not the constraint; the shrinking edge and the low time in market are. |
| Mechanism, other side | Index arbitrage and ETF creation/redemption pass liquidity shocks to the basket (A27, A30). |
| Pine | ETF ownership and ETF flows are not available as Pine series ([SECONDARY] P8 lists `FUND_FLOWS` and `AUM` as daily `request.financial` fields for ETFs; I did not test them). The index-level dip rule is plain OHLC. |
| Verdict | Stock-level ETF-ownership signal: **REJECT** (no data in Pine). Index-level dip: **CANDIDATE**, low prior, mainly as a market-timing overlay (H11). |

### F14. Practitioner "oversold in an uptrend" rules

| Item | Content |
|---|---|
| Rules as published | Connors: trade with the 200-day average ("The long-term trend is up when a security is above its 200-day SMA"); buy "when 2-period RSI moves below 10"; "returns were higher when buying on an RSI dip below 5 than on one below 10"; exit "on a move above the 5-day SMA"; "Connors does not advocate using stops … stops actually 'hurt' performance" [SECONDARY] P1. ConnorsRSI: "CRSI(3,2,100) = [ RSI(3) + RSI(UpDown Length,2) + ROC(100) ] / 3", oversold under 10 [DOC] P2. Internal bar strength, (close − low)/(high − low): common practitioner variant; I found no verifiable primary paper for it today [MEMORY]. |
| Independent evidence on stocks | Russell 1000 with delisted names, 1995–mid 2015, RSI(2) < 5, exit RSI(2) > 70, at the close: average 0.75% per signal, 2014 at 0.13%, holding 4.1–5.1 bars, verdict "doing just fine" [SECONDARY] P3 (2015). Russell 3000, 2001–2018, RSI(2) crossing below 1, price above $2, entries and exits at the next open, 88,750 signals: 0.52% average; 0.89% in 2003–07; 0.52% in 2010–18; 0.33% in the last two years; win rate about 65%; costs not mentioned; verdict "slowly shrinking" [SECONDARY] P3 (2019). S&P 500 point-in-time members (345 names with data in 2006, 498 from 2021; the author notes missing early names flatter the result), 2006–2025, at most ten positions: annual growth 14.2% (no cost), 12.0% (2 bp per side), 8.8% (5 bp), 3.6% (10 bp); SPY price-only 8.4%; pooled Sharpe 0.92, 0.80, 0.61, 0.30 against 0.52 for SPY; fills at the signal close. Forward returns bought at the next open, all 65,205 dips: +0.02% (1 day), +0.33% (5 days), +0.55% (10 days), +0.94% (20 days), +0.06% over SPY at 20 days [SECONDARY] P5. |
| Reading | (1) Per-trade averages of +0.3% to +0.9% are raw returns of long positions in rising markets; against SPY the S&P 500 figure is +0.06% at 20 days. (2) The edge is roughly halved after the publication era. (3) It is concentrated in stressed markets (F4). (4) Results that assume a fill at the signal close cannot be reproduced from an end-of-bar alert. (5) All of this is blog-level evidence with unknown multiple-testing history. Inference. |
| Costs | P5: about 2,480 trades per year; every 5 bp per side removes about 5 percentage points of annual growth. At the protocol's 5 bp the rule is level with holding SPY; at the stress level it is far behind. |
| Mechanism, other side | Same as F4; the 200-day filter adds market and momentum beta. |
| Pine | `ta.rsi(close, 2)`, `ta.sma`, IBS, hand-built ConnorsRSI all compile; `ta.crsi` does not exist ("Could not find function or function reference 'ta.crsi'") [COMPILE] P9. |
| Verdict | Unconditional rule: **REJECT** for single stocks net of drift and costs (kept only as the null benchmark H1). Conditional versions go through H2–H5. |

### F15. Reversal, then continuation: the time limit on a fade

| Item | Content |
|---|---|
| Claim | The week-ahead reversal is brief; afterwards the original move tends to continue for months. |
| Evidence | "These subsequent momentum profits are strong enough to offset the initial reversal and to produce a significant momentum effect over the full year following portfolio formation. Thus, ex post, extreme weekly returns are not too extreme." [PAPER] (abs) A12. In high-volatility stocks "momentum sets in after just two weeks" after a one-month signal [PAPER] (full, WP) A38. "Price declines over the previous quarter lead to stronger reversals across the subsequent 2 months … active institutions participate less in losing stocks" [PAPER] (abs) A26: a counter-current for stocks that are already quarter-long losers. |
| Costs | Not a strategy; a constraint on holding time. No net figures apply. |
| Mechanism, other side | After the liquidity shock is absorbed, the information part of the move (underreaction) takes over; whoever keeps holding a fade is then short momentum. |
| Pine | A bar counter since entry (`ta.barssince`) for a time stop; compiles [COMPILE] P9. |
| Verdict | **CONTEXT**: a dip trade needs a time stop of the order of 5–10 bars in liquid, volatile, heavily traded names; without one it turns into a bet against momentum. |

## 5. Consolidated numbers for large and liquid US stocks

### 5.1 Gross and net

| Signal and construction | Universe | Period | Gross | Net (cost model) | Source, tag |
|---|---|---|---|---|---|
| 1-month reversal, deciles, value-weighted | NYSE breakpoints, all stocks excluding financials | 1967-01 to 2014-12 (WP version) | 0.26%/month (t 1.31) for losers minus winners | not reported | A31 [PAPER] |
| 1-month reversal, quintiles, value-weighted | all | 1973–2021; 2001-05 to 2021 | 0.31%/month (1.68); 0.18%/month (0.62) | not reported | A38 [PAPER] |
| 1-month reversal, cost-mitigated buy/hold-spread form | above NYSE median | 1963-07 to 2012-12 | 0.18%/month (0.88) | −0.51%/month (effective spreads) | A25 [PAPER] |
| Industry-relative reversal, same form | above NYSE median | 1963-07 to 2012-12 | 0.61%/month (4.08) | −0.12%/month | A25 [PAPER] |
| Industry-relative reversal, low-volatility stocks, same form | above NYSE median | 1963-07 to 2012-12 | 0.92%/month (7.83) | +0.31%/month (2.73) | A25 [PAPER] |
| Industry-relative, announcement-adjusted | all, value-weighted | 1973–2021; 2001-05 to 2021 | 1.08%/month (9.35); 0.58%/month (3.29) | not reported | A38 [PAPER] |
| Low-turnover 1-month reversal | megacaps; 500 largest | 1963–2018 | 0.74%/month (4.27); 0.02%/month | all-stock version: cost 1.94%/month | A35 [PAPER] |
| High-turnover 1-month continuation | megacaps; 500 largest | 1963–2018 | 0.53%/month (2.53); 0.42%/month (4.91) | megacaps ex end-of-month: 0.59%/month (3.10) | A35 [PAPER] |
| 1-day signal, 5-day hold, extreme deciles | top size quintile | 2001-04 to 2020-05 | 20 bp per 5 days (4.47), Sharpe 0.5; CAPM alpha 17 bp; −2 bp after volatility-risk adjustment | not reported | A34 [PAPER] |
| 1-week signal, quintiles, daily rebalancing | 500 largest; 100 largest | 1990–2009 | about 72 bp/week (inferred from net and cost) for the 500 | −3.0 bp/week standard; +30.5 and +53.1 bp/week with reduced turnover (Nomura model) | A16 [PAPER] |
| 1-day contrarian weights | largest decile | 1995–2007 | between −0.11% and +0.14% per day by year; 0.00% in 2006 | none | A10 [PAPER] |
| 5 daily lags | large, liquid, low-volatility stocks | 1998–2010 | about 0 at low VIX; about 0.1%/day at high VIX | none | A15 [PAPER] |
| 20-day signal, daily rebalancing, next day | top size quintile, value-weighted | 1963–2004; 2005–09; 2010–19; 2020–22 | 9–14; 4.2; 1.1–2.2; −1.5 bp/day | none | A41 [DOC], own arithmetic |
| RSI(2) < 10 above 200-day average, exit above 5-day average | S&P 500 members | 2006–2025 | 14.2%/year | 8.8% at 5 bp per side; 3.6% at 10 bp; SPY price-only 8.4% | P5 [SECONDARY] |
| Same entry on SPY | SPY | 1993–2008; 2009–2026-09 | – | 0.79% and 0.51% per trade at 2 bp per side | P4 [SECONDARY] |

### 5.2 Holding-period profile: how fast the bounce goes

| Evidence | Profile | Tag |
|---|---|---|
| NYSE intermediary data | Price pressure half-life 0.92 days on average; 0.54 days (17 bp) for the largest quintile; 2.11 days (118 bp) for the smallest | A21 [PAPER] (abs; quote via A35) |
| Top size quintile, 1-day signal, 2001–2020 | "The returns build steadily and begin to level off after about five days" (horizons to ten days) | A34 [PAPER] |
| 5-day signal by turnover | Over "after only two weeks" in high-turnover stocks; grows "for almost three months" in low-turnover stocks | A38 [PAPER] |
| 5-day and 21-day signals by volatility | High volatility: faster, more than twice the spread at two weeks; with a 21-day signal reversal ends and momentum starts after two weeks | A38 [PAPER] |
| 1-month signal, high turnover | Reversal "end[s] after a single week"; continuation persists 12 months | A38, A35 [PAPER] |
| Weekly signal | Brief reversal, then continuation for up to a year | A12 [PAPER] (abs) |
| Residual-based monthly reversal | 1.57% in month 1, 0.40% in month 2, about zero after | A19 [PAPER] |
| RSI(2) exit rule, Russell 1000 | Average hold 4.1–5.1 bars | P3 [SECONDARY] |
| RSI(2) dips, S&P 500, from the next open | +0.02% (1 day), +0.33% (5), +0.55% (10), +0.94% (20); +0.06% over SPY at 20 days | P5 [SECONDARY] |

Inference for a liquid, actively traded stock: whatever bounce exists is concentrated in the first one to five sessions, is partly gone by the next open, and is finished within about two weeks. Slow, months-long reversal belongs to low-turnover names, which are mostly outside the protocol's universe.

## 6. Where the literature and the practitioners are wrong or contested

| # | Issue | Positions | My reading |
|---|---|---|---|
| C1 | What the premium is | Overreaction (A1; A2: "inefficiency in the market for liquidity"); pay for bearing inventory under capital limits (A15, A38); pay for volatility risk and adverse selection (A34: large-cap pricing error −2 bp after the adjustment) | For large caps treat it as a risk premium earned by selling insurance against volatility, not as mispricing |
| C2 | Does volume strengthen or weaken reversal | Strengthens at one week (A5; A9), weakens at one week in large caps (A6), reverses into continuation at one month (A35) | Horizon-dependent (A38); the sign at 1–5 days in today's liquid stocks is an empirical question (H6) |
| C3 | Does it survive costs in large caps | No (A9; A25 except the low-volatility industry-relative variant); yes (A16: 30–50 bp/week; A18) | The "yes" papers end in 2009–2010, use institutional cost models with zero or negative costs for the most liquid names, and predate the fall to about zero gross in the French big-quintile series |
| C4 | News matters | Yes at one month (A38, A19, A8); not visibly at one week (A12) | Keep the earnings exclusion; do not expect a generic "news" proxy to add much at 5-day horizons |
| C5 | Size | Stronger in small stocks (A9, A15, A10, A34); flat across the top four NYSE quintiles (A38); "highest" among the largest (A16) | Flat-to-weaker in large caps and near zero recently |
| C6 | "Low-volatility industry-relative reversal is the strongest" | A25 (and the pricing-kernel result A38 cites) versus A38: stronger in high-volatility stocks but so short-lived that monthly sampling misses it | Matters for holding period, not for stock selection |
| C7 | Practitioner statistics | Raw per-trade means and win rates near 65% (P3) | Not adjusted for market drift; no costs; a no-stop rule with a 65% win rate has its risk in the left tail (worst SPY trade −10.2% in P4) |
| C8 | Entry price | Papers and most blogs: signal close. This project: next open | A29 says reversal profits accrue overnight; the first night may hold a material share of a small effect (H10) |
| C9 | Version drift | A19: "three times" (2011 WP) versus "four times" (2014 abstract). A34: predictive coefficient differs across drafts (a search-engine summary reports 5.37 bp for the 2018 draft [SECONDARY]; the Sept 2021 draft says 9 bp [PAPER]). A38 text prints t = 0.18 where its table has 0.62 | Quote tables, name the version |
| C10 | Open-price results | A39's 1.68%/day; A17's opening-price effect | Opening prints are the least reliable daily field; nothing here should be built on a single opening print without checking the data source |
| C11 | Short side | A19: the short-side profit comes from sentiment and short-sale limits | Irrelevant to a long-only trader; do not count the short leg's contribution when sizing expectations (A35 says STMOM's profit is on the long side; the reversal papers do not split legs for large caps) |

## 7. Pine computability

| Quantity | Pine expression (bar close) | Status | Limits |
|---|---|---|---|
| RSI(2), 200- and 5-bar averages | `ta.rsi(close, 2)`, `ta.sma(close, 200)`, `ta.sma(close, 5)` | [COMPILE] `rev_proto.pine` | none |
| IBS | `(close - low) / (high - low)` | [COMPILE] | zero-range bars need a guard |
| ConnorsRSI(3,2,100) | RSI(3), RSI(2) of the up/down streak, `ta.percentrank(ta.roc(close, 1), 100)`, averaged | [COMPILE] `rev_proto2.pine`; `ta.crsi` rejected [COMPILE] `neg_crsi.pine` | hand-built streak variable |
| Industry-relative return | `r1 - request.security(sectorEtf, timeframe.period, close/close[1]-1)` | [COMPILE] | one request per benchmark; ETF mapping by hand; beta assumed 1 |
| Announcement exclusion | `earnBar = not na(request.earnings(syminfo.tickerid, earnings.actual, gaps = barmerge.gaps_on))`; zero the residual on the report bar and the bar after | [COMPILE] | historical versus real-time bar of after-close reports unresolved [SECONDARY] P8 |
| Days to next report | `(earnings.future_time - time_close) / 86400000` | [COMPILE] | live only [SECONDARY] P8 |
| Residual z-score | window sum divided by `ta.stdev(res1, 63) * math.sqrt(n)` | [COMPILE] | per-symbol, time-series normalisation, not a cross-sectional rank |
| Overnight and intraday parts | `open/close[1]-1`, `close/open-1`, `math.sum(..., n)` | [COMPILE] | opening-print quality |
| Relative volume | `volume / ta.sma(volume, 63)` | [COMPILE] | – |
| Turnover | `ta.sma(volume, 63) / syminfo.shares_outstanding_float` | [COMPILE] | float is a current snapshot [SECONDARY] P8: not point-in-time on history |
| VIX state | `request.security("CBOE:VIX", "1D", close[1], lookahead = barmerge.lookahead_on)` | [COMPILE] | one day old on a daily chart by construction |
| Daily values on 1h/4h charts | tuple request on `"1D"` with `[1]` offsets and `lookahead_on` | [COMPILE] | last confirmed day only |
| Alerts | `alertcondition(barstate.isconfirmed and ...)`, `alert(..., alert.freq_once_per_bar_close)` | [COMPILE] | – |
| Cross-sectional decile or quintile rank | not possible inside one script: 40 unique `request.*` calls on Premium | [SECONDARY] P8 | ranking across symbols would have to happen in the Pine Screener, which the sibling report says can scan "up to 4,000" symbols with an indicator that plots; not verified by me |
| News flag, ETF ownership, short interest | not available | [SECONDARY] P8 | – |

Design consequence (inference): every academic signal here is a cross-sectional sort; the Pine version is a per-symbol threshold on a standardised residual. The research code must test the Pine-form signal, not the academic sort, or the parity step will fail.
Timing consequence (inference): the protocol's base case is an entry at the next open. For reversal signals the alternative worth measuring is a signal computed on the last full intraday bar before the close and an order placed for the close. US regular-session 1h bars on TradingView starting at 09:30, and exchange cut-off times for closing-auction orders, are [MEMORY] and need checking before any such design.

## 8. Hypotheses to test

Common definitions. Universe and costs: protocol §5 (base: 60-day median dollar volume ≥ $20M, price ≥ $5; "liquid" bucket ≥ $50M; 10 bp round trip, 20 bp stress). `r1` = daily close-to-close return on adjusted prices; `res1` = `r1` minus the same-day return of the stock's sector ETF; `sd_res` = 63-bar standard deviation of `res1`; announcement bars = the earnings report bar and the next bar; `RES5` = sum of `res1` over the last 5 bars with announcement bars set to zero; `z5 = RES5 / (sd_res × √5)`; `VIX` = last confirmed daily close of CBOE:VIX. Base entry: open of bar t+1. Outcome: return in excess of SPY (and, as a second cut, of the sector ETF) over the identical holding interval, per trade, gross and net; standard errors clustered by entry date, because dips cluster in sell-offs; reported by sub-period, liquidity bucket and A/B halves as the protocol requires. Every test below needs a survivorship-free daily OHLCV panel; extra data is named where needed.

| # | (a) Signal at the close of bar t | (b) Comparison or control | (c) Expected sign and size | (d) Data | (e) How it could fail | (f) Prior that it survives out-of-sample net of costs |
|---|---|---|---|---|---|---|
| H1 | Null benchmark. RSI(2) < 10 and close > SMA(200). Enter open t+1; exit at the open after the first close > SMA(5), or after 10 bars | All stock-days with close > SMA(200) held for the same number of bars (drift of uptrending stocks); SPY over the same windows | Gross excess 0.00% to +0.15% per trade; net ≤ 0 in the ≥ $50M bucket. Expectation is that there is **no** tradable edge | OHLCV | The hypothesis "no edge" fails if net excess exceeds +0.15% per trade with date-clustered t > 3 in both halves and both sub-periods | 0.10 (that an edge exists) |
| H2 | H1 signal and VIX ≥ 25 (variant: VIX above its own 252-day 80th percentile) | H1 signals with VIX below the threshold; SPY over the same windows, to remove the market's own rebound | Excess over SPY +0.3% to +0.6% over 5–10 bars gross, +0.2% to +0.5% net | OHLCV; VIX | Profit confined to 2008–09 and 2020; negative in grinding declines such as 2022; fewer than about 30 independent date clusters; nothing left after subtracting SPY | 0.30 |
| H3 | `z5 ≤ −2`, no announcement bar in the 5-bar window, no scheduled report in the next 5 bars. Enter open t+1; exit after 5 bars (variants 3 and 10) | Same threshold on the raw 5-bar return standardised by the 63-bar return volatility; residual dips that do contain an announcement bar | Excess over the sector ETF +0.2% to +0.4% gross per trade, +0.1% to +0.3% net; residual dips beat raw dips by at least 0.1% | OHLCV; sector ETF map; earnings dates | Present only below $50M dollar volume; absent after 2011; the gap at the next open takes most of it; sector ETF too coarse to remove news | 0.25 |
| H4 | Among H3 dips: intraday share `sum(close/open−1) / (sum(abs(open/close[1]−1)) + sum(abs(close/open−1)))` over the window ≤ −0.5 (decline made during sessions) | H3 dips whose overnight share ≤ −0.5 (decline made in gaps) | Intraday-made dips outperform gap-made dips by +0.2% to +0.4% over 5 bars; gap-made dips ≤ 0 | OHLCV with reliable opens | No difference once announcement bars are already excluded; bad opening prints; effect only in small names | 0.25 |
| H5 | Filter test. For the H1 and H3 dip definitions: flag = the signal window contains an announcement bar | Flagged versus unflagged dips, same rule otherwise | Flagged dips underperform by 0.3% to 0.6% over 5–20 bars and have a fatter left tail; removing them raises net expectancy | OHLCV; earnings dates with before-open/after-close timing | Post-earnings drift has also decayed in liquid names, leaving no difference after 2011; report-bar misdating | 0.45 (that the filter improves net expectancy) |
| H6 | One-day shock: `r1 ≤ −2 × sd(r1, 63)`, not an announcement bar. Split by `volume / SMA(volume, 63)[1]` ≥ 2 versus ≤ 1 | The two volume groups against each other; hold 1, 3, 5 bars from open t+1 | High-volume, no-news drops in liquid names bounce +0.1% to +0.3% more over 5 bars (A4). Opposite sign is possible (A6, A7); record the sign first | OHLCV; earnings dates | Sign negative or both groups at zero; the high-volume group is unflagged news | 0.20 |
| H7 | Continuation. Return over bars t−20 to t−3 ≥ +1.5 × sd(r1, 63) × √18 and average turnover over the same bars in the top quintile of the universe (Pine form: relative volume ≥ 1.5 and turnover above a fixed level). Long, hold 21 bars | Same return condition with turnover in the bottom two quintiles; SPY | Long-leg excess +0.2% to +0.4% per month gross, +0.1% to +0.3% net (published long-short: +0.42%/month in the 500 largest) | OHLCV; point-in-time shares outstanding | No effect after 2018; the Pine threshold form does not reproduce the cross-sectional sort; losses bunch in momentum crashes | 0.25 |
| H8 | Exit clock. For H3 dips, cumulative excess return over bars 1–5, 6–10, 11–21 after entry, by turnover tercile | Terciles against each other | High turnover: all of the bounce by bar 10 and bars 11–21 ≤ 0, so a 10-bar time stop costs nothing; low turnover: bars 11–21 add +0.1% to +0.3% | OHLCV; point-in-time shares | No monotone pattern inside a universe where even the lowest tercile trades heavily | 0.35 (that the pattern holds and a time stop is not harmful) |
| H9 | Pre-earnings dip. Market-adjusted return over t−4 to t−2 ≤ −1.5 × sd × √3, where t is the scheduled report day. Enter close t−2 or open t−1; exit close t+1 | Same signal on pseudo-event days at least 20 bars from any report | Long-only excess about +0.1% to +0.2% gross per event in liquid names (published large-cap long-short: about 16 bp, inferred); net ≤ 0 | Historical announcement dates with timing; OHLCV | Too small; dominated by the announcement gap; scheduled dates unavailable point-in-time | 0.07 |
| H10 | Execution. For H3 dips compare fills: (i) close t; (ii) open t+1; (iii) limit at close t valid for bar t+1; (iv) open t+1 only if open ≤ close t | (ii) is the base case; each alternative against it on the same signals, counting unfilled signals as zero | Overnight return after a dip signal +5 to +15 bp, so (ii) trails (i); (iii) and (iv) add +0.1% to +0.2% per filled trade | OHLCV; for (i), intraday bars to measure how often a pre-close signal equals the close signal | Adverse selection: limits fill mostly in the dips that keep falling, and the dips that bounce at once never fill | 0.30 |
| H11 | Index and sector ETFs (SPY, QQQ, IWM, 11 sector SPDRs): RSI(2) < 10 and close > SMA(200); exit close > SMA(5) | Unconditional drift of the same ETF over the same number of bars; pre- and post-2009 | +0.1% to +0.3% per trade over drift after 2 bp per side, about ten trades a year per ETF | ETF OHLCV | Edge over drift already down to about +0.1% in 2015–2026 (P6); Sharpe below buy and hold since 2009 (P4); few trades | 0.20 |
| H12 | Risk. Regress the per-trade excess returns of H2 and H3 on the change in VIX over the holding window, controlling for the SPY return | Coefficient against zero; then a rule "exit if VIX has risen by X points since entry" against no such rule; then position size proportional to 1/sd | Negative loading, of the order of −0.1% to −0.3% per VIX point; a VIX-triggered exit does not help because the loss persists (A34) | OHLCV; VIX | No loading in single-stock, long-only form | 0.75 that the negative loading is found; 0.15 that a VIX-triggered exit improves net risk-adjusted return |

Order of work suggested by priors and dependencies: H5 and H1 first (they define the dip and the null), then H3, H2, H8, H10, H12, then H4, H7, H6, H11, H9. Twelve hypotheses with variants are well over twelve trials; each variant belongs in `registry/trials.jsonl`.

## 9. Not verified today

| # | Item | Why | Consequence |
|---|---|---|---|
| 1 | So and Wang (2014) tables: 1.45% versus 0.22%, results by size, split across days t−1, t, t+1 | MIT DSpace returned HTTP 429 four times; SSRN returned 403 | Numbers in F12 are [SECONDARY] from Quantpedia; the 16 bp per event figure is my inference from Quantpedia's annualisation |
| 2 | Chan (2003) | No abstract on IDEAS; only a search-engine summary of the abstract | F10 cites it as [SECONDARY] |
| 3 | Lehmann (1990) weekly profit figures | Working-paper scan not legible enough to quote | Only the abstract and the sample dates are used |
| 4 | Avramov, Chordia, Goyal (2006); Hameed and Mian (2015); Blitz et al. (2013); Cooper (1999); Conrad et al. (1994); Campbell et al. (1993); Llorente et al. (2002); Tetlock (2010, 2011); Kaniel et al. (2008); Gutierrez and Kelley (2008); Lou, Polk, Skouras (2019); Berkman et al. (2012); Ben-David et al. (2018); Baltussen et al. (2019) | Abstracts only | No effect sizes for large caps or recent periods are quoted from them |
| 5 | Journal versions of Nagel, Da et al., de Groot et al., Novy-Marx and Velikov, Hou et al., Medhat and Schmeling, Dai et al. | Publisher sites returned 403; working-paper or accepted-manuscript versions were read | Numbers may differ slightly from the printed tables |
| 6 | Publication status and final numbers of Drechsler, Moreira, Savov; the scaling of "one point" of VIX and VIX-squared in that draft | Only the Sept 2021 draft was read | F4's coefficients are orders of magnitude, not exact |
| 7 | Barardehi, Bogousslavsky, Muravyev effect sizes | Abstract excerpts and slides only; the figures in the slides are images | F11 and H4 rest on the direction, not on a number |
| 8 | Della Corte, Kosowski, Wang | Draft marked incomplete; no later version found | Used only to illustrate; no hypothesis depends on it |
| 9 | Any peer-reviewed, post-2010, survivorship-free, cost-adjusted test of Connors-type rules on single stocks | Searched; none found | F14 rests on three blogs |
| 10 | Internal bar strength: a primary source | The paper I recalled could not be found by search | Mentioned as [MEMORY] only |
| 11 | That the French 5×5 size breakpoints are NYSE quintiles | The library's description page was not re-read | [MEMORY] |
| 12 | Runtime behaviour of the two prototype scripts on a chart; whether `CBOE:VIX` daily bars are final at the stock close; historical alignment of `request.earnings` bars | The compile tool checks compilation only | Needs a chart run (see the sibling report's open items) |
| 13 | TradingView 1h bar boundaries for US stocks and closing-auction order cut-offs | Not looked up | [MEMORY]; needed only if a pre-close entry is designed |
| 14 | Evidence after 2022 for anything in sections 3 to 5 | French data deliberately cut at 2022-12-30 under the protocol; papers end between 2009 and 2021; blogs P4–P6 run to 2025–2026 but are [SECONDARY] | The recent-period picture for single stocks must come from the project's own tests |
| 15 | Size of the first-night give-up for a next-open entry in today's liquid stocks | No source found | H10 |
