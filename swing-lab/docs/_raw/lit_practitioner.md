# Practitioner swing-trading canon, dissected

Raw research report. Topic: the most influential practitioner swing/position methods, reduced to
rules a Pine script can compute at a bar close, and mapped to documented academic effects or to
"no evidence". Written 11 Nov 2026 (system date; the brief says 10 Nov). **All sources were accessed
on 2026-11-11.** Nothing here was tested on the project's own panel; no trial was added to the registry.

## 0. How to read this

| Tag | Meaning in this file |
|---|---|
| [DOC] | Read today on the primary/official page itself (TradingView pages, the practitioner's own site or book text) |
| [COMPILE] | Confirmed today with `tools/pine_compile.py` (9 of the 15 allowed compiler calls used; scripts in Appendix A) |
| [PAPER] | Abstract or full text of the paper read today (Crossref/NBER/RePEc record, publisher page or PDF) |
| [SECONDARY] | Third-party page, a search-result summary of a page I could not open, or third-party data computed today |
| [MEMORY] | Recalled from training, **not verified today**; do not treat as fact |

Limits that matter: `investors.com` (IBD) renders by JavaScript and could not be read; SSRN, OpenAlex,
Semantic Scholar and the Wayback Machine refused or rate-limited requests. IBD's own definitions are
therefore [SECONDARY] throughout. Books by O'Neil, Minervini, Weinstein, Darvas, Connors/Alvarez and
Shannon were not read; only *Street Smarts* (Connors & Raschke 1995), Qullamaggie's blog and Bulkowski's
glossary were read in the original. Where a quotation comes from a page read through a fetch tool, the
wording is the tool's extract of that page.

## 1. What the evidence says, in ten lines

1. Every method in the canon reduces to one of four measurable things: **long-horizon trend/relative
   strength** (O'Neil, Minervini, Weinstein, Darvas, RS line), **short-horizon reversal** (Connors,
   Turtle Soup, liquidity sweeps, Wyckoff springs), **event drift** (episodic pivots, anchored VWAP from
   earnings) and **risk rules** (stops, ADR%, sizing). Chart-reading vocabularies (Wyckoff, ICT/SMC,
   volume profile) add names, not measurable effects.
2. The trend/RS family rests on published effects: momentum, nearness to the 52-week high,
   moving-average distance (P1, P2, P7 [PAPER]). They are **slow filters, not entry signals**, and
   their recent strength is disputed: one study finds US momentum profits insignificant since the
   late 1990s (P3 [PAPER]); a later replication study says most factors hold up (P38 [PAPER]).
3. No independent, survivorship-free test was found showing that **any specific entry pattern** of the
   canon (VCP, cup-with-handle, pocket pivot, Darvas box, stage-2 breakout, RS-line blue dot) beats
   holding the same trending stocks. The one large survivorship-free test of a breakout rule that I
   found (all-time-high close,
   next-open entry, 10-ATR trailing stop, 1950-2024, delisted stocks included) is profitable only
   through a few outliers: fewer than 7% of trades make all the profit (P50 [PAPER]).
4. A real-money test of IBD's stock ranking exists: the IBD 50 ETF returned -1.35% a year from
   9 Apr 2015 to 30 Dec 2022 against +10.15% for SPY (Yahoo adjusted closes, computed today,
   [SECONDARY]). It tests the ranks, not O'Neil's timing and sell rules.
5. Buying every gap-up of 6% or more (9,794 events, 2016-2023, CRSP, survivorship-free) **loses**
   money mechanically; only a skilled trader's chart selection plus intraday management turned it
   positive (P51 [PAPER]). Post-earnings drift itself is reported gone for large stocks since 2006
   (P20 [PAPER]).
6. Connors-style RSI(2) dip buying is the only short-horizon canon rule for which I found a
   documented edge **at next-open execution**, and its own co-author measures the decay: 0.89% per trade in 2003-2007, 0.52% in
   2010-2018, 0.33% in 2017-2018, negative above the 200-day average in the 2020 and 2022 bear
   phases (S5, S6 [SECONDARY], gross of costs, Russell 3000).
7. Bulkowski's pattern statistics are measured to the "ultimate high", a level known only in
   hindsight, with no costs (S3 [DOC]). They are not tradable returns.
8. For ICT/"smart money concepts" I found no peer-reviewed test; the one mechanical test found
   reports no significant edge (best t = 1.22 on SPY; S14 [SECONDARY]). The most-boosted script among
   those checked on TradingView is an SMC script (180,820 boosts, S15 [DOC]); popularity is not evidence.
9. Stops are not universally good or bad: theory and data say they help when returns trend and hurt
   when returns revert (P39, P40 [PAPER]). This reconciles O'Neil/Minervini (always stop) with
   Connors (stops hurt).
10. For a trader who acts on bar-close alerts, the binding question is what is left at the **next
    open**. For a fast reversal signal on SPY the average trade fell from 31 bp (fill at the signal
    close) to 22 bp (next open) (S9 [SECONDARY]); momentum's abnormal return is earned overnight
    (P41 [PAPER]).

## 2. Source register (all accessed 2026-11-11)

### 2.1 Papers

| ID | Reference | URL | How read |
|---|---|---|---|
| P1 | Jegadeesh & Titman (1993), "Returns to Buying Winners and Selling Losers", J. Finance 48, 65-91 | https://doi.org/10.1111/j.1540-6261.1993.tb04702.x | abstract (Crossref) |
| P2 | George & Hwang (2004), "The 52-Week High and Momentum Investing", J. Finance 59 | https://doi.org/10.1111/j.1540-6261.2004.00695.x | abstract (Crossref) |
| P3 | Bhattacharya, Li & Sonaer (2017), "Has momentum lost its momentum?", Rev. Quant. Finance & Accounting 48, 191-218 | https://ideas.repec.org/a/kap/rqfnac/v48y2017i1d10.1007_s11156-015-0547-8.html | abstract |
| P4 | Daniel & Moskowitz (2016), "Momentum Crashes", JFE (NBER w20439) | https://www.nber.org/papers/w20439 | abstract |
| P5 | Barroso & Santa-Clara (2015), "Momentum has its moments", JFE 116, 111-120 | https://ideas.repec.org/a/eee/jfinec/v116y2015i1p111-120.html | abstract |
| P6 | Da, Gurun & Warachka (2014), "Frog in the Pan: Continuous Information and Momentum", RFS (SSRN version) | https://doi.org/10.2139/ssrn.1777988 | abstract (Crossref) |
| P7 | Avramov, Kaplanski & Subrahmanyam (2021), "Moving average distance as a predictor of equity returns", Rev. Financial Economics 39, 127-145 | https://doi.org/10.1002/rfe.1118 | abstract (Crossref) |
| P8 | Han, Zhou & Zhu (2016), "A trend factor", JFE 122, 352-375 | https://ideas.repec.org/a/eee/jfinec/v122y2016i2p352-375.html | abstract |
| P9 | Han, Yang & Zhou (2013), "A New Anomaly: The Cross-Sectional Profitability of Technical Analysis", JFQA 48, 1433-1461 | https://econpapers.repec.org/RePEc:cup:jfinqa:v:48:y:2013:i:05:p:1433-1461_00 | abstract |
| P10 | Brock, Lakonishok & LeBaron (1992), "Simple Technical Trading Rules...", J. Finance 47, 1731-1764 | https://doi.org/10.1111/j.1540-6261.1992.tb04681.x | abstract (Crossref) |
| P11 | Sullivan, Timmermann & White (1999), "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap", J. Finance 54, 1647-1691 | https://doi.org/10.1111/0022-1082.00163 | abstract (Crossref) |
| P12 | Bajgrowicz & Scaillet (2012), "Technical trading revisited: False discoveries, persistence tests, and transaction costs", JFE 106, 473-491 | https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html | abstract |
| P13 | Park & Irwin (2007), "What do we know about the profitability of technical analysis?", J. Economic Surveys 21, 786-826 | https://doi.org/10.1111/j.1467-6419.2007.00519.x | abstract (Crossref) |
| P14 | Lo, Mamaysky & Wang (2000), "Foundations of Technical Analysis", J. Finance (NBER w7613) | https://www.nber.org/papers/w7613 | abstract |
| P15 | Huddart, Lang & Yetman (2009), "Volume and Price Patterns Around a Stock's 52-Week Highs and Lows", Management Science (SSRN 2003 version) | https://doi.org/10.2139/ssrn.353749 | abstract (Crossref) |
| P16 | Gervais, Kaniel & Mingelgrin (2001), "The High-Volume Return Premium", J. Finance 56, 877-919 | https://doi.org/10.1111/0022-1082.00349 | abstract (Crossref) |
| P17 | Lee & Swaminathan (2000), "Price Momentum and Trading Volume", J. Finance (SSRN version) | https://doi.org/10.2139/ssrn.92589 | abstract (Crossref) |
| P18 | Medhat & Schmeling (2022), "Short-term Momentum", RFS 35, 1480-1526 | https://econpapers.repec.org/RePEc:oup:rfinst:v:35:y:2022:i:3:p:1480-1526. | abstract |
| P19 | Bernard & Thomas (1989), "Post-Earnings-Announcement Drift", J. Accounting Research 27 | https://doi.org/10.2307/2491062 | existence confirmed (Crossref); abstract not available |
| P20 | Martineau (2022), "Rest in Peace Post-Earnings Announcement Drift", Critical Finance Review (preprint) | https://doi.org/10.31235/osf.io/z7k3p | abstract (Crossref) |
| P21 | Brandt, Kishore, Santa-Clara & Venkatachalam (2008), "Earnings Announcements are Full of Surprises" | https://doi.org/10.2139/ssrn.909563 | abstract (Crossref) |
| P22 | Garfinkel & Sokobin (2006), "Volume, Opinion Divergence and Returns: A Study of Post-Earnings Announcement Drift", J. Accounting Research (SSRN version) | https://doi.org/10.2139/ssrn.280913 | abstract (Crossref) |
| P23 | Lerman, Livnat & Mendenhall (2008), "The High-Volume Return Premium and Post-Earnings Announcement Drift" | https://doi.org/10.2139/ssrn.1122463 | abstract (Crossref) |
| P24 | Frazzini & Lamont (2007), "The Earnings Announcement Premium and Trading Volume", NBER w13090 | https://www.nber.org/papers/w13090 | abstract |
| P25 | Savor (2012), "Stock returns after major price shocks: The impact of information", JFE 106, 635-659 | https://ideas.repec.org/a/eee/jfinec/v106y2012i3p635-659.html | abstract |
| P26 | Frazzini (2006), "The Disposition Effect and Underreaction to News", J. Finance 61, 2017-2046 | https://doi.org/10.1111/j.1540-6261.2006.00896.x | abstract (Crossref) |
| P27 | Grinblatt & Han (2005), "Prospect theory, mental accounting, and momentum", JFE (SSRN version) | https://doi.org/10.2139/ssrn.288466 | abstract (Crossref) |
| P28 | Aboody, Lehavy & Trueman (2010), "Limited attention and the earnings announcement returns of past stock market winners", Rev. Accounting Studies (SSRN version) | https://doi.org/10.2139/ssrn.1127764 | abstract (Crossref); sign of one number unclear, see 4.3 |
| P29 | Ang, Hodrick, Xing & Zhang (2006), "The Cross-Section of Volatility and Expected Returns", J. Finance (NBER w10852) | https://www.nber.org/papers/w10852 | abstract |
| P30 | Bali, Cakici & Whitelaw (2011), "Maxing Out: Stocks as Lotteries...", JFE (NBER w14804) | https://www.nber.org/papers/w14804 | abstract |
| P31 | Zhang (2006), "Information Uncertainty and Stock Returns", J. Finance (SSRN version) | https://doi.org/10.2139/ssrn.535783 | abstract (Crossref) |
| P32 | Greenwood, Shleifer & You (2019), "Bubbles for Fama", JFE (NBER w23191) | https://www.nber.org/papers/w23191 | abstract |
| P33 | Nagel (2012), "Evaporating Liquidity", RFS (NBER w17653) | https://www.nber.org/papers/w17653 | abstract |
| P34 | de Groot, Huij & Zhou (2012), "Another look at trading costs and short-term reversal profits", J. Banking & Finance 36, 371-382 | https://ideas.repec.org/a/eee/jbfina/v36y2012i2p371-382.html | abstract |
| P35 | Dai, Medhat, Novy-Marx & Rizova (2023), "Reversals and the Returns to Liquidity Provision", NBER w30917 | https://www.nber.org/papers/w30917 | abstract |
| P36 | McLean & Pontiff (2016), "Does Academic Research Destroy Stock Return Predictability?", J. Finance (SSRN version) | https://doi.org/10.2139/ssrn.2080900 | abstract (Crossref) |
| P37 | Novy-Marx & Velikov (2016), "A Taxonomy of Anomalies and their Trading Costs", RFS (NBER w20721) | https://www.nber.org/papers/w20721 | abstract |
| P38 | Jensen, Kelly & Pedersen (2023), "Is There a Replication Crisis in Finance?", J. Finance (NBER w28432) | https://www.nber.org/papers/w28432 | abstract |
| P39 | Kaminski & Lo (2014), "When Do Stop-Loss Rules Stop Losses?", J. Financial Markets (SSRN version) | https://doi.org/10.2139/ssrn.968338 | abstract (Crossref) |
| P40 | Han, Zhou & Zhu (2016), "Taming Momentum Crashes: A Simple Stop-Loss Strategy" (SSRN) | https://doi.org/10.2139/ssrn.2407199 | abstract (Crossref) |
| P41 | Lou, Polk & Skouras (2019), "A tug of war: Overnight versus intraday expected returns", JFE 134, 192-213 | https://econpapers.repec.org/RePEc:ehl:lserod:119010 | abstract |
| P42 | Bogousslavsky & Muravyev (2023), "Who trades at the close?", J. Financial Markets 66 | https://ideas.repec.org/a/eee/finmar/v66y2023ics1386418123000502.html | abstract |
| P43 | Osler (2003), "Currency Orders and Exchange-Rate Dynamics: Explaining the Success of Technical Analysis", J. Finance (SSRN version) | https://doi.org/10.2139/ssrn.923370 | abstract (Crossref) |
| P44 | Kavajecz & Odders-White (2004), "Technical Analysis and Liquidity Provision", RFS (SSRN version) | https://doi.org/10.2139/ssrn.315660 | abstract (Crossref) |
| P45 | Barber & Odean (2013), "The Behavior of Individual Investors" (SSRN version) | https://doi.org/10.2139/ssrn.1872211 | abstract (Crossref) |
| P46 | Chague, De-Losso & Giovannetti (2019), "Day Trading for a Living?" | https://doi.org/10.2139/ssrn.3423101 | abstract (Crossref) |
| P47 | Olson, Nelson, Witt & Mossman (1998), "A Test of the Investor's Daily Stock Ranking System", Financial Review 33(2), 161-175 | https://ideas.repec.org/a/bla/finrev/v33y1998i2p161-75.html | abstract (via fetch summary) |
| P48 | Schadler & Cotten (2008), "Are the AAII stock screens a useful tool for investors?", Financial Services Review 17, 185-201 | https://doi.org/10.61190/fsr.v17i3.4917 | abstract (Crossref) |
| P49 | Lutey & Rayome (2022), "Live Out of Sample Testing of CAN SLIM Stock Selection Strategy", J. Accounting and Finance 22(2) | https://articlegateway.com/index.php/JAF/article/view/5134 | abstract |
| P50 | Zarattini, Pagani & Wilcox (2025), "Does Trend Following Still Work on Stocks?" (SSRN 5084316; version 17 Jan 2025) | https://concretumgroup.com/wp-content/uploads/2026/02/Does-Trend-Following-Still-Work-on-Stocks.pdf | full text |
| P51 | Zarattini & Stamatoudis (2024), "The Power Of Price Action Reading" (SSRN 4879527; 28 Jun 2024) | https://concretumgroup.com/wp-content/uploads/2026/02/The-Power-Of-Price-Action-Reading.pdf | full text |

### 2.2 Practitioner and third-party sources

| ID | Source | URL | Tag when cited |
|---|---|---|---|
| S1 | Qullamaggie (K. Kullamägi), "My 3 timeless setups..." (his own blog) | https://qullamaggie.com/my-3-timeless-setups-that-have-made-me-tens-of-millions/ | [DOC] |
| S2 | Connors & Raschke, *Street Smarts* (1995), book text (third-party hosted PDF) | https://thechartist.com.au/wp-content/uploads/2024/12/504/StreetSmarts(LaurenceConnors).pdf | [DOC] |
| S3 | Bulkowski, ThePatternSite glossary ("Updated 2/20/2025") | https://www.thepatternsite.com/glossary.html | [DOC] |
| S4 | StockCharts ChartSchool, "RSI(2)" | https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2 | [SECONDARY] |
| S5 | C. Alvarez, "How is mean reversion doing? Dead, Shrinking or Doing Just Fine" (13 Mar 2019) | https://alvarezquanttrading.com/blog/how-is-mean-reversion-doing-dead-shrinking-or-doing-just-fine/ | [SECONDARY] |
| S6 | C. Alvarez, "Mean Reversion Check Up 2022" | https://alvarezquanttrading.com/blog/mean-reversion-check-up-2022/ | [SECONDARY] |
| S7 | Empirica Lab, "Connors' RSI(2) had a Sharpe of 0.97 before the book. Since then: 0.68." (note EL-R-2026-302) | https://empiricalab.substack.com/p/connors-rsi2-spy | [SECONDARY] |
| S8 | CXO Advisory, "Out-of-sample tests of bullish regime 2-day RSI signals" (19 Mar 2009) | https://www.cxoadvisory.com/technical-trading/out-of-sample-tests-of-bullish-regime-2-day-rsi-signals | [SECONDARY] |
| S9 | C. Zarattini (Concretum), "When Execution Delays Erode Short-Term Alpha" | https://concretumgroup.com/when-execution-delays-erode-short-term-alpha/ | [SECONDARY] |
| S10 | AAII Journal, "A Tribute to William O'Neil: Revisiting the CAN SLIM Strategy" (July 2023) | https://www.aaii.com/journal/article/68036-a-tribute-to-william-o-neil-revisiting-the-can-slim-strategy | [SECONDARY] |
| S11 | LuxAlgo library concept pages: pocket pivot; Weinstein stage analysis; volatility contraction pattern | https://www.luxalgo.com/library/concept/pocket-pivot/ ; https://www.luxalgo.com/library/concept/weinstein-stage-analysis/ ; https://www.luxalgo.com/library/concept/volatility-contraction-pattern/ | [SECONDARY] |
| S12 | TradingView script "Minervini Trend Template" (yogy.frestarahmawan, 2021), description | https://www.tradingview.com/script/zygjiw4C-Minervini-Trend-Template/ | [SECONDARY] for Minervini's rule |
| S13 | Wikipedia, "Nicolas Darvas" | https://en.wikipedia.org/wiki/Nicolas_Darvas | [SECONDARY] |
| S14 | StatOasis (A. Casey), "I Backtested ICT / Smart Money Concepts - What Survives" (3 Sep 2026, updated 17 Sep 2026) | https://statoasis.com/overfit/research/ict-backtest-what-survives | [SECONDARY] |
| S15 | TradingView script pages and script search pages (boost counts, creation dates) | https://www.tradingview.com/script/<id>/ and https://www.tradingview.com/scripts/search/<query>/ ; ids in section 6 | [DOC] |
| S16 | TradingView, "The 2025 TradingView Community Awards Are Official" | https://www.tradingview.com/chart/SPX/g2U4uwkM-The-2025-TradingView-Community-Awards-Are-Official/ | [DOC] |
| S17 | TradingView Help Center, "Connors RSI (CRSI)" | https://www.tradingview.com/support/solutions/43000502017-connors-rsi-crsi/ | [DOC] |
| S18 | Web-search result summaries only (page not opened): IBD/inkl articles on the RS Rating and RS line; Innovator FFTY factsheet figures; AAII and Chartmill pages on O'Neil's 7-8% rule and buy zone; pages on Minervini's risk rules; pages on Darvas box rules; pages on anchored VWAP; Chartmill on the trend template | search queries of 2026-11-11; the URLs the summaries drew on are listed in 2.3 | [SECONDARY], weakest grade |
| S19 | Yahoo Finance adjusted closes for FFTY and SPY via `yfinance`, computed today, window ends 2022-12-30 (lockbox period not touched) | n/a | [SECONDARY] |
| S20 | Sibling report `docs/_raw/pine_requests.md` (request limits, `request.earnings`, `request.footprint`) | local file | cited as "sibling report", not re-verified |

### 2.3 URLs behind the search-summary citations (S18)

These pages were returned by the search tool and summarised by it. I did not open them (or the fetch
failed), so wording and numbers taken from them are the weakest evidence in this file.

| Topic | URLs returned by the search |
|---|---|
| IBD RS Rating definition and weighting | https://inkl.com/news/how-to-invest-3-month-relative-strength-rating-reacts-faster-to-stock-moves (IBD syndication; HTTP 403 when fetched) ; https://tapeboard.com/glossary/what-is-relative-strength ; https://www.tradingview.com/script/Zrvmov68-RS-Rating-Multi-Timeframe-v2 (the 40/20/20/20 replica) |
| Reported April 2026 change to IBD ratings | https://www.pulse.bot/stock-investing/news/ibd-stock-ratings-get-even-better-with-these-upgrades-c21cf724-3be8-443f-bf53-3ca9679e5396/ (HTTP 503 when fetched) |
| RS line "blue dot" | https://inkl.com/news/growth-stocks-and-how-to-find-big-stock-market-winners-try-this-blue-dot-list-in-marketsmith ; https://www.inkl.com/news/use-relative-strength-to-find-breakout-stocks-and-watchlist-candidates |
| O'Neil 7-8% rule, 5% buy zone, breakout volume | https://www.aaii.com/journal/article/sell-rules-to-build-your-stock-investing-performance ; https://www.chartmill.com/documentation/trading-and-investing/methodologies/527-William-ONeils-7-8-Sell-Rule-Explained ; https://tradingqna.com/t/why-you-should-pay-close-attention-to-the-5-buy-zone-after-a-breakout-updated/95357 |
| Minervini trend template (30% figure) | https://www.chartmill.com/documentation/trading-and-investing/methodologies/523-SEPA-Explained-Mark-Minervinis-Specific-Entry-Point-Analysis-System (HTTP 403 when fetched) |
| Minervini risk rules and championship result | https://www.daytrading.com/mark-minervini-momentum-strategies ; https://traderlion.com/investing-champions/mark-minervinis-risk-management/ |
| Biased GitHub test of a Minervini/VCP screener | https://github.com/phuazz/vcp-screener |
| Weinstein: weighted vs simple 30-week average | https://www.tradingview.com/script/zwO4XZlA-Stage-Analysis/ |
| Darvas box rules | https://thepatternsite.com/Darvas.html ; https://www.sharescope.co.uk/sharescope_tutorial33.jsp ; https://therighttrader.com/learn/trading-strategies/darvas-box-strategy |
| Cumulative RSI rules | https://trader.autochartist.com/?p=66427 |
| Anchored VWAP usage | https://alphatrends.net/?p=623098 ; https://help.trendspider.com/kb/indicators/anchored-vwap-volume-weighted-average-price ; https://chartinglens.com/blog/anchored-vwap-trading-guide |
| Episodic pivot attributed to P. Bonde | https://completetradersedge.com/kristjan-kullamagi-qullamaggie/ ; https://tikamalma.substack.com/p/qullamaggie-swing-trading-setups |
| FFTY factsheet figures and reorganisation | https://innovatoretfs.com/pdf/ffty_factsheet.pdf (returns an HTML page now) ; https://www.barchart.com/story/news/1371799/capital-force-enters-etf-market-with-acquisition-of-innovator-ibd-50-ffty-and-ibd-breakout-opportunities-bout-etfs |
| Short-term momentum, 1.37% a month | https://alphaarchitect.com/short-term-momentum/ |
| Han, Yang & Zhou sample period and break-even cost remark | https://www.econbiz.de/Record/a-new-anomaly-the-cross-sectional-profitability-of-technical-analysis/10010343641 ; https://ideas.repec.org/a/cup/jfinqa/v48y2013i05p1433-1461_00.html |
| SMC vendor win-rate claims | https://fxnx.com/en/blog/smart-money-concepts-work-backtest-evidence ; https://indicatoredge.io/smart-money |

## 3. The canon, method by method

Columns: **Rule** = the mechanical core, computable at a bar close. **Kernel** = the documented effect
it proxies. **Independent test** = a test by someone other than the author on data that include
delisted stocks. **Pine** = computability. Detailed evidence follows in section 4.

### 3.1 Trend, relative strength and breakout methods

| Method | Rule (mechanical core) | Kernel | Independent survivorship-free test | Pine | Verdict |
|---|---|---|---|---|---|
| **O'Neil CAN SLIM** | C: quarterly EPS up 20%+ year on year; A: 5 years of EPS growth, 25%+ a year; N: price at least 90% of the 52-week high; L: 52-week relative strength in top 30%; I: at least five institutional holders (AAII's screen version, S10 [SECONDARY]); M: market in an uptrend, part of O'Neil's method but not of the screen [MEMORY]. Buy a breakout from a base; stop 7-8% below cost; do not buy more than 5% above the pivot; breakout volume 40-50% above the 50-day average (S18 [SECONDARY]) | Momentum (P1), 52-week high (P2), earnings drift (P19, P21), attention at new highs (P15) | P47 [PAPER]: the best system built on IBD rankings gave market-adjusted abnormal returns of 1.81% a month buying S&P 500 stocks; returns were lower in the second half of the sample (abstract as summarised by the fetch tool; sample period not seen). P48 [PAPER]: after costs only 32% of AAII screens significantly beat the S&P 500. Real money: IBD 50 ETF -1.35%/yr vs SPY +10.15%/yr, Apr 2015 - Dec 2022 (S19 [SECONDARY]) | C: yes from `request.earnings` (EPS only). A, I: no usable history. L as a 1-99 percentile: no (needs the whole cross-section). N, M, breakout, stop: yes [COMPILE] | **CONTEXT** (N, L, M as filters). The full system: **REJECT** as a mechanical rule |
| **IBD RS Rating** | 1-99 percentile of 12-month price performance against all stocks, recent 3 months weighted more (S18 [SECONDARY]). Exact formula unpublished; the 40/20/20/20 weighting of 3/6/9/12-month returns is a community approximation (S18 [SECONDARY]). A search summary says IBD changed the rating in April 2026 to 12-, 6- and 3-month windows (S18 [SECONDARY], not confirmed) | Cross-sectional momentum (P1) | None specific to the rating beyond P47 | Percentile not computable in one script (40 `request.*` calls per script on Premium, sibling report S20). Computable proxies: weighted ROC minus the benchmark's, RS line, Mansfield RS [COMPILE] | **CONTEXT** |
| **RS line new high ("blue dot")** | RS line = close / S&P 500. Signal: RS line at a 52-week high while the stock is in a base or breaking out, ideally before price makes its high (S18 [SECONDARY]) | Momentum relative to market; 52-week high of a ratio | None found | Yes [COMPILE] (`rsLeadsPrice` in Appendix A1) | **CANDIDATE** (H5) |
| **Minervini trend template** | (1) close > 150- and 200-day SMA; (2) 150 > 200; (3) 200-day SMA rising for at least 1 month; (4) 50 > 150 and 200; (5) close > 50; (6) close at least 25% (S12) or 30% (S18, attributed to the 2013 book) above the 52-week low: **sources conflict**; (7) within 25% of the 52-week high; (8) RS rating 70+ (S12, S18 [SECONDARY]) | Momentum, nearness to 52-week high (P2), moving-average distance (P7) | None found. One GitHub screener test (current constituents, Yahoo data, biased) trailed its benchmark in both windows (S18 [SECONDARY]) | Yes except the RS percentile [COMPILE] | **CONTEXT** (H6) |
| **Minervini VCP** | Base with typically 2-4 pullbacks, each smaller than the last ("commonly near half"), volume drying up, pivot = high of the last contraction, buy the close above the pivot on above-average volume, stop under the last contraction's low (S11 [SECONDARY]). "Automated detections differ across implementations" (S11) | No documented effect for contraction itself. Volatility clusters, so low range predicts low range, not direction [MEMORY]. Possible link to P6 (smooth trends continue more) | None found | Proxy only (range ratios and volume ratio) [COMPILE]; the discretionary pattern is not uniquely definable | **CANDIDATE**, low prior (H4) |
| **Weinstein stages** | Weekly chart, 30-week average (SMA in most sources; one script author says the book uses a weighted average: **conflict**, S18). Stage 2: close above base resistance on "strong volume" with the average turning up and Mansfield RS above zero; exit when stage 2 is lost; stage 4 is the short side (S11 [SECONDARY]). Mansfield RS, common form: (ratio / its 52-week average - 1) x 100 (S11) | Time-series trend: MA rules (P10, P9, P8) | None found for the stage rules. MA timing in general: see 4.1 | Yes, non-repainting weekly form [COMPILE] (Appendix A3) | **CONTEXT** (weekly trend state) |
| **Darvas box** | Box top = a high not exceeded for three following sessions; bottom = a low then not undercut for three sessions; buy stop just above the top; stop just below (sources differ on whether the high day counts and on stop placement, S18, S13 [SECONDARY]) | Breakout to new highs: attention and anchoring (P15, P2) | None for the box. Closest clean test: all-time-high breakout, P50. Darvas's own result is disputed: per Time magazine as cited in S13 [SECONDARY], the New York Attorney General found only $216,000 of ascertainable profits against the $2 million claimed; a court later stopped the probe | Yes [COMPILE] (state machine in A1) | **CANDIDATE** only as one member of the breakout family (H3) |
| **Qullamaggie breakout** | Universe: top 1-2% of stocks by 1-, 3- and 6-month gain; prior move "30-100%+", then an orderly consolidation; "Enter on the opening range highs" (1-, 5- or 60-minute); "Stop is always lows of the day and stop should not be wider than the ATR or ADR of the stock"; sell 1/3-1/2 after 3-5 days, move stop to break-even, trail the rest with the 10- or 20-day average (S1 [DOC]) | Momentum (P1), smooth-trend continuation (P6), short-term momentum in high-turnover stocks (P18) | None found | Daily-close version yes; the opening-range entry and low-of-day stop need intraday bars and a live trader | **CANDIDATE** in close-based form (H3, H4); intraday form outside the user's constraints |
| **Pocket pivot** (Morales & Kacher 2010) | Up day whose volume exceeds the largest down-day volume of the prior 10 sessions, near the 10- or 50-day average, not extended (S11 [SECONDARY]) | High-volume return premium (P16) | None found. S11 shows no test and says the rule "deserves independent testing rather than borrowed confidence" outside US equities | Yes [COMPILE] | **CANDIDATE**, low prior (variant inside H3) |
| **50/150/200-day templates** | Alignment of price > 50 > 150 > 200 with rising 200 | Moving-average distance, 21-day over 200-day (P7); trend factor (P8) | P7: value-weighted alphas "around 9%" annualized, "survive reasonable trading costs faced by institutions" | Yes [COMPILE] | **CONTEXT** |
| **ADR% / ATR% filters** | ADR% = 100 x (SMA(high/low, 20) - 1); Qullamaggie wants high ADR and stops no wider than one ADR (S1 [DOC]) | Trend signals pay most in high-volatility stocks (P9, P31); but high idiosyncratic volatility and high MAX stocks have low average returns (P29, P30) | Not as a filter on swing entries | Yes [COMPILE] | **CONTEXT** (risk unit and sizing, split variable in H6) |

