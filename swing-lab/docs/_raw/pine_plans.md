# TradingView plan limits for a Premium swing trader: history depth, intraday, screeners, alerts, exports, data feeds

Research date: **2026-11-11** by the machine clock (UTC, all pages fetched between 20:40 and 21:10 UTC). The task brief gives the date as 2026-11-10; every "accessed" date below is 2026-11-11.
Scope: what the **Premium** plan gives, against the adjacent plans, for a US-stock swing trader who reads 1h, 4h, daily and weekly charts and depends on alerts.

## 0. How to read this file

| Tag | Meaning |
|---|---|
| [DOC] | Read today in a primary TradingView source. The "Type" column or the source ID says which kind: pricing page data, Help Center article, TradingView blog, Pine manual / reference, **shipped front-end code** (the JavaScript TradingView serves to browsers), or **measured** (numbers returned today by TradingView's own public services to a guest, no login). The last two are primary but are not documentation: they describe what the product did today, not what TradingView promises |
| [COMPILE] | Confirmed today with TradingView's compiler through `tools/pine_compile.py` (compile only, never runtime) |
| [SECONDARY] | Third-party page |
| [MEMORY] | Recalled from training, **not verified today**; do not rely on it |

"Inference" marks a conclusion I drew from a quoted source; it is not itself a sourced fact.
Plan order in every table: **Basic / Essential / Plus / Premium / Expert / Ultimate**. Expert and Ultimate are the two "professional" plans. Plan ids inside the pricing data: `free` = Basic, `pro` = Essential, `pro_realtime` = Plus, `pro_premium` = Premium, `pro_expert` = Expert, `pro_premium_expert` = Ultimate [DOC] P1. That the name "PRO+" in the 2019 blog post B7 is today's Plus is [MEMORY].

### Sources (all accessed 2026-11-11)

| ID | Source | URL |
|---|---|---|
| P1 | Pricing page. Values taken from the page's embedded data object `compare_table` (the rendered plan cards list every feature on every plan and strike some through, so plain-text extraction of the cards is misleading) | https://www.tradingview.com/pricing/ |
| C1 | Market data coverage page | https://www.tradingview.com/data-coverage/ |
| H1 | Help: "Historical intraday data: bars and limits explained" | https://www.tradingview.com/support/solutions/43000480679-historical-intraday-data-bars-and-limits-explained/ |
| H2 | Help: "How much data is available for Bar Replay?" | https://www.tradingview.com/support/solutions/43000692816-how-much-data-is-available-for-bar-replay/ |
| H3 | Help: "What is Deep Backtesting?" | https://www.tradingview.com/support/solutions/43000666199-what-is-deep-backtesting/ |
| H4 | Help: "How Deep Backtesting works" | https://www.tradingview.com/support/solutions/43000666265-how-deep-backtesting-works/ |
| H5 | Help: "How much data is available for Deep Backtesting?" | https://www.tradingview.com/support/solutions/43000668210-how-much-data-is-available-for-deep-backtesting/ |
| H6 | Help: "Why do the data of the regular mode and Deep Backtesting not match?" | https://www.tradingview.com/support/solutions/43000666266-why-do-the-data-of-the-regular-mode-and-deep-backtesting-not-match/ |
| H7 | Help: "What is bar magnifier backtesting mode" | https://www.tradingview.com/support/solutions/43000669285-what-is-bar-magnifier-backtesting-mode/ |
| H8 | Help: "Custom chart intervals" | https://www.tradingview.com/support/solutions/43000543883-custom-chart-intervals-personalizing-your-analysis/ |
| H9 | Help: "What are second-based intervals" | https://www.tradingview.com/support/solutions/43000762068-what-are-second-based-intervals/ |
| H10 | Help: "How to export chart data" | https://www.tradingview.com/support/solutions/43000537255-how-to-export-chart-data/ |
| H11 | Help: "How to export strategy data" | https://www.tradingview.com/support/solutions/43000613680-how-to-export-strategy-data/ |
| H12 | Help: "Introduction to TradingView alerts" | https://www.tradingview.com/support/solutions/43000520149-introduction-to-tradingview-alerts/ |
| H13 | Help: "How to use price alerts" | https://www.tradingview.com/support/solutions/43000763313-how-to-use-price-alerts/ |
| H14 | Help: "Getting started with technical alerts" | https://www.tradingview.com/support/solutions/43000763315-getting-started-with-technical-alerts/ |
| H15 | Help: "Watchlist alerts: your trading edge" | https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts-your-trading-edge/ |
| H16 | Help: "Multi-condition alerts" | https://www.tradingview.com/support/solutions/43000761492-multi-condition-alerts/ |
| H17 | Help: "Learn how to configure alerts" | https://www.tradingview.com/support/solutions/43000763312-learn-how-to-configure-alerts/ |
| H18 | Help: "Differences between alert frequencies" | https://www.tradingview.com/support/solutions/43000474415-differences-between-alert-frequencies/ |
| H19 | Help: "Alert was triggered too often and stopped" | https://www.tradingview.com/support/solutions/43000690939-alert-was-triggered-too-often-and-stopped/ |
| H20 | Help: "Alerts on alert() function" | https://www.tradingview.com/support/solutions/43000597494-alerts-on-alert-function/ |
| H21 | Help: "Strategy Alerts" | https://www.tradingview.com/support/solutions/43000481368-strategy-alerts/ |
| H22 | Help: "Issue with 'Once Per Bar' alert" | https://www.tradingview.com/support/solutions/43000741171-issue-with-once-per-bar-alert/ |
| H23 | Help: "Why is the Once Per Bar option missing?" | https://www.tradingview.com/support/solutions/43000690908-why-is-the-once-per-bar-option-missing/ |
| H24 | Help: "I upgraded to the Premium plan but my alerts still expiring in 2 months" | https://www.tradingview.com/support/solutions/43000688759-i-upgraded-to-the-premium-plan-but-my-alerts-still-expiring-in-2-months/ |
| H25 | Help: "How to get more active alerts per subscription" | https://www.tradingview.com/support/solutions/43000690941-how-to-get-more-active-alerts-per-subscription/ |
| H26 | Help: "Alerts separation by type" | https://www.tradingview.com/support/solutions/43000696403-alerts-separation-by-type/ |
| H27 | Help: "Alerts based on real-time and non-real-time symbols" | https://www.tradingview.com/support/solutions/43000698958-alerts-based-on-real-time-and-non-real-time-symbols/ |
| H28 | Help: "How to configure webhook alerts" | https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/ |
| H29 | Help: "Alert name and message size limits" | https://www.tradingview.com/support/solutions/43000773947-alert-name-and-message-size-limits/ |
| H30 | Help: "Automatic deletion of old alert triggers from the Log" | https://www.tradingview.com/support/solutions/43000766116-automatic-deletion-of-old-alert-triggers-from-the-log/ |
| H31 | Help: "Stopping alerts when downgrading your plan" | https://www.tradingview.com/support/solutions/43000766059-stopping-alerts-when-downgrading-your-plan/ |
| H32 | Help: "Limited functionality state in Watchlist Alerts" | https://www.tradingview.com/support/solutions/43000739521-limited-functionality-state-in-watchlist-alerts/ |
| H33 | Help: "Notification schedule for alerts" | https://www.tradingview.com/support/solutions/43000787196-notification-schedule-for-alerts/ |
| H34 | Help: "Alerts on Earnings & Revenue" | https://www.tradingview.com/support/solutions/43000796730-alerts-on-earnings-revenue/ |
| H35 | Help: "Alerts on fundamentals" | https://www.tradingview.com/support/solutions/43000786831-alerts-on-fundamentals/ |
| H36 | Help: "Alert presets" | https://www.tradingview.com/support/solutions/43000774194-alert-presets/ |
| H37 | Help: "What timezone is displayed in alerts?" | https://www.tradingview.com/support/solutions/43000691967-what-timezone-is-displayed-in-alerts/ |
| H38 | Help: "TradingView Pine Screener: key features and requirements" | https://www.tradingview.com/support/solutions/43000742436-tradingview-pine-screener-key-features-and-requirements/ |
| H39 | Help: "TradingView screeners walkthrough" | https://www.tradingview.com/support/solutions/43000718885-tradingview-screeners-walkthrough/ |
| H40 | Help: "TradingView Stock Screener: trade smarter, not harder" | https://www.tradingview.com/support/solutions/43000718866-tradingview-stock-screener-trade-smarter-not-harder/ |
| H41 | Help: "How do I change the timeframe in the screener?" | https://www.tradingview.com/support/solutions/43000723616-how-do-i-change-the-timeframe-in-the-screener/ |
| H42 | Help: "How to scan watchlist or flagged list?" | https://www.tradingview.com/support/solutions/43000724549-how-to-scan-watchlist-or-flagged-list/ |
| H43 | Help: "How to export screener data" | https://www.tradingview.com/support/solutions/43000474432-how-to-export-screener-data/ |
| H44 | Help: "How to purchase additional market data" | https://www.tradingview.com/support/solutions/43000471705-how-to-purchase-additional-market-data/ |
| H45 | Help: "Is US stock market data free by default?" | https://www.tradingview.com/support/solutions/43000473924-is-us-stock-market-data-free-by-default/ |
| H46 | Help: "Why do the values on the TradingView intraday charts differ from other sources?" | https://www.tradingview.com/support/solutions/43000710585-why-do-the-values-on-the-tradingview-intraday-charts-differ-from-other-sources/ |
| H47 | Help: "I want to access Extended Hours data" | https://www.tradingview.com/support/solutions/43000502023-i-want-to-access-extended-hours-data/ |
| H48 | Help: "How to adjust data for dividends" | https://www.tradingview.com/support/solutions/43000590597-how-to-adjust-data-for-dividends/ |
| H49 | Help: "I see 'Calculation takes too long to execute' error" | https://www.tradingview.com/support/solutions/43000579793-i-see-calculation-takes-too-long-to-execute-error/ |
| H50 | Help: "How many symbols can I add to the watchlist?" | https://www.tradingview.com/support/solutions/43000611193-how-many-symbols-can-i-add-to-the-watchlist/ |
| H51 | Help: "How do I set an alert at a preset time?" | https://www.tradingview.com/support/solutions/43000698959-how-do-i-set-an-alert-at-a-preset-time/ |
| B1 | Blog, 2025-01-23: "Watchlist alerts: one alert to track them all" | https://www.tradingview.com/blog/en/watchlist-alerts-on-tradingview-49839/ |
| B2 | Blog, 2026-07-02: "Extended hours support for watchlist alerts is here" | https://www.tradingview.com/blog/en/extended-hours-support-59226/ |
| B3 | Blog, 2026-09-01: "Pine Screener: scan any index, pick any script" | https://www.tradingview.com/blog/en/pine-screener-update-60542/ |
| B4 | Blog, 2026-10-23: "Pine Screener now supports up to 40 request calls per script" | https://www.tradingview.com/blog/en/pine-screener-40-request-calls-61952/ |
| B5 | Blog, 2025-10-23: "Introducing multi-condition alerts" | https://www.tradingview.com/blog/en/multi-condition-alerts-54525/ |
| B6 | Blog, 2024-08-27: Stock Screener "Recent and Upcoming earnings dates" | https://www.tradingview.com/blog/en/earnings-dates-in-stock-screener-46267/ |
| B7 | Blog, 2019-09-25: "You can now export & download data into a CSV file" | https://www.tradingview.com/blog/en/export-chart-data-in-csv-14395/ |
| D1 | Pine manual, "Alerts" | https://www.tradingview.com/pine-script-docs/concepts/alerts/ |
| D2 | Pine FAQ, "Alerts" | https://www.tradingview.com/pine-script-docs/faq/alerts/ |
| D3 | Pine manual, "Limitations" | https://www.tradingview.com/pine-script-docs/writing/limitations/ |
| D4 | Pine manual, "Time" | https://www.tradingview.com/pine-script-docs/concepts/time/ |
| D5 | Pine manual, "Other timeframes and data" | https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ |
| D6 | Pine FAQ, "Other data and timeframes" | https://www.tradingview.com/pine-script-docs/faq/other-data-and-timeframes/ |
| D7 | Pine FAQ, "Indicators" | https://www.tradingview.com/pine-script-docs/faq/indicators/ |
| D8 | Pine manual, "Strategies" | https://www.tradingview.com/pine-script-docs/concepts/strategies/ |
| D9 | Pine FAQ, "Strategies" | https://www.tradingview.com/pine-script-docs/faq/strategies/ |
| D10 | Pine "Release notes" | https://www.tradingview.com/pine-script-docs/release-notes/ |
| D11 | Pine Reference Manual v6, rendered with Playwright: `request.security`, `ticker.new`, `ticker.modify`, `alert`, `alertcondition`, `syminfo.volumetype`, `session.ismarket` | https://www.tradingview.com/pine-script-reference/v6/ |
| X1 | TradingView screener backend, field list for the US market (3,786 fields; the service the Stock Screener page calls; not a documented API) | https://scanner.tradingview.com/america/metainfo |
| X2 | Shipped front-end code: chart export dialog; chunk index; watchlist-alert paywall and limit pop-up | https://static.tradingview.com/static/bundles/chart-export-dialog.3e6c2adf33f61d367018.js ; `runtime.263e0b9da5ccc5d05984.js` ; `paywall-watchlist-alerts.5994856965bfda91e4ef.js` ; `show-overall-watchlist-alerts-limit-popup.51f089f96462fdb1a15b.js` (same host and folder) |
| X3 | Measured: TradingView's public chart data socket, **guest session, no login**, the feed an anonymous visitor's chart uses. Probe scripts: `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/pine_plans_scripts/ws_probe.py`, `ws_volratio.py`, `ws_volratio_hist.py` | wss://data.tradingview.com/socket.io/websocket |
| X4 | TradingView symbol page of a delisted stock (embedded symbol data) | https://www.tradingview.com/symbols/NYSE-TWTR/ |
| Y1 | Yahoo Finance daily bars through `yfinance`, used only as an outside reference for consolidated daily volume and official close | (library call, no URL) |
| S1 | PineConnector blog on watchlist alerts, marked "Reviewed 23 September 2026" | https://www.pineconnector.com/blogs/pico-blog/how-to-use-watchlist-alerts-in-tradingview-for-smarter-trading-1 |
| S2 | PickMyTrade docs on watchlist alerts, modified 2026-09-29 | https://docs.pickmytrade.trade/docs/watchlist-alerts-on-tradingview/ |
| T | Compile tests for this report (5 compiler calls of the 15 allowed) | `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/pine_plans/pine/` |

---

## 1. The findings that change design decisions

| # | Finding | Tag |
|---|---|---|
| 1 | Premium: **20,000 bars** per intraday chart; daily and higher charts show all history. On a regular-session US stock that is about 11 years of 1h bars and more than the stored intraday history for 4h bars | [DOC] P1, H1, D3 ; arithmetic in section 3 |
| 2 | A 4h chart of a US stock in the regular session has **two bars a day, 09:30-13:30 and 13:30-16:00** (4 h and 2.5 h). With extended hours it has four: 04:00, 08:00, 12:00, 16:00, and the 08:00 bar mixes pre-market with the first 2.5 hours of the regular session | [DOC] X3 measured ; rule in D4 |
| 3 | Alert quotas on Premium: **400 price + 400 technical + 2 watchlist** alerts. All `alert()` calls of one script instance on one symbol cost one technical alert; each `alertcondition()` alert costs one | [DOC] P1, H26, D2 |
| 4 | **Watchlist alerts exist** (one alert, one condition, every symbol of a watchlist, up to 1,000 symbols) but Premium has only **2**, and they **cannot be open-ended** | [DOC] P1, H15, H17, H50 |
| 5 | "Open-ended" alerts are still switched off automatically after **one year without a trigger or an edit** | [DOC] H12, H24 |
| 6 | An alert runs on TradingView's servers on a **snapshot** of the script, inputs, symbol and timeframe; editing the script or its inputs does not change a running alert. Alerts fire only on realtime bars. More than 15 triggers in 3 minutes stops the alert | [DOC] D1, D2, H19 |
| 7 | The **Pine Screener** (Premium and above) runs one indicator over a watchlist or an index and filters on its plots and `alertcondition()`s, but calculates on **only the last 500 bars**, supports only the timeframes 1, 5, 15, 30, 60, 120, 240, 1D, 1W, 1M (no 65 or 195), ignores `input.timeframe()` / `input.symbol()` choices, is scan-on-demand, and no source says it can raise alerts | [DOC] H38, B3, B4, P1 |
| 8 | The regular Stock Screener cannot use Pine values. It has built-in relative volume, average volume, performance over many horizons, gap, ATR/ADR, 52-week high/low, pre/post-market, and recent/upcoming earnings date | [DOC] D2, X1, B6 |
| 9 | Chart CSV export needs **Plus or higher**. It exports every loaded bar (scroll back first) with time, the main series and every plot of every visible indicator. Plots shown only in the Data Window are exported; plots set to `display.none` and indicators hidden with the eye icon are not. Time is ISO or UNIX, user's choice | [DOC] P1, H10, D7, X2 |
| 10 | Without paid exchange data, US stock charts use **Cboe One**. Measured today: **settled daily bars carry consolidated volume** (equal to Yahoo's within 0.06% on AAPL and JPM), while **intraday bars carry only about 4-12% of it** (AAPL, quarterly medians 2016-2026), with level shifts in 2020 and 2023 | [DOC] H44, H45, C1 ; X3 measured |
| 11 | Measured today: from 2 to 9 minutes after the 16:00 close the realtime daily bar on the Cboe One feed showed AAPL volume 23.4M and close 355.79; Yahoo showed 31.4M and 355.63. The settled daily bars of earlier days equal Yahoo's figures. A daily bar-close alert therefore sees a lower volume and a slightly different close than the backtest will later show for the same bar | [DOC] X3 measured, Y1 |
| 12 | Deep Backtesting (Premium and above): all stored history, up to 2,000,000 bars and 1,000,000 trades, results only in the Strategy Report. Bar Magnifier (Premium and above) refines fills with lower-timeframe bars | [DOC] P1, H4, H5, H7 |
| 13 | Custom minute intervals such as 65 and 195 are available on charts from Essential upward and compile as `request.security` timeframes, but they are refused for guests, so their bar alignment could not be measured today | [DOC] P1 ; [COMPILE] T t1 ; X3 |
| 14 | Delisted US stocks can remain chartable with daily and intraday history (TWTR: daily to 2022-10-27, hourly bars served), flagged `discontinued`; not every delisted name resolves (NASDAQ:SIVB did not) | [DOC] X3 measured, X4 |

---

## 2. Plan matrix (pricing page data, P1)

All rows [DOC] P1. Y = included, N = not included. Bold column = Premium.

| Section on the page | Row title (verbatim) | Basic | Essential | Plus | **Premium** | Expert | Ultimate |
|---|---|---|---|---|---|---|---|
| Charts | Charts per tab | 1 | 2 | 4 | **8** | 10 | 16 |
| Charts | Saved chart layouts | 1 | 5 | 10 | **∞** | ∞ | ∞ |
| Charts | Custom intervals: minutes, hours, days, weeks, months | N | Y | Y | **Y** | Y | Y |
| Charts | Predefined second intervals | N | N | Y | **Y** | Y | Y |
| Charts | Custom second intervals | N | N | N | **N** | N | Y |
| Charts | Tick-based intervals | N | N | N | **N** | Y | Y |
| Charts | Spread charts | N | N | Y | **Y** | Y | Y |
| Charts | Data export | N | N | Y | **Y** | Y | Y |
| Charts | Dividend-adjusted charts | Y | Y | Y | **Y** | Y | Y |
| Charts | Extended trading hours | Y | Y | Y | **Y** | Y | Y |
| Charts | Parallel chart connections | 2 | 10 | 20 | **50** | 80 | 200 |
| Bar replay | Historical data by day and higher timeframes | All | All | All | **All** | All | All |
| Bar replay | Historical data by the minute | N | 180 days | 365 days | **All** | All | All |
| Bar replay | Historical data by the second | N | N | N | **All** | All | All |
| Technical analysis | Indicators per chart | 2 | 5 | 10 | **25** | 30 | 50 |
| Technical analysis | Indicators on indicators | 1 | 1 | 9 | **24** | 29 | 49 |
| Technical analysis | Financials per chart | 1 | 4 | 7 | **10** | 15 | 25 |
| Technical analysis | Time limit for making calculations | 20 sec | 40 sec | 40 sec | **40 sec** | 60 sec | 100 sec |
| Strategy backtesting | Export trades in CSV | N | Y | Y | **Y** | Y | Y |
| Strategy backtesting | Export report in XLSX | N | Y | Y | **Y** | Y | Y |
| Strategy backtesting | Deep backtesting | N | N | N | **Y** | Y | Y |
| Strategy backtesting | High detalization of historical bars (the Bar Magnifier; the row links to H7) | N | N | N | **Y** | Y | Y |
| Strategy backtesting | Each history tick execution | N | N | N | **Y** | Y | Y |
| Watchlists | Number of watchlists | 1 | ∞ | ∞ | **∞** | ∞ | ∞ |
| Watchlists | Symbols per watchlist | 30 | 1000 | 1000 | **1000** | 1000 | 1000 |
| Watchlists | Import and export | N | Y | Y | **Y** | Y | Y |
| Alerts | Active price alerts | 3 | 20 | 100 | **400** | 600 | 1000 |
| Alerts | Active technical alerts | N | 20 | 100 | **400** | 600 | 1000 |
| Alerts | Active watchlist alerts | N | N | N | **2** | 10 | 15 |
| Alerts | Alert duration | 1 month | 2 months | 2 months | **∞** | ∞ | ∞ |
| Alerts | Webhook notifications | N | Y | Y | **Y** | Y | Y |
| Alerts | Multi-condition alerts | N | N | Y | **Y** | Y | Y |
| Alerts | Alerts on financial metrics | N | Y | Y | **Y** | Y | Y |
| Alerts | Second-based alerts | N | N | Y | **Y** | Y | Y |
| Screeners | Watchlists as filters | N | Y | Y | **Y** | Y | Y |
| Screeners | Auto-refresh | N | 10 sec / 1 min | 10 sec / 1 min | **10 sec / 1 min** | 10 sec / 1 min | 10 sec / 1 min |
| Screeners | Data export | N | Y | Y | **Y** | Y | Y |
| Screeners | Timeframes | D W M | All | All | **All** | All | All |
| Screeners | Pine Screener | N | N | N | **Y** | Y | Y |
| Screeners | Active filters | 2 | ∞ | ∞ | **∞** | ∞ | ∞ |
| Data | Maximum market data subscriptions allowed | N | 2 | 4 | **6** | 12 | ∞ |
| Data | Historical bars available | 5K | 10K | 10K | **20K** | 25K | 40K |

Hint texts on the same page that matter: Alert duration: "Regular alerts expire in two months. But this feature keeps your alerts running as long as you need." Active watchlist alerts: "Apply the same alert conditions to hundreds of symbols in a single click." Pine Screener: "Apply an indicator to all the symbols in your watchlist and see detailed indicator readings for each symbol that meets your set parameters." Deep backtesting: "Unlock all the symbol's price history to get a fuller view of the asset's performance." Maximum market data subscriptions: "Every user on TradingView benefits from real-time US stock, worldwide forex, and crypto data. You can add real-time data to your plan from many other exchanges around the world. Exchanges charge per-user fees for real-time subscriptions, so these are purchased separately." [DOC] P1

Where the pricing page is ambiguous or silent: section 12.

---

## 3. History depth

### 3.1 Bars per chart and per request

| Statement | Exact wording | Tag |
|---|---|---|
| Intraday bars per chart by plan | "The length of historical data for any intraday interval (i.e. chart timeframe) is 5000 bars/candles (for Essential and Plus account holders it is doubled to 10000 bars and for Premium holders it's quadrupled to 20000) + additionally several bars back to the beginning of the week, month or year (depending on the selected chart timeframe). While Professional plans offer more historical intraday data: Expert plans have access to 25000 bars, and Ultimate plans can have the maximum number of historical intraday bars, which is 40000." | [DOC] H1 |
| The cap cannot be raised | "Unfortunately, these limits cannot be extended for now due to technical reasons." | [DOC] H1 |
| Daily and higher: no cap | "If you change the chart interval to daily or daily-based, you will see a longer date range. We display all available data for daily-based intervals." | [DOC] H1 |
| Same numbers in the Pine manual | "When the required historical date is available, the minimum number of chart bars is: 40000 historical bars for the Ultimate plan. 25000 historical bars for the Expert plan. 20000 historical bars for the Premium plan. 10000 historical bars for Essential and Plus plans. 5000 historical bars for other plans." | [DOC] D3 |
| Bars per `request.security()` call | `calc_bars_count`: "Determines the maximum number of recent historical bars that the function can request. ... The default is the same as the number of chart bars available for the symbol and timeframe. The maximum number of bars that the function can attempt to retrieve depends on the intrabar limit of the user's plan. However, the request cannot retrieve more bars than are available in the dataset." | [DOC] D11 |
| Intrabar (lower-timeframe) limit | "Scripts can retrieve up to the most recent 200,000 intrabars (lower-timeframe bars) via the request.security() or request.security_lower_tf() functions, depending on the user's plan: All non-professional plans – Basic, Essential, Plus, and Premium – can request up to 100K bars of data. Expert plans have access to 125K bars of data. Ultimate plans can request 200K lower-timeframe bars." | [DOC] D3 |
| How deep stored intraday history goes | "if you play NASDAQ:AAPL on a daily interval, the daily history starts from December 12, 1980, while 1-minute AAPL data starts from January 3, 2000, and the earliest 1-second bar in Replay dates from August 17, 2022." and "For some symbols, we have 1-minute data as far back as 2011, for some, back to 2009, while for others, the data can extend even further, back to 2000." | [DOC] H2 |
| Guest session, measured | A request for 5,200 regular-session 4h bars of NASDAQ:AAPL returned 5,200 bars, first bar 2016-06-30 09:30 ET. A request for 2,400 1h bars returned 2,400 bars, first bar 2025-07-01. (A guest is not a Premium account; this shows only that the data exist to those dates and the bar counts per day.) | [DOC] X3 measured |

Reading of the `request.security` row: by default a request to another symbol or timeframe gets as many bars as a chart of that symbol and timeframe would (20,000 intraday on Premium, everything on daily and above). Whether an explicit `calc_bars_count` above 20,000 really returns more than 20,000 same-or-higher-timeframe bars on Premium is not stated; **not verified**.

### 3.2 How many years 20,000 bars are (US stock)

Bars per day come from the measured alignment in 3.3; 252 sessions a year; half-days ignored. This is arithmetic on [DOC] numbers, not a TradingView statement.

| Chart | Session | Bars per day | Bars per year | Years in 20,000 bars | What actually limits it |
|---|---|---|---|---|---|
| 1h (`"60"`) | regular | 7 | 1,764 | 11.3 | the 20K cap |
| 1h | extended | 16 | 4,032 | 5.0 | the 20K cap |
| 65 min | regular | 6 | 1,512 | 13.2 | the 20K cap |
| 4h (`"240"`) | regular | 2 | 504 | 39.7 | stored intraday history (AAPL: from 2000-01-03, about 13,500 bars) |
| 4h | extended | 4 | 1,008 | 19.8 | the cap or stored history, whichever is shorter |
| 195 min | regular | 2 | 504 | 39.7 | stored intraday history |
| 1D | - | 1 | 252 | no cap | listing history (AAPL from 1980-12-12) |
| 1W | - | - | 52 | no cap | listing history |

The 65- and 195-minute rows assume the documented session-start rule (3.3); their alignment was not measured.

### 3.3 Bar alignment for US stocks

| Statement | Evidence | Tag |
|---|---|---|
| Intraday bars start at the session open; the last bar is cut at the session close | "the chart aligns bars with session opening and closing times. A session's final bar closes when the session ends, and a new bar opens when a new session starts. A typical session on our 60-minute chart with regular trading hours (RTH) spans from 09:30 to 16:00 (6.5 hours). The chart divides this interval into as many 60-minute bars as possible, starting from the session's opening time, which leaves only 30 minutes for the final bar to cover." | [DOC] D4 |
| 1h, regular session: 7 bars, opening 09:30, 10:30, 11:30, 12:30, 13:30, 14:30, 15:30 ET; the last is 30 minutes | NASDAQ:AAPL, 2026-11-11, seven bars with exactly these open times | [DOC] X3 measured |
| **4h, regular session: 2 bars, opening 09:30 and 13:30 ET** (4 h, then 2.5 h) | NASDAQ:AAPL, 30 bars 2026-10-22 to 2026-11-11, every day exactly 09:30 and 13:30 | [DOC] X3 measured |
| 4h, extended session: 4 bars, opening 04:00, 08:00, 12:00, 16:00 ET | NASDAQ:AAPL, 12 bars 2026-11-06 to 2026-11-11 | [DOC] X3 measured |
| Session definitions the feed reports for NASDAQ:AAPL | regular "0930-1600"; premarket "0400-0930"; postmarket "1600-2000"; a "24h" subsession "2000-2000" also exists; half-days are listed as corrections "0930-1300" on dated days (for example 20261127, 20261224) | [DOC] X3 measured |
| 65 min regular: 09:30, 10:35, 11:40, 12:45, 13:50, 14:55 (six equal bars). 195 min regular: 09:30 and 12:45 (two equal bars) | Inference from the D4 rule. The guest data socket answers `custom_resolution` errors for 65 and 195, in line with P1 (custom intervals start at Essential) | Inference ; refusal [DOC] X3 measured |
| Weekly bars | Not examined today | - |

Consequences: on the regular session a "4h close" exists only at 13:30 and 16:00 ET, the two 4h bars are unequal, and the second one closes together with the daily bar. With extended hours switched on, the same script sees different 4h bars (and 16 hourly bars), so indicator values and alert times change with the session setting.

---

## 4. Deep Backtesting and Bar Magnifier

| Item | Value | Exact wording | Tag |
|---|---|---|---|
| Deep Backtesting: plan | Premium, Expert, Ultimate | P1 row "Deep backtesting"; "This feature is available for Premium and higher plan users." | [DOC] P1, H4 |
| What it is | Strategy Report mode over all stored history with a chosen date range | "an additional mode of operation of the Strategy Report, which makes it possible to calculate the strategy on all historical data available for the selected symbol, and not only on those loaded on the chart." | [DOC] H3 |
| Limits | 2,000,000 bars, 1,000,000 trades | "The limit of available historical data is up to two million bars and one million trades." ; "the maximum length of historical data per calculation is 2 million bars. If the period used for a backtest covers more than 2 million bars, the strategy will execute on the most recent 2 million bars within the selected period." | [DOC] H4, H5 |
| Order limit | 9,000 normally, 1,000,000 in Deep Backtesting | "A script can place a maximum of 9000 orders when backtesting strategies. ... When using Deep Backtesting, the order limit is 1,000,000." | [DOC] D3 |
| Where results appear | Strategy Report only | "Deep Backtesting results are only shown in the Strategy Report tab and are not displayed on the chart." | [DOC] H4 |
| Data used | Same stores as charts; intraday shorter than daily | "On daily and daily-based timeframes, charts display all available data, and the Deep Backtesting mode uses this same data. On intraday timeframes, TradingView keeps a limited amount of data." | [DOC] H5 |
| Results differ from the chart run | Different first bar, so EMA/RMA-type values differ | "in Deep Backtesting, script calculations will start at the beginning of the date range, whereas regular backtesting calculations always begin on the chart's first bar." | [DOC] H6 |
| Indicators | Deep Backtesting is a Strategy Report mode; nothing found that applies it to indicators | absence in H3-H6 | [DOC] (absence) |
| Bar Magnifier: plan | Premium, Expert, Ultimate | P1 row "High detalization of historical bars": "Enhance historical data quality using lower-timeframe intrabar price movements to improve the accuracy of price behavior." | [DOC] P1 |
| What it does | Order fills use lower-timeframe bars | "This tool uses intrabar inspection to give you a more granular view of price movement within a bar for more precise order fills." Enabled with `use_bar_magnifier = true` or in the strategy's Properties | [DOC] H7 ; [COMPILE] T t2 |
| Intrabar timeframe used | 60 → 10 ; 240 → 30 ; 1D → 60 ; 3D → 240 ; 1W → 1D | H7 table: "Chart timeframe (includes timeframes between it and the next one)": 1 → 10S, 5 → 30S, 10 → 1, 15 → 2, 30 → 5, 60 → 10, 240 → 30, 1D → 60, 3D → 240, 1W → 1D | [DOC] H7 |
| Limit | 200,000 lower-timeframe bars | "The strategy can't request more than 200,000 bars from the lower timeframe." ; affected range roughly "last_bar_index - (200000 / Num of Lower Timeframe Bars per Chart Bar)" | [DOC] H7 |
| "Each history tick execution" | Premium and above; no article found | P1 hint: "Add extra strategy recalculations using data from every tick. Together with historical bars detalization, you get the best backtest quality." | [DOC] P1 |

Bar Magnifier reach on our timeframes (arithmetic on H7): daily chart, 7 hourly intrabars per bar, 28,500 daily bars covered (everything); 4h chart, 30-minute intrabars, 8 and 5 per bar; 1h chart, 10-minute intrabars, 6 per bar, 33,000 chart bars covered (more than the 20K on the chart).

---

## 5. Chart capacity, intervals, delisted symbols

| Item | Premium | Wording / evidence | Tag |
|---|---|---|---|
| Indicators per chart | 25 | P1 | [DOC] |
| Charts per tab (layout) | 8 | P1 | [DOC] |
| Saved layouts | unlimited | P1 | [DOC] |
| Parallel chart connections | 50 | "Each tab in the web version and apps is counted as one connection. ... Once the limit is reached, the oldest connection (the earliest opened tab) will get closed." | [DOC] P1 ; https://www.tradingview.com/support/solutions/43000694474-parallel-chart-connections/ |
| Script calculation time | 40 s | "20 seconds (for Basic plan) 40 seconds (for Essential, Plus and Premium plans) 100 seconds (for Ultimate plan)" ; P1 adds Expert 60 sec | [DOC] H49, P1 |
| Custom minute/hour intervals (65, 195, 2.5 h) | yes | "you can set your custom time interval by clicking on the '+ Add custom interval…' button ... Another way you can set your custom interval is by simply typing numbers, which will represent minutes." Example given: "instead of a 2-hour interval, you can set the interval to 2.5-hour interval." | [DOC] H8, P1 |
| `"65"` and `"195"` as Pine timeframe strings | compile | `request.security(tid, "195", close[1], lookahead = barmerge.lookahead_on)`, `timeframe.in_seconds("195")` | [COMPILE] T t1 |
| Seconds charts | predefined only | "Standard second-based intervals (1, 5, 10, 15, 30, and 45 seconds) are available starting from the Plus plan. Custom second-based intervals from 1 to 299 seconds are available on the Ultimate plan" | [DOC] H9 |
| Seconds data depth | from August 2022 | "For all seconds-based intervals, TradingView stores the data starting from August 2022" | [DOC] H2 |
| Bar Replay depth | all stored data | "Our Premium and professional plans (Expert and Ultimate) ... allow you to play absolutely all time-based data available in TradingView's data storage." | [DOC] H2 |
| Delisted stock, daily history | available for TWTR | Symbol data: `typespecs: ["common","discontinued"]`, `has_intraday: true`, first daily bar 2013-11-07, last daily bar 2022-10-27 (volume 140,831,508). Daily bars served on the data socket | [DOC] X4, X3 measured |
| Delisted stock, intraday history | available for TWTR | Ten 1h bars served, last 2022-10-27 15:30 ET | [DOC] X3 measured |
| Not every delisted stock resolves | NASDAQ:SIVB → "invalid symbol" | One probe; the stock may exist under another prefix or ticker, not checked | [DOC] X3 measured |

No Help Center article about delisted symbols was found today; coverage of delisted names is therefore unknown beyond these two probes.

---

## 6. Alerts

### 6.1 Quotas and types

| Statement | Exact wording | Tag |
|---|---|---|
| Three separately counted types | "all alerts are divided into 3 types: Price and Technicals and Watchlist ... Each type has a separate limit on the number of active alerts ... You can run no more than 400 price alerts and no more than 400 technical + 2 watchlist ones (in this case, you can run 802 alerts in total)." | [DOC] H26 |
| Premium totals | "Premium Plan: 800 active alerts (400 price alerts + 400 technical alerts). Ultimate Plan: 2000 active alerts (1000 price alerts + 1000 technical alerts)." | [DOC] H25, P1 |
| What is a price alert | "only a symbol is used in the alert (for any type of chart: Bars, Renko, PnF, etc) and a price value" with Crossing, Crossing Up, Crossing Down, Greater Than or Less Than | [DOC] H26 |
| What is a technical alert | "the alert uses an overlay symbol, indicator, drawing or strategy", or a Channel/Moving operator, or "the alert with multiple conditions" | [DOC] H26 |
| A script alert on `alert()` calls counts once | "all calls to the alert() function count as one alert, regardless of the number of calls in the code." ; "Each active alert condition counts toward the total number of alerts the user's plan allows." | [DOC] D2 |
| A cheaper substitute for line alerts | "You can often save your technical alert quota by using price alerts instead. For example, rather than setting an alert directly on a trendline drawing, place a simple Crossing price alert at that level" | [DOC] H13 |
| Downgrade | "When you switch to a lower-tier plan, all active alerts will be automatically stopped." | [DOC] H31 |
| Alert presets | "You can save up to 5 alert presets." Webhook URLs, value fields and drawings are not saved in presets | [DOC] H36 |

### 6.2 Expiration

| Statement | Exact wording | Tag |
|---|---|---|
| Default lifetime | "Alerts have an expiration period, after which they will automatically stop. The maximum lifetime of a standard alert is two months. However, for Premium and Ultimate plans, an open-ended option is available, allowing the alert to remain active indefinitely." | [DOC] H12 |
| Pricing page | Alert duration: 1 month / 2 months / 2 months / ∞ / ∞ / ∞ | [DOC] P1 |
| Open-ended is a per-alert choice, not automatic | "1. Open the Create/Edit alert window; 2. Click on Expiration section's button; 3. Click on the Open-ended option in appeared pop-up; 4. Save your alert." | [DOC] H24 |
| **Inactivity switch-off, also for open-ended alerts** | "Alerts are automatically deactivated if all of the following conditions are met: The alert was created more than one year ago. The alert hasn't triggered for over a year. The alert hasn't been edited for over a year." | [DOC] H12, H24 |
| **Watchlist alerts cannot be open-ended** | "Expiration: Choose the date when the alert will expire, or toggle the 'Open-ended alert' option. Please note that the 'Open-ended alert' feature is not available for alerts on watchlists." | [DOC] H17 |
| Longest expiry date a watchlist alert accepts on Premium | Not stated anywhere I read. If the standard maximum applies it is two months; **not verified** | - |

### 6.3 How alerts are evaluated (server side)

| Statement | Exact wording | Tag |
|---|---|---|
| Server side, round the clock | "TradingView alerts run 24x7 on our servers and do not require users to be logged in to execute." | [DOC] D1 |
| Snapshot of script, inputs, symbol, timeframe | "When an alert is created in the charts UI, TradingView saves a mirror image of the script and its inputs, along with the chart's main symbol and timeframe to run the alert on its servers. Subsequent changes to your script's inputs or the chart will thus not affect running alerts previously created from them. If you want any changes to your context to be reflected in a running alert's behavior, you will need to delete the alert and create a new one in the new context." | [DOC] D1 |
| Same, from the FAQ | "that action saves a 'snapshot' of the script, its inputs, and the current chart's context on TradingView's servers. ... To update an alert after making changes, delete the existing alert and create a new one." | [DOC] D2 |
| Realtime bars only | "Alerts only trigger in the realtime bar. The operational scope of Pine Script code dealing with any type of alert is therefore restricted to realtime bars only." | [DOC] D1 |
| The interval matters for script alerts, and can differ from the chart's | "Alerts for data series are independent of time intervals, but for other types, the interval does matter, as it directly affects indicator calculations." ; alert dialog, Condition field: "You can also choose an operator, input values for the alert, and set a different interval from your chart" | [DOC] H12, H17 |
| A script runtime error stops the alert | "If a script instance raises a runtime error at some point during its executions, alerts from that instance cannot fire because the error stops the script from continuing to execute its code." | [DOC] D2 |
| No ticks, no execution | "because Pine scripts execute on realtime bars only after new price updates, and an alert only fires when a script executes, it is difficult to predict the exact time of a delayed alert. There are no price updates in a closed market" | [DOC] D2 |
| Realtime and historical bars use different feeds | "A chart's realtime and historical bars often rely on different data feeds. Data providers may retroactively adjust the reported values on realtime bars, which the displayed data reflects after users refresh their charts or restart their scripts." | [DOC] D2 |
| Which feed an alert on a US stock uses | "In case you see the red icon on the chart, this means the data is provided by Cboe. ... The prefix of the exchange is only displayed in the alerts manager section." Inference: an alert is created on one feed's symbol (the manager shows its exchange prefix), so without exchange subscriptions it runs on Cboe One data. What happens to existing alerts when a subscription is added later was not read today | [DOC] H27 ; inference |
| How many historical bars the server-side copy loads before it starts | Not stated; **not verified** | - |
| Exact moment a "once per bar close" alert on a daily US-stock bar fires (at 16:00 ET, or later) | Not stated; **not verified**. See 10.3 for what the daily bar contains at 16:00 | - |

### 6.4 `alert()` and `alertcondition()`

| Property | `alert()` | `alertcondition()` | Tag |
|---|---|---|---|
| Script types | indicators and strategies; allowed in library functions | indicators only: "While the presence of alertcondition() calls in a strategy script will not cause a compilation error, alerts cannot be created from them." | [DOC] D1, D2 ; strategy with `alertcondition()` compiles with 0 errors, 0 warnings [COMPILE] T t5 |
| Scope | local scopes allowed | global scope only; compiler: `CE10188 Cannot use "alertcondition" in local scope` | [DOC] D11 ; [COMPILE] T t3 |
| Entry in the "Condition" list | one entry, "Any alert() function call", for all calls | one entry per call | [DOC] D2 |
| Frequency set by | the script: `alert.freq_once_per_bar` (default), `alert.freq_once_per_bar_close`, `alert.freq_all` | the user, in the dialog | [DOC] D1, D11 ; constants compile [COMPILE] T t1 |
| Frequency wording | "alert.freq_once_per_bar_close: An alert is only triggered when the realtime bar closes and an alert() call is executed during that script iteration." | "The frequency of alertcondition() alerts is determined by users in the 'Create Alert' dialog box." | [DOC] D1 |
| A wrong frequency string | `alert("x", "once_per_week")` compiles without error or warning, so a typo is not caught by the compiler; use the constants | - | [COMPILE] T t4 |
| Message | "series string", built at run time; placeholders are not processed | "const string"; dynamic values only through placeholders: `{{ticker}}`, `{{exchange}}`, `{{interval}}`, `{{open}}`, `{{high}}`, `{{low}}`, `{{close}}`, `{{volume}}`, `{{time}}`, `{{timenow}}`, `{{plot_0}}` to `{{plot_19}}`, `{{plot("title")}}` | [DOC] D1, D2 |
| Placeholder limits | - | "Plots are numbered from zero to 19 in order of appearance in the script, so only one of the first 20 plots can be used." `{{time}}` is "UTC, formatted as yyyy-MM-ddTHH:mm:ssZ". For delayed symbols `{{exchange}}` "will end with '_DL' or '_DLY.'" | [DOC] D1 |
| Plot count | not counted | "an alertcondition call generates an additional plot" | [DOC] D11 |
| Strategies | by default strategies run at bar close, so "all alert() calls will use the alert.freq_once_per_bar_close frequency, regardless of the argument used for freq" unless `calc_on_every_tick = true` | no effect | [DOC] D1 |
| Dialog frequencies | controlled by the script, not by the dialog | "Once only", "Once per bar", "Once per bar close", "Once per minute" | [DOC] H20, H18, H23 |

Dialog frequency definitions: "Once per bar — the system checks every bar and triggers an alert whenever conditions are met (no more than once per bar). Once per bar close — same as above, but the bar needs to close for an alert to be triggered." [DOC] H18. Plain price alerts offer only "Only Once and Every Time" [DOC] H23.

Repainting through the alert frequency: "Alerts on indicators with a frequency different from Once Per Bar Close (which are Once, Once Per Minute, and Once Per Bar) can trigger during the bar building. ... the time of execution of the triggering condition on the chart does not always coincide with the time of the actual alert triggering." [DOC] H22. The manual's rule: "The simplest way to avoid this type of repainting is to configure the triggering frequency of alerts so they only trigger on the close of the realtime bar." [DOC] D1

### 6.5 Throttling and other limits

| Limit | Value | Exact wording | Tag |
|---|---|---|---|
| Trigger rate, any alert | 15 in 3 minutes, then stopped | "For regular alerts: no more than 15 triggers in 3 minutes." ; "if a script alert triggers more than 15 times within a three-minute window, it will automatically stop." | [DOC] H19, H20, D2 |
| Trigger rate, watchlist alert | 15 per symbol and 1,000 in total per 3 minutes | "the overall limit is no more than 1000 triggers in 3 minutes for the entire watchlist alert. the limit for each watchlist symbol is no more than 15 triggers in 3 minutes ... If the total number of symbol triggers within 3 minutes reaches the limit (1000), the entire watchlist alert is stopped, along with all symbols within it." | [DOC] H19 |
| Alert name | 300 characters | "300 characters is the maximum length of an alert name." | [DOC] H29 |
| Message typed in the dialog | 4,000 characters | "4000 characters is the maximum length of the message specified in the 'Message' field of the alert creation dialog." | [DOC] H29 |
| `alert()` message / `alert_message` | 40,960 characters | "40960 characters is the maximum length of the message specified in PineScript's alert() function or in the 'alert_message' argument. The same limits apply to the request body size as to the alert message size." | [DOC] H29 |
| Alert log | 30 days, last 100 triggers per alert | "Cleanup runs every day at 21:00 UTC. Alert triggers are deleted if ... The trigger is older than 30 days ... There are more than 100 trigger events for the same alert (only the most recent 100 are kept)" | [DOC] H30 |
| Alert log export | CSV, UTC | "In the alerts log section, you can export alerts log data to a CSV file. The time in a CSV file is displayed in the UTC timezone" | [DOC] H37 |
| Notification schedule | delivery only | "The schedule only controls notification delivery, not alert triggering. If an alert triggers outside your scheduled hours, the event is still recorded and will appear in your alert log." Default "24/7 (Always Active)" | [DOC] H33 |
| Timer alerts | none | "As of now, a timer alert feature is not available on the platform." (work-around: alert on a vertical line) | [DOC] H51 |

### 6.6 Webhooks

| Statement | Exact wording | Tag |
|---|---|---|
| Plan | Essential and above (P1 row "Webhook notifications") | [DOC] P1 |
| Needs two-factor authentication | "For your data protection, webhook alerts are only allowed when 2-factor authentication is enabled." | [DOC] H28 |
| Request | "we will send a POST request as soon as the alert is triggered, with the alert message in the body of the request. If the alert message is valid JSON, the request will include an 'application/json' content-type header. Otherwise, the request will use 'text/plain'" | [DOC] H28 |
| Network limits | "only ports 80 and 443 are accepted ... If a remote server takes longer than three seconds to process a request, the request will be cancelled. Also, IPv6 isn't currently supported for webhooks." | [DOC] H28 |
| Source addresses | 52.89.214.238, 34.212.75.30, 54.218.53.128, 52.32.178.7 | [DOC] H28 |
| Reliability | "webhooks may occasionally fail to reach the specified URL. You can monitor their delivery by checking the 'Webhook status' column in the alert log." | [DOC] H28 |

### 6.7 Watchlist alerts

| Statement | Exact wording / evidence | Tag |
|---|---|---|
| They exist today | "Watchlist alerts create a single alert for an entire watchlist, using the same condition for each symbol. Each alert operates independently for every symbol in the list." | [DOC] H12 |
| Plan and count | "Set up to 2 active watchlist alerts with our Premium subscription and more with our plans for professionals: up to 10 with the Expert plan and up to 15 — with Ultimate." (2025-01-23). P1 today: N / N / N / 2 / 10 / 15 | [DOC] B1, P1 |
| Counted apart from the 400 technical alerts | "no more than 400 technical + 2 watchlist ones" | [DOC] H26 |
| Symbols per alert | Bounded by the watchlist size: "Watchlist can contain no more than 1000 symbols." No smaller alert-specific cap found | [DOC] H50 |
| The list is followed dynamically | "The alert will still trigger if you add a new symbol to the watchlist after creating the alert. Conversely, if you remove a symbol from the watchlist, the alert will no longer apply to it." | [DOC] H15 |
| When it stops | "The overall alert will stop only when it has been triggered for all symbols in the list; until then, it remains active." | [DOC] H15 |
| Session setting | "You can change the session setting to make the alert calculate outside regular trading hours. Select Extended to include pre- and post-market hours for US stocks and ETFs, or 24 hours to also include the overnight session for stocks with overnight trading data." | [DOC] H15 |
| Extended hours only on intraday | "Extended monitoring applies to intraday intervals (minutes, hours). Daily alerts are calculated using standard daily bars" | [DOC] B2 |
| Operators | "This feature allows you to use the same operators available for other types of alerts" | [DOC] H15 |
| Not open-ended | see 6.2 | [DOC] H17 |
| No multi-condition | "They can't be used for watchlist alerts or in Pine scripts or strategies that include alert() functions." | [DOC] B5 |
| Partial failure state | "an alert may enter a limited functionality state due to various factors like activated fire-control or a Pine script calculation error. This means it's still active, but calculations may be halted for certain symbols." (The mention of a "Pine script calculation error" implies script conditions are possible; that is an inference) | [DOC] H32 |
| A cap on stored watchlist alerts, active plus inactive | Interface text: "You've reached the overall limit of {count} watchlist alerts. This includes both, active and inactive alerts. Please remove unnecessary alerts in order to add any new ones." The number comes from the account and is not published | [DOC] X2 shipped code |
| **Can the condition be a custom Pine indicator (`alertcondition()` / `alert()`)?** | No official page I read says yes or no. Official wording stops at "Define your technical condition (e.g., Price Moving Up)" (B2). Third parties say yes: the condition can be "a condition from a Pine Script indicator" (S1, which also states that it did not test this on an account) and "Use the alertcondition() function to create alerts based on your script" (S2) | [SECONDARY] S1, S2 ; **not verified** |
| Which timeframes a watchlist alert accepts | S2 lists "5 minutes, 1 hour, 4 hours, 1 day, etc."; no official list found | [SECONDARY] S2 ; **not verified** |

### 6.8 Other alert types worth knowing

| Type | Fact | Tag |
|---|---|---|
| Multi-condition alerts | Plus and above; "combine up to five different conditions — including price, drawings, and indicators ... The alert will only trigger when all conditions are met simultaneously." "multi-condition alerts count as just one technical alert". "You can mix conditions with different timeframes ... with the frequency based on the smallest timeframe used." "All conditions must use the same symbol. Multi-condition alerts don't support strategies and scripts with alert() function." | [DOC] H16 |
| Earnings and revenue alerts | "exclusively available for stock instruments"; conditions "New report", "Beats estimates", "Misses estimates", "Greater / Less than"; set from the Earnings icon under the chart. Plan requirement not stated in the article | [DOC] H34 |
| Alerts on fundamentals | 11 valuation metrics (market cap, P/E, PEG, P/B, P/S, dividend yield and others); Essential and above | [DOC] H35, P1 |
| Strategy alerts | "When an alert is created for a strategy, a copy of the strategy is created on our servers." "Alerts are only triggered for orders executed in realtime." | [DOC] H21 |
| Indicator setting changes | "If an indicator's parameters are changed after an alert is created, the alert will still trigger using the old settings." | [DOC] H14 |

---

## 7. Pine Screener

| Question | Answer | Exact wording | Tag |
|---|---|---|---|
| What it is | A screener that runs one Pine indicator over a list of symbols | "allows you to scan your custom watchlists and indices using Pine Script® ... you can filter, compare, and discover trading opportunities using your own custom indicators, built-in technicals, or community scripts." | [DOC] H38 |
| Plan | Premium, Expert, Ultimate | P1 row "Pine Screener" | [DOC] P1 |
| Where | "From the TradingView home page, go to Products → Screeners → Pine." | | [DOC] H38 |
| Symbol sources | One watchlist (including colour-flagged lists) or one index | "You can scan only one source at a time." ; "Watchlists and indices are mutually exclusive, and multi-select isn't supported yet." | [DOC] H38, B3 |
| Maximum symbols | Watchlist: 1,000 (the watchlist cap). Index: 4,000 per the Help Center and the Pine release notes, 3,500 per the blog | "Indices are supported as a source up to a maximum of 4,000 symbols." ; "scan up to 4,000 of its symbols" ; "including large universes of up to 3,500 symbols" | [DOC] H50, H38, D10, B3 |
| Mixed asset types | Allowed | "it can scan a full watchlist containing a mix of stocks, crypto symbols, bonds, and other assets simultaneously." | [DOC] H38 |
| Scripts | Indicators only, one per screen | "You can use only one indicator per screen." ; "It also does not support profiles, strategies, or patterns." Since August 2026 any script from the Indicators dialog (personal, invite-only, purchased, built-in, community), no longer only favourites | [DOC] H38, B3, D10 |
| Outputs it can use | Plots and alert conditions | "the indicator must output at least one supported plot (e.g., plot(), plotbar(), plotcandle(), plotchar(), plotshape(), plotarrow(), or hline()) or an alertcondition()." | [DOC] H38 |
| What is loaded by default | 10 plots, 2 alert conditions | "The first ten plots are added for subsequent filter configuration. These plots are added to the table as columns. Two alert conditions from the script are added. Options to add additional filters or columns will appear." | [DOC] H38 |
| Filters | On plot values (condition plus target value) and on alert conditions | "As filters, you can use: Indicator plots, Indicator alert conditions" | [DOC] H38 |
| Table columns | Only the script's plots | "Only plots are available for display in the table." ; "You cannot add arbitrary external data" | [DOC] H38 |
| Timeframes | 1, 5, 15, 30 min; 1, 2, 4 h; 1D; 1W; 1M | "Custom timeframes are not supported. The supported timeframes include: minutes (1, 5, 15, 30), hours (1, 2, 4), 1 day, 1 week, and 1 month." | [DOC] H38 |
| **History** | **500 bars** | "The indicator calculates data based on only the last 500 bars on the chart." | [DOC] H38 |
| `request.*()` | Up to 40 calls, listed timeframes only | "The Pine Screener supports all `request.*()` functions, with the following limitations: No more than forty separate `request.*()` calls can be used inside of the scanned script. The requested timeframe must be in the list of the supported timeframes. Valid Pine string identifiers of these timeframes are: "1", "5", "15", "30", "60", "120", "240", "1D", "1W", and "1M"." Raised from 5 to 40 on 2026-10-23 | [DOC] H38, B4 |
| Inputs | Most work; three are ignored | "The following functions are not supported: input.timeframe(), input.symbol(), input.time(). If a script uses these functions, the Pine Screener ignores user-selected values and uses the default script values instead." | [DOC] H38 |
| Indicator on indicator | No | "The Indicator-on-Indicator feature is not supported." | [DOC] H38 |
| Old Pine versions | Alert conditions need v4 or later | "Using custom alert conditions is not compatible with scripts written in Pine version 3 or earlier." | [DOC] H38 |
| Refresh | On demand; a change needs a rescan; one scan at a time | "You will need to restart the scan if you modify any of the following parameters after a previous run: Source, Studies, Current study inputs, Study timeframe, Filter set" ; "if a scan is already running in one browser tab, another tab cannot execute a concurrent scan." The auto-refresh setting of the other screeners is documented "with the exception of the Pine Screener" | [DOC] H38, H39 |
| Compatibility shown in advance | Only for non-indicators and scripts without plots | "we only flag scripts whose incompatibility can be determined in advance ... Every other script is available for selection, though some may still fail to run." | [DOC] B3 |
| Drawings (lines, labels, tables) | Not used: columns come only from plots. Whether a script that also draws is rejected is not stated | absence in H38 | [DOC] (absence) |
| Can it trigger alerts | Nothing in H38, B3, B4, D10 or P1 says so; **not verified** either way | - | - |
| Does a scan use the forming bar or only closed bars | Not stated; **not verified** | - | - |

What 500 bars means (arithmetic): 1h regular session ≈ 71 sessions; 4h ≈ 250 sessions; 1D ≈ 2 years; 1W ≈ 9.6 years. A 200-day average on daily bars fits; anything that needs more than 500 bars of the scan timeframe does not, and recursive indicators (EMA, RSI, ATR) are seeded from only 500 bars, so screener values can differ from chart values computed on 20,000 bars.

Documentation that lags the product: the Pine FAQ still says "There is no automated method to set the same alert across many symbols simultaneously in a single action. It's also important to note that the TradingView screener uses built-in filters and does not support custom Pine Script® code." [DOC] D2. Watchlist alerts (H15) and the Pine Screener (H38) contradict the first half and qualify the second.

---

## 8. Regular Stock Screener

| Question | Answer | Evidence | Tag |
|---|---|---|---|
| Custom Pine values as columns or filters | No | "the TradingView screener uses built-in filters and does not support custom Pine Script® code" ; the 3,786 fields of the US field list are all built-in names | [DOC] D2, X1 |
| Field count | Hundreds | "500+ fundamental and technical fields" on the pricing page; the backend lists 1,131 distinct field names for the US market, 3,786 counting timeframe variants | [DOC] P1, X1 |
| Timeframes of technical fields | 1, 5, 15, 30, 60, 120, 240 min, 1D, 1W, 1M | Suffixes present in the field list: 1, 5, 15, 30, 60, 120, 240, 1W, 1M, plus the unsuffixed daily. No 65 or 195. "Screeners do not have a standard timeframe responsible for all columns ... by default, inactive filters in the top bar have a timeframe of 1 day." Basic plan: D W M only | [DOC] X1, H41, P1 |
| Scan a watchlist | Yes, Essential and above | "To scan a specific watchlist or a flagged list, click the Watchlist filter in the header." | [DOC] H42, P1 |
| Auto-refresh | Yes, Essential and above | "every 10 seconds, every 1 minute, or never" | [DOC] H39, P1 |
| Export | CSV, Essential and above | "Export screen results: Download your filtered data as a CSV file." | [DOC] H39, H43, P1 |
| Filter groups | 8 groups | Security info, Market data, Technicals, Financials, Dividends, Valuation, Growth, Margins and ratios | [DOC] H40 |
| Column sets | 12 sets | Overview, Performance, Technicals, Extended hours, Forecasts, Valuation, Dividends, Profitability, Income statement, Balance sheet, Cash flow, Per share | [DOC] H40 |

Built-in fields that matter for swing trading, by backend name ([DOC] X1; these are names in the field list, not Help Center definitions):

| Need | Field names |
|---|---|
| Relative volume | `relative_volume`, `relative_volume_10d_calc` (also with `\|5 … \|240, \|1W, \|1M`), `relative_volume_intraday\|5` |
| Liquidity | `volume`, `average_volume_10d_calc`, `_30d_`, `_60d_`, `_90d_`, `AvgValue.Traded_10d/30d/60d/90d`, `market_cap_basic`, `float_shares_outstanding`, `float_shares_percent_current` |
| Performance | `Perf.W`, `Perf.5D`, `Perf.1M`, `Perf.3M`, `Perf.6M`, `Perf.YTD`, `Perf.Y`, `Perf.3Y`, `Perf.5Y`, `Perf.10Y`, `Perf.All`; `change` and `change_from_open` (with intraday variants) |
| Earnings | `earnings_release_date`, `earnings_release_next_date`, `earnings_release_time`, `earnings_release_next_time`, `earnings_release_trading_date_fq`, `earnings_release_next_trading_date_fq`, `eps_surprise_fq`, `eps_surprise_percent_fq`, `earnings_per_share_forecast_next_fq` |
| Volatility | `ATR`, `ATRP`, `ADR`, `ADRP` (each with timeframe variants), `Volatility.D/W/M`, `beta_1_year`, `beta_3_year`, `beta_5_year` |
| Gaps and extended hours | `gap`, `gap_up`, `gap_down`, `premarket_change`, `premarket_gap`, `premarket_volume`, `postmarket_change`, `postmarket_volume` |
| Highs and lows | `price_52_week_high`, `price_52_week_low` (and dates), `High.5D`, `High.1M`, `High.3M`, `High.6M`, `High.All`, the `Low.*` counterparts |
| Trend and oscillators | `SMA…`/`EMA…` for 31 lengths from 2 to 300, `RSI`, `RSI7`, `MACD.*`, `ADX`, `Stoch.*`, `BB.*`, `KltChnl.*`, `DonchCh20.*`, `Ichimoku.*`, `VWAP`, `VWMA`, `HullMA*`, `Recommend.All/MA/Other`, 44 `Candle.*` patterns |
| Classification | `sector`, `industry`, `exchange`, `is_primary`, `indexes` |
| Dividends | `dividend_ex_date_recent`, `dividend_ex_date_upcoming`, `dividend_payment_date_upcoming` |
| Short interest | no field name containing "short interest", "short volume" or "days to cover" was found |

Earnings-date filter options: Recent earnings date "Current trading day / Previous day / Previous 5 days / This week / Previous week / This month"; Upcoming earnings date "Current trading day / Next day / Next 5 days / This week / Next week / This month". "If the upcoming earnings date is not available, we estimate it using our provider's algorithms based on the company's historical reporting dates." [DOC] B6

---

## 9. Exports

### 9.1 Chart data (CSV)

| Question | Answer and evidence | Tag |
|---|---|---|
| Plan | Plus, Premium, Expert, Ultimate (not Basic, not Essential). P1 row "Data export" in the Charts section; 2019 announcement: "This feature is available on PRO+ & Premium plans." | [DOC] P1, B7 |
| Where | "choose 'Download chart data…' from the dropdown menu on the upper toolbar. Next, select the chart and click 'Download'." | [DOC] H10 |
| What is in it | "You can save chart data, including tickers and indicators, into a CSV file." ; "exports a comma-separated values (CSV) file that includes time, OHLC data, and any plots generated by your script. This option can also export strategy data. To include specific information in the CSV file, ensure that it is plotted by the script." | [DOC] H10, D7 |
| How many bars | The bars loaded in the chart: "The data you export is what your chart shows you. If you need more data, scroll the chart left or drag the x-axis and then download a CSV." In the shipped code the rows run over the chart's whole loaded time-scale range, not just the visible window | [DOC] H10 ; X2 shipped code |
| Plots shown only in the Data Window | Exported; the plot title is the column header. "consider using the display parameter in the plot() function. Here is an example plot that displays the close only in the Data Window. The plot title 'No chart display' becomes the column header for this value in the CSV file. `plot(close * 0.5, "No chart display", display = display.data_window)`" | [DOC] D7 ; compiles [COMPILE] T t1 |
| Plots with display set to None | **Not exported**: the export loop skips a plot whose style `display` equals `StudyPlotDisplayTarget.None` | [DOC] X2 shipped code (my reading of minified code) |
| Indicators hidden with the eye icon | **Not exported**: default options `includedStudies:"all", includeHiddenStudies:false`; studies are filtered by `isVisible()` | [DOC] X2 shipped code |
| Boolean conditions | "use the plotshape() function, which records a 1 (for true) or 0 (for false) in the CSV file." | [DOC] D7 |
| Plot values offset beyond the last bar | Not exported by default (`includeOffsetStudyValues:false`) | [DOC] X2 shipped code |
| Main series columns | open, high, low, close for candle-type styles; only close (or the price source) for line-type styles; high and low for the High-low style | [DOC] X2 shipped code |
| Volume | The main-series columns in the code are prices only; volume appears as a column when an indicator on the chart plots it (the built-in Volume indicator, or a script) | [DOC] X2 shipped code (my reading) |
| Menu name | The Help Center calls the menu item "Download chart data…" (H10); the Pine FAQ calls it "Export chart data…" (D7) | [DOC] H10, D7 |
| Time format | A selector with two options, internal ids `time-format-iso` and `time-format-unix`; the choice is remembered. UNIX writes the bar time as a number in seconds. ISO writes `YYYY-MM-DD` on daily and higher charts, and `YYYY-MM-DDTHH:MM:SS` plus the UTC offset of the chart's time zone (`Z` when the offset is zero) on intraday charts. The visible labels of the two options were not retrieved | [DOC] X2 shipped code |
| File name | `<symbol>, <interval>.csv` | [DOC] X2 shipped code |
| Which chart of a layout | One chart, chosen in the dialog | [DOC] H10, X2 |

Not verified on a live account today: an actual exported file. The shipped-code rows are my reading of minified JavaScript and should be confirmed by exporting one small chart.

### 9.2 Strategy Tester

| Question | Answer | Exact wording | Tag |
|---|---|---|---|
| Plan | Essential and above | P1 rows "Export trades in CSV" and "Export report in XLSX" | [DOC] P1 |
| List of trades | CSV, all columns | "The adjacent 'Download' icon enables users to download all available data for the list as a CSV file. ... The downloaded CSV file for the list of trades contains data for all available columns, regardless of the display columns selected in the 'Column setup' menu." | [DOC] D8 |
| Whole report | XLSX | "Use the 'Download data as XLSX' option from the context menu in the strategy report to export all the available report data." | [DOC] D9 |
| Per tab | Separate files | "Information from each tab is exported separately: if you click on the 'Download' button from the 'List of Trades' tab, you will only export the trade information." | [DOC] H11 |
| Trade cap | Latest 9,000 trades unless Deep Backtesting | "If a strategy uses the default testing range, it preserves individual data for up to the latest 9000 trades. If the strategy uses a different testing range, enabling Deep Backtesting mode, it maintains individual trade data for all trades." ; trimmed trades "are not visible in the strategy report interface or any downloaded XLSX or CSV files." | [DOC] D8 |

### 9.3 Other exports

| Export | Fact | Tag |
|---|---|---|
| Screener results | CSV, Essential and above (8) | [DOC] H39, P1 |
| Alert log | CSV, times in UTC (6.5) | [DOC] H37 |
| Watchlist | "Download all symbols as a list in a TXT format." Essential and above | [DOC] P1 |
| Pine Screener results | No export statement found in H38; **not verified** | - |

---

## 10. Data feeds for US stocks

### 10.1 What the documentation says

| Statement | Exact wording | Tag |
|---|---|---|
| Default feed is Cboe | "By default, the U.S. stock market data is provided by Cboe Exchange. Thus it's slightly different from that of the primary exchanges. To get real-time data directly from NASDAQ, NYSE, or ARCA, you can add it to your plan." | [DOC] H44 |
| Why it differs | "by default, our charts display real-time US stock data from the Cboe exchange. It's an alternative exchange with high trading volume, actually over one fourth (25%+) of the US stock market. ... Sometimes it can be just a bit different, mainly because the trading volume is lower vs primary exchanges, and – as a result – it offers fewer price updates." ; "the most noticeable deviations usually on lower timeframes (i.e. 1 min), on non-active or unpopular tickers and during pre-/post-market sessions" | [DOC] H45 |
| Paid plans do not include exchange fees | "Most of the stock and futures exchanges we support charge fees for their real-time data. Currently, our paid plans don't cover those fees even if you have an active TradingView subscription." | [DOC] H44 |
| Coverage page | NASDAQ, NYSE, NYSE Arca: "Delayed data free: Limited real-time via Cboe One"; real-time fee $3.00 a month each; "US Stock Markets bundle … Includes: NYSE, NASDAQ, NYSE Arca, NASDAQ GIDS, OTC" $9.95 a month; "Cboe One — Cboe Global Markets (Arca, NYSE, NASDAQ)" real-time at $0.00; "Blue Ocean ATS — US stock markets (overnight quotes)" $9.00 | [DOC] C1 |
| Intraday and end-of-day are separate feeds | "Intraday historical data (for timeframes < 1D) ; End-of-day (EOD) historical data (for timeframes >= 1D) ; Realtime data (which may be delayed, depending on your account type and extra data services) ; Extended hours data" | [DOC] D5 |
| Volume differs between them | "For some instruments with intraday and EOD historical feeds, volume data may not be the same since some trades (block trades, OTC trades, etc.) may only be available at the end of the trading day. Consequently, the EOD feed will include this volume data, but the intraday feed will not. Differences between EOD and intraday volume feeds are almost nonexistent for instruments such as cryptocurrencies, but they are commonplace in stocks." | [DOC] D5 |
| Prices can differ too | "the high value on one EOD bar may not match any intraday high values supplied by the data provider for that day." | [DOC] D5 |
| Daily bars have no extended hours | "EOD feeds do not contain information from extended hours." | [DOC] D5 |
| Intraday history excludes odd lots | "our data provider filters the odd lots trades out in the history, and as a result, our intraday charts are built based on the full trades only." | [DOC] H46 |
| Pre-market late prints | Until October 2024 some 08:00 ET one-minute bars carried large OTC "late prints"; "Since October 2024, we have implemented a filtering feature for such trades ... However, such bars have been preserved in history" | [DOC] H46 |
| Extended hours on charts | "You can display the Extended Hours data on intraday charts either by choosing the ETH option in the bottom right corner or in the Symbol tab in the Settings menu." ; "not all exchanges have Extended Hours data" ; P1: available on every plan | [DOC] H47, P1 |
| Dividend adjustment | Off unless switched on: "To enable adjustment for dividends, go to the Supercharts settings and click the 'Adjust data for dividends' option." Available on every plan | [DOC] H48, P1 |
| Adjustment inside a script | `ticker.new` / `ticker.modify`, parameter `adjustment`: "Possible values: adjustment.none, adjustment.splits, adjustment.dividends. If adjustment is not given, then default adjustment value is used (can be different depending on particular instrument)." Session: "Possible values: session.regular, session.extended. ... If session is not given, then syminfo.session value is used." | [DOC] D11 ; all compile [COMPILE] T t1 |
| Split adjustment as the default for US stocks | The reference says only that the default "can be different depending on particular instrument". That US stock charts are split-adjusted by default is my recollection | [MEMORY] |
| History is revised | "Historical data may also be revised for other reasons, e.g., for stock splits." | [DOC] https://www.tradingview.com/pine-script-docs/concepts/repainting/ |
| `syminfo.volumetype` | "Only some data feed suppliers provide information qualifying volume. As a result, the variable will return a value on some symbols only, mostly in the crypto sector." It does not tell whether a stock's volume is consolidated | [DOC] D11 |

No TradingView page read today uses the word "consolidated" for daily volume. The measurements below fill that gap.

### 10.2 Measured today: daily volume is consolidated, intraday volume is not

Guest session on the public chart data socket (X3). The socket resolved NASDAQ:AAPL, NYSE:JPM and NYSE:TWTR with `exchange: "Cboe One"`, `source_id: "BATS"`, `listed_exchange` NASDAQ or NYSE, `provider_id: "ice"`. All rows [DOC] X3 measured; Yahoo figures Y1.

| Symbol, date | TradingView daily bar volume | Yahoo daily volume | Sum of the 7 regular-session 1h bars | Intraday / daily |
|---|---|---|---|---|
| AAPL 2026-11-09 | 48,753,052 | 48,753,100 | 3,038,359 | 0.062 |
| AAPL 2026-11-10 | 29,756,060 | 29,756,100 | 1,889,228 | 0.063 |
| JPM 2026-11-09 | 7,058,849 | 7,055,800 | 435,748 | 0.062 |
| JPM 2026-11-10 | 4,995,331 | 4,992,400 | 306,246 | 0.061 |
| TWTR 2022-10-26 (delisted) | 28,064,973 | not compared | 19,959,348 | 0.711 |

AAPL, ratio of summed regular-session 4h volume to daily volume, by quarter (5,200 4h bars against 2,700 daily bars):

| Period | Quarterly median of the daily ratio | Lowest and highest single day |
|---|---|---|
| 2016 Q3 - 2020 Q2 | 0.050 to 0.075 | 0.022 to 0.115 |
| 2020 Q3 - 2023 Q1 | 0.039 to 0.051 | 0.027 to 0.124 |
| 2023 Q2 - 2024 Q1 | 0.111 to 0.123 | 0.051 to 0.149 |
| 2024 Q2 - 2026 Q4 | 0.063 to 0.097 | 0.031 to 0.131 |

What this shows, and its limits:

- Settled daily bars carry consolidated volume even without any exchange subscription (two symbols, two days, equal to Yahoo within 0.06%; the AAPL closes equal Yahoo's too).
- Intraday bars on the Cboe One feed carry a small share of the day's volume. The share moves between about 2% and 15% from day to day and has two level shifts (2020 Q3 down, 2023 Q2 up). Absolute intraday volume thresholds, dollar-volume filters and long look-back intraday volume averages are therefore not comparable across those dates or with daily volume.
- The ratio assumes that TradingView split-adjusts intraday and daily volume in the same way (AAPL split 4:1 in August 2020). The 2020 shift does not sit on the split date in a way a one-sided adjustment would produce, but this was not examined further. The cause of either shift is unknown; that the 2023 step is the move of the free feed from one Cboe exchange to the four-exchange "Cboe One" product is a guess from memory [MEMORY].
- The delisted TWTR shows about 70-80% in October 2022, so the intraday volume basis is not the same for every symbol or period.
- These are guest-session numbers. H45 says the default chart feed is Cboe, so a Premium account without exchange subscriptions should see the same feed, but that was **not verified** in a logged-in session. What intraday volume looks like **with** the NASDAQ/NYSE/Arca subscriptions (primary-exchange volume or consolidated) is **not verified**.

### 10.3 Measured today: the daily bar at the close is not yet the final daily bar

| Reading (AAPL, 2026-11-11) | Volume | Close | Tag |
|---|---|---|---|
| TradingView realtime daily bar, read at 21:02, 21:03 and 21:09 UTC (2 to 9 minutes after the close), unchanged across the three reads | 23,392,425 | 355.79 | [DOC] X3 measured |
| TradingView last 1h bar (15:30 ET) at 21:02 UTC | 410,784 | 355.79 | [DOC] X3 measured |
| Yahoo at 21:02 UTC | 31,443,643 | 355.63 | Y1 |
| For comparison, 2026-11-10: TradingView settled daily bar | 29,756,060 | 348.51 | [DOC] X3 measured |
| 2026-11-10: TradingView last 1h bar | 285,022 | 348.55 | [DOC] X3 measured |
| 2026-11-10: Yahoo | 29,756,100 | 348.51 | Y1 |

Reading: at its close, the daily bar on the Cboe One feed showed a volume well below Yahoo's consolidated figure (74% of it today) and a close equal to the last trade on the intraday feed, not Yahoo's closing price. The settled bars of earlier days equal Yahoo's volume and close, so the bar is evidently replaced after the close by end-of-day data; the time at which that happens was not measured (not within 9 minutes). That the gap is the closing auction plus late-reported trades is my interpretation, in line with D5 ("block trades, OTC trades, etc. may only be available at the end of the trading day"). One day, one symbol. In practice this is a repaint of the daily bar's volume (large) and close (0.04% today) between alert time and history.

---

## 11. Compile log (5 of 15 calls used, all 2026-11-11)

Files in `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/pine_plans/pine/`.

| Test | What it contains | Result |
|---|---|---|
| t1_alerts_screener.pine | v6 indicator: `session.ismarket/ispremarket/ispostmarket`, `barstate.isconfirmed`, `timeframe.isdwm`, `timeframe.in_seconds("195")`, `timeframe.in_seconds("65")`, `syminfo.session`, `syminfo.volumetype`; `ticker.new(prefix, ticker, session.regular, adjustment.splits)`; `ticker.modify(tickerid, session.regular, adjustment.dividends)`; `ticker.modify(tickerid, session.extended)`; `request.security` on "1D", "195", "65", "240" with `[1]` + `lookahead_on` and `calc_bars_count = 5000`; plots with `display.data_window`, `display.none`, `display.status_line + display.data_window`; `plotshape`; two `alertcondition()` with `{{ticker}}`, `{{interval}}`, `{{plot_0}}`, `{{time}}`, `{{plot("RSI")}}`, `{{exchange}}`; `alert()` with `alert.freq_once_per_bar_close`, `alert.freq_once_per_bar`, `alert.freq_all` | 0 errors, 0 warnings |
| t2_strategy.pine | `//@strategy_alert_message`; `strategy(..., use_bar_magnifier = true, process_orders_on_close = false, calc_on_every_tick = false, fill_orders_on_standard_ohlc = true, calc_bars_count = 0)`; `alert_message` on entry, close and exit; `strategy.closedtrades.first_index` | 0 errors, 0 warnings |
| t3_negative.pine | `alertcondition()` inside an `if` block | `CE10188 Cannot use "alertcondition" in local scope` |
| t4_negative_freq.pine | `alert("x", "once_per_week")` | 0 errors, 0 warnings (the frequency string is not validated at compile time) |
| t5_negative_strategy_alertcondition.pine | `alertcondition()` in a strategy | 0 errors, 0 warnings (documented as having no effect) |

Compilation proves that the names and parameters exist. It does not prove runtime behaviour, bar alignment of "65"/"195", or what an alert does.

---

## 12. Where sources conflict, and where the pricing page is ambiguous

### 12.1 Conflicts (both sides shown)

| Topic | Side A | Side B |
|---|---|---|
| Pine Screener, index size | "up to a maximum of 4,000 symbols" (H38) ; "scan up to 4,000 of its symbols" (D10, August 2026) | "large universes of up to 3,500 symbols" (B3, 2026-09-01) |
| Alerts over many symbols, Pine in a screener | "There is no automated method to set the same alert across many symbols simultaneously in a single action. ... the TradingView screener uses built-in filters and does not support custom Pine Script® code." (D2) | Watchlist alerts (H15, B1) and the Pine Screener (H38) exist |
| Who gets open-ended alerts | "for Premium and Ultimate plans" (H12) ; "available for Premium and Ultimate plans only" (H24) | Pricing data: ∞ for Premium, Expert and Ultimate (P1) |
| Calculation time | 20 / 40 / 100 seconds, Expert not mentioned (H49) | Expert 60 sec (P1) |
| Lower-timeframe bars | Bar Magnifier: "can't request more than 200,000 bars from the lower timeframe" with no plan distinction (H7) | Intrabars through `request.*`: 100K on Premium, 125K Expert, 200K Ultimate (D3). They may be separate mechanisms; not resolved |
| Backtest cap | "maximum of 9000 orders" (D3) | "up to the latest 9000 trades" (D8) |
| Deep Backtesting cap | "two million bars and one million trades" (H4) | "the order limit is 1,000,000" (D3) |
| Maximum alert lifetime | "The maximum lifetime of a standard alert is two months." (H12) | Basic: 1 month (P1) |
| Chart export plan | Plan cards on the rendered pricing page list "Chart data export" under every plan (struck through where absent) | The page's data: Plus and above (P1), agreeing with B7 |
| Guest history depth | Basic plan "5K" bars (P1) | The guest data socket returned 5,200 4h bars in one request (X3). The socket is not a statement about plan caps |

### 12.2 Pricing page: ambiguous or silent

| Row | What it does not say | Where the answer is |
|---|---|---|
| "Historical bars available: 20K" | That the cap is for intraday intervals only and that daily-based charts show everything | H1 |
| "Historical data by the minute: All" | That this row belongs to the Bar replay section, not to charts | P1 section header, H2 |
| "Alert duration: ∞" | That open-ended is a per-alert setting, that alerts idle for a year are switched off, and that watchlist alerts cannot be open-ended | H24, H12, H17 |
| "Active watchlist alerts: 2" | Symbols per alert, which conditions are allowed, expiry, the cap on stored alerts | H15, H17, H50, X2 ; partly unknown |
| "Pine Screener: Y" | The 500-bar history, the timeframe list, the 40 requests, the symbol limits | H38 |
| "Deep backtesting: Y" | The 2,000,000-bar and 1,000,000-trade limits | H4, H5 |
| "Webhook notifications: Y" | That two-factor authentication is required | H28 |
| "Data export" | Appears twice with different thresholds: charts from Plus, screeners from Essential | P1 |
| "Extended trading hours: Y" | Which feed supplies the extended-hours prints | H45, H47 |
| Market-data hint "real-time US stock … data" | That this is Cboe One, not the primary exchanges | H44, H45, C1 |
| Earnings and revenue alerts | Not listed at all | H34 (no plan given) |

---

## 13. Not verified today

1. Whether a watchlist alert can use a custom Pine indicator's `alertcondition()` or `alert()` as its condition; only third-party pages say so (S1, S2), and S1 states it did not test it.
2. The longest expiry a watchlist alert accepts on Premium, the timeframes it accepts, and the size of the cap on stored (active plus inactive) watchlist alerts.
3. Whether the Pine Screener can raise alerts, export results, or evaluates the forming bar; no source addresses these.
4. How many historical bars the server-side copy of a script loads before an alert goes live, and whether that matches the 20,000 chart bars.
5. The exact moment a "once per bar close" alert on a daily US-stock chart fires, and when the end-of-day update replaces the realtime daily bar (10.3 shows only that it had not happened 9 minutes after the close).
6. Everything in 10.2 and 10.3 for a logged-in Premium account, and intraday volume with the paid NASDAQ/NYSE/Arca feeds.
7. Bar alignment of 65- and 195-minute charts (refused for guests; inferred from the documented rule).
8. Whether `calc_bars_count` above 20,000 returns more than 20,000 same-or-higher-timeframe bars in `request.security()` on Premium.
9. A real chart-data CSV: the export rules in 9.1 marked "shipped code" are my reading of minified JavaScript; the visible labels of the two time-format options were not retrieved.
10. Coverage of delisted US stocks beyond TWTR (served) and NASDAQ:SIVB (not resolved under that name); no Help Center article on delisted symbols was found.
11. That US stock charts are split-adjusted by default ([MEMORY]); the reference says only that the default adjustment depends on the instrument.
12. Plan requirement for earnings and revenue alerts.
13. Weekly bar boundaries, and how half-days (13:00 close) change the 4h bars; the feed lists the half-day sessions but no half-day was inspected.
14. Whether the old screener's alert feature has any equivalent in the current Stock Screener; nothing found, not searched exhaustively.

---

## 14. Design rules that follow directly from the verified facts

| Rule | Because |
|---|---|
| Fire signals only on confirmed bars: `alert.freq_once_per_bar_close` in `alert()`, "Once per bar close" for `alertcondition()` alerts | 6.4, H22, D1 |
| After any change to the script or its inputs, delete and recreate the alerts | 6.3 snapshot |
| Put every signal of a script behind `alert()` calls so that one technical alert per symbol and timeframe carries them all; keep `alertcondition()`s as well, because the Pine Screener and the dialog's "Condition" list need them | 6.1, 7 |
| Budget: 400 technical alerts and 2 watchlist alerts. One script that scans up to 40 symbols through `request.security()` and calls `alert()` costs one technical alert | 6.1, D2 |
| Do not build the workflow on watchlist alerts until item 1 of section 13 is tested on the account; even then they expire and there are only 2 | 6.2, 6.7 |
| Edit or re-save every open-ended alert at least once a year | 6.2 |
| Keep any single alert below 15 triggers per 3 minutes; a multi-symbol script should send one combined message per bar | 6.5 |
| On 1h and 4h charts never use absolute intraday volume or dollar-volume thresholds. Take liquidity and average volume from daily data (previous confirmed day), and treat intraday relative volume as feed-specific | 10.2 |
| Do not condition a daily bar-close alert on the current day's volume unless the threshold is calibrated on the realtime feed; the backtest sees a larger number for the same bar | 10.3 |
| Treat "4h" on the regular session as two unequal bars (09:30-13:30, 13:30-16:00). Decide the session (regular or extended) once and fix it in the script with `ticker.modify(..., session.regular)` where it matters | 3.3, 10.1 |
| A Pine Screener version of an indicator must work on 500 bars, on the listed timeframes, with default values for timeframe and symbol inputs, and expose its key numbers in the first ten plots | 7 |
| For parity checks against the research code, plot diagnostic series with `display = display.data_window` (not `display.none`), keep the indicator visible, scroll back to load the bars, and export with ISO time | 9.1 |
| Use Deep Backtesting only as a strategy-side check; its first bar differs from the chart's, so recursive values and trades can differ | 4 |
