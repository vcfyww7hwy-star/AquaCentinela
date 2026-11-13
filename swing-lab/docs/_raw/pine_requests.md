# Pine `request.*` family: other symbols, timeframes, fundamentals, earnings

Research date: **2026-11-10** (every URL below was accessed on this date). Pine version checked: **v6**.
Scope: what a Pine script can pull from outside its own chart, at bar close, without repainting, on a TradingView **Premium** plan.

## 0. How to read this file

| Tag | Meaning |
|---|---|
| [DOC] | Read today in an official TradingView source (Pine User Manual, Reference Manual, Help Center, TradingView's own published script, TradingView's own symbol directory/symbol pages) |
| [COMPILE] | Confirmed today with TradingView's compiler through `tools/pine_compile.py` (compile only, never runtime) |
| [SECONDARY] | Third-party page |
| [MEMORY] | Recalled from training, **not verified today**; do not rely on it |

"Inference" marks a conclusion I drew from a quoted source; it is not itself a sourced fact.

### Sources (all accessed 2026-11-10)

| ID | Source | URL |
|---|---|---|
| S1 | Pine User Manual, "Other timeframes and data" | https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ |
| S2 | Pine User Manual, "Limitations" | https://www.tradingview.com/pine-script-docs/writing/limitations/ |
| S3 | Pine Reference Manual v6 (rendered with Playwright; entries such as `#fun_request.security`, `#var_earnings.future_time`) | https://www.tradingview.com/pine-script-reference/v6/ |
| S4 | Pine FAQ, "Other data and timeframes" | https://www.tradingview.com/pine-script-docs/faq/other-data-and-timeframes/ |
| S5 | Pine User Manual, "Repainting" | https://www.tradingview.com/pine-script-docs/concepts/repainting/ |
| S6 | Pine User Manual, "Chart information" | https://www.tradingview.com/pine-script-docs/concepts/chart-information/ |
| S7 | Pine "Release notes" | https://www.tradingview.com/pine-script-docs/release-notes/ |
| S8 | Pine migration guide "To Pine Script version 6" | https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/ |
| S9 | Pine User Manual, "Timeframes" | https://www.tradingview.com/pine-script-docs/concepts/timeframes/ |
| S10 | Help Center, "What financial data is available in Pine?" | https://www.tradingview.com/support/solutions/43000564727-what-financial-data-is-available-in-pine/ |
| S11 | Help Center, "Earnings" | https://www.tradingview.com/support/solutions/43000629790-earnings/ |
| S12 | Help Center, "Earnings report date" | https://www.tradingview.com/support/solutions/43000761837/ |
| S13 | Help Center, "Why does Financial Data differ from other sources?" | https://www.tradingview.com/support/solutions/43000540145/ |
| S14 | Help Center, "Spread charts explained" | https://www.tradingview.com/support/solutions/43000502298/ |
| S15 | Pine Seeds documentation README (GitHub, TradingView-maintained) | https://github.com/tradingview-pine-seeds/docs |
| S16 | Script "FINRA Daily Short Sale Volume", author TradingView, v2 dated 2026-04-15 (description + open source) | https://www.tradingview.com/script/4KIgeLGo-FINRA-Daily-Short-Sale-Volume/ |
| S17 | TradingView symbol directory (the site's own symbol-search service) | https://symbol-search.tradingview.com/symbol_search/v3/?text=SYMBOL&exchange=PREFIX |
| S18 | TradingView symbol pages (embedded symbol metadata: `has_intraday`, `first_bar_time_1d`, `daily_bar.time`) | https://www.tradingview.com/symbols/PREFIX-SYMBOL/ |
| S19 | TradingView pricing page | https://www.tradingview.com/pricing/ |
| S20 | Compile tests written for this report (13 compiler calls of the 15 allowed) | `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/pine_requests/pine/` |

## 1. The findings that change design decisions

| # | Finding | Tag |
|---|---|---|
| 1 | **Premium gets 40 unique `request.*()` calls per script**, the same as every plan below Ultimate (64). | [DOC] S2 |
| 2 | The only officially recommended non-repainting higher-timeframe form is **`expression[1]` together with `lookahead = barmerge.lookahead_on`**. | [DOC] S1, S4 |
| 3 | **`request.financial()` is not aligned to publication.** Quote: "you get a new value on the bar where the next fiscal period begins". Inference: that bar comes weeks before the company reports, so a backtest that reads the series on historical bars sees unpublished numbers. | [DOC] S10, S1 for the quote; the leak is inference, not tested on a chart |
| 4 | `request.earnings()` / `request.dividends()` do align to the publication bar ("the new value is returned on the bar where the report was published"). | [DOC] S10 |
| 5 | `earnings.future_time`, `earnings.future_eps`, `earnings.future_revenue`, `earnings.future_period_end_time` exist, but each is "only fetched once during the script's initial calculation" and does not refresh until the script recalculates. | [DOC] S3, [COMPILE] |
| 6 | There is **no short-interest data** in Pine: no built-in, no `request.*` function, no `financial_id`. FINRA daily **short-sale volume** is available as `FINRA:<TICKER>_SHORT_VOLUME`. | [DOC] S1, S3, S10, S16; [COMPILE] |
| 7 | `syminfo.sector`, `.industry`, `.shares_outstanding_float`, `.shares_outstanding_total`, `.employees` are `simple` values: one current snapshot, no history. | [DOC] S6, [COMPILE] |
| 8 | Barchart-sourced breadth symbols (`INDEX:S5FI`, `INDEX:S5TH`, `INDEX:MMFI`, `INDEX:HIGN`…) are **end-of-day only** (`has_intraday = false`); the ICE-sourced `USI:*` internals (`USI:ADD`, `USI:TICK`, `USI:PCC`…) have intraday data. | [DOC] S18 |
| 9 | Pine Seeds (`request.seed`) cannot be used for our own data: new repositories are suspended. | [DOC] S1, S3, S15 |
| 10 | The compile tool (`translate_light`) **does not catch every request-related error** the docs describe as compilation errors (two documented error cases compiled cleanly). Request logic needs a real chart run. | [COMPILE] S20 vs [DOC] S1 |

## 2. The `request.*` namespace today

Complete list per the Reference Manual v6 (11 functions). [DOC] S3. Unknown names are rejected by the compiler: `request.short_interest`, `request.short_volume`, `request.options`, `request.news`, `request.calendar`, `request.screener`, `request.fundamental`, `request.security_higher_tf` all return "Could not find function or function reference". [COMPILE] `t5_neg.pine`, `t9_neg2.pine`

| Function | Signature (S1/S3) | Returns | Status | Compiled |
|---|---|---|---|---|
| `request.security` | `(symbol, timeframe, expression, gaps, lookahead, ignore_invalid_symbol, currency, calc_bars_count)` | `series <type>` | Current | [COMPILE] t1, all 8 parameters by name |
| `request.security_lower_tf` | `(symbol, timeframe, expression, ignore_invalid_symbol, currency, ignore_invalid_timeframe, calc_bars_count)` | `array<type>` | Current | [COMPILE] t1, all 7 parameters |
| `request.earnings` | `(ticker, field, gaps, lookahead, ignore_invalid_symbol, currency)` | `series float` | Current | [COMPILE] t2 |
| `request.dividends` | `(ticker, field, gaps, lookahead, ignore_invalid_symbol, currency)` | `series float` | Current | [COMPILE] t2 |
| `request.splits` | `(ticker, field, gaps, lookahead, ignore_invalid_symbol)`; no `currency` | `series float` | Current | [COMPILE] t2; `currency` rejected in t5 |
| `request.financial` | `(symbol, financial_id, period, gaps, ignore_invalid_symbol, currency)`; no `lookahead` | `series float` | Current | [COMPILE] t3; `lookahead` rejected in t5 |
| `request.economic` | `(country_code, field, gaps, ignore_invalid_symbol)` | `series float` | Current | [COMPILE] t3 |
| `request.currency_rate` | `(from, to, ignore_invalid_currency)` | `series float` | Current | [COMPILE] t3 |
| `request.seed` | `(source, symbol, expression, ignore_invalid_symbol, calc_bars_count)` | `series <type>` | Existing repos only (section 8) | [COMPILE] t3 |
| `request.footprint` | `(ticks_per_row, va_percent, imbalance_percent)` | `series footprint` | New, January 2026; Premium/Ultimate only | [COMPILE] t7 |
| `request.quandl` | `(ticker, gaps, index, ignore_invalid_symbol)` | `series float` | Deprecated, runtime error | [COMPILE] t7 (still compiles, no warning) |

## 3. Limits

| Limit | Value for Premium | Exact wording | Tag |
|---|---|---|---|
| Unique `request.*()` calls per script | **40** | "A script can use up to 40 unique calls to the functions in the request.*() namespace, or up to 64 unique calls if the user has the Ultimate plan. A subsequent call to the same request.*() function with the same arguments is not typically unique." | [DOC] S2 |
| Same, second statement | 40 | "Scripts can perform up to 40 unique requests using any combination of request.*() function calls, or up to 64 if the user has the Ultimate plan." | [DOC] S1 |
| Functions counted | all ten data functions | Listed: `request.security()`, `request.security_lower_tf()`, `request.currency_rate()`, `request.dividends()`, `request.splits()`, `request.earnings()`, `request.quandl()`, `request.financial()`, `request.economic()`, `request.seed()` | [DOC] S2 |
| Identical calls | counted once | "When a script executes two or more identical request.*() function calls, only the first call usually counts toward this limit." Reference Manual: "A call is unique only if it does not call the same function with the same arguments." | [DOC] S2, S3 |
| Calls inside imported libraries | counted, even if duplicated | "when a script imports library functions containing request.*() calls within their scopes, those calls do count toward this limit, even if the script already calls the same request.*() function with the same arguments in its main scope." | [DOC] S2 |
| Loops | each distinct context counts | Docs example: 50 iterations with 50 different timeframes "causes a runtime error when `i == 41`". The limit is a **runtime** error, not a compile error. | [DOC] S2 |
| Tuple elements, whole script | **127** | "All the request.*() function calls in a script taken together cannot return more than 127 tuple elements." Workaround given: pass a user-defined type object as the expression. | [DOC] S2 |
| Intrabars (lower-timeframe bars) | **100,000** | "All non-professional plans – Basic, Essential, Plus, and Premium – can request up to 100K bars of data. Expert plans have access to 125K bars of data. Ultimate plans can request 200K lower-timeframe bars." | [DOC] S2 |
| Chart bars | **20,000** | "20000 historical bars for the Premium plan." Pricing page row "Historical bars available: 5K / 10K / 10K / 20K / 40K" agrees. | [DOC] S2, S19 |
| `request.footprint` | 1 call per script; Premium or Ultimate | "A script can execute only one unique call to this function. Additionally, only users who have a Premium or Ultimate plan can use scripts that call it." | [DOC] S2 |
| Spread symbol size | 10 symbols | "A single spread can include no more than 10 unique symbols." | [DOC] S14 |

Budget arithmetic for one script on Premium (derived from the [DOC] numbers above): 40 unique requests; one tuple request counts once however many elements it returns, so the binding constraints are 40 contexts and 127 tuple elements in total. Whether a tuple request inside a loop counts its elements once or once per symbol is **not stated**; not verified.

## 4. `request.security()`

### 4.1 Parameters

| Parameter | Qualifier and type (S3) | Default | Behaviour | Tag |
|---|---|---|---|---|
| `symbol` | series string | required | Ticker, `"Exchange:Symbol"`, spread string, `syminfo.tickerid`, or a `ticker.*()` ID. Empty string means the chart symbol. "We recommend specifying the exchange prefix when possible for consistent results." | [DOC] S1, S3 |
| `timeframe` | series string | required | Timeframe string; empty string or `timeframe.period` means the chart timeframe | [DOC] S1, S3 |
| `expression` | series int/float/bool/string/color/enum, tuple, UDT object, array/matrix/map | required | Evaluated on the requested dataset | [DOC] S3 |
| `gaps` | simple barmerge_gaps | `barmerge.gaps_off` | `gaps_on`: "returns na results on all chart bars where new data is not yet confirmed from the requested context". `gaps_off`: "fills the gaps in the requested data with the last confirmed values on historical bars and the most recent developing values on realtime bars." | [DOC] S1 |
| `lookahead` | simple barmerge_lookahead | `barmerge.lookahead_off` | "On historical bars only, returns data from the timeframe before it elapses… Has no effect on realtime values." | [DOC] S3 |
| `ignore_invalid_symbol` | input bool | `false` | `true` returns `na` instead of a runtime error | [DOC] S1, S3 |
| `currency` | series string | `syminfo.currency` | Converts using "the previous daily value of a corresponding currency pair from the most popular exchange" | [DOC] S1, S3 |
| `calc_bars_count` | simple int | all chart bars | Limits how many recent historical bars are requested | [DOC] S3 |

Timeframe strings: "There is no "hour" unit; "1H" is not valid. The correct format for one hour is "60"". So 1h = `"60"`, 4h = `"240"`, daily = `"1D"`, weekly = `"1W"`. In v6, `timeframe.period` always includes the multiplier ("D" becomes "1D"). [DOC] S9, S8

### 4.2 The documented non-repainting pattern for higher-timeframe data

Quoted in full, S1 section "Avoiding repainting / Higher-timeframe data" [DOC]:

> "The most reliable approach to achieve non-repainting results is to use an expression argument that only references past bars (e.g., close[1]) while using barmerge.lookahead_on as the lookahead value."

> "if the values used in the expression are offset by at least one bar, the "future" data the function retrieves is no longer from the future. Instead, the data represents confirmed values from established, available HTF bars."

The docs' own code [DOC] S1:

```pine
float requestedWMA = request.security(
    syminfo.tickerid, timeframe, ta.wma(close, length)[1], lookahead = barmerge.lookahead_on
)
```

Supporting statements:

| Statement | Tag |
|---|---|
| "The request.security() call uses barmerge.lookahead_on and offsets each item in the tuple by one bar. This is the only recommended method to avoid repainting." | [DOC] S1 (Libraries example) |
| "The most robust method is to offset all expressions by 1… The request.security() call must also use barmerge.lookahead_on. This method returns data that is up to one HTF bar "late", and is thus not subject to change." | [DOC] S4 |
| Why the default repaints: on realtime bars `request.security()` "returns the symbol's current close value, regardless of confirmation"; after a reload those bars show only confirmed values. | [DOC] S1 |
| Leak case: "Using barmerge.lookahead_on at timeframes higher than the chart's without offsetting the expression argument like in close[1] will introduce future leak in scripts". Such scripts "are not allowed as script publications". | [DOC] S3, S1 |
| The compiler does **not** warn about the leak case: `request.security(syminfo.tickerid, "1W", close, lookahead = barmerge.lookahead_on)` compiled with 0 errors and 0 warnings. | [COMPILE] t8 |
| In a tuple, every element needs its own `[1]`. | [DOC] S1 (tuple example); [COMPILE] t1 |

Lookahead is acceptable only in three documented cases: the expression has a historical offset; the timeframe equals the chart's; or the request is to an intrabar timeframe. [DOC] S1

### 4.3 Requests on the chart's own timeframe (other symbols)

| Statement | Tag |
|---|---|
| "Retrieving data from a different symbol on the chart's timeframe does not risk repainting… When using the chart's timeframe, there is no need to offset the data, change the default lookahead value, or use barmerge.lookahead_on in order to avoid repainting." | [DOC] S4 |
| Time-axis caveat: "request.*() functions adapt the returned series to the chart's time axis… requesting "BTCUSD" data on the "SPY" chart… will only show new values when the "SPY" chart has new data as well." | [DOC] S1 |
| Realtime caveat: chart feed and requested feeds "are managed by independent, concurrent processes… it's possible for races to occur where requested results temporarily fall out of synch with the chart on a realtime bar". | [DOC] S1 |
| Inference: an alert evaluated at bar close reads the other symbol's value as it stands at that tick. For an end-of-day-only series (section 11.1) the day's value may not be published yet at 16:00 ET; the publication time is not documented, so the `[1]` form is the safe choice for those series. | Inference; publication time not verified |

### 4.4 Lower timeframes through `request.security()`

| Statement | Tag |
|---|---|
| "it returns the results from only a single intrabar (LTF bar) on each chart bar." | [DOC] S1 |
| "When using barmerge.lookahead_on, it will return the first available intrabar from the chart period. When using barmerge.lookahead_off, it will return the last intrabar from the chart period. On realtime bars, it returns the last available value… regardless of the lookahead value". | [DOC] S1 |
| "To prevent repainting… use barmerge.lookahead_off for lower timeframe data requests." | [DOC] S4 |
| "we don't typically recommend using this function for LTF data requests. The request.security_lower_tf() function is more optimal for such cases." | [DOC] S1 |
| Consequence for this trader: a script that hard-codes `"1D"` and is opened on a **weekly** chart silently becomes a lower-timeframe request with different semantics. The docs' guard is a `runtime.error()` when `timeframe.in_seconds() > timeframe.in_seconds(higherTimeframe)`. | [DOC] S1 (guard); the weekly-chart consequence is inference |

### 4.5 Tuples, objects, dynamic requests

| Topic | Rule | Tag |
|---|---|---|
| Tuples | One call can return several series of different types; tuples cannot nest | [DOC] S1; [COMPILE] t1 |
| UDT objects | Allowed as `expression`; the documented way around the 127-element limit | [DOC] S1, S2; [COMPILE] t1 |
| Dynamic requests | "By default, unlike all previous Pine Script versions, request.*() function calls in Pine Script v6 are dynamic." They accept series symbol/timeframe arguments, run inside loops and `if` blocks, and can nest. | [DOC] S1, S8; [COMPILE] t1 |
| Dynamic limitation 1 | "scripts must request all required datasets while executing on historical bars. All request.*() calls on realtime bars can retrieve data from the datasets that the script previously accessed on historical bars, but they cannot request a new context or evaluate a new expression." | [DOC] S1 |
| Dynamic limitation 2 | In a loop, "a request.*() call's evaluated expression cannot depend on the values of those variables" (loop variables). | [DOC] S1 |
| Order of evaluation | Declared variables used as `expression` are duplicated with "all preceding code"; code after the call is not included | [DOC] S1 |
| Wrong idiom | `ta.sma(request.security(sym, "1D", ohlc4), 20)` is a 20-chart-bar average of daily values, not a daily 20-bar average; put the calculation inside `expression` | [DOC] S1 |
| Source inputs | An `input.source()` wired to another indicator's plot is evaluated on the chart's symbol, not the requested symbol | [DOC] S1 |
| Function calling `ta.*` inside a looped request | Compiles with warning CW10003 ("should be called on each calculation for consistency") | [COMPILE] t1 |
| Helper `f(sym, tf, src) => request.security(sym, tf, src[1], lookahead = barmerge.lookahead_on)` | Compiles. Whether `src` is evaluated in the requested context for every argument form is not verified. | [COMPILE] t12; semantics not verified |

### 4.6 Data-feed differences that affect 1h and 4h charts

| Statement | Tag |
|---|---|
| Intraday and end-of-day are separate feeds: "volume data may not be the same since some trades (block trades, OTC trades, etc.) may only be available at the end of the trading day… commonplace in stocks." | [DOC] S1 |
| "EOD feeds do not contain information from extended hours." | [DOC] S1 |
| "the high value on one EOD bar may not match any intraday high values supplied by the data provider for that day." | [DOC] S1 |
| Historical and realtime bars come from different feeds; providers revise prices and split-adjust history, so some repainting is "Unavoidable". | [DOC] S5 |
| Realtime data "may be delayed, depending on your account type and extra data services". | [DOC] S1 |

### 4.7 Alternative: `indicator(timeframe = ...)`

"Programmers can also enable compatible scripts to perform calculations on data from another timeframe, without requiring request.*() calls, by supplying an argument to the timeframe parameter of the indicator() declaration statement." [DOC] S1. `indicator("x", timeframe = "1D", timeframe_gaps = false)` compiles. [COMPILE] t8

## 5. `request.security_lower_tf()`

| Item | Detail | Tag |
|---|---|---|
| Returns | "an array containing one element for each lower-timeframe bar within the chart bar… ordered by time with the earliest value first"; a tuple expression returns a tuple of arrays | [DOC] S3; [COMPILE] t1 |
| No data | "When executing this function on a chart bar that doesn't have accessible intrabar data, it will return an empty array." | [DOC] S1 |
| Timeframe rule | Only timeframes lower than or equal to the chart's; otherwise runtime error, or `na` with `ignore_invalid_timeframe = true` | [DOC] S1, S3 |
| Expression limits | No direct collections or mutable variables as expression | [DOC] S1 |
| Limit | 100,000 intrabars on Premium (section 3) | [DOC] S2 |
| Repainting | "Scripts using this function might calculate differently on historical and realtime bars, leading to repainting." It is better than `request.security()` for intrabars because it keeps them time-ordered, but "it's still possible in some cases for minor repainting to occur due to data differences from the provider". | [DOC] S3, S1 |
| Spreads | "spreads (e.g., "AAPL+MSFT*TSLA") do not always return reliable data with this function." | [DOC] S3 |
| Volume caveat | Intraday bars exclude the block/OTC volume that the daily bar contains, so summed intrabar volume differs from daily `volume` | [DOC] S1 (inference from the data-feed statement) |

History reachable with 100,000 intrabars. Derived arithmetic from the [DOC] limit, assuming the regular 390-minute session and a full intrabar feed; the result does not depend on the chart timeframe (1h, 4h, D or W) as long as the intrabar timeframe is lower. The docs use the same reasoning: on a 60-minute chart requesting 1-minute data "the minimum number of chart bars covered by the request is 1666, because 100000 / 60 = 1666.67". Extended-hours data would shorten these spans.

| Intrabar timeframe | Intrabars per regular session | Sessions covered by 100,000 intrabars | About |
|---|---|---|---|
| `"1"` | 390 | 256 | 1 year |
| `"5"` | 78 | 1,282 | 5 years |
| `"15"` | 26 | 3,846 | 15 years |
| `"30"` | 13 | 7,692 | 30 years |
| `"60"` | 7 | 14,285 | more than most stocks' history |

Typical uses (from S1 examples and the function's shape): up/down intrabar volume and delta, intrabar realised volatility, first/last intrabar values, opening-range statistics on a daily chart. [DOC] S1 for the pattern; the list of uses is inference.

## 6. Earnings, dividends, splits

### 6.1 Field constants (complete)

| Function | Field constants | Meaning | Tag |
|---|---|---|---|
| `request.earnings` | `earnings.actual` (default) | "the earnings value as it was reported" | [DOC] S3; [COMPILE] t2 |
| | `earnings.estimate` | "the estimated earnings value" | [DOC] S3; [COMPILE] t2 |
| | `earnings.standardized` | "the standardized earnings value" | [DOC] S3; [COMPILE] t2 |
| `request.dividends` | `dividends.gross` (default), `dividends.net` | Before / after expenses the company deducts from its payouts | [DOC] S1, S3; [COMPILE] t2 |
| `request.splits` | `splits.numerator`, `splits.denominator` | Parts of the split ratio | [DOC] S1, S3; [COMPILE] t2 |

`request.earnings` returns **EPS only**. There is no revenue field: `earnings.revenue`, `earnings.reported`, `earnings.surprise` are undeclared identifiers. [COMPILE] t5, t9

What the three EPS fields mean, Help Center "Earnings" [DOC] S11:

| Chart label | Pine field | Definition |
|---|---|---|
| As reported | `earnings.actual` | "the EPS collected directly from a company's press release for the corresponding period… the value can be either GAAP or non-GAAP, depending on what the majority of brokers report for the specific metric." |
| Estimate | `earnings.estimate` | "the estimated value of the As reported EPS derived from data collected by research analysts." |
| Standardized | `earnings.standardized` | "the fully-diluted GAAP EPS. It appears only when a full report is available and it can differ from the As reported." |
| Surprise | none; compute `actual - estimate` | "the absolute difference between As reported and Estimate." |

### 6.2 When values appear

| Statement | Tag |
|---|---|
| "Note that when you request financial data using the request.dividends() and request.earnings() functions, the new value is returned on the bar where the report was published. Using the financial function, you get a new value on the bar where the next fiscal period begins." | [DOC] S10 |
| "the values returned by these functions reflect the data available as it comes in. This behavior differs from financial data originating from a request.financial() call". | [DOC] S1 |
| With `barmerge.gaps_on` "they only return values when new data is available. Otherwise, they return na." With the default `gaps_off` the last value is carried forward. | [DOC] S1 |
| `ticker` must be `"Exchange:Symbol"`: "Using syminfo.ticker will cause an error. Use syminfo.tickerid instead." | [DOC] S3 |
| `lookahead` exists on all three functions, default `barmerge.lookahead_off` | [DOC] S3; [COMPILE] t2 |
| On the chart, earnings icons "are placed along the X-axis on the report date." | [DOC] S11 |

Not established by any official text I found:

| Open point | Why it matters |
|---|---|
| For a report released **after the close** of day D, does the daily bar D carry the value on historical bars? | If yes, a signal on bar D's close uses information released minutes later. Safe handling until tested: treat the earnings value as usable from the bar after it first appears. |
| Is historical `earnings.estimate` the consensus that stood just before the report? | Needed for a clean surprise measure. |
| Does the realtime bar receive the value on the same bar as history shows it? | Repainting of the event bar. |
| Which bar carries a `request.dividends()` value (ex-date or another date)? | Not stated in S1, S3, S10. |

### 6.3 Upcoming earnings and dividends

All are built-in variables, not `request.*` calls; type `series`. [DOC] S3; types confirmed by compiler (`simple int x = earnings.future_time` is rejected: "cannot accept values of the "series int" form"). [COMPILE] t2, t5

| Variable | Type | Reference Manual description |
|---|---|---|
| `earnings.future_time` | series int | "Returns a UNIX timestamp indicating the expected time of the next earnings report, or na if this data isn't available." |
| `earnings.future_eps` | series float | "Returns the estimated Earnings per Share of the next earnings report in the currency of the instrument, or na if this data isn't available." |
| `earnings.future_revenue` | series float | "Returns the estimated Revenue of the next earnings report in the currency of the instrument, or na if this data isn't available." |
| `earnings.future_period_end_time` | series int | "returns the UNIX timestamp of the day when the financial period covered by those earnings ends, or na" |
| `dividends.future_amount` | series float | "Returns the payment amount of the upcoming dividend in the currency of the current instrument, or na" |
| `dividends.future_ex_date` | series int | "Returns the Ex-dividend date (Ex-date) of the current instrument's next dividend payment, or na" |
| `dividends.future_pay_date` | series int | "Returns the Payment date (Pay date) of the current instrument's next dividend payment, or na" |

Names that do not exist: `earnings.future_date`, `earnings.future_estimate`, `dividends.future_record_date`, `splits.future_date`. [COMPILE] t5, t9

Remark on every `earnings.future_*` variable [DOC] S3:

> "This value is only fetched once during the script's initial calculation. The variable will return the same value until the script is recalculated, even after the expected time of the next earnings report."

| Consequence | Tag |
|---|---|
| The value is today's "next report", repeated on every bar. It cannot reconstruct "days to earnings" on past bars. | Inference from the quote |
| An alert left running past the report date keeps the old date until the script recalculates. Whether server-side alert instances recalculate on their own is not documented. | Inference; not verified |
| The date can be an estimate: report dates are "Exact — received directly from the company or official sources." or "Approximate — calculated by our data provider based on their methodology." If an approximate date passes with no report, "The provider moves the date forward by one day." Pine exposes no flag that distinguishes the two. | [DOC] S12; absence of a flag from S3 |
| `request.security("NASDAQ:MSFT", "1D", earnings.future_time)` compiles; whether it returns the other symbol's date at runtime is not verified. | [COMPILE] t2 |

## 7. `request.financial()`

### 7.1 Parameters and periods

| Item | Detail | Tag |
|---|---|---|
| Source | "retrieves financial data from FactSet" | [DOC] S1 |
| `symbol` | Needs `"Exchange:Symbol"`; use `syminfo.tickerid` | [DOC] S1 |
| `period` per User Manual | "FQ" (quarterly), "FH" (semiannual), "FY" (annual), "TTM" (trailing twelve months) | [DOC] S1 |
| `period` per Reference Manual | "Possible values are "TTM", "FY", "FQ", "FH", "D"." | [DOC] S3 |
| "D" | Added February 2024 for daily data, example `request.financial("AMEX:SPY", "NAV", "D")`; Help Center lists D only for ETF fields `NAV`, `NAV_ALL`, `FUND_FLOWS`, `AUM` | [DOC] S7, S10 |
| Missing data | Returns `na` when the period does not exist for the company; error unless `ignore_invalid_symbol = true` | [DOC] S1 |
| `gaps` | Default `barmerge.gaps_off` | [DOC] S3 |
| Compiler | The ID and period are plain strings; the compiler does not validate them. A typo fails only at runtime. | [COMPILE] t3 (inference from string typing) |

### 7.2 Timing: not point-in-time

| Statement | Tag |
|---|---|
| "Using the financial function, you get a new value on the bar where the next fiscal period begins." | [DOC] S10 |
| "the data retrieved from this function comes in at a fixed frequency, independent of the precise date on which the data is made available within a fiscal period. For a company's dividends, splits, and earnings per share (EPS) information, one can request data reported on exact dates via request.dividends(), request.splits(), and request.earnings()." | [DOC] S1 |
| Data are standardised by the provider and "may not always coincide with the data indicated in the annual or interim report". | [DOC] S13 |
| Restatements: **no official statement found** on whether history shows first-reported or restated values. | Searched S1, S3, S10, S13 and the web today; not verified |

Inference from the two quotes: a quarter ending 31 March steps into the series at the start of April, while the company reports in late April or May. On historical bars the script therefore sees roughly three to six weeks of unpublished data. On the live edge the number cannot exist before publication, so history and realtime differ. Treat every `request.financial()` series as contaminated for backtesting unless it is latched on a `request.earnings()` report bar, and even then restatement is unresolved.

### 7.3 Financial IDs most relevant to swing trading

Periods as listed in S1 (S10 agrees unless noted). [DOC] S1, S10

| Need | `financial_id` | Periods | Note |
|---|---|---|---|
| Diluted EPS | `EARNINGS_PER_SHARE_DILUTED` | FQ, FH, FY, TTM | |
| Basic EPS | `EARNINGS_PER_SHARE_BASIC` | FQ, FH, FY, TTM | |
| EPS (unqualified) | `EARNINGS_PER_SHARE` | used with "TTM" in S1 and S10 example code | Not in either ID table; validity not verified |
| EPS growth, 1 year | `EARNINGS_PER_SHARE_BASIC_ONE_YEAR_GROWTH` / `EARNINGS_PER_SHARE_DILUTED_ONE_YEAR_GROWTH` | FQ, FH, FY, TTM / FQ, FH, FY | |
| Revenue | `TOTAL_REVENUE` | FQ, FH, FY, TTM | |
| Revenue growth, 1 year | `REVENUE_ONE_YEAR_GROWTH` | FQ, FH, FY, TTM | |
| EPS estimate | `EARNINGS_ESTIMATE` | FQ, FH, FY | Which period it refers to on a given bar is not documented |
| Revenue estimate | `SALES_ESTIMATES` | FQ, FH, FY | Same caveat |
| Forward P/E, forward P/S | `PRICE_EARNINGS_FORWARD`, `PRICE_SALES_FORWARD` | FQ, FY | |
| Shares outstanding | `TOTAL_SHARES_OUTSTANDING` | FQ, FH, FY | Market cap = this × `close` |
| Float | `FLOAT_SHARES_OUTSTANDING` | **FY only** | |
| Diluted / basic average shares | `DILUTED_SHARES_OUTSTANDING`, `BASIC_SHARES_OUTSTANDING` | FQ, FH, FY | |
| Margins | `GROSS_MARGIN`, `OPERATING_MARGIN`, `NET_MARGIN`, `EBITDA_MARGIN`, `FREE_CASH_FLOW_MARGIN` | mostly FQ, FH, FY (some TTM) | |
| Profit and cash | `NET_INCOME`, `EBITDA`, `FREE_CASH_FLOW`, `CASH_F_OPERATING_ACTIVITIES` | FQ, FH, FY, TTM | |
| Balance sheet | `TOTAL_DEBT`, `NET_DEBT`, `CASH_N_SHORT_TERM_INVEST`, `BOOK_VALUE_PER_SHARE` | FQ, FH, FY | |
| Quality scores | `PIOTROSKI_F_SCORE`, `ALTMAN_Z_SCORE`, `BENEISH_M_SCORE`, `SLOAN_RATIO`, `ACCRUALS_RATIO` | FQ, FH, FY | |
| Buybacks | `BUYBACK_YIELD`, `SHARE_BUYBACK_RATIO` | FQ, FH, FY | |
| ETF daily | `NAV`, `NAV_ALL`, `FUND_FLOWS`, `AUM` | D | S10 only |
| **Short interest** | **none** | | Not in S1 or S10 tables |

Price-based ratios (market cap, P/E, P/B, P/S, earnings yield) are not IDs; they are computed from an ID and `close`. [DOC] S1, S10. Full ID tables: S1 lists about 222 IDs, S10 about 271 (S10 has about 50 extra, mostly FY-only detail lines; S1 has `PEG_RATIO`, which S10 lacks).

## 8. Other `request.*` functions

| Function | Facts | Tag |
|---|---|---|
| `request.economic(country_code, field)` | Example `request.economic("US", "GDPQQ")`. US-relevant field codes present in the S1 table: `INTR` (Interest Rate), `IRYY` (Inflation Rate, YoY), `IRMM`, `UR` (Unemployment Rate), `NFP` (Nonfarm Payrolls), `IJC` (Initial Jobless Claims), `CJC`, `GDPQQ`, `GDPYY`, `CCI`, `BCOI`, `NMPMI`, `PPI`, `CPI`, `RSMM`, `RSYY`, `M2`, `CBBS`. Country availability per metric is in the Help Center, not in the table. Default `gaps_off`. | [DOC] S1 |
| | Same data as chart symbols: "Use "ECONOMIC" as the exchange name and {country_code}{field} as the ticker… "ECONOMIC:USGDP"." The symbol directory lists the prefix as `ECONOMICS:` (for example `ECONOMICS:USINTR`, `ECONOMICS:USIRYY`). | [DOC] S3 versus [DOC] S17 (conflict) |
| | Whether values are placed on the release date or the reference period, and whether revisions overwrite history: not documented. | Not verified |
| `request.currency_rate(from, to)` | "requests a daily rate for currency conversion calculations". User Manual: "it ensures non-repainting results without requiring additional specification." Reference Manual remark: "Please note that using this variable/function can cause indicator repainting." | [DOC] S1 versus [DOC] S3 (conflict) |
| `request.seed(source, symbol, expression)` | User Manual: "The creation of new Pine Seeds repositories is currently unavailable. However, the data feeds from existing repositories are still accessible to charts and scripts." | [DOC] S1 |
| | Reference Manual: "The creation of new Pine Seeds repositories is suspended; only existing repositories are currently supported." | [DOC] S3 |
| | GitHub README: "**The creation of new repositories has been suspended**. We will continue to support the existing repositories." | [DOC] S15 |
| | Properties when it worked: EOD only, "only daily-based timeframes (1D and above)", "the data can only be updated 5 times per day", no `gaps` parameter ("It always returns na values when no new data exists"). | [DOC] S15, S1 |
| `request.quandl()` | "This function has been deprecated due to the API change from NASDAQ Data Link. Requests for "QUANDL" symbols are no longer valid and requests for them return a runtime error." Replacements named: "BCHAIN" or "FRED" feeds, and the `LibraryCOT` library for COT data. Still listed among the counted functions in S2 and still compiles. | [DOC] S3, S2; [COMPILE] t7 |
| `request.footprint(ticks_per_row, va_percent, imbalance_percent)` | Added January 2026. Returns a `footprint` object or `na`. Companion functions: `footprint.buy_volume/sell_volume/total_volume/delta/poc/vah/val/rows/get_row_by_price`, `volume_row.up_price/down_price/buy_volume/sell_volume/total_volume/delta/has_buy_imbalance/has_sell_imbalance`. Defaults: `va_percent` 70, `imbalance_percent` 300. | [DOC] S7, S1, S3; [COMPILE] t7 |
| | "Volume footprints are available exclusively to users who have a Premium or Ultimate plan." "Scripts cannot perform more than one footprint request… it raises a runtime error." | [DOC] S1 |
| | Higher-timeframe form in the docs: `request.security(syminfo.tickerid, htf, request.footprint(ticks)[1], barmerge.gaps_on, barmerge.lookahead_on)`. | [DOC] S1; [COMPILE] t7 |
| | "On timeframes higher than or equal to "1D", a footprint's total volume might differ significantly from the value of the volume variable." | [DOC] S1 |
| | Sharing constraint: a published script using it cannot be used by non-Premium accounts. | [DOC] S1 (inference from the plan note) |

## 9. `syminfo.*` for cross-sectional context

Rule from the User Manual [DOC] S6: "Most syminfo.* variables have the "simple" type qualifier, because their values do not change after the first bar. However, the variables relating to analyst recommendations and targets have the "series" qualifier, because they store dynamic data that can change over time."

Every row was compiled with the stated qualifier in an explicit declaration. [COMPILE] t4. The `series` rows were also confirmed by a failing `simple` declaration. [COMPILE] t5

| Variable | Type | Description (S3/S6) | History? |
|---|---|---|---|
| `syminfo.sector` | simple string | Sector, for example "Electronic Technology" for NASDAQ:AAPL, "Technology Services" for NYSE:IBM, "Miscellaneous" for AMEX:SPY. These example names are not GICS sector names. | Current only |
| `syminfo.industry` | simple string | Narrower industry, for example "Telecommunications Equipment" | Current only |
| `syminfo.country` | simple string | Two-letter exchange country | Current only |
| `syminfo.type` | simple string | "stock", "fund", "dr", "index", "futures"… | Current only |
| `syminfo.isin` | simple string | ISIN or empty string (added November 2025) | Current only |
| `syminfo.employees` | simple int | Reported number of employees | Current only |
| `syminfo.shareholders` | simple int | Reported number of shareholders | Current only |
| `syminfo.shares_outstanding_float` | simple float | "The total number of shares outstanding a company has available, excluding any of its restricted shares." | Current only |
| `syminfo.shares_outstanding_total` | simple int | Total shares including restricted | Current only |
| `syminfo.target_price_average` / `_median` / `_high` / `_low` | series float | "The average of the last yearly price targets for the symbol predicted by analysts." (and median, highest, lowest) | Not documented |
| `syminfo.target_price_estimates` | series float | "The latest total number of price target predictions" | Not documented |
| `syminfo.target_price_date` | series int | "The starting date of the last price target prediction" | Not documented |
| `syminfo.recommendations_buy` / `_buy_strong` / `_hold` / `_sell` / `_sell_strong` / `_total` | series int | Analyst counts per rating | Not documented |
| `syminfo.recommendations_date` | series int | "The starting date of the last set of recommendations" | Not documented |
| `syminfo.main_tickerid` | simple string | Chart ticker ID even inside a request's expression | n/a |
| `syminfo.current_contract`, `syminfo.expiration_date`, `syminfo.mincontract`, `syminfo.volumetype` | simple | Futures and contract metadata | n/a |

| Point | Tag |
|---|---|
| The analyst variables are described only as "the last" or "latest" values; no text says past bars hold past values. The official examples read them once, under `barstate.islastconfirmedhistory`. Treat them as a current snapshot. | [DOC] S3 (wording); the snapshot reading is inference, not verified on a chart |
| Remark on targets: "If analysts supply the targets when the market is closed, the variable can return na until the market opens." | [DOC] S3 |
| Other symbols: "Most of these variables, excluding syminfo.main_tickerid, can also represent information relating to a requested dataset if a script uses them as the expression argument in a request.*() function call." `request.security("NASDAQ:MSFT", "1D", syminfo.sector)` compiles. | [DOC] S6; [COMPILE] t4 |
| No sector: Reference Manual says `na`, User Manual says "an empty string". Test for both. | [DOC] S3 versus S6 (conflict) |
| Do not exist: `syminfo.short_interest`, `syminfo.market_cap`, `syminfo.market_cap_basic`, `syminfo.float`, `syminfo.beta`. | [COMPILE] t5, t9 |
| Float history: only `FLOAT_SHARES_OUTSTANDING` (FY) through `request.financial()`, with the timing problem of section 7.2. Using today's `syminfo.shares_outstanding_float` on past bars applies today's float to old volume. | [DOC] S1, S6 (inference) |

## 10. `ticker.*` and spread symbols

### 10.1 Functions

| Function | Parameters | Purpose | Tag |
|---|---|---|---|
| `ticker.new` | `prefix, ticker, session, adjustment, backadjustment, settlement_as_close` | Build a ticker ID with modifiers | [DOC] S3; [COMPILE] t6 (all by name) |
| `ticker.modify` | `tickerid, session, adjustment, backadjustment, settlement_as_close` | Change modifiers on an existing ID | [DOC] S3; [COMPILE] t6 |
| `ticker.standard` | `symbol` (default `syminfo.tickerid`) | "Creates a ticker to request data from a standard chart that is unaffected by modifiers like extended session, dividend adjustment, currency conversion, and the calculations of non-standard chart types" | [DOC] S3; [COMPILE] t6 |
| `ticker.inherit` | `from_tickerid, symbol` | Copy the chart's modifiers onto another symbol | [DOC] S3; [COMPILE] t6 |
| `ticker.heikinashi`, `.renko`, `.kagi`, `.linebreak`, `.pointfigure` | | Non-standard chart datasets | [DOC] S1; [COMPILE] t6 (heikinashi) |

| Constant group | Values | Tag |
|---|---|---|
| Session | `session.regular`, `session.extended`; chart's own is `syminfo.session` | [DOC] S3; [COMPILE] t6 |
| Adjustment | `adjustment.none`, `adjustment.splits`, `adjustment.dividends` | [DOC] S3; [COMPILE] t6 |
| Futures only | `backadjustment.inherit/on/off`, `settlement_as_close.inherit/on/off` | [DOC] S3; [COMPILE] t6 |

| Behaviour | Tag |
|---|---|
| If `session` is omitted, "syminfo.session value is used"; if `adjustment` is omitted, "default adjustment value is used (can be different depending on particular instrument)". | [DOC] S3 |
| A request with plain `syminfo.tickerid` inherits the chart's modifiers: changing "the chart type or enabling extended trading hours in the chart's settings" changes the data. A plain literal such as `"NYSE:PFE"` "represents a standard ticker ID" without them. | [DOC] S1 |
| "If a modifier included in a constructed ticker ID does not apply to the symbol, the script will ignore that modifier". | [DOC] S1 |
| Dividend-adjusted prices change history "before the date of the latest dividend", so values calculated on them shift after each dividend. | [DOC] S1 (the shift is inference) |
| Design consequence: an alert must not depend on what the user toggled on the chart. Pin session and adjustment with `ticker.new(syminfo.prefix, syminfo.ticker, session.regular, adjustment.splits)` or use `ticker.standard()`. | Inference from the three rows above |

### 10.2 Spread symbols inside `request.security()`

| Statement | Tag |
|---|---|
| `symbol` accepts "A "string" representing a spread symbol (e.g., "AMD/INTC"). Note that "Bar Replay" mode does not work with these symbols." | [DOC] S1 |
| Compiled: `"AAPL/SPY"`, `"NASDAQ:AAPL/AMEX:SPY"`, `"CBOE:VIX/CBOE:VIX3M"`. | [COMPILE] t1 |
| Operators: subtraction, addition, multiplication, division; at most 10 symbols. | [DOC] S14 |
| "Spreads for intraday charts are calculated by taking the open, high, low, and close of each 1-minute bar and then recompiling them into the selected interval." | [DOC] S14 |
| "Spread charts can get repainted. The reason for this is that real-time bars are built on tick data, whereas historical bars are built from minute data… This affects alerts set on spread charts." | [DOC] S14 |
| Safer for signals: request each leg separately (two requests, or one tuple per leg) and divide in the script; a ratio of two confirmed closes equals the spread's close and avoids spread-bar construction. | Inference from S14 |

## 11. Market-wide symbols usable in `request.security()`

Verification method. "Listed" means the exact `PREFIX:SYMBOL` was returned by TradingView's symbol directory today (S17). "Intraday", "First daily bar" and "Last daily bar" come from the metadata embedded in the symbol's own page today (S18), viewed without login. A blank cell means the page was not fetched. This proves the symbol exists and was updating; it does **not** prove data quality, time of publication, or delay on a Premium account. All rows [DOC] S17/S18.

### 11.1 Breadth: percent of stocks above a moving average (provider Barchart, prefix `INDEX`, EOD only)

| Ticker | Description | Intraday | First daily bar | Last daily bar seen |
|---|---|---|---|---|
| `INDEX:S5FI` | S&P 500 Stocks Above 50-Day Average | No | 2006-12-29 | 2026-11-09 |
| `INDEX:S5TH` | S&P 500 Stocks Above 200-Day Average | No | 1990-10-15 | 2026-11-09 |
| `INDEX:S5TW` | S&P 500 Stocks Above 20-Day Average | No | 2006-12-29 | 2026-11-09 |
| `INDEX:S5FD`, `INDEX:S5OH`, `INDEX:S5OF` | S&P 500 above 5-, 100-, 150-Day Average | listed | | |
| `INDEX:MMFI` | Percent of Stocks Above 50-Day Average (broad market) | No | 2002-01-02 | 2026-11-09 |
| `INDEX:MMTH` | Percent of Stocks Above 200-Day Average | No | 2002-01-02 | 2026-11-09 |
| `INDEX:MMTW`, `INDEX:MMFD`, `INDEX:MMOH`, `INDEX:MMOF` | Broad market above 20-, 5-, 100-, 150-Day | listed | | |
| `INDEX:NDFI` | Nasdaq 100 Stocks Above 50-Day Average | No | 2006-12-29 | 2026-11-09 |
| `INDEX:NDTH`, `INDEX:NDTW` | Nasdaq 100 above 200-, 20-Day | listed | | |
| `INDEX:NCFI`, `INDEX:NCTH`, `INDEX:NCTW` | Nasdaq Composite above 50-, 200-, 20-Day | listed | | |
| `INDEX:R2FI` | Russell 2000 Stocks Above 50-Day Average | No | 2013-10-14 | 2026-11-09 |
| `INDEX:R2TH`, `INDEX:R2TW`, `INDEX:R1FI`, `INDEX:R1TH`, `INDEX:R3FI`, `INDEX:R3TH`, `INDEX:DIFI`, `INDEX:DITH` | Russell 2000/1000/3000, Dow Industrials | listed | | |
| `INDEX:S1TH`, `INDEX:S4TH`, `INDEX:S6TH` | S&P 100, 400, 600 above 200-Day | listed | | |
| Sector, 50-Day: `INDEX:SKFI` (Info Tech), `SFFI` (Financials), `SEFI` (Energy), `SVFI` (Health Care), `SYFI` (Cons. Disc.), `SPFI` (Cons. Staples), `SIFI` (Industrials), `SBFI` (Materials), `SUFI` (Utilities), `SSFI` (Real Estate), `SLFI` (Telecom) | S&P sector stocks above 50-Day Average | listed | | |
| Sector, 200-Day: `INDEX:SKTH`, `SFTH`, `SETH`, `SVTH`, `SYTH`, `SPTH`, `SITH`, `SBTH`, `SUTH`, `SSTH` | S&P sector stocks above 200-Day Average | listed | | |

Naming pattern seen in the directory: 2-character universe code + `FD`/`TW`/`FI`/`OH`/`OF`/`TH` for 5/20/50/100/150/200 days. [DOC] S17 (pattern is my reading of the listed names)

### 11.2 Breadth: advancers/decliners, volume, TICK, TRIN, new highs/lows

| Ticker | Description | Provider | Intraday | First daily bar | Last daily bar seen |
|---|---|---|---|---|---|
| `USI:ADD` | NYSE $ADV minus $DECL | ICE | Yes | 1993-11-01 | 2026-11-09 |
| `USI:ADDQ` | NASDAQ $ADVQ minus $DECLQ | ICE | Yes | 1993-11-01 | 2026-11-09 |
| `USI:ADDA` | AMEX advancers minus decliners | ICE | listed | | |
| `USI:ADVDEC.NY` | NYSE Advancing - Declining | ICE | Yes | 1971-04-05 | 2026-11-10 |
| `USI:ADVDEC.NQ` | NASDAQ Advancing - Declining | ICE | Yes | 2009-08-25 | 2026-11-09 |
| `USI:ADVDEC.US` | US Stocks Advancing - Declining | ICE | Yes | 1971-01-29 | 2026-11-10 |
| `USI:ADV`, `USI:DECL` | NYSE advancing / declining issues | ICE | Yes | 1991-12-02 | 2026-11-09 |
| `USI:ADVQ`, `USI:DECLQ` | NASDAQ advancing / declining issues | ICE | listed | | |
| `USI:ADVN.NY`, `USI:DECL.NY`, `USI:UNCH.NY`, `USI:ADVN.NQ`, `USI:DECL.NQ`, `USI:ADVN.US`, `USI:DECL.US` | Advancing / declining / unchanged counts | ICE | listed | | |
| `USI:UVOL` | NYSE Up Volume | ICE | Yes | 1996-04-19 | **2026-11-06** |
| `USI:DVOL` | NYSE Down Volume | ICE | Yes | 1992-01-02 | 2026-11-09 |
| `USI:VOLD` | NYSE $UVOL minus $DVOL | ICE | Yes | 1996-04-19 | **2026-11-06** |
| `USI:UVOLQ` | NASDAQ Up Volume | ICE | Yes | 1996-04-19 | **2026-11-06** |
| `USI:DVOLQ` | NASDAQ Down Volume | ICE | Yes | 1996-04-19 | 2026-11-09 |
| `USI:VOLDQ`, `USI:TVOLQ` | NASDAQ up-minus-down volume, total volume | ICE | listed | | |
| `USI:TVOL` | NYSE Total Volume | ICE | Yes | 1996-04-19 | 2026-11-09 |
| `USI:UPVOL.NY`, `USI:DNVOL.NY`, `USI:UPVOL.NQ`, `USI:DNVOL.NQ`, `USI:UPVOL.US`, `USI:DNVOL.US` | Advancing / declining volume | ICE | listed | | |
| `USI:TICK` | NYSE Cumulative Tick | ICE | Yes | 1989-08-18 | 2026-11-09 |
| `USI:TICKQ` | NASDAQ Combined Tick | ICE | Yes | 1996-04-22 | **2026-11-06** |
| `USI:TICKA`, `USI:TICKI`, `USI:TICK.NY`, `USI:TICK.NQ`, `USI:TICK.US` | AMEX, Dow, NYSE, NASDAQ, US tick | ICE | listed | | |
| `USI:TRIN.NY` | NYSE TRIN (Arms index) | ICE | Yes | 1971-04-05 | 2026-11-09 |
| `USI:TRIN.NQ`, `USI:TRIN.US` | NASDAQ, US TRIN | ICE | listed | | |
| `INDEX:TRIN` | NYSE Trin | Barchart | No | 2003-07-18 | 2026-11-09 |
| `INDEX:ADVN` | NYSE Advancing Stocks | Barchart | No | 2007-09-28 | **2026-11-06** |
| `INDEX:DECN` | NYSE Declining Stocks | Barchart | No | 2007-09-28 | 2026-11-09 |
| `INDEX:ADVQ`, `INDEX:DECQ`, `INDEX:UNCN` | NASDAQ advancing / declining, NYSE unchanged | Barchart | listed | | |
| `INDEX:HIGN`, `INDEX:LOWN` | NYSE New Highs / New Lows | Barchart | No | 2001-06-05 | 2026-11-09 |
| `INDEX:HIGQ`, `INDEX:LOWQ`, `INDEX:HIGA`, `INDEX:LOWA` | NASDAQ, AMEX new highs / lows | Barchart | listed | | |
| `INDEX:MAHN`, `INDEX:MALN` | 52-Week Highs / Lows NYSE | Barchart | No | 2005-01-03 | 2026-11-09 |
| `INDEX:MAHQ`, `INDEX:MALQ` | 52-Week Highs / Lows Nasdaq | Barchart | No | 2005-01-03 | 2026-11-09 |
| `INDEX:MAHP`, `INDEX:MALP` | 52-Week Highs / Lows S&P 500 | Barchart | listed | | |
| `INDEX:M1HN`/`M1LN`, `INDEX:M3HN`/`M3LN`, `INDEX:M6HN`/`M6LN` | 1-, 3-, 6-Month Highs / Lows NYSE | Barchart | listed | | |

Not found under the tested names: `USI:TRIN`, `USI:TRINQ`, `USI:ADD.US`, `USI:VOLD.NY`, `INDEX:ADD`, `INDEX:TVOL`, `INDEX:UVOL`, `INDEX:MAH5`. [DOC] S17

Data-quality warning. In today's snapshot several series were one session behind their own counterpart: `USI:UVOL` at 2026-11-06 while `USI:DVOL` was at 2026-11-09; `INDEX:ADVN` at 11-06 while `INDEX:DECN` was at 11-09; `USI:UVOLQ` and `USI:TICKQ` at 11-06. [DOC] S18. Any ratio built from such a pair can combine different days. A script should compare the two series' `time` values and return `na` when they differ. The cause, and whether it occurs on a Premium account, is not verified.

### 11.3 Volatility indices

| Ticker | Description | Intraday | First daily bar | Last daily bar seen |
|---|---|---|---|---|
| `CBOE:VIX` | CBOE Volatility Index | Yes | 1990-01-03 | 2026-11-10 |
| `TVC:VIX` | Volatility S&P 500 (TVC feed) | Yes | 1990-01-03 | 2026-11-10 |
| `CBOE:VIX1D` | Cboe 1-Day Volatility Index | Yes | 2022-05-13 | 2026-11-10 |
| `CBOE:VIX9D` | 9-Day Volatility Index | Yes | 2011-01-04 | 2026-11-09 |
| `CBOE:VIX3M` | 3-Month Volatility Index | Yes | 2007-12-05 | 2026-11-10 |
| `CBOE:VIX6M` | 6-Month Volatility Index | Yes | 2008-01-02 | 2026-11-09 |
| `CBOE:VIX1Y` | One-Year Volatility Index | Yes | 2018-03-14 | 2026-11-09 |
| `CBOE:VVIX` | VIX of VIX | Yes | 2006-03-06 | 2026-11-09 |
| `CBOE:SKEW` | CBOE SKEW Index | Yes | 1990-01-02 | 2026-11-09 |
| `CBOE:VXN` | Nasdaq 100 Volatility | Yes | 2001-01-24 | 2026-11-09 |
| `CBOEFTSE:RVX` | Russell 2000 Volatility (**not** `CBOE:RVX`) | Yes | 2004-01-05 | 2026-11-09 |
| `CBOE:VXD` | DJIA Volatility | Yes | 2005-04-01 | 2026-11-09 |
| `CBOE:OVX`, `CBOE:GVZ` | Crude oil, gold volatility | Yes | 2007-05-11, 2008-08-01 | 2026-11-09 |
| `CBOE:COR3M` | Cboe Implied Correlation Index | Yes | 2006-01-03 | 2026-11-09 |
| `CBOE:DSPX` | Cboe S&P 500 Dispersion Index | Yes | 2014-06-19 | 2026-11-09 |
| `TVC:MOVE` | ICE BofAML US Bond Market Option Volatility | Yes | 2002-11-12 | 2026-11-09 |
| `CBOE:VXEEM`, `CBOE:VXTLT` | EM ETF, 20+ Year Treasury ETF volatility | Yes | 2011-03-17, 2015-04-22 | 2026-11-09 |
| `CBOE:VXEFA`, `CBOE:VXFXI`, `CBOE:VXEWZ`, `CBOE:VXSLV`, `CBOE:VIXMO`, `CBOE:VXTH` | Other ETF and strategy volatility indices | listed | | |
| `CBOE:VX1!`, `CBOE:VX2!` | VIX futures, continuous front / second | Yes | | 2026-11-10 / 2026-11-09 |

Single-stock VIX indices: a directory search for "VIXON" on CBOE returned exactly five. [DOC] S17, S18

| Ticker | Underlying | Intraday | First daily bar | Last daily bar seen |
|---|---|---|---|---|
| `CBOE:VXAPL` | Apple | Yes | 2010-06-01 | 2026-11-10 |
| `CBOE:VXAZN` | Amazon | Yes | 2010-06-01 | 2026-11-09 |
| `CBOE:VXGOG` | Google | Yes | 2010-06-01 | 2026-11-09 |
| `CBOE:VXGS` | Goldman Sachs | Yes | 2010-06-01 | 2026-11-09 |
| `CBOE:VXIBM` | IBM | Yes | 2010-06-01 | 2026-11-09 |

Five names only; there is no general per-stock implied-volatility series, so implied volatility cannot be a general input for a stock indicator. [DOC] S17 (absence of others in that search); general options data: no `request.options` [COMPILE] t9

Not found: `CBOE:RVX`, `CBOE:VIX2M`, `CBOE:EVZ`, `CBOE:VXXLE`. [DOC] S17

### 11.4 Put/call ratios

| Ticker | Description | Provider | Intraday | First daily bar | Last daily bar seen |
|---|---|---|---|---|---|
| `USI:PCC` | Put/Call Ratio (Equities + Indices), CBOE | ICE | Yes | 2006-10-17 | 2026-11-09 |
| `USI:PCCE` | Put/Call Ratio (Equities), CBOE | ICE | Yes | 2007-01-23 | 2026-11-09 |
| `USI:PCCI` | Put/Call Ratio (Indices), CBOE | ICE | Yes | 2007-01-23 | 2026-11-09 |
| `USI:PC` | Put/Call Ratio (all exchanges) | ICE | Yes | 2006-10-17 | 2026-11-09 |
| `USI:PCE` | Put/Call Ratio, Equities | ICE | Yes | 2006-10-17 | 2026-11-09 |
| `USI:PCI` | Put/Call Ratio, Indices | ICE | listed | | |
| `USI:PCSPX` | Put/Call Ratio, SPX | ICE | Yes | 2006-10-18 | 2026-11-10 |
| `USI:PCOEX` | Put/Call Ratio, OEX | ICE | listed | | |
| `INDEX:CPC` | Total Put/Call Ratio | Barchart | No | 2006-11-01 | 2026-11-09 |
| `INDEX:CPCI` | Index Put/Call Ratio | Barchart | No | 2006-11-02 | 2026-11-09 |
| `INDEX:CPCS` | Equity Put/Call Ratio | Barchart | listed | | |
| `INDEX:PCSP` | Put Call Ratio Spy | Barchart | No | 2021-01-29 | 2026-11-09 |

Per-exchange variants also listed (`USI:PCQ`, `USI:PCA`, `USI:PCN`, and `…E` / `…I` pairs for ISE, BOX, C2, EDGX, BATS, MIAX…). Not found: `INDEX:CPCE`, `USI:CPC`, `USI:PCVIX`, `CBOE:PCC`. [DOC] S17. What the OHLC of an intraday put/call series represents (cumulative-so-far or interval) is not documented; not verified.

### 11.5 Rates, credit, dollar

| Ticker | Description | Type | Intraday | First daily bar | Last daily bar seen |
|---|---|---|---|---|---|
| `TVC:US10Y` | US 10-year yield | bond | Yes | 1912-06-03 | 2026-11-10 |
| `TVC:US02Y` | US 2-year yield | bond | Yes | 1988-02-26 | 2026-11-10 |
| `TVC:US03MY`, `TVC:US01Y`, `TVC:US05Y`, `TVC:US30Y` | Other points on the curve | bond | listed | | |
| `TVC:DXY` | US Dollar Index | index | Yes | 1967-01-31 | 2026-11-10 |
| `FRED:BAMLH0A0HYM2` | ICE BofA US High Yield OAS | economic | No | 1996-12-31 | **2026-11-06** |
| `FRED:BAMLC0A0CM` | ICE BofA US Corporate (IG) OAS | economic | No | 1996-12-31 | **2026-11-06** |
| `FRED:BAMLH0A3HYC` | CCC & lower OAS | economic | listed | | |
| `FRED:T10Y2Y` | 10-year minus 2-year | economic | No | 1976-06-01 | **2026-11-06** |
| `FRED:T10Y3M`, `FRED:DGS10`, `FRED:DGS2`, `FRED:DFF`, `FRED:SOFR` | Curve and policy rates | economic | listed | | |
| `FRED:NFCI` | Chicago Fed National Financial Conditions Index (weekly) | economic | No | 1971-01-08 | 2026-10-30 |
| `FRED:STLFSI4`, `FRED:VIXCLS`, `FRED:WALCL`, `FRED:RRPONTSYD`, `FRED:WTREGEN`, `FRED:M2SL`, `FRED:ICSA`, `FRED:UMCSENT` | Stress, liquidity, macro | economic | listed | | |
| `AMEX:HYG`, `AMEX:JNK`, `AMEX:LQD` | High-yield and IG credit ETFs | fund | listed | | |
| `NASDAQ:TLT`, `NASDAQ:IEF`, `NASDAQ:IEI`, `NASDAQ:SHY` | Treasury ETFs | fund | listed | | |
| `ECONOMICS:USINTR`, `ECONOMICS:USIRYY` | US interest rate, inflation rate YoY | economic | No | | |
| `ECONOMICS:USUR`, `ECONOMICS:USNFP`, `ECONOMICS:USIJC`, `ECONOMICS:USGDP`, `ECONOMICS:USCCI`, `ECONOMICS:USBCOI` | Other US economic series as chart symbols | economic | listed | | |

FRED series lagged the market by one to two sessions in today's snapshot (last bar 2026-11-06 on 2026-11-10). They suit slow regime filters, not day-level signals. Credit ETFs (`AMEX:HYG` against `NASDAQ:IEF`) are the same-day alternative. [DOC] S18 for the lag; the suitability judgement is inference. Not found: `FRED:DEXUSEU`. [DOC] S17

### 11.6 Indices and sector ETFs

| Group | Tickers (all listed today) | Tag |
|---|---|---|
| Broad ETFs | `AMEX:SPY`, `NASDAQ:QQQ`, `AMEX:IWM`, `AMEX:DIA`, `AMEX:MDY`, `AMEX:RSP` (equal weight) | [DOC] S17 |
| Select Sector SPDRs | `AMEX:XLK`, `AMEX:XLF`, `AMEX:XLE`, `AMEX:XLV`, `AMEX:XLY`, `AMEX:XLP`, `AMEX:XLI`, `AMEX:XLB`, `AMEX:XLU`, `AMEX:XLRE`, `AMEX:XLC` | [DOC] S17 |
| Industry ETFs | `NASDAQ:SMH` (not `AMEX:SMH`), `NASDAQ:SOXX`, `AMEX:XBI`, `AMEX:KRE`, `AMEX:XHB`, `AMEX:XRT` | [DOC] S17 |
| Cash indices | `SP:SPX`, `NASDAQ:NDX`, `NASDAQ:IXIC`, `TVC:RUT`, `TVC:DJI`, `SP:SPXEW` (first bar 1990-01-02) | [DOC] S17, S18 |
| S&P 500 sector indices | `SP:S5INFT`, `SP:SPF`, `SP:SPN`, `SP:S5HLTH`, `SP:S5COND`, `SP:S5CONS`, `SP:S5INDU`, `SP:S5MATR`, `SP:S5UTIL`, `SP:S5REAS`, `SP:S5TELS` (`SP:S5INFT` first bar 2012-09-25) | [DOC] S17, S18 |
| Volatility products | `CBOE:VXX`, `CBOE:UVXY`, `CBOE:SVXY`, `CBOE:VIXY` (prefix is `CBOE`, not `AMEX`) | [DOC] S17 |
| Others | `AMEX:GLD`, `AMEX:USO`, `TVC:GOLD`, `TVC:USOIL`, `NASDAQ:IBIT`, `CME_MINI:ES1!` | [DOC] S17, S18 |

Not found: `CBOE:SPX`, `AMEX:SMH`, `AMEX:VXX`. [DOC] S17. Mapping `syminfo.sector` (TradingView's classification) to a sector ETF (GICS) needs a hand-made table; the two taxonomies differ ("Electronic Technology" for AAPL). [DOC] S6 for the example; the mapping need is inference.

### 11.7 FINRA short-sale volume

| Fact | Tag |
|---|---|
| Ticker format, from TradingView's own script: `str.format("FINRA:{0}_SHORT_VOLUME", syminfo.ticker(userSymbol))`; the value is the series' `close`, requested at `"1D"`. | [DOC] S16 (source code) |
| "On TradingView, Short Sale Volume data is accessible through tickers using special names. For example, NASDAQ:AAPL's Short Sale Volume data can be loaded on your chart via the FINRA:AAPL_SHORT_VOLUME ticker." | [DOC] S16 |
| Supported listing prefixes in that script: "BATS", "NASDAQ", "NYSE", "AMEX". | [DOC] S16 |
| `FINRA:AAPL_SHORT_VOLUME`, `FINRA:SPY_SHORT_VOLUME`: daily only (`has_intraday = false`), first bar 2018-08-01, last bar 2026-11-09. Also listed: TSLA, NVDA, MSFT, AMZN, META, QQQ, AMD. | [DOC] S17, S18 |
| Meaning: "aggregated volume by security for all short trades executed and reported to FINRA during normal market hours… Short Sale Volume is not consolidated with exchange data and excludes trading activity that is not publicly disseminated." | [DOC] S16 |
| "Short Interest data reported by FINRA is not yet available on our platform." (description first published 2022-02-10; script updated 2026-04-15). A directory search today for "SHORT_INTEREST" and "AAPL_SHORT_INTEREST" returned nothing. | [DOC] S16, S17 |
| A short-volume ratio needs a denominator. FINRA short volume covers off-exchange/FINRA-reported trades only, so dividing by the chart's consolidated `volume` understates the short share. Whether the `volume` field of the FINRA symbol holds FINRA total volume is not verified. | Inference; denominator not verified |
| Time of day the daily value is published is not documented; use the previous day's confirmed value. | Not verified |

## 12. Reference pattern (compiled)

Compiles with 0 errors and 0 warnings: [COMPILE] `t11_context_pack.pine`. It uses 11 of the 40 unique requests. Runtime behaviour was not tested. The block below is the request section of that file; the compiled file also contains the plots and an `alertcondition()` gated on `barstate.isconfirmed`, which a script needs in order to compile.

```pine
//@version=6
indicator("Context pack: confirmed-only requests (reference pattern)", overlay = false)

// Daily context is requested from "1D" only when the chart timeframe is <= 1D.
// On a weekly chart a "1D" request would be a LOWER-timeframe request, so use the chart TF.
bool   chartLeDaily = timeframe.in_seconds() <= timeframe.in_seconds("1D")
string ctxTf        = chartLeDaily ? "1D" : timeframe.period
bool   chartLtWeek  = timeframe.in_seconds() < timeframe.in_seconds("1W")

// 1) Market regime: last CONFIRMED context bar ([1] + lookahead_on = documented non-repainting form)
[spyC, spyMa200, spyRoc20] = request.security("AMEX:SPY", ctxTf, [close[1], ta.sma(close, 200)[1], ta.roc(close, 20)[1]], lookahead = barmerge.lookahead_on)
float vix    = request.security("CBOE:VIX",          ctxTf, close[1], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)
float vix3m  = request.security("CBOE:VIX3M",        ctxTf, close[1], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)
float pct50  = request.security("INDEX:S5FI",        ctxTf, close[1], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)
float pct200 = request.security("INDEX:S5TH",        ctxTf, close[1], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)
float hyOas  = request.security("FRED:BAMLH0A0HYM2", ctxTf, close[1], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)

// 2) Relative strength on the chart's own timeframe (same-timeframe request)
float spyTf  = request.security("AMEX:SPY", timeframe.period, close)
float rsLine = close / spyTf

// 3) Weekly trend of the chart symbol, confirmed (only meaningful below 1W)
[wkClose, wkMa30] = request.security(syminfo.tickerid, "1W", [close[1], ta.sma(close, 30)[1]], lookahead = barmerge.lookahead_on)
bool weeklyUp = chartLtWeek ? wkClose > wkMa30 : close > ta.sma(close, 30)

// 4) Earnings: values arrive on the report bar (gaps_on); next report date from the built-in
float epsAct = request.earnings(syminfo.tickerid, earnings.actual,   gaps = barmerge.gaps_on, ignore_invalid_symbol = true)
float epsEst = request.earnings(syminfo.tickerid, earnings.estimate, gaps = barmerge.gaps_on, ignore_invalid_symbol = true)
bool  earnBar       = not na(epsAct)
float surprisePct   = earnBar and not na(epsEst) and epsEst != 0 ? 100 * (epsAct - epsEst) / math.abs(epsEst) : na
int   barsSinceEarn = ta.barssince(earnBar)
float daysToNext    = na(earnings.future_time) ? na : (earnings.future_time - time_close) / 86400000.0

// 5) FINRA daily short-sale volume for the chart symbol (ticker format from TradingView's own script)
string svTicker = str.format("FINRA:{0}_SHORT_VOLUME", syminfo.ticker)
float  shortVol = request.security(svTicker, ctxTf, close[1], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)
```

Known weaknesses of this pattern, to settle on a chart before use:

| Weakness | Basis |
|---|---|
| With `ctxTf = "1D"` on a daily chart, every context value is one day old at the bar's close. Reading same-bar values is allowed by S4 for same-timeframe requests, but EOD-only series may not be published at 16:00 ET. | [DOC] S4; publication time not verified |
| `syminfo.tickerid` in the weekly request inherits chart modifiers (extended hours, adjustment). Pin with `ticker.new()` (section 10). | [DOC] S1 |
| On 1h/4h charts the `"1D"` values come from the EOD feed (no extended hours, different volume). | [DOC] S1 |
| `daysToNext` is valid on the last bar only and goes stale after the report date (section 6.3). | [DOC] S3 |
| `earnBar` timing for after-close reports is unresolved (section 6.2). | Not verified |

## 13. Compile log

Tool: `python3 /home/user/aquacentinela/swing-lab/tools/pine_compile.py <file>`; files in `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/pine_requests/pine/`. 13 compiler calls used of 15.

| # | File | What it checks | Result |
|---|---|---|---|
| 1 | `t1_security.pine` | `request.security` all parameters, tuple, UDT, loop with series symbol, request inside `if`, three spread strings, `request.security_lower_tf` all parameters and tuple, `timeframe.in_seconds/from_seconds`, `syminfo.main_tickerid`, `timeframe.main_period` | OK, 1 warning (CW10003: `ta.roc` inside the looped request) |
| 2 | `t2_corp.pine` | `request.earnings/dividends/splits` with every field constant and parameter; all seven `*.future_*` variables; `earnings.future_time` inside `request.security` | OK |
| 3 | `t3_fin.pine` | `request.financial` (FQ, FH, FY, TTM, D; 12 IDs), `request.economic`, `request.currency_rate`, `request.seed` with all parameters | OK (string IDs are not validated) |
| 4 | `t4_syminfo.pine` | 20 `simple` and 13 `series` `syminfo.*` variables with explicit qualifiers; three used inside `request.security` | OK |
| 5 | `t5_neg.pine` | Negative controls | 12 errors, all expected (listed below) |
| 6 | `t6_ticker.pine` | `ticker.new/modify/standard/inherit/heikinashi`, session, adjustment, backadjustment, settlement constants, `session.ismarket/ispremarket/ispostmarket` | OK |
| 7 | `t7_footprint_quandl.pine` | `request.footprint`, 9 `footprint.*` and 8 `volume_row.*` functions, HTF footprint form, `request.quandl` | OK, no deprecation warning |
| 8 | `t8_mtf_indicator.pine` | `indicator(timeframe = "1D", timeframe_gaps = false)`; lookahead_on without offset | OK, **no warning for the future-leak form** |
| 9 | `t9_neg2.pine` | Negative controls | 13 errors, all expected |
| 10 | `t10_dyn.pine` | `dynamic_requests = false` with a series string symbol (docs: compilation error) | **OK, 0 errors** |
| 11 | `t11_context_pack.pine` | Reference pattern of section 12 | OK |
| 12 | `t12_helper.pine` | Helper function with the expression passed as a parameter | OK |
| 13 | `t13_loopexpr.pine` | Loop-dependent request expression (docs: compilation error) | **OK, 0 errors** |

Negative-control errors returned by the compiler (confirming the names do not exist or the qualifier is `series`):

| Line tested | Compiler message |
|---|---|
| `simple float a = syminfo.target_price_average` | cannot accept values of the "series float" form |
| `simple int a = syminfo.recommendations_buy` | cannot accept values of the "series int" form |
| `simple int a = earnings.future_time` | cannot accept values of the "series int" form |
| `earnings.future_date`, `earnings.reported`, `earnings.revenue`, `earnings.surprise`, `earnings.future_estimate` | Undeclared identifier |
| `dividends.future_record_date`, `splits.future_date` | Undeclared identifier |
| `syminfo.short_interest`, `syminfo.market_cap`, `syminfo.market_cap_basic`, `syminfo.float`, `syminfo.beta` | Undeclared identifier |
| `request.short_interest`, `request.short_volume`, `request.options`, `request.news`, `request.calendar`, `request.screener`, `request.fundamental`, `request.security_higher_tf` | Could not find function or function reference |
| `request.splits(..., currency = ...)` | does not have an argument with the name "currency" |
| `request.financial(..., lookahead = ...)` | does not have an argument with the name "lookahead" |

## 14. Where sources conflict

| # | Topic | Source A | Source B | Reading |
|---|---|---|---|---|
| 1 | Series symbol with `dynamic_requests = false` | S1: "the "series" argument causes a compilation error" | S20 t10: compiles, 0 errors | The lint endpoint skips this check, or the docs are out of date. Not material: v6 default is dynamic. |
| 2 | Loop-dependent request expression | S1: "resulting in a compilation error" | S20 t13: compiles, 0 errors | Same. The compile tool cannot be trusted to catch request-logic errors. |
| 3 | Request limit | S3: "A single script can contain no more than 40 unique request.*() function calls." | S2, S1: 40, "or up to 64… Ultimate plan" | Both give 40 for Premium. |
| 4 | Economic symbol prefix | S3: "Use "ECONOMIC" as the exchange name… "ECONOMIC:USGDP"" | S17: directory lists `ECONOMICS:USGDP` | Use `request.economic()` instead of a literal symbol to avoid the question. |
| 5 | `request.currency_rate` repainting | S1: "ensures non-repainting results" | S3: "can cause indicator repainting" | Unresolved. Irrelevant for USD stocks. |
| 6 | `request.financial` periods | S1: FQ, FH, FY, TTM | S3: adds "D"; S7 and S10 confirm D for ETF fields | "D" is valid for ETF fields. |
| 7 | `EARNINGS_PER_SHARE` | Used in S1 and S10 example code with "TTM" | In neither ID table (only `_BASIC`, `_DILUTED`) | Use the listed IDs. |
| 8 | Financial ID lists | S1: about 222 IDs, includes `PEG_RATIO` | S10: about 271 IDs, lacks `PEG_RATIO` | Test each ID at runtime. |
| 9 | `syminfo.sector` when absent | S3: `na` | S6: "an empty string" | Check both. |
| 10 | `syminfo.type` values | S3: includes "spread", "economic", "fundamental", "crypto", "spot", "swap", "option", "commodity" | S6: includes "cfd", omits several | For US equities: "stock", "fund", "dr". |
| 11 | Intrabar ceiling | S1: "up to 200,000 intrabars" | S2: 100K for Premium | S2 is the plan-specific figure. |

## 15. Not verified today

| # | Item | What would settle it |
|---|---|---|
| 1 | Whether `request.financial()` history shows first-reported or restated values | Official statement, or comparing a known restatement on a chart |
| 2 | Exact historical bar of a `request.earnings()` value for after-close reports, and whether realtime matches history | Chart test on a known after-close reporter |
| 3 | Whether historical `earnings.estimate` is the pre-report consensus | Chart comparison with an archived consensus |
| 4 | Which bar carries `request.dividends()` values | Chart test |
| 5 | Whether `syminfo.target_price_*` and `syminfo.recommendations_*` hold past values on past bars | Plot them on a chart |
| 6 | Whether `earnings.future_*` refresh inside a long-running server-side alert, and whether they work for another symbol through `request.security()` | Live alert test |
| 7 | All runtime behaviour: the 40-request error, 127-tuple counting inside loops, intrabar coverage, footprint availability | Chart tests; the compiler checks none of it |
| 8 | Validity of each `financial_id` string, including `EARNINGS_PER_SHARE`, and which period `EARNINGS_ESTIMATE` / `SALES_ESTIMATES` refer to | Chart test per ID |
| 9 | Time of day at which Barchart `INDEX:*` breadth, `FRED:*` and `FINRA:*_SHORT_VOLUME` daily values are published | Observe after a close |
| 10 | Whether the one-session staleness seen in `USI:UVOL`, `USI:VOLD`, `USI:UVOLQ`, `USI:TICKQ`, `INDEX:ADVN` occurs on a Premium account | Check on the account |
| 11 | Data delay of CBOE and USI indices on Premium without extra data subscriptions | Account data-subscription page |
| 12 | What the OHLC of intraday put/call series (`USI:PCC` etc.) represents | Chart inspection |
| 13 | Whether the `volume` field of `FINRA:*_SHORT_VOLUME` is FINRA total volume | Chart inspection |
| 14 | `ECONOMIC:` versus `ECONOMICS:` prefix; release-date alignment and revision handling of `request.economic()` | Chart test |
| 15 | Whether TradingView offers short interest anywhere today: S16's sentence dates from 2022, and only two name patterns were searched | Help Center search for a short-interest product page |
| 16 | Semantics of a helper that passes the expression as a function parameter (t12) | Chart comparison with the inline form |
| 17 | Symbols marked "listed" without page data were confirmed to exist only; their history depth and freshness were not checked | Fetch their symbol pages |