### 3.2 Mean-reversion and reversal methods

| Method | Rule | Kernel | Independent test | Pine | Verdict |
|---|---|---|---|---|---|
| **Connors RSI(2)** | Close above the 200-day SMA; buy when RSI(2) < 10 (below 5 "did better"); exit on a close above the 5-day SMA; no stop: stops "hurt" performance; entry just before the close is preferred over the next open (S4 [SECONDARY]) | Short-term reversal as pay for providing liquidity (P33, P34, P35) | S5/S6 (Norgate data, Russell 3000, entry and exit at next open, RSI(2) < 1, exit RSI(2) > 70): 88,750 trades 2001-2018, about 65% winners; average per trade 0.89% in 2003-2007, 0.52% in 2010-2018, 0.33% in 2017-2018; 2022 update: returns negative above the 200-day in the 2020 and 2022 bear phases; "the edges are continuing to get smaller but are still there". Costs not included; inclusion of delisted names not stated. S7 (SPY only, fills at the signal close, 2 bp a side): Sharpe 0.97 before 2009, 0.68 after; 0.79% a trade before, 0.51% after. S8 (2009): out-of-sample evidence "mixed" | Yes [COMPILE] (A2) | **CANDIDATE** (H1, H2) |
| **Cumulative RSI** | Close above 200-day SMA; sum of RSI(2) over X days below Y; exit RSI(2) > 65; X = 2 in the book's tests on SPY 1993-2007 (S18 [SECONDARY]). Thresholds 35 / 65: [MEMORY] | Same | None beyond the RSI(2) tests | Yes [COMPILE] | Variant of H1 |
| **%b** | Close above 200-day SMA; %b below 0.2 three days running; exit %b > 0.8 [MEMORY]. Not confirmed today | Same | None found | Yes [COMPILE] | Variant of H1 |
| **ConnorsRSI** | "CRSI(3,2,100) = [ RSI(3) + RSI(UpDown Length,2) + ROC(100) ] / 3"; oversold below 10 (S17 [DOC]) | Same | Vendor tests only | Yes, no built-in `ta.crsi` needed [COMPILE] | Variant of H1 |
| **Raschke/Connors "Holy Grail"** | "A 14-period ADX must initially be greater than 30 and rising"; pullback "to the 20-period exponential moving average"; "put a buy stop above the high of the previous bar"; stop "at the newly formed swing low"; exit at the most recent swing high (S2 [DOC]). The book: "this is not a mechanical system" | Pullback inside a trend: momentum plus short-term reversal | None found. A Concretum study of eight patterns from Crabel and *Street Smarts* exists but is paywalled (not read) | Yes [COMPILE] | **CANDIDATE**, low prior (variant of H1 with a trend-strength gate) |
| **Turtle Soup** | "Today must make a new 20-day low"; "The previous 20-day low must have occurred at least four trading sessions earlier"; buy stop "5-10 ticks above the previous 20-day low", good today only; stop one tick under today's low (S2 [DOC]) | Stop-loss clusters just beyond obvious levels (P43, FX market); reversal after forced selling | S14: "liquidity sweep" on SPY daily, 547 events, +0.119% over 5 days, t = 0.94 | Yes [COMPILE] | **CANDIDATE**, low prior (H9) |
| **80-20** | Yesterday opened in the top 20% of its range and closed in the bottom 20%; today trades below yesterday's low; buy stop at yesterday's low. "This trade is a day trade only" (S2 [DOC]) | Intraday reversal | None | Yes on daily bars, but the trade is intraday | **REJECT**: a day trade by its authors' definition, outside the user's constraints |
| **Qullamaggie parabolic short** | "A stock up 50-100%+ in a few days or weeks (if larger cap) or 300-1000%+ (if smaller cap)", "up 3-5+ days in a row"; short the opening-range low or a VWAP failure; stop at the high of day; target the 10- and 20-day averages (S1 [DOC]) | Lottery stocks: high MAX predicts low returns, more than 1% a month between extreme deciles (P30); run-ups raise crash probability but not reliably the mean (P32, industries) | None found | Detection yes [COMPILE]; borrow cost and availability are not in TradingView data | **REJECT** as a trade (intraday entry, borrow, unbounded loss). **CONTEXT** as "do not open longs here" (H10) |

### 3.3 Event methods and reference levels

| Method | Rule | Kernel | Independent test | Pine | Verdict |
|---|---|---|---|---|---|
| **Episodic pivot** (Qullamaggie; attributed to P. Bonde in a search summary, S18 [SECONDARY]) | "An EP needs to be a gap of 10%+ and big volume should be there"; best ones trade their average daily volume in the first 15-30 minutes; earnings with large growth and a beat; "It's best if the stock has not rallied over the past 3-6 months"; enter the opening-range high, stop at the low of the day, trail with the 10- or 20-day average (S1 [DOC]) | Earnings drift (P19), announcement-return drift (P21), volume at the announcement (P22, P23), information-driven shocks drift while no-news shocks reverse (P25) | P51: 9,794 gaps of 6%+ with 200,000+ pre-market shares, 2016-2023, CRSP: buying the open and holding loses, minimum -0.25R after 8 days; with opening-range entry, trailing stop and four targets only "slightly profitable from the tenth day onwards". P20: drift gone for large stocks since 2006 | Daily version yes: gap, relative volume, close location, `request.earnings` bar [COMPILE]. Revenue surprise: not available (sibling report). Pre-market volume: not in a daily script | **CANDIDATE**, low prior, earnings-linked and liquid names only (H8) |
| **Anchored VWAP** (Shannon) | Volume-weighted average price since a chosen event bar (earnings gap, swing high/low, 52-week high). Above it the average buyer since the event is in profit; a reclaim is read as recovery (S18 [SECONDARY]; Shannon's own rules not read) | Reference prices and the disposition effect: unrealized-gain measures predict returns (P27); drift is strongest when news and holders' capital gains have the same sign (P26) | None found | Yes: `ta.vwap(source, anchor)` with a boolean anchor, for example the earnings bar [COMPILE]. Discretionary anchors need a user input | **CONTEXT** (stop/trail level; split variable in H8) |
| **Volume profile / market profile** | Volume by price over a window: point of control, value area (70%), high- and low-volume nodes | Support and resistance levels "coincide with peaks in depth on the limit order book" (P44 [PAPER]; NYSE sample [MEMORY]) | None found for swing horizons | True footprint via `request.footprint` on Premium (sibling report S20); OHLCV approximation compiles [COMPILE] (A3) but its loop cost is untested at runtime. TradingView's built-in profile indicators cannot be read by a script [MEMORY] | **CONTEXT** at most; no testable claim with evidence |
| **Wyckoff** | Accumulation/distribution "schematics": selling climax, spring (dip under the range low that closes back inside), sign of strength, last point of support [MEMORY] | The spring is the Turtle Soup / sweep event. The rest is narrative | None found | Spring: yes (same as H9). Phase labelling: not uniquely definable | **REJECT** as a system; spring folded into H9 |
| **ICT / "smart money concepts"** | Order block = last opposite-colour bar before an impulse; fair value gap = three-bar gap (low > high two bars earlier); liquidity sweep = break of an N-bar extreme that closes back; BOS/CHoCH = swing breaks | P43 (stop clusters), P44 (book depth at levels). No study of the constructs themselves | S14 (SPY, QQQ, DIA, IWM daily, next-open fills, no costs): order block +0.121% over 5 days (t = 1.22), FVG -0.005% (t = -0.08), sweep +0.119% (t = 0.94); of 32 t-statistics one reached 2; "0 of 648 backtests beat buy-and-hold" | Yes [COMPILE] | **REJECT** (no evidence, null test); sweep kept only inside H9 |
| **Bulkowski pattern statistics** | Per-pattern "average rise", "failure rate", throwback rate | P14: some patterns carry incremental information about return distributions (1962-1996) | Not independently replicated as tradable returns | Patterns partly definable; statistics not usable | **REJECT** as evidence (section 5.7) |

## 4. The documented effects behind the canon

One row per finding. "Net" = whether it survives realistic costs for liquid US stocks. "Other side" =
who loses.

### 4.1 Trend, momentum, breakouts

| # | Claim | Size, universe, period | Source | Replication / recent evidence | Net of costs | Mechanism; other side | Pine | Verdict |
|---|---|---|---|---|---|---|---|---|
| A1 | Past 3-12 month winners keep winning for 3-12 months; part reverses in years 2-3 | Abstract gives no number; about 1% a month for the 6x6 strategy, NYSE/AMEX 1965-1989 [MEMORY] | P1 [PAPER] | P3 [PAPER]: "momentum profits have become insignificant since the late 1990s" (US, 1965-2012). P38 [PAPER]: most factors "can be replicated" and "work out-of-sample" (general statement, not momentum-specific). **Contested** | P37 [PAPER]: anomalies with one-sided monthly turnover below 50% mostly keep significant net spreads | Under-reaction; sellers anchored on purchase price (P27). Other side: holders who sell winners early | `close[21]/close[252]-1` [COMPILE] | CONTEXT |
| A2 | Nearness to the 52-week high "dominates and improves upon the forecasting power of past returns"; no long-run reversal | No number in abstract | P2 [PAPER] | Not checked today | Low turnover | Anchoring on the high; other side: sellers who treat the high as resistance | `close/ta.highest(close,252)` [COMPILE] | CONTEXT (H6) |
| A3 | Distance between short and long moving averages (21-day over 200-day) predicts returns beyond momentum and the 52-week high | "Annualized value-weighted alphas ... around 9%", long side stronger | P7 [PAPER] | Published 2021; no later check found | "survive reasonable trading costs faced by institutions" | Same family | `ta.sma(close,21)/ta.sma(close,200)` [COMPILE] | CONTEXT (H6) |
| A4 | Momentum from many small moves continues; momentum from a few jumps does not | Six-month momentum "8.86%" for continuous information vs "2.91%" for discrete | P6 [PAPER] | Not checked | Not stated | Inattention to gradual news ("frog in the pan") | Sign(past return) x (% down days - % up days) [COMPILE] | CANDIDATE (H7) |
| A5 | Momentum crashes after market declines in high volatility; risk-scaled momentum roughly doubles the Sharpe ratio | No numbers in abstracts | P4, P5 [PAPER] | Both published and widely cited [MEMORY] | n/a | Losers behave like options in rebounds | Market state: index below 200-day, VIX via `request.security` | CONTEXT (market filter) |
| A6 | Moving-average timing on volatility-sorted portfolios beats buy-and-hold, most in high-volatility portfolios, more than momentum | No numbers in abstract; US, about 1963/65-2009 per a library record (S18 [SECONDARY]; start year not confirmed) | P9 [PAPER] | Not checked | Break-even cost said to be large (S18 [SECONDARY]) | Under-reaction under uncertainty (P31) | Yes | CONTEXT |
| A7 | Simple MA and trading-range-break rules "provide strong support" on the Dow 1897-1986 | Buy signals followed by higher, less volatile returns than sell signals | P10 [PAPER] | P11 [PAPER] re-examines with data-snooping control. P12 [PAPER], Dow 1897-2011: "an investor would never have been able to select ex ante the future best-performing rules" and "even in-sample, the performance is completely offset by the introduction of low transaction costs" | **No** (P12) | n/a | Yes | REJECT as stand-alone index timing |
| A8 | When price crosses its 52-week high or low, volume spikes, and "returns are reliably positive" afterwards | No number in abstract | P15 [PAPER] | Not checked | Unknown | Attention-driven buying by small investors. Other side: anchored sellers at the old high | Yes [COMPILE] | CANDIDATE (H3) |
| A9 | All-time-high breakout, next-open entry, 10 x ATR(42) trailing stop, all liquid US stocks incl. about 24,000 delisted, 1950 - Oct 2024 | About 66,000 trades; win rate 43.9%; average +0.50R (winner +1.90R, loser -0.70R); "less than 7% of the trades were responsible for generating all of the strategy's profits"; 8% of trades lost more than 1R, usually on overnight gaps; average trade 0.39R before the 2005 publication of the original study, 0.31R after; winners held 370 days on average. Portfolio 1991-2024 gross: CAGR 15.02% vs 11.18% market, Sharpe 0.85 vs 0.54, max drawdown 31.75% vs 54.68% | P50 [PAPER]; cost per round trip 0.50% in the trade statistics | The paper is itself the out-of-sample check of Wilcox & Crittenden (2005) | Portfolio net of costs: $100k account 2.45% CAGR, alpha -4.63%; with their turnover control 12.97%. Weights are 1/max(200, number of holdings) per name: a book built for hundreds of positions | Outlier capture. Other side: sellers at new highs | Yes on daily bars | CONTEXT. Holding period (a year for winners) and hundreds of positions do not fit the user; the lesson is the skew |
| A10 | High-turnover stocks show one-month continuation; low-turnover stocks show reversal | "as profitable and as persistent as conventional price momentum", "survives transaction costs", "strongest among the largest, most liquid" stocks. 1.37% a month in the top turnover decile is a third-party figure (S18 [SECONDARY]) | P18 [PAPER] | US and international in the paper | Yes per abstract | Traders under-read the information in prices | 21-day return and turnover proxy (volume / average volume; shares outstanding not historical) | CONTEXT; supports volume-confirmed moves over quiet ones |
| A11 | Unusually high volume over a day or week predicts higher returns over the next month | No number in abstract | P16 [PAPER] | P23 [PAPER]: holds around earnings and is separate from the earnings surprise | Unknown | Visibility: a volume shock widens the set of potential buyers | Relative volume [COMPILE] | CANDIDATE inside H3, H8 |
| A12 | High-volume winners reverse sooner; low-volume winners continue up to three years | High-volume winners minus losers beats plain momentum "by 2% to 7% per year" at intermediate horizons, then reverses in years 2-3 | P17 [PAPER] | Not checked | Unknown | Volume marks where a stock is in its "momentum life cycle" | Yes | CONTEXT. **Conflicts** with the canon's "more volume is better" at longer horizons |

### 4.2 Short-term reversal

| # | Claim | Size, universe, period | Source | Replication / recent | Net | Mechanism; other side | Pine | Verdict |
|---|---|---|---|---|---|---|---|---|
| B1 | Reversal profits are the pay for providing liquidity and rise sharply with the VIX | No number in abstract | P33 [PAPER] | P35 [PAPER]: higher volatility gives faster, initially stronger reversals; lower turnover gives more persistent ones | See B2 | Other side: sellers who need immediacy. The dip buyer carries inventory risk exactly when it is highest | RSI(2), VIX via `request.security` | CANDIDATE (H2) |
| B2 | Reversal strategies restricted to large caps earn "30-50 basis points per week net of trading costs" | Weekly, large US caps; sample ends about 2009 [MEMORY] | P34 [PAPER] | Practitioner decay evidence S5, S6, S7 (section 3.2) | Yes in the paper's period; margin now thin | Same | Yes | CANDIDATE (H1) |
| B3 | Published predictors lose about half their return after publication | "average post-publication decay ... is about 50%"; out-of-sample but pre-publication decay 15% | P36 [PAPER], 56 characteristics (97 in the published version [MEMORY]) | - | - | Informed traders act on publications | - | Prior for every published rule: halve it |

### 4.3 Events

| # | Claim | Size, universe, period | Source | Replication / recent | Net | Mechanism; other side | Pine | Verdict |
|---|---|---|---|---|---|---|---|---|
| C1 | Prices drift in the direction of the earnings surprise for weeks | About 4% over 60 days between extreme surprise deciles, 1974-1986 [MEMORY] | P19 (existence only) | P20 [PAPER]: "For large stocks, PEAD have been non-existent since 2006"; disappeared "only recently for microcap stocks" | For liquid names today: doubtful | Under-reaction; now arbitraged on the announcement day | Surprise = (actual - estimate) / abs(estimate) from `request.earnings` [COMPILE] | CONTEXT; lowers the prior of H8 |
| C2 | Sorting on the announcement-window return (EAR) gives drift of "7.55% per year", 1.3% more than the classic surprise; combining both about 12.5% | US, sample ends mid-2000s [MEMORY] | P21 [PAPER] | Predates P20's finding | Unknown | The price reaction contains more than the EPS number | Gap + first-day return on the earnings bar | CANDIDATE (H8) |
| C3 | Post-earnings returns increase with unexplained volume at the announcement | "strictly increasing in the component of volume that is unexplained by prior trading activity" | P22 [PAPER]; P23 [PAPER] finds it complementary to the surprise | Not checked | Unknown | Divergence of opinion / visibility | Relative volume on the earnings bar | CANDIDATE (H8) |
| C4 | Large price moves with information drift; without information they reverse | No number in abstract; information proxied by analyst reports | P25 [PAPER] | Not checked | Unknown | Under-reaction to fundamentals, over-reaction to noise | Earnings bar yes; other news no | CANDIDATE: the control group of H8 |
| C5 | Drift is strongest when the news and holders' unrealized gains have the same sign | "monthly alphas of over 200 basis points" for the event strategy | P26 [PAPER] | Not checked | Unknown | Disposition effect: winners are sold too early into good news. Other side: those sellers | Capital-gain proxy: close vs anchored VWAP or vs 52-week high | CONTEXT. **Conflicts** with Qullamaggie's "best if the stock has not rallied" |
| C6 | Past-year winners rise before their earnings date and fall after | "+1.58 percent" market-adjusted in the five days before; "1.86 percent" in the five days after. The abstract's own explanation (negative news "just afterwards") implies the second figure is negative; the minus sign is missing in the record read | P28 [PAPER] | Not checked | "remain significant even after accounting for transactions costs" | Attention-driven retail buying before the date | Next earnings date: `earnings.future_time` (sibling report) | CONTEXT: do not open momentum longs just before earnings |
| C7 | Stocks rise around scheduled announcements, more so with high past announcement volume | No number in abstract | P24 [PAPER] | Not checked | Unknown | Small-investor buying on attention | As C6 | CONTEXT |

### 4.4 Volatility and lottery effects

| # | Claim | Size | Source | Note | Verdict |
|---|---|---|---|---|---|
| D1 | High idiosyncratic volatility stocks have "abysmally low average returns" | No number in abstract | P29 [PAPER] | P30 says including MAX "reverses" this relation | CONTEXT |
| D2 | High maximum daily return over the past month predicts low returns | Decile spread "exceed[s] 1% per month" | P30 [PAPER] | Basis for H10 | CONTEXT |
| D3 | Greater information uncertainty gives higher returns after good news and lower after bad news | No number in abstract | P31 [PAPER] | Reconciles D1/D2 with the canon's taste for high ADR: volatility helps only conditional on good news or an uptrend | CONTEXT |
| D4 | Sharp run-ups do not predict low average returns but do predict a "substantially heightened probability of a crash" | US industries 1926-2014 | P32 [PAPER] | Industry level, not single stocks | CONTEXT for H10 |

## 5. Where practitioners or the literature are wrong, or disagree

| # | Point | The two sides | What it means for us |
|---|---|---|---|
| 5.1 | **Do IBD-style ranks pick winners?** | For: P47 (1.81% a month abnormal, declining in the second half); AAII's hypothetical CAN SLIM screen, 19.2% a year since 1998 against 5.7% for the S&P 500 price index, as of 31 May 2023 (S10 [SECONDARY]). Against: the screens "usually have a small number of passing companies" (none on 12 Jun 2023 for the original screen), and the article states no costs or rebalancing method; P48: after costs 32% of AAII screens beat the index; IBD 50 ETF 2015-2022 lost 1.35% a year, drawdown -57.5% against -33.7% for SPY; by sub-period +11.15% vs +10.65% a year to mid-2018, then -9.73% vs +9.75% (S19 [SECONDARY]). A search summary of the fund's factsheet gives 1.24% a year since inception against 12.45% for the S&P 500 as of 31 Mar 2025 (S18 [SECONDARY], factsheet not opened) | Ranks on growth and relative strength do not carry a reliable premium in recent real-money form. Use them as context only |
| 5.2 | **Is momentum still alive in US stocks?** | P3: insignificant since the late 1990s. P38: factors replicate. P7 (2021): moving-average distance alpha about 9% | The filter family is the best-supported part of the canon, but its recent strength is disputed. H6 tests it as a filter on our own entries, not as a premium |
| 5.3 | **Does the entry pattern matter?** | Canon: yes (VCP, handle, pivot, pocket pivot). Evidence: none found either way with clean data; P50 shows the profit comes from a few outliers held for a year; the previous session of this project found no entry rule beating random entries in the same uptrends (project log, prior not fact) | Entry patterns are tested against matched controls in the same trend state (H3-H5), never against zero |
| 5.4 | **High-volume breakouts** | For: P15, P16, P18. Against: P17 (high-volume winners reverse sooner) | Horizon-dependent. Pre-register the horizon (20 days) before testing |
| 5.5 | **High volatility: sought or avoided?** | Canon: high ADR%. P29, P30: high volatility and lottery stocks underperform. P9, P31: trend signals work best in volatile stocks | ADR% is a risk unit and a split variable, not a return predictor |
| 5.6 | **Earnings gaps** | Canon: buy 10%+ gaps on volume. P51: mechanical buying loses; P20: drift gone in large stocks. P21-P23, P25: announcement return and volume predicted drift in older samples. Qullamaggie prefers no prior rally; P26 predicts stronger drift when holders sit on gains | H8 with two pre-registered splits (prior 6-month return; earnings vs no earnings) |
| 5.7 | **Bulkowski's numbers** | His definitions (S3 [DOC]): average rise is measured "from the opening price the day after the breakout to the ultimate high"; ultimate high is "the highest peak before price declines by at least 20%"; failure = a pattern that fails to move "by at least 5%"; bull and bear markets are fixed calendar windows chosen afterwards. No costs | Three defects: (1) the exit is known only in hindsight, so "average rise" is an upper bound on a path, not a return; (2) the 5% failure threshold ignores the loss taken when a pattern fails; (3) pattern identification and sample membership are not reproducible, so survivorship and selection cannot be audited. Academic work finds at most "incremental information" in some patterns (P14) and no cost-robust, selectable rule on the Dow (P12). Head-and-shoulders excess returns of 7-9% a year over three months: [MEMORY], Savin, Weller & Zvingelis (2007), abstract not obtained |
| 5.8 | **Stops** | O'Neil 7-8%, Minervini, Qullamaggie: always. Connors: stops "hurt". P39: under a random walk a stop "always decrease[s] a strategy's expected return, but in the presence of momentum, stop-loss rules can add value"; P40: a 10% stop on momentum portfolios cut the worst month from -49.79% to -11.36% (equal-weighted, 1926-2013) and more than doubled the Sharpe ratio | Stops belong on trend/breakout trades; on dip trades a time or strength exit is the consistent choice (H11) |
| 5.9 | **Trader track records** | Minervini (US Investing Championship 2021, +334% per a search summary, S18 [SECONDARY]), Kullamägi (self-reported, S1), Stamatoudis (P51) are selected outcomes of single traders | Not evidence for a rule. P51's discretionary result (1,580 trades, 18% winners, +1.03R average, Sharpe 1.7, max drawdown 35%, 2016-2023) rests on one trader and on intraday opening-range entries; the charts were anonymised, but they come from years in which he traded live |
| 5.10 | **SMC win rates** | Vendors quote 65-80% (S18 [SECONDARY]); S14 finds no significant edge | Fill rates of gaps are not returns |
| 5.11 | **Day-trading economics** | P46: of Brazilian individuals who day-traded more than 300 days, "97% ... lost money". P45: individuals underperform, sell winners and hold losers | The swing trader's counterparties in A1-A8 are largely these behaviours; the same biases threaten our own user |

## 6. What swing traders actually load on TradingView

Boost counts read today from each script's page (S15 [DOC]). TradingView's script listing offers only
two sorts, `latest_popular` and `recent_extended` (page source, [DOC]); there is no all-time ranking,
so the first table is a set of known scripts, not a guaranteed top list.

| Script (author, year) | Boosts | What it computes | Underlying idea |
|---|---|---|---|
| Smart Money Concepts (SMC) [LuxAlgo] (2022), `CnB3fSph` | 180,820 | "market structure (internal & swing BOS / CHoCH), order blocks, premium & discount zones, equal highs & lows" [DOC] | ICT vocabulary; no evidence (3.3) |
| Squeeze Momentum Indicator [LazyBear] (2014), `nqQ1DT5a` | 118,154 | "a derivative of John Carter's 'TTM Squeeze' volatility indicator" [DOC]: Bollinger bands inside Keltner channels plus a regression momentum histogram [MEMORY] | Volatility contraction then expansion |
| SuperTrend (KivancOzbilgic, 2020), `r6dAP7yi` | 85,435 | "one of the most common ATR based trailing stop indicators" [DOC] | Trend following |
| CM_Williams_Vix_Fix (ChrisMoody, 2014), `og7JPrRA` | 66,209 | Larry Williams's synthetic VIX from price, with percentile highlight bars [DOC]; formula (highest close of 22 bars minus low, over that highest close) [MEMORY] | Capitulation / reversal |
| UT Bot Alerts (QuantNomad, 2020), `n8ss8BID` | 62,094 | Alerts from an ATR trailing stop [MEMORY for the computation] | Trend following |
| WaveTrend Oscillator [LazyBear] (2014), `2KE8wTuF` | 61,566 | Oscillator; crosses in overbought/oversold bands as signals [DOC] | Mean reversion |
| Machine Learning: Lorentzian Classification (jdehorty, 2023), `WhBzgfDu` | 37,606 | A Lorentzian-distance classifier over a multi-dimensional feature space, used to predict price direction [DOC] | Nearest-neighbour classifier on oscillators; no out-of-sample evidence on the page read |
| Nadaraya-Watson Envelope [LuxAlgo] (2021), `Iko0E2kL` | 35,544 | Kernel-smoothed envelope with alerts on crosses of its extremities, described as contrarian [DOC]; repaints in its default mode [MEMORY] | Mean reversion; repaint risk |
| Order Blocks & Breaker Blocks [LuxAlgo] (2023), `piIbWMpY` | 30,745 | Order-block zones | ICT |
| Fair Value Gap [LuxAlgo] (2022), `jWY4Uiez` | 26,838 | Three-bar gaps | ICT |
| VuManChu Cipher B + Divergences (2019), `Msm4SjwI` | 24,966 | Page description reads "Market Cipher B" [DOC]; WaveTrend, money flow, RSI, divergences [MEMORY] | Oscillator bundle |

Scripts that implement the swing canon itself, highest boosts on the first page of each search (S15 [DOC]):

| Search | Top result (author, year) | Boosts |
|---|---|---|
| ADR% | Swing Data - ADR% / RVol / PVol / Float % / Avg $ Vol (jfsrev, 2023) | 7,207 |
| ADR% | ADR% - Average Daily Range % by MikeC (TheScrutiniser, 2020) | 5,653 |
| darvas | DARVAS BOX by KIVANC fr3762 (KivancOzbilgic, 2018) | 6,246 |
| wyckoff | Wyckoff [theUltimator5] (2026) | 8,324 |
| volume profile | Volume Profile [Makit0] (2020) | 4,961 |
| relative strength rating | Industry Group Strength (Amphibiantrading, 2024) | 4,372 |
| minervini | Minervini Trend Template (yogy.frestarahmawan, 2021) | 3,518 |
| RS line | RS Line - Relative Strength Line [LevelUp] (2021) | 3,000 |
| pocket pivot | Pocket Pivot Breakout (simatricks, 2023) | 1,800 |
| anchored vwap | Anchored VWAP (stuehmer, 2019) | 1,610 |
| qullamaggie | Qullamaggie Breakout V2 (millerrh, 2021) | 1,529 |
| stage analysis | Stage Analysis (EquityCraze, 2022) | 1,227 |
| episodic pivot | Episodic Pivot (yogy.frestarahmawan, 2021) | 481 |
| connors rsi | Stochastic Connors RSI (everget, 2017) | 369 |

Reading: generic oscillators, ATR trailing stops and SMC overlays have 10 to 100 times the boosts of
canon-specific tools. TradingView's 2025 awards for "Most Boosted Public Pine Scripts" went to
Smart Money Breakout Channels [AlgoAlpha], Support and Resistance Power Channel [ChartPrime] and
Dynamic Swing Anchored VWAP [Zeiierman] (S16 [DOC]). None of the pages read publishes a
survivorship-free, out-of-sample test. The gap in the market is not another overlay; it is a tool that
states its tested edge and its controls.

## 7. Execution for a part-time trader: what practitioners say, what the evidence adds

| Topic | Practitioner rule | Evidence | Implication for the design |
|---|---|---|---|
| **Entry at the close vs next open (reversal signals)** | Connors prefers entering just before the close (S4 [SECONDARY]) | SPY reversal signal: fill at the signal close 31 bp per trade and 74% winners; signal at 15:45 with a market-on-close order 27 bp; next open 22 bp and 63% (S9 [SECONDARY]; period and costs not stated). Alvarez's stock tests enter at the next open and still show the edge, shrinking (S5, S6) | About a third of a fast signal's edge is gone by the next open (one index, one study). H12 measures it on our universe. An alert shortly before the close on the forming daily bar is the alternative, and it must be labelled as not bar-close |
| **Entry at the open (momentum signals)** | O'Neil/Minervini/Qullamaggie buy the breakout intraday as it happens | "all of the abnormal returns on momentum strategies remarkably occur overnight", stronger "for large-cap and high-price stocks" (P41 [PAPER]). P50 enters at the next open and exits at the next open after a close below the stop | A next-open entry skips the first overnight but holds all later ones. For multi-week holds the loss is one night out of many; for 3-5 day holds it is material |
| **Closing auction** | - | "Closing auctions ... account for a striking 7.5% of daily volume in 2018, up from 3.1% in 2010"; "price impact is lower than during continuous trading" (P42 [PAPER]) | Market-on-close orders are a cheap fill for a trader who can act 10-15 minutes before the close |
| **Buying gap-ups at the open** | Qullamaggie buys the opening-range high, stop at the low of day, risk 0.25-1% (S1 [DOC]) | P51: "Open - No Stop" on 6%+ gaps: minimum -0.25R after 8 days; with a 1-ATR stop -0.17R; opening-range variants still unprofitable until four profit targets are added | Without intraday selection the gap entry has negative expectancy in that sample. Not for an alert-driven trader |
| **Stop placement** | O'Neil: sell at 7-8% below cost (S18 [SECONDARY]). Minervini: risk 1.25-2.5% of equity per trade, stop at most about 10% (sources vary: 8%, 5-8%; S18 [SECONDARY]). Qullamaggie: low of the entry day, never wider than one ADR (S1 [DOC]). Raschke: "one tick under today's low" or the new swing low (S2 [DOC]). Connors: none (S4) | P39, P40 (5.8). P50: stop about 10 ATR(42) below the high, ratchets up, acted on at the next open after a close below it | Trend trades: volatility-scaled stop. Dip trades: time/strength exit; test a wide disaster stop separately (H11) |
| **Gaps through stops** | Rarely addressed | P50: 5,497 trades (8%) lost more than the initial risk, "usually ... when stocks experienced negative overnight drops due to unexpected news"; spikes in 1987 and 2020 | Size positions on the assumption that roughly one stop in twelve fills worse than planned. The project protocol already fills gap-throughs at the open |
| **Position size** | Qullamaggie: "My risk on most trades is usually 0.25-1%"; never "more than 30% of your account over night in any stock" (S1 [DOC]). P51 sizes every trade to lose 0.25% of equity at the stop | P50 sizes by volatility: weight proportional to 30% / stock volatility | Size = risk budget / stop distance, with a cap per name. ADR% or ATR% is the natural unit |
| **Partial exits and trailing** | Qullamaggie: sell 1/3-1/2 after 3-5 days, stop to break-even, trail with the 10- or 20-day average (S1 [DOC]). Raschke: exit at the prior swing high, trail the rest (S2 [DOC]) | P51: adding four targets (2R, 4R, 8R, 10R) moved the gap strategy from losing to "slightly profitable"; no general evidence | A management choice; test it as such, with the same entries |
| **Win rate to expect** | Qullamaggie: "You can be wildly profitable with having just a 25-30% winrate" (S1 [DOC]) | P50: 43.9% winners, 56% losers, 7% of trades make the profit. P51 discretionary: 18% winners. Dip buying: about 65% winners with small average gain (S5) | The display must show expectancy in R and the losing streak to expect, not win rate alone |
| **Number of positions** | Not verified today for O'Neil or Minervini | P50's edge needs breadth: its weights assume at least 200 names, and the base portfolio is not viable under $1M without turnover control because of per-order costs | A 5-10 position trader running an outlier-dependent rule will see far more variance than the paper. Favour rules whose edge does not hinge on catching the 7% |
| **Costs** | Usually ignored | P50 cites 5-25 bp for the 500 largest US stocks (de Groot et al.) and settles on 25 bp a side as conservative; P37: high-turnover anomalies rarely survive | The project's 5/10/25 bp per side by liquidity bucket is in line |
| **Earnings dates** | Qullamaggie trades the earnings gap itself | P28, P24 (pre-announcement run-up, post-announcement give-back for past winners) | Show days to the next earnings date on every alert |

## 8. Pine computability

All checks below are compile-level only; runtime limits and numerical parity are not tested.

| Item | Status | Evidence |
|---|---|---|
| Trend template (7 price criteria), 52-week nearness, MA distance, 12-1 momentum, information discreteness, ADR%, ATR%, Darvas state machine, pocket pivot loop, VCP proxy, relative-volume breakout, RS line, RS-line new high, Mansfield RS, weighted ROC vs benchmark | Compiles, 0 errors, 0 warnings | [COMPILE] Appendix A1 |
| RSI(2), cumulative RSI, %b via `ta.bb`, ConnorsRSI built from `ta.rsi`, a streak series and `ta.percentrank`; Holy Grail via `ta.dmi` and `ta.ema`; Turtle Soup via `ta.lowest` and `ta.lowestbars`; 80-20; earnings-bar detection and EPS surprise via `request.earnings`; gap/relative-volume episodic pivot; parabolic extension; MAX(21); anchored VWAP with `ta.vwap(source, anchor)`; fair value gap, sweep, order-block proxy | Compiles, 0 errors, 0 warnings | [COMPILE] Appendix A2 |
| Weekly 30-week average, weekly breakout with 2x volume, weekly RS proxy from a lower-timeframe chart using the previous completed week (`[1]` inside the expression with `lookahead_on`); volume-at-price approximation with point of control and 70% value area | Compiles, 0 errors, 0 warnings | [COMPILE] Appendix A3 |
| Function syntax: a return type before a function name is rejected (`CE10152 "float" is not a valid method keyword`) | Compiler error observed, then fixed | [COMPILE] |
| `ta.*` calls inside `and` expressions or `if` blocks raise CW10002 / CW10003; all history-dependent calls were moved to global scope | Warnings observed, then fixed | [COMPILE] |
| IBD RS Rating as a percentile of all stocks | Not computable in a script; needs an external screener or a fixed basket | 40 unique `request.*` calls per script on Premium (sibling report S20) |
| Revenue growth and revenue surprise for episodic pivots | Not available: `request.earnings` returns EPS only (sibling report S20) | not re-verified |
| Pre-market volume, opening-range entries, low-of-day stops | Need intraday bars; on a 1h chart the first-hour high is known only at 10:30 ET | design constraint |
| Short borrow cost / availability (parabolic shorts) | Not in TradingView data [MEMORY] | - |
| True volume profile | `request.footprint` on Premium, one call per script (sibling report S20) | not re-verified |
| Which bar carries an after-close earnings report | Unresolved (sibling report, open item) | affects H8 |

## 9. Could not verify today

1. IBD's own definition of the RS Rating, the RS-line "blue dot" and the buy rules (site not readable);
   the reported April 2026 change to the rating; the 40/20/20/20 weighting (community approximation).
2. Minervini's exact trend-template wording (25% vs 30% above the 52-week low) and his risk rules:
   books not read; secondary sources conflict.
3. Weinstein: SMA vs weighted 30-week average; any numeric volume threshold (2x is an unverified convention).
4. Darvas: exact box rules from the book; the Time/Attorney-General account is via Wikipedia only.
5. Connors & Alvarez: cumulative-RSI thresholds, the %b rule and the book's own statistics.
6. Brian Shannon's own anchored-VWAP rules.
7. FFTY factsheet figures (1.24% vs 12.45% a year since inception as of 31 Mar 2025): search summary
   only; the fund page now returns "Page Not Found"; a reorganisation into a Capital-FORCE trust was
   approved in April 2026 per search summaries. My own computation stops at 30 Dec 2022.
8. Effect sizes marked [MEMORY]: Jegadeesh-Titman 1% a month; Bernard-Thomas drift; Han-Yang-Zhou
   sample; Savin-Weller-Zvingelis head-and-shoulders result; de Groot et al. sample end; George, Hwang &
   Li (2015) on the 52-week high and earnings drift (abstract blocked); Kumar, Ruenzi & Ungeheuer on
   daily winners (abstract blocked).
9. The sign of the post-announcement figure in P28 (record shows "1.86 percent" without a minus sign).
10. Sample period of P47 (Olson et al.) and whether its returns are net of costs.
11. Whether Alvarez's Norgate tests include delisted stocks (not stated on the pages read).
12. Period, data and costs behind S9's SPY execution-delay figures.
13. Concretum's paywalled study of eight Crabel / *Street Smarts* patterns.
14. Any all-time "most boosted" ranking on TradingView (the site exposes none); repaint behaviour of the
    Nadaraya-Watson Envelope script; exact computations of UT Bot and Vix Fix.
15. Runtime behaviour of the three Pine packs (loop cost of the volume-at-price approximation,
    `request.earnings` bar alignment, weekly values on intraday charts).
16. Wyckoff definitions (no source read) and any quantitative Wyckoff or market-profile study.

## 10. Appendix A: Pine definitions that compile (TradingView compiler, 2026-11-11)

Three scripts, each 0 errors and 0 warnings. Nine compiler calls in total: six during development
(one failure, two warning rounds) and three to compile the blocks below exactly as printed in this
file. Compile-level only.

### A1. Trend, relative strength, breakout

```pine
//@version=6
indicator("canon pack 1: trend / RS / breakout definitions", overlay = false, max_bars_back = 600)

string benchSym = input.symbol("AMEX:SPY", "Benchmark")
int    yearBars = input.int(252, "Bars in 52 weeks", minval = 50)
float bench = request.security(benchSym, timeframe.period, close, ignore_invalid_symbol = true)

// Minervini trend template (RS rating replaced by weighted ROC in excess of the benchmark)
float ma50  = ta.sma(close, 50)
float ma150 = ta.sma(close, 150)
float ma200 = ta.sma(close, 200)
float hi52  = ta.highest(high, yearBars)
float lo52  = ta.lowest(low, yearBars)
bool c1 = close > ma150
bool c1b = close > ma200
bool c2 = ma150 > ma200
bool c3 = ma200 > ma200[21]
bool c4 = ma50 > ma150
bool c4b = ma50 > ma200
bool c5 = close > ma50
bool c6 = close >= 1.30 * lo52
bool c7 = close >= 0.75 * hi52
wroc(float s) => 0.4 * (s / s[63] - 1) + 0.2 * (s / s[126] - 1) + 0.2 * (s / s[189] - 1) + 0.2 * (s / s[252] - 1)
float rsRawStock = wroc(close)
float rsRawBench = wroc(bench)
float rsExcess   = rsRawStock - rsRawBench
bool c8 = rsExcess > 0
bool trendTemplate = c1 and c1b and c2 and c3 and c4 and c4b and c5 and c6 and c7 and c8

// RS line, RS-line new high before price, Mansfield RS
float rsLine    = close / bench
float rsHi      = ta.highest(rsLine, yearBars)
bool  rsNewHigh = rsLine >= rsHi
bool  priceNewHigh = high >= hi52
bool  rsLeadsPrice = rsNewHigh and not priceNewHigh
float mansfield = (rsLine / ta.sma(rsLine, yearBars) - 1) * 100

// Weinstein stage proxy on the chart timeframe (150 bars ~ 30 weeks on daily)
float wma30   = ta.sma(close, 150)
float slope30 = wma30 / wma30[20] - 1
int stage = close > wma30 and slope30 > 0.005 ? 2 : close < wma30 and slope30 < -0.005 ? 4 : slope30 >= -0.005 and slope30 <= 0.005 and close[60] < wma30[60] ? 1 : 3

// Academic kernels
float near52   = close / ta.highest(close, yearBars)
float mad      = ta.sma(close, 21) / ma200
float mom12_1  = close[21] / close[252] - 1
float posDays  = math.sum(close > close[1] ? 1.0 : 0.0, 231)[21]
float negDays  = math.sum(close < close[1] ? 1.0 : 0.0, 231)[21]
float fipID    = math.sign(mom12_1) * (negDays - posDays) / 231

float adrPct = 100 * (ta.sma(high / low, 20) - 1)
float atrPct = 100 * ta.atr(14) / close

// Darvas-style box
var float boxTop = na
var float boxBot = na
var int   boxState = 0
float hh4 = ta.highest(high, 4)
float ll4 = ta.lowest(low, 4)
bool  isTop = high[3] == hh4 and high[3] >= hi52[3]
bool  isBot = low[3] == ll4
bool  darvasBreak = false
if boxState == 0 and isTop
    boxTop := high[3]
    boxBot := na
    boxState := 1
else if boxState == 1
    if high > boxTop
        boxState := 0
    else if isBot
        boxBot := low[3]
        boxState := 2
else if boxState == 2
    if close > boxTop
        darvasBreak := true
        boxState := 0
    else if close < boxBot
        boxState := 0

// Pocket pivot
float maxDownVol = 0.0
for i = 1 to 10
    if close[i] < close[i + 1]
        maxDownVol := math.max(maxDownVol, volume[i])
float ma10 = ta.sma(close, 10)
bool pocketPivot = close > close[1] and volume > maxDownVol and close > ma50 and low <= ma10 * 1.02

// VCP proxy
rng(int n) => (ta.highest(high, n) - ta.lowest(low, n)) / ta.highest(high, n)
float r60 = rng(60)
float r30 = rng(30)
float r10 = rng(10)
float volDry = ta.sma(volume, 10) / ta.sma(volume, 50)
bool vcpProxy = trendTemplate and r10 < 0.5 * r30 and r30 < 0.75 * r60 and volDry < 0.8 and close >= 0.90 * hi52
float pivot = ta.highest(high, 10)[1]
float volAvg50 = ta.sma(volume, 50)
bool vcpBreak = vcpProxy[1] and close > pivot and volume > 1.4 * volAvg50[1]

float rvol = volume / volAvg50[1]
bool hi52Break = close > hi52[1] and rvol >= 1.5

plot(rsExcess, "weighted ROC excess")
plot(mansfield, "Mansfield RS")
plot(near52, "nearness to 52w high")
plot(mad, "MAD 21/200")
plot(fipID, "FIP information discreteness")
plot(adrPct, "ADR%")
plot(atrPct, "ATR%")
plot(stage, "stage proxy")
plotshape(trendTemplate, "trend template", shape.circle, location.bottom, color.green)
plotshape(rsLeadsPrice, "RS new high before price", shape.circle, location.top, color.blue)
plotshape(pocketPivot, "pocket pivot", shape.triangleup, location.bottom, color.teal)
plotshape(darvasBreak, "Darvas break", shape.triangleup, location.bottom, color.orange)
plotshape(vcpBreak, "VCP-proxy break", shape.triangleup, location.bottom, color.purple)
plotshape(hi52Break, "52w high + rvol", shape.triangleup, location.bottom, color.red)
alertcondition(barstate.isconfirmed and vcpBreak, "VCP-proxy breakout", "VCP-proxy breakout on {{ticker}}")
alertcondition(barstate.isconfirmed and rsLeadsPrice and trendTemplate, "RS line new high before price", "RS line new high on {{ticker}}")
```

### A2. Mean reversion, Raschke, events, SMC

```pine
//@version=6
indicator("canon pack 2: mean reversion / Raschke / event / SMC definitions", overlay = false, max_bars_back = 600)

// Connors / Alvarez
float ma200   = ta.sma(close, 200)
float ma5     = ta.sma(close, 5)
float rsi2    = ta.rsi(close, 2)
float cumRsi2 = math.sum(rsi2, 2)
[bbMid, bbUp, bbLo] = ta.bb(close, 5, 1.0)
float pctB    = (close - bbLo) / (bbUp - bbLo)
bool  upTrend = close > ma200
bool  rsi2Buy = upTrend and rsi2 < 10
bool  rsi2Exit = close > ma5
bool  cumRsiBuy = upTrend and cumRsi2 < 35
bool  pctBlow = pctB < 0.2
bool  pctBBuy = upTrend and pctBlow and pctBlow[1] and pctBlow[2]
var float streak = 0.0
streak := close > close[1] ? (streak[1] > 0 ? streak[1] + 1 : 1) : close < close[1] ? (streak[1] < 0 ? streak[1] - 1 : -1) : 0
float rsi3      = ta.rsi(close, 3)
float rsiStreak = ta.rsi(streak, 2)
float prRoc     = ta.percentrank(ta.roc(close, 1), 100)
float crsi      = (rsi3 + rsiStreak + prRoc) / 3

// Raschke / Connors "Street Smarts"
[diPlus, diMinus, adx] = ta.dmi(14, 14)
float ema20 = ta.ema(close, 20)
bool  hgSetup = adx[1] > 30 and adx[1] > adx[4] and diPlus > diMinus and low <= ema20
bool  hgTrigger = hgSetup[1] and high > high[1]
float prevLow20   = ta.lowest(low, 20)[1]
int   prevLowBars = ta.lowestbars(low, 20)[1]
bool  turtleSoupBuy = low < prevLow20 and prevLowBars <= -3 and close > prevLow20
float rngY = high[1] - low[1]
bool  bar8020 = rngY > 0 and (open[1] - low[1]) / rngY >= 0.8 and (close[1] - low[1]) / rngY <= 0.2
bool  buy8020 = bar8020 and low < low[1] and close > low[1]

// Episodic pivot and parabolic extension
float epsAct = request.earnings(syminfo.tickerid, earnings.actual, gaps = barmerge.gaps_on, ignore_invalid_symbol = true)
float epsEst = request.earnings(syminfo.tickerid, earnings.estimate, gaps = barmerge.gaps_on, ignore_invalid_symbol = true)
bool  earnBar  = not na(epsAct)
bool  earnNear = earnBar or earnBar[1]
float gapPct   = open / close[1] - 1
float volAvg50 = ta.sma(volume, 50)
float rvol     = volume / volAvg50[1]
float closeLoc = high > low ? (close - low) / (high - low) : 0.5
bool  epDay    = gapPct >= 0.10 and rvol >= 3 and closeLoc >= 0.5 and close > open[0] * 0.98
bool  epEarnings = epDay and earnNear
float epsSurprise = na(epsEst) or epsEst == 0 ? na : (epsAct - epsEst) / math.abs(epsEst)
float adrPct   = 100 * (ta.sma(high / low, 20) - 1)
var int upStreak = 0
upStreak := close > close[1] ? upStreak + 1 : 0
float ext10    = close / close[10] - 1
float ma20     = ta.sma(close, 20)
float extMa20  = close / ma20 - 1
bool  parabolic = ext10 >= 0.5 and upStreak >= 3 and extMa20 > 0.3
float max21    = ta.highest(close / close[1] - 1, 21)

// Anchored VWAP
float avwapEarn = ta.vwap(hlc3, earnBar)
bool  newHi52   = high >= ta.highest(high, 252)
float avwapHigh = ta.vwap(hlc3, newHi52)
bool  aboveAvwapEarn = close > avwapEarn
bool  reclaimAvwap   = close > avwapEarn and close[1] <= avwapEarn[1]

// "Smart money concepts"
bool  fvgBull = low > high[2]
float fvgTop  = low
float fvgBot  = high[2]
float sweepLvl = ta.lowest(low, 20)[1]
bool  sweepBull = low < sweepLvl and close > sweepLvl
float atr20 = ta.atr(20)
bool  impulseUp = close - close[3] > 2 * atr20[3]
bool  obBull = impulseUp and close[3] < open[3]
var float obHi = na
var float obLo = na
if obBull
    obHi := high[3]
    obLo := low[3]
bool  obRetest = not na(obHi) and low <= obHi and close >= obLo and not obBull

plot(rsi2, "RSI(2)")
plot(cumRsi2, "cumulative RSI(2), 2 days")
plot(pctB, "%b (5,1)")
plot(crsi, "ConnorsRSI(3,2,100)")
plot(avwapEarn, "AVWAP from earnings")
plot(avwapHigh, "AVWAP from 52w high")
plot(epsSurprise, "EPS surprise")
plot(max21, "MAX(21)")
plot(adrPct, "ADR%")
plotshape(rsi2Buy, "RSI2 buy", shape.triangleup, location.bottom, color.green)
plotshape(cumRsiBuy, "cum RSI buy", shape.triangleup, location.bottom, color.teal)
plotshape(pctBBuy, "%b buy", shape.triangleup, location.bottom, color.blue)
plotshape(hgTrigger, "Holy Grail", shape.circle, location.bottom, color.orange)
plotshape(turtleSoupBuy, "Turtle Soup", shape.circle, location.bottom, color.purple)
plotshape(buy8020, "80-20", shape.circle, location.bottom, color.gray)
plotshape(epEarnings, "episodic pivot (earnings)", shape.diamond, location.top, color.red)
plotshape(parabolic, "parabolic", shape.xcross, location.top, color.maroon)
plotshape(fvgBull, "FVG", shape.square, location.top, color.aqua)
plotshape(sweepBull, "sweep", shape.square, location.top, color.lime)
plotshape(obRetest, "order-block retest", shape.square, location.top, color.navy)
plotshape(reclaimAvwap, "AVWAP reclaim", shape.flag, location.top, color.fuchsia)
alertcondition(barstate.isconfirmed and rsi2Buy, "RSI(2) pullback in uptrend", "RSI2 < 10 above 200-day on {{ticker}}")
alertcondition(barstate.isconfirmed and epEarnings, "Earnings gap on volume", "Episodic pivot candidate on {{ticker}}")
```

### A3. Weekly stage without repainting; volume-at-price approximation

```pine
//@version=6
indicator("canon pack 3: weekly stage (non-repainting) / volume-at-price approximation", overlay = true, max_bars_back = 600)

// previous COMPLETED weekly bar: [1] inside the expression + lookahead_on
[wClose, wMa30, wMa30Prev, wVol, wVolAvg, wHi] = request.security(syminfo.tickerid, "W", [close[1], ta.sma(close, 30)[1], ta.sma(close, 30)[5], volume[1], ta.sma(volume, 10)[2], ta.highest(high, 30)[2]], lookahead = barmerge.lookahead_on)
[bClose, bMa52] = request.security("AMEX:SPY", "W", [close[1], ta.sma(close, 52)[1]], lookahead = barmerge.lookahead_on)
float wSlope = wMa30 / wMa30Prev - 1
bool stage2 = wClose > wMa30 and wSlope > 0
bool stage4 = wClose < wMa30 and wSlope < 0
bool stage2Breakout = stage2 and wClose > wHi and wVol >= 2 * wVolAvg
float rsW = request.security(syminfo.tickerid, "W", close[1] / ta.sma(close, 52)[1], lookahead = barmerge.lookahead_on)
float mansfieldW = (rsW / (bClose / bMa52) - 1) * 100   // ratio-of-ratios proxy, not the exact Mansfield formula

int   nBars = input.int(120, "Profile bars", minval = 20, maxval = 500)
int   nBins = input.int(40, "Bins", minval = 10, maxval = 100)
float poc = na
float vah = na
float val = na
float top = ta.highest(high, nBars)
float bot = ta.lowest(low, nBars)
if barstate.islast or barstate.isconfirmed
    float step = (top - bot) / nBins
    if step > 0
        array<float> bins = array.new_float(nBins, 0.0)
        for i = 0 to nBars - 1
            float h = high[i]
            float l = low[i]
            float v = volume[i]
            int b0 = math.max(0, math.min(nBins - 1, math.floor((l - bot) / step)))
            int b1 = math.max(0, math.min(nBins - 1, math.floor((h - bot) / step)))
            float share = v / (b1 - b0 + 1)
            for b = b0 to b1
                array.set(bins, b, array.get(bins, b) + share)
        int iPoc = array.indexof(bins, array.max(bins))
        poc := bot + (iPoc + 0.5) * step
        float total = array.sum(bins)
        float acc = array.get(bins, iPoc)
        int lo = iPoc
        int hi = iPoc
        while acc < 0.7 * total and (lo > 0 or hi < nBins - 1)
            float up = hi < nBins - 1 ? array.get(bins, hi + 1) : -1.0
            float dn = lo > 0 ? array.get(bins, lo - 1) : -1.0
            if up >= dn
                hi += 1
                acc += up
            else
                lo -= 1
                acc += dn
        vah := bot + (hi + 1) * step
        val := bot + lo * step

plot(poc, "POC (approx.)", color.orange)
plot(vah, "VAH (approx.)", color.gray)
plot(val, "VAL (approx.)", color.gray)
plot(wMa30, "30-week SMA (last closed week)", color.blue)
bgcolor(stage2 ? color.new(color.green, 92) : stage4 ? color.new(color.red, 92) : na)
plotshape(stage2Breakout, "Stage-2 breakout (weekly, 2x volume)", shape.triangleup, location.belowbar, color.green)
alertcondition(barstate.isconfirmed and stage2Breakout and not stage2Breakout[1], "Stage 2 breakout", "Weekly stage-2 breakout on {{ticker}}")
alertcondition(barstate.isconfirmed and mansfieldW > 0 and stage2, "Stage 2 with positive RS", "Stage 2 + RS on {{ticker}}")
```

Known weaknesses of these definitions, stated so that nobody mistakes them for finished signals:
the stage proxy and VCP proxy are my own parameterisations, not the authors'; the Darvas state machine
requires the box top to be a 52-week high, which the sources do not all require; the weekly breakout
and its 2x volume threshold are an unverified convention; the volume-at-price loop runs up to
500 x 100 iterations on every confirmed bar and may hit the execution-time limit; `request.earnings`
bar alignment for after-close reports is unresolved.

## 11. Hypotheses to test

Common frame: universe and costs as in protocol section 5 ($20M median dollar volume, price $5+);
signal at the close of bar *t*; entry at the open of *t*+1 unless stated; inference on the daily series
of signal-minus-control differences. "Prior" = my probability that the stated sign survives
out-of-sample net of costs. All magnitudes are rough.

| ID | (a) Signal at the bar close | (b) Control | (c) Expected sign and size | (d) Data | (e) How it fails | (f) Prior |
|---|---|---|---|---|---|---|
| **H1** Dip in uptrend (Connors/Alvarez) | close > SMA(200) and RSI(2) < 5; exit at the open after the first close > SMA(5), or after 7 bars | Random entries in the same stocks' uptrend days, matched on date, liquidity bucket and ATR% | Positive; +20 to +40 bp per trade gross over 3-5 bars, 0 to +25 bp net | Daily OHLCV | Edge already near zero after 2018 (S5: 0.33% at a far more extreme threshold); negative in 2020 and 2022 (S6); bad ticks create false dips; costs | 0.30 |
| **H2** Dip edge scales with stress | H1 signal split by VIX tercile at *t* (VIX from FRED / `CBOE:VIX`) | Same control within each tercile | Signal-minus-control larger in the top VIX tercile (P33) | Daily OHLCV + VIX | S6 reports negative returns in the two most recent bear phases: the sign may have flipped; top tercile is where gaps and delistings cluster | 0.30 |
| **H3** New 52-week high on volume (Darvas / O'Neil pivot) | Trend template true; close > highest high of 252 bars as of *t*-1; volume >= 1.5 x SMA(volume, 50). Pre-registered variants: Darvas box break; pocket pivot | Trend-template stocks on the same date within 15% of their high that did not break out | Positive; +0.3% to +1.0% over 20 bars vs control | Daily OHLCV | Previous session found no entry beating random entries in the same uptrends; breakouts are bought at worse prices next open (P41); P17 reversal | 0.20 |
| **H4** Contraction before the breakout (VCP) | H3 breakouts with 10-bar range < 0.5 x 30-bar range, 30-bar < 0.75 x 60-bar, SMA(vol,10)/SMA(vol,50) < 0.8 on *t*-1 | H3 breakouts without contraction | (i) Raw 20-bar return: no difference expected. (ii) Return in units of stop distance (entry to the low of the last 10 bars): higher by 0.2R or more | Daily OHLCV | Tighter stops are hit more often and by gaps; any "edge" may be only the arithmetic of a smaller denominator: report stop-out rate and R jointly | (i) 0.15, (ii) 0.35 |
| **H5** RS line leads price (blue dot) | Trend template true; close/SPY at a 252-bar high; stock's own high below its 252-bar high | Trend-template stocks, same date, RS line not at a high, matched on distance from the 52-week high | Positive; +0.3% to +0.8% excess over 20-60 bars | Daily OHLCV + SPY | It is momentum restated; adds nothing once 12-1 momentum and nearness to the high are matched | 0.20 |
| **H6** Trend state as a filter | For any long entry (H1, H3, H8): trend template true vs false; splits by MA distance and by ADR% tercile | The same entry rule outside the template | Better drawdown and lower loss frequency inside; mean return higher by 0.2-0.5% over 20 bars | Daily OHLCV | P3: momentum premium gone since the late 1990s; filter removes the deepest (most profitable) dips for H1, as Alvarez found the 200-day filter "does not add anything" to average profit (S5) | 0.45 for risk reduction, 0.25 for higher mean |
| **H7** Smooth momentum beats jumpy momentum | Among stocks in the top third of 12-1 return: information discreteness = sign(ret) x (% down days - % up days) over bars *t*-252..*t*-21, bottom tercile ("smooth") | Top tercile ("jumpy"), same momentum bucket | Smooth outperforms by 0.3-0.8% a month over 1-3 months (P6: 8.86% vs 2.91% over six months, long-short) | Daily OHLCV | Monthly-horizon effect, weak at 5-20 bars; long-only capture smaller; post-publication decay (P36) | 0.30 |
| **H8** Earnings gap on volume (episodic pivot, liquid names) | Earnings bar (calendar date; `request.earnings` in Pine); open >= 1.05 x prior close; volume >= 3 x SMA(50); close >= open and in the top half of the bar's range. Enter next open; stop at the gap bar's low; hold 20 bars. Pre-registered splits: prior 126-bar return above/below zero; close above/below the earnings-anchored VWAP on later bars | (i) Same-size gap-ups on non-earnings days (P25: should reverse); (ii) earnings days without a gap | Positive vs both controls; +0.5% to +1.5% over 20 bars | Daily OHLCV + earnings dates with before/after-market flag (2020-2026 in the project's data) | P51: mechanical gap buying lost in 2016-2023; P20: drift gone in large stocks; the first day's move is not capturable; date alignment of after-close reports | 0.20 |
| **H9** Failed breakdown (Turtle Soup / sweep / spring) | close > SMA(200); low < lowest low of the prior 20 bars; that prior low at least 4 bars old; close back above it | Uptrend days with a new 20-bar low that closed below it; and H1 signals not meeting H9 | Positive; +10 to +30 bp over 5 bars vs control | Daily OHLCV | S14: t = 0.94 on SPY; it may be H1 under another name: test incremental effect with RSI(2) matched | 0.20 |
| **H10** Parabolic extension as a "no new longs" state | close/close[10] - 1 >= 0.5, three or more up closes in a row, close > 1.3 x SMA(20); or top decile of MAX(21) | Top-third 12-1 momentum stocks not in this state, same date | Negative relative return, -1% to -3% over 20 bars; larger left tail | Daily OHLCV | Rare in a $20M+, $5+ universe; the mean may be flat with only higher crash probability (P32); squeezes continue | 0.40 as an avoidance filter |
| **H11** Stops help trend trades and hurt dip trades | Same entries as H3 and H1, with and without a resting stop at entry - 2 x ATR(14) (trend) or - 3 x ATR(14) (dip) | The no-stop version of the same trades | H3: Sharpe and max drawdown improve, mean little changed. H1: mean per trade falls | Daily OHLCV with gap-through fills | Daily bars cannot order intrabar stop and target; gap-throughs erase the stop's benefit (P50: 8% of trades) | 0.50 for the joint sign pattern |
| **H12** Cost of waiting for the open | For H1 and H3 signals: return from the close of *t* to the open of *t*+1 as a share of the gross 5-bar edge measured from the close of *t* | Unconditional overnight return of matched stocks | 20-40% of the 5-bar edge is earned before the next open (S9: 31 bp to 22 bp on SPY; P41 for momentum) | Daily OHLC; vendor "open" vs auction print caveat in the data inventory | Vendor opens differ from the auction print; effect may be small in single stocks | 0.60 that at least 20% is lost for H1; 0.40 for H3 |

Families for the trial registry: {H1, H2, H9} reversal; {H3, H4, H5} breakout entry; {H6, H7, H10}
trend state; {H8} event; {H11, H12} execution.
