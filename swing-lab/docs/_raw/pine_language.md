# Pine Script: language version, release notes, hard limits

Research date: **2026-11-10**. Every URL below was accessed on 2026-11-10 unless stated otherwise.
Scope: what the current language can and cannot do, for an indicator author on a **Premium** plan who depends on alerts.

## 0. Evidence legend, sources, method

| Tag | Meaning |
|---|---|
| [DOC] | Read today in an official TradingView page (User Manual, Reference Manual, pricing page, Help Center) |
| [COMPILE] | Confirmed today by running `tools/pine_compile.py` (TradingView `translate_light` endpoint) |
| [SECONDARY] | Third-party page |
| [MEMORY] | Recalled from training, NOT verified today |

| Short name | URL |
|---|---|
| RN (Release notes) | https://www.tradingview.com/pine-script-docs/release-notes/ |
| LIM (Limitations) | https://www.tradingview.com/pine-script-docs/writing/limitations/ |
| MIG6 (v5 to v6 migration guide) | https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/ |
| DECL (Declaration statements) | https://www.tradingview.com/pine-script-docs/language/declaration-statements/ |
| LIB (Libraries) | https://www.tradingview.com/pine-script-docs/concepts/libraries/ |
| PUB (Publishing scripts) | https://www.tradingview.com/pine-script-docs/writing/publishing/ |
| EXEC (Execution model) | https://www.tradingview.com/pine-script-docs/language/execution-model/ |
| TYPES (Type system) | https://www.tradingview.com/pine-script-docs/language/type-system/ |
| COND (Conditional structures) | https://www.tradingview.com/pine-script-docs/language/conditional-structures/ |
| OTF (Other timeframes and data) | https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ |
| STR (Strings) | https://www.tradingview.com/pine-script-docs/concepts/strings/ |
| ARR / MAT / MAP | https://www.tradingview.com/pine-script-docs/language/arrays/ , .../language/matrices/ , .../language/maps/ |
| TF (Timeframes) | https://www.tradingview.com/pine-script-docs/concepts/timeframes/ |
| DBG (Debugging) | https://www.tradingview.com/pine-script-docs/writing/debugging/ |
| L&B (Lines and boxes) | https://www.tradingview.com/pine-script-docs/visuals/lines-and-boxes/ |
| ERR (Errors overview) | https://www.tradingview.com/pine-script-docs/errors/overview/ (plus `/errors/CE10101/`, `/errors/CE10117/`, `/errors/CW10003/`, `/errors/CW10026/`, `/errors/RE10139/`, `/errors/RE10143/`) |
| FAQ-A / FAQ-I | https://www.tradingview.com/pine-script-docs/faq/alerts/ , https://www.tradingview.com/pine-script-docs/faq/indicators/ |
| REF (Reference Manual v6) | https://www.tradingview.com/pine-script-reference/v6/ (JavaScript app, rendered with Playwright; anchors such as `#fun_indicator`, `#fun_max_bars_back`, `#kw_once`, `#kw_import`, `#fun_library`, `#fun_request.security`, `#fun_request.footprint`, `#fun_time`, `#fun_ta.ema`) |
| PRICE (Pricing, "Compare plans") | https://www.tradingview.com/pricing/ (rendered with Playwright) |
| HC-MTF (Help Center) | https://www.tradingview.com/support/solutions/43000591555-leveraging-multi-timeframe-analysis/ |

Method notes:
- The User Manual pages are static HTML. The served `release-notes` file carried a gzip header reading "last modified: Mon Nov 9 21:23:28 2026", so the manual was regenerated the day before this research. [DOC]
- The Reference Manual page was rendered headlessly and 945 entries were extracted (475 functions, 241 constants, 162 variables, 21 operators, 20 types, 16 keywords, 10 annotations). [DOC]
- Compiler budget: 15 of 15 calls used. Files are in `/tmp/claude-0/-home-user/94f008b0-b600-564c-8470-7cce270163c3/scratchpad/pine-language/compile/`. Full log in section 9.

---

## 1. Current language version

| Fact | Evidence |
|---|---|
| The current version is **Pine Script v6** (`//@version=6`). The manual's landing page is titled "Welcome to Pine Script® v6" and the Reference Manual lives under `/pine-script-reference/v6/`. | [DOC] https://www.tradingview.com/pine-script-docs/welcome/ ; REF |
| v6 was released in November 2024: "Pine Script has graduated to v6! Starting today, future Pine updates will apply exclusively to this version." | [DOC] RN, "November 2024" |
| No v7 is mentioned anywhere in RN (latest entry: "October 2026"; there is no "November 2026" entry yet) or in the migration guides (latest guide: "To Pine Script® version 6"). | [DOC] RN ; https://www.tradingview.com/pine-script-docs/migration-guides/overview/ |
| A script with no `//@version=` annotation is compiled as v1: "The version should always be specified. Otherwise, for compatibility reasons, the script will be compiled using Pine Script® v1". | [DOC] REF `#an_@version=` |
| Consequence: every feature in section 2 exists only in v6. Write all project scripts as `//@version=6`. | [DOC] RN (same quote as row 2) |

---

## 2. Release notes, 2025-01 through 2026-10 (everything that changes what an indicator can do)

Source for every row: RN, under the month heading shown. All rows [DOC]; the last column says what was additionally confirmed by the compiler.
Months with **no entry** in RN: January 2025, February 2026, March 2026, May 2026, June 2026, November 2026 (as of today). [DOC]

| Month | Change (quoted or tightly paraphrased from RN) | Why it matters for our indicators | Compiler check |
|---|---|---|---|
| Feb 2025 | "We’ve removed the scope count limit. Previously, any script’s total number of scopes ... was limited to 550. Now, scripts can contain an indefinite number of local scopes" | Large multi-module indicators no longer hit the 550-scope wall | not tested |
| Feb 2025 | New variables `bid`, `ask`: "These variables are only available on the `"1T"` timeframe. On other timeframes, their values are `na`." | Useless on 1h/4h/D/W charts (always `na`) | [COMPILE] identifiers exist (test A) |
| Mar 2025 | `box.set_xloc()` added | Minor drawing convenience | [COMPILE] test A |
| Mar 2025 | `for` loops: "a for loop evaluates the `to_num` boundary dynamically, before every iteration" | Behaviour change. `for i = 0 to arr.size() - 1` re-evaluates the bound each pass; mutating the array inside the loop changes the iteration count | not tested (runtime behaviour) |
| Apr 2025 | `"PercentageLTP"` box-size style for `ticker.renko()`, `ticker.pointfigure()`, `ticker.kagi()` | Not relevant (non-standard charts) | not tested |
| May 2025 | `time_close` / `time_close()` now keep closing times of elapsed realtime bars on tick and price-based charts | Not relevant to time-based stock charts | not tested |
| Jun 2025 | "Libraries can now export user-defined constant variables. Exported variables must be of the “int”, “float”, “bool”, “color”, or “string” type and include the const keyword" | Shared parameter constants across a family of indicators | [COMPILE] test J |
| Jul 2025 | "All `input*()` functions feature a new parameter: `active`" (greys out an input based on other inputs) | Cleaner settings panels | [COMPILE] test A |
| Jul 2025 | New `syminfo.current_contract` (continuous futures only) | Not relevant to stocks | [COMPILE] test A |
| Aug 2025 | "Previously, a “string” value could not exceed 4,096 characters. Now, strings can contain up to 40,960 encoded characters." | Longer alert/JSON payloads and table text can be built in one string (alert delivery limits are a separate matter, not checked here) | not tested |
| Aug 2025 | Pine Editor moved to the side panel; word wrap (`Alt+Z`) | Editor only | n/a |
| Sep 2025 | `plot()` gets `linestyle`: `plot.linestyle_solid`, `plot.linestyle_dashed`, `plot.linestyle_dotted` | Dashed/dotted levels without drawing objects (plots are not capped at 500 like lines) | [COMPILE] test A |
| Oct 2025 | `time()` / `time_close()` get `timeframe_bars_back` | Timestamp of the N-th previous weekly/monthly bar without `request.security()` | [COMPILE] test A |
| Nov 2025 | `syminfo.isin`: "holds a string containing the 12-character International Securities Identification Number (ISIN) ... or an empty string if no ISIN is available" | Identify the same stock across exchanges | [COMPILE] test A |
| Dec 2025 | Line wrapping: code inside parentheses may be indented by any amount, including multiples of four | Formatting only; older "not a multiple of 4" rule still applies outside parentheses | used in tests |
| Jan 2026 | `request.footprint()`, types `footprint` and `volume_row`, namespaces `footprint.*` and `volume_row.*`. "Programmers who have a Premium or Ultimate plan can use these features" | **New data**: per-bar buy volume, sell volume, delta, POC, value area, row imbalances. Available on our Premium plan. Limits: section 3, row R6 | [COMPILE] test N (all 9 `footprint.*` and 8 `volume_row.*` functions listed in REF compile) |
| Apr 2026 | Multiline strings `"""..."""` / `'''...'''` | Readable alert message templates | [COMPILE] test A |
| Apr 2026 | `array.sort()`, `array.sort_indices()`, `matrix.sort()` can sort collections of UDT objects via `sort_field` | Ranking tables of objects | [COMPILE] test A |
| Apr 2026 | Editor setting "Use word wrap by default" | Editor only | n/a |
| Jul 2026 | `strategy()` gets `calc_on_every_history_tick`: "This new feature is available on standard charts for users with Premium and Ultimate plans." Strategy report/properties UI reworked ("Bar detalization" menu replaces "Using bar magnifier", leverage inputs replace margin inputs, etc.) | Strategies only. Relevant if a strategy twin is used to sanity-check an indicator on TradingView | not tested |
| Jul 2026 | Editor auto-inserts parentheses when a line is broken | Editor only | n/a |
| Aug 2026 | Pine Screener: "scan the symbols of any index ... scan up to 4,000 of its symbols"; any personal, invite-only, purchased, built-in or community indicator can be used; "the Pine Screener supports only indicator scripts that contain at least one `plot*()` or alertcondition() call" | A way to scan a universe with our own indicator, provided it exposes `plot()`/`alertcondition()` outputs | n/a |
| Aug 2026 | New keyword `once`: "defines a conditional structure that executes a block of code when its condition evaluates to `true`. After the local block executes for the first time on a closed bar, it does not execute again on any subsequent bars" | One-shot initialisation or "first time ever" events. Trap: on an open realtime bar it can run on several ticks (rollback), so `alert()` inside `once` can fire repeatedly unless the condition includes `barstate.isconfirmed` (COND, "`once` on the realtime bar") | [COMPILE] test A |
| Aug 2026 | `array.binary_search*()` works on UDT arrays with `sort_field` | The `val` argument is the numeric field value, not an object | [COMPILE] tests A run 1 (error when an object is passed) and run 2 (OK) |
| Sep 2026 | Tables can be moved to the chart's bottom panel ("Move tables to bottom"); there they stack vertically, never truncate text, and text can be selected/copied | Good fit for a "quick look" dashboard table | n/a (UI) |
| Sep 2026 | Free indentation inside square brackets | Formatting only | n/a |
| Oct 2026 | Inline inputs align automatically if only the first input on a line has a title; otherwise compiler warning CW10026 | Settings panel layout; a new warning to expect | not tested |

Deprecations and withdrawals visible today:

| Item | Wording | Evidence |
|---|---|---|
| `request.quandl()` | "This function has been deprecated due to the API change from NASDAQ Data Link. Requests for "QUANDL" symbols are no longer valid and requests for them return a runtime error." | [DOC] REF `#fun_request.quandl` |
| `request.seed()` | "The creation of new Pine Seeds repositories is suspended; only existing repositories are currently supported." | [DOC] REF `#fun_request.seed` |
| Formal deprecations in the 2025-2026 release notes | None are listed. The only behaviour changes are the `for` loop boundary (Mar 2025) and the strategy UI rework (Jul 2026). | [DOC] RN |

v6 launch items (Nov 2024) that define today's language are in section 4.

---

## 3. Hard limits

"Premium value" is the value that applies to our plan. Quotes are verbatim from the page named.

### 3.1 Time and size

| # | Limit | Premium value | Exact wording | Source | Tag |
|---|---|---|---|---|---|
| T1 | Total script execution time on a dataset | **40 seconds** | LIM: "The time allotted for the script to execute on all bars of a dataset varies with account types. See the “Compare plans” section of the pricing page for details." PRICE row "Time limit for making calculations": "20 sec / 40 sec / 40 sec / 40 sec / 100 sec" for the columns Basic / Essential / Plus / Premium / Ultimate | LIM ; PRICE | [DOC] |
| T2 | Loop time per bar | 500 ms | "The execution time for any loop on any single bar is limited to 500 milliseconds. The outer loop of embedded loops counts as one loop, so it will time out first." | LIM | [DOC] |
| T3 | Compilation time | 2 minutes | "A two-minute limit is imposed on compilation time ... When a compile exceeds the two-minute limit, a warning is issued. ... after three consecutive warnings a one-hour ban on compilation attempts is enforced." | LIM | [DOC] |
| T4 | Compiled script size | 100,256 tokens per script | "The IL form of each indicator, strategy, and library script can contain a maximum of 100,256 tokens." Size is measured on the optimised intermediate language, not on characters or lines; unused code is discarded first. | LIM ; ERR CE10117 | [DOC] |
| T5 | Total size of imported libraries | 1,000,000 tokens | "the total size of all libraries that a script imports cannot exceed 1 million tokens" | LIM | [DOC] |
| T6 | Compilation request size | 5 MB | "The size of the compilation request for a script cannot exceed 5MB. ... This information comprises the script itself and any libraries the script imports." Includes unused code. | LIM | [DOC] |
| T7 | Variables per scope | 1,000 | "Scripts can contain up to 1,000 variables in each of its scopes." | LIM | [DOC] |
| T8 | Number of local scopes | no limit | Removed Feb 2025 (was 550); quote in section 2 | RN | [DOC] |
| T9 | Memory | not published | Error "Memory limits exceeded" (RE10139) exists; no numeric limit is given. LIM: "There are currently no means for Pine Script programmers to get data on the resources consumed by their scripts." Main causes listed: returning collections/objects from `request.*()` on every bar, oversized history buffers, careless `max_bars_back`. | LIM ; ERR RE10139 | [DOC] |
| T10 | String length | 40,960 characters | "Pine Script® strings are immutable values containing sequences of up to 40,960 encoded characters" | STR | [DOC] |
| T11 | Number of inputs | **no documented limit found** | Only indirect mention: "Reduce the number of script inputs (script inputs are counted separately)" as a way to shrink the compilation request | LIM ; Inputs page https://www.tradingview.com/pine-script-docs/concepts/inputs/ | [DOC] (absence of a stated limit) |
| T12 | External inputs (`input.source()` fed by another script's plot) | 10 | "Scripts with an input of type input.source() can take a plot from another script (up to a maximum of ten) as an input." | FAQ-I | [DOC] |
| T13 | Pine Logs | 10,000 historical logs | "The Pine Logs pane can display the most recent 10,000 logs for historical bars." | DBG | [DOC] |

### 3.2 History and bars

| # | Limit | Premium value | Exact wording | Source | Tag |
|---|---|---|---|---|---|
| H1 | Bars back with `[]` | 5,000 for most series | "limited to a maximum of 5000 bars for most series. Some built-in series like open, high, low, close, and time have larger historical buffers that can reference up to 10,000 bars." | LIM | [DOC] |
| H2 | `max_bars_back` (parameter and function) | 0 to 5000 | DECL: "It accepts an “int” value from 0 to 5000". REF `max_bars_back()`: "The largest possible argument is 5000." Compiler: `CE10041 Invalid value "5001" for "max_bars_back" parameter of the "indicator()" function. It must be between 0 and 5000` and the same for the `num` parameter of `max_bars_back()` | DECL ; REF ; test G | [COMPILE] |
| H3 | Automatic buffer sizing | first 244 bars | "It analyzes all the historical references that occur while executing the script on the dataset’s first 244 bars, then sets the initial size of each buffer". If later historical bars need more, the script restarts with a bigger buffer. "It does not adjust any historical buffers during executions on new bars from the realtime data feed." | EXEC "Historical buffers" | [DOC] |
| H4 | Chart bars available | 20,000 | "20000 historical bars for the Premium plan." PRICE: "Historical bars available 5K / 10K / 10K / 20K / 40K" | LIM ; PRICE | [DOC] |
| H5 | Drawings into the past with `xloc.bar_index` | 10,000 bars | "Drawings using xloc.bar_index can be positioned a maximum of 10,000 bars in the past." | LIM | [DOC] |
| H6 | Drawings into the future with `xloc.bar_index` | 500 bars | "A maximum of 500 bars in the future can be referenced." | LIM | [DOC] |
| H7 | `time()` / `time_close()` forward offsets | -1 to -500 | "If the value is a negative number from -1 to -500, the function calculates the expected timestamp" | REF `#fun_time` | [DOC] |

Rough capacity check for our timeframes on Premium. This is my arithmetic on top of H4, not a TradingView statement, and the bars-per-session figures are [MEMORY] (a 6.5-hour regular US session gives 7 one-hour bars and 2 four-hour bars on TradingView; not verified today): 20,000 one-hour bars is roughly 2,850 sessions (about 11 years), 20,000 four-hour bars is about 39 years, and daily and weekly histories are limited by the data, not by the bar cap. Extended-hours charts have more bars per day and therefore fewer years.

### 3.3 Visual outputs

| # | Limit | Value | Exact wording | Source | Tag |
|---|---|---|---|---|---|
| V1 | Plot count | 64 | "A maximum of 64 plot counts are allowed per script." Counted: `plot()`, `plotarrow()`, `plotbar()`, `plotcandle()`, `plotchar()`, `plotshape()`, `alertcondition()`, `bgcolor()`, `barcolor()`, and `fill()` "but only if its `color` is of the series form". Not counted: `hline()`, `line.new()`, `label.new()`, `table.new()`, `box.new()`. "One function call can generate up to seven plot counts" (a `plot()` with a series colour costs 2; `plotshape` with series colour and text colour costs 3). | LIM | [DOC] |
| V1b | When the plot limit is enforced | not at lint time | LIM says "the runtime error message will display the plot count". A script with 65 plot counts (63 `plot()` + 1 `alertcondition()` + 1 `bgcolor()`) passed `pine_compile.py` with 0 errors. | test C | [COMPILE] |
| V2 | `alert()` calls | do not use plot counts | "In contrast to alertcondition(), calls to this function do not count toward a script's plot count." Also: "all calls to the alert() function count as one alert" against the plan quota, while "Each active alert condition counts toward the total number of alerts the user’s plan allows." | REF `#fun_alert` ; FAQ-A | [DOC] |
| V3 | Lines, labels, boxes | default about 50, max 500 each | "scripts will only show the last 50 lines, boxes, polylines, and labels on the chart by default" ; "The maximum number of line, box, and label IDs is 500, and the maximum number of polyline IDs is 100." DECL adds that the limits "are approximate". A drawing whose coordinate is `na` still counts. | LIM ; DECL | [DOC] |
| V4 | Polylines | max 100, each up to 10,000 points | "These powerful drawings can connect up to 10,000 points" | L&B | [DOC] |
| V5 | Tables | 9 | "Scripts can display a maximum of nine tables on the chart, one for each of the possible locations ... When attempting to place two tables in the same location, only the newest instance will show on the chart." | LIM | [DOC] |
| V6 | Table rows/columns/cells | no limit found in the manual today | I looked in the Tables page and LIM and found none | https://www.tradingview.com/pine-script-docs/visuals/tables/ | [DOC] (absence) |
| V7 | `precision` | 0 to 16 | "The value must be an integer from 0 to 16." | REF `#fun_indicator` | [DOC] |

### 3.4 Data requests

| # | Limit | Premium value | Exact wording | Source | Tag |
|---|---|---|---|---|---|
| R1 | Unique `request.*()` calls | **40** | "A script can use up to 40 unique calls to the functions in the `request.*()` namespace, or up to 64 unique calls if the user has the Ultimate plan." Applies to `request.security()`, `request.security_lower_tf()`, `request.currency_rate()`, `request.dividends()`, `request.splits()`, `request.earnings()`, `request.quandl()`, `request.financial()`, `request.economic()`, `request.seed()`. Identical repeated calls usually count once. | LIM | [DOC] |
| R2 | Requests inside imported library functions | always counted | "when a script imports library functions containing `request.*()` calls within their scopes, those calls do count toward this limit, even if the script already calls the same `request.*()` function with the same arguments in its main scope." | LIM | [DOC] |
| R3 | Tuple elements returned by all requests together | 127 | "All the `request.*()` function calls in a script taken together cannot return more than 127 tuple elements." Workaround given: return a user-defined type object instead of a tuple. | LIM | [DOC] |
| R4 | Lower-timeframe bars (intrabars) | 100,000 | "All non-professional plans – Basic, Essential, Plus, and Premium – can request up to 100K bars of data. Expert plans have access to 125K bars of data. Ultimate plans can request 200K lower-timeframe bars." | LIM | [DOC] |
| R5 | Dynamic requests on realtime bars | no new datasets | "scripts must request all required datasets while executing on historical bars. All `request.*()` calls on realtime bars can retrieve data from the datasets that the script previously accessed on historical bars, but they cannot request a new context or evaluate a new expression." | OTF "Dynamic requests" | [DOC] |
| R6 | `request.footprint()` | 1 call per script; Premium or Ultimate only | LIM: "A script can execute only one unique call to this function. Additionally, only users who have a Premium or Ultimate plan can use scripts that call it." OTF: "If a script contains multiple calls to this function, it raises a runtime error." REF: "A single script cannot include more than one request.footprint() call." Returns `na` when no footprint exists for a bar. On 1D and above "a footprint’s total volume might differ significantly from the value of the volume variable" because end-of-day feeds include block and OTC trades that intraday feeds do not. | LIM ; OTF ; REF | [DOC] |
| R7 | `calc_bars_count` on two requests for the same expression and context | first call wins | "if a script calls request.security("AAPL", "", close, calc_bars_count = 3) after it calls request.security("AAPL", "", close, calc_bars_count = 5), the second call also uses five bars of historical data, not three." | REF `#fun_request.security` | [DOC] |

### 3.5 Collections

| # | Limit | Value | Exact wording | Source | Tag |
|---|---|---|---|---|---|
| C1 | Array, matrix | 100,000 elements | LIM: "Pine Script collections (arrays, matrices, and maps) can have a maximum of 100,000 elements." ARR: "The total number of elements in any array cannot exceed 100,000." | LIM ; ARR ; MAT | [DOC] |
| C2 | Map | 50,000 key-value pairs | "Each key-value pair in a map contains two elements, meaning maps can contain a maximum of 50,000 key-value pairs." | LIM ; MAP | [DOC] |
| C3 | Is 100,000 per collection or across all collections of a type? | **sources differ** | ARR says "in any array" (per array). DBG says "the maximum number of elements across all instances of each collection type is 100,000". Unresolved; design for the stricter reading (total across all arrays below 100,000). | ARR vs DBG | [DOC] |

### 3.6 Plan-level limits that constrain an alert-driven workflow (from the pricing page; alert mechanics are another researcher's topic)

| Item | Premium value | Wording on PRICE ("Compare plans", columns Basic / Essential / Plus / Premium / Ultimate) | Tag |
|---|---|---|---|
| Indicators per chart | 25 | "Indicators per chart 2 / 5 / 10 / 25 / 50" | [DOC] |
| Active technical alerts | 400 | Premium plan card: "400 technical alerts" | [DOC] |
| Active watchlist alerts | 2 | Premium plan card: "2 watchlist alerts" | [DOC] |
| Alert rate | halts above 15 in 3 minutes | FAQ-A: "If more than 15 alerts occur within three minutes, the system automatically halts further alerts." | [DOC] |
| Timeframe multipliers accepted in timeframe strings | minutes 1-1440, days 1-365, weeks 1-52, months 1-12 | TF: "There is no “hour” unit; “1H” is not valid. The correct format for one hour is “60”". So 1h = `"60"`, 4h = `"240"`, daily = `"1D"`, weekly = `"1W"`. | [DOC] |

Strategy-only limit, for completeness: "A script can place a maximum of 9000 orders when backtesting strategies. Once it reaches that limit, the earlier orders are trimmed ... When using Deep Backtesting, the order limit is 1,000,000." (LIM) [DOC]

---

## 4. v6 behaviour and type-system changes that commonly break code

Source for the "Rule" column: MIG6 unless another page is named. All rules are [DOC]; the "Compiler" column records what `pine_compile.py` did today.

| # | Rule in v6 | Typical failure | Safe pattern | Compiler today |
|---|---|---|---|---|
| B1 | "Values of the “bool” type are now strictly `true` or `false`. They are never na in v6." `na()`, `nz()`, `fixnan()` no longer accept bool. An `if`/`switch` returning bool with no matching branch returns `false`; `boolVar[1]` on the first bar is `false`. (RN Nov 2024; TYPES "bool") | `bool x = na`; three-state flags; `na(cond)` | Use an `int` (-1/0/1) or an enum for three states | [COMPILE] `bool b1 = na` gives `CE10173 Cannot assign a value of the "simple na" type to the "b1" variable. The variable is declared with the "const bool" type.` (test B). `na(b2)` gives `CE10123 ... An argument of "series bool" type was used but a "simple float" is expected.` (test R) |
| B2 | "“int” and “float” values are no longer implicitly cast to “bool”." | `if ta.change(x)`, `cond = volume ? ... : ...`, `if pivot` | `bool(x)`, `x != 0`, `not na(x)` | [COMPILE] `bar_index ? 1.0 : 0.0` gives `CE10123 Cannot call "operator ?:" with argument "expr0"="bar_index". An argument of "series int" type was used but a "const bool" is expected.` (test R) |
| B3 | Comparisons with `na`: "The ==, != operators, and all other comparison operators always return `false` if at least one of the operands is a variable with an na value." Using literal `na` as an operand is a compile error. (TYPES "`na` value") | `x == na`; `close > sma` silently `false` during warm-up | Test with `na(x)`; guard warm-up bars explicitly | not tested |
| B4 | Lazy `and` / `or`: "If the first expression of an or operation is `true`, or the first expression of an and operation is `false`, the script does not evaluate the second expression". (RN Nov 2024) MIG6 shows `close > open and ta.rsi(close, 14) > 50` producing wrong RSI values because `ta.rsi()` is skipped on some bars. | Any `ta.*` or history-dependent call on the right side of `and`/`or`, in a ternary branch, or in an `if`/loop body | Compute every history-dependent value once per bar in the global scope, then combine the stored variables | [COMPILE] warning `CW10002 The "ta.rsi()" call inside the conditional expression might not execute on every bar, which can cause inconsistent calculations...` (test A). The manual documents the sibling warning CW10003 for calls inside `if`/loops. Treat both warnings as errors. |
| B5 | "Dividing two integer “const” values can return a fractional value." `5 / 2` is 2.5 in v6 (2 in v5). | Index or length arithmetic such as `len / 2` | `int(a / b)`, `math.floor()`, `math.round()` | [COMPILE] `int i1 = 5 / 2` compiles with no error or warning (test C). The value held by `i1` at run time was **not** checked. Do not rely on it; always wrap integer division explicitly. |
| B6 | Dynamic requests are on by default: "the `dynamic_requests` parameter of the indicator(), strategy(), and library() functions is `true` by default." Requests may sit in loops/`if` blocks and take "series string" symbol/timeframe. "There are minor differences between dynamic and non-dynamic requests in some obscure cases, such as when using the result of one request.security() call in the `expression` argument of another call." | Ported v5 code giving slightly different values; nested requests | Add `dynamic_requests = false` to reproduce v5 behaviour when all requests are global and static | [COMPILE] request in a `for ... in` loop with series symbol and in an `if` block compiles (test A) |
| B7 | "The history-referencing operator [] can no longer reference the history of literal values or fields of user-defined types directly." | `obj.field[1]`, `true[1]` | `(obj[1]).field`, or copy the field into a variable and index that | not tested separately |
| B8 | "Some mutable variables are no longer erroneously marked as “const”" - MIG6 says a mutated variable is "series" and "raises a compilation error if passed in place of the expected “simple int”". | Passing a changing length to `ta.ema()`, `ta.rsi()`, `ta.atr()`, `ta.rma()`, `ta.macd()` (their length parameters are "simple int" in REF), while `ta.sma()`, `ta.highest()`, `ta.stdev()`, `ta.linreg()`, `ta.correlation()`, `ta.percentrank()`, `ta.wma()`, `ta.bb()` take "series int" | Lengths for "simple" parameters must come from inputs or constants | [COMPILE] **partly contradicts the manual**: see section 8, conflict K1 |
| B9 | "The value of timeframe.period now always includes a multiplier (e.g., `"1D"` instead of `"D"`)." | `timeframe.period == "D"` is never true | Compare with `"1D"`, `"1W"`, `"1M"`, or use `timeframe.isdaily` etc. | not tested (runtime) |
| B10 | "The `offset` parameter of plot() and other functions no longer accepts “series” values." | `plot(x, offset = someSeries)` | Constant or input offset | not tested |
| B11 | "na values are no longer allowed in place of built-in constants of unique types." A `switch` returning e.g. a plot style needs a default branch; an `if` needs an `else`. | `style = cond ? plot.style_line : na` | Always return a real constant | not tested |
| B12 | "Function calls can no longer include more than one argument for the same parameter." | Duplicate named arguments | Remove duplicates | not tested |
| B13 | "The `transp` parameter is removed from all applicable functions." | `plot(x, transp = 80)` | `color.new(c, 80)` | not tested |
| B14 | `linewidth` must be at least 1 for `plot()` and `hline()`. | `linewidth = 0` | Use 1 or more | not tested |
| B15 | "Some `array.*()` functions now accept negative index arguments" (`array.get/set/insert/remove`; -1 is the last element). | An accidental negative index no longer raises an error; it reads from the end | Validate index arithmetic | not tested (runtime) |
| B16 | "The for loop statement now evaluates its end boundary dynamically before every iteration." | `for i = 0 to data.queue(x) - 1` loops forever | Store the bound in a variable before the loop | not tested (runtime) |
| B17 | Colour constants changed (`color.red` #FF5252 to #F23645, `color.teal` #00897B to #089981, `color.yellow` #FFEB3B to #FDD835); default label text colour is white. | Cosmetic differences | Use explicit hex colours | not tested |
| B18 | Strategies: `when` removed; default `margin_long`/`margin_short` = 100; orders above 9000 are trimmed; `strategy.exit()` uses whichever of the relative/absolute level is hit first. | Strategy twins of an indicator behave differently from v5 | See MIG6 "Strategies" | not tested |
| B19 | History-dependent functions must run on every bar. ERR CW10003: a call that executes only on some bars "builds a series ... for only those bars"; `source[1]` then means "the last bar on which the call executed", not the previous bar. | `ta.sma()` inside `if`; user function using `[]` called conditionally | Global-scope call, conditional use of the result | covered by B4 warning |
| B20 | Realtime history buffers: a `[]` offset larger than anything used on historical bars fails on the first realtime tick; drawings anchored in the past on realtime bars need `max_bars_back(time, n)`. (ERR RE10143) | Script loads fine and dies when the market opens; alerts stop | Reference the largest offset on the first bar, or call `max_bars_back(series, n)` for the specific series | not testable by lint |

History-referencing rules worth restating for a no-repaint design:

| Rule | Evidence |
|---|---|
| `[]` accepts a variable, expression or function call; a float offset is rounded down. | [DOC] REF `#op_[]` |
| Data is committed to history only on closed bars: "After each execution on a confirmed bar, Pine’s runtime system commits (saves) data for a script’s variables and expressions on that bar". | [DOC] ERR RE10143 |
| With `calc_bars_count` set, the first executed bar is `bar_index` 0 and "[] operations cannot retrieve data from bars before the first bar determined by the `calc_bars_count` argument." | [DOC] DECL |

---

## 5. Libraries

| Question | Answer | Evidence |
|---|---|---|
| Can an unpublished library be imported? | **No.** "Before a script can import a library, the author must publish the library." The manual's own example says: "This script is an unpublished example library. Other scripts cannot import it, because it is not published." REF `import`: "A library must be published (privately or publicly) before it can be imported." | [DOC] LIB ; REF `#kw_import` |
| What does the compiler say for a path that is not published? | `The user 'zzqqnouser12345' does not have a published library titled 'NoSuchLibraryQq'` | [COMPILE] test H |
| Can a **privately published** library be imported by our own unpublished indicator? | **Yes.** "Library publications can be public or private, but they are always open-source." "Private scripts and personal scripts saved in the Pine Editor can also import public or private libraries." | [DOC] LIB "House Rules" |
| Who can see a private library? | "private scripts are accessible only via their URLs"; "Other users cannot see the script widget, and they cannot view the script page without having access to its URL." The source is open to anyone who has the URL. Private publications can always be edited or deleted. The privacy type cannot be changed after publishing. | [DOC] PUB "Privacy types" |
| Which scripts may import which libraries? | "Public open-source scripts can import only public libraries. Public protected and invite-only scripts can import public or private libraries." | [DOC] LIB |
| Versioning | `import <username>/<libraryName>/<libraryVersion> [as <alias>]`. "The version number is required. Scripts do not automatically use the latest version of a library". Every library update is a new published version, and each importing script must be edited to pick it up. | [DOC] LIB |
| What can be exported? | Functions, methods, user-defined types, enums, and (since Jun 2025) `const` variables of type int/float/bool/color/string. | [DOC] LIB ; [COMPILE] test J |
| Restrictions on exported functions | Every parameter needs an explicit type; parameters cannot be `const`; an exported function "cannot return values qualified as “const” or “input”"; the body "cannot depend on inputs or on global objects of reference types". | [DOC] LIB |
| `request.*()` inside exported functions | Allowed when the library's `dynamic_requests` is `true` (default), but "the `expression` argument of each request cannot depend on the exported function’s parameters." These requests always count toward the 40-request limit (row R2). | [DOC] LIB ; LIM ; [COMPILE] test J |
| Alerts from libraries | "A library can export functions and methods that contain alert() calls. However, users cannot create alerts directly from a library on the chart." The importing indicator creates the alert with "Any alert() function call". | [DOC] LIB ; [COMPILE] test J |
| Size limits | Each library is compiled separately and has its own 100,256-token limit; all imported libraries together must stay under 1 million tokens; "The entire library is sent for compilation, regardless of which functions are called" (counts toward the 5 MB request). | [DOC] LIM |
| Title rule | The `title` is the identifier: ASCII letters, digits, underscores only, not starting with a digit. | [DOC] LIB |
| Import rules | "The same version of a library can only be imported once. Aliases must be distinct for each imported library." | [DOC] REF `#kw_import` |
| Logs | "only personal scripts can create logs. Published scripts that import a library can call its logging functions, but they do not display the outputs". | [DOC] LIB |

Practical reading for this project (my judgement, not a TradingView statement): a private library is technically usable, but it adds a publish-and-bump-version step to every change and exposes the source to anyone holding the link. Keep each indicator self-contained unless a script approaches the 100,256-token limit.

---

## 6. `indicator()` parameters: `calc_bars_count`, `max_bars_back`, `timeframe`, `timeframe_gaps`

Current signature (REF `#fun_indicator` and DECL, identical): [DOC]

```
indicator(title, shorttitle, overlay, format, precision, scale, max_bars_back, timeframe, timeframe_gaps, explicit_plot_zorder, max_lines_count, max_labels_count, max_boxes_count, calc_bars_count, max_polylines_count, dynamic_requests, behind_chart) → void
```

"all parameters in each declaration statement require arguments qualified as “const”" (DECL), so none of them can come from an input. [DOC]

| Parameter | Type / default / range | Behaviour (quoted) | Traps for us | Evidence |
|---|---|---|---|---|
| `calc_bars_count` | const int, default 0, must be 0 or more | "If the value is 0 (default), the script executes on all the available bars in the dataset ... If the value is greater than 0, the script instead starts executions on the bar that is N bars before the latest available bar at loading time". "a positive `calc_bars_count` argument adds a “Calculation” group with a “Calculated bars” input" | The first executed bar becomes `bar_index` 0 and earlier history is invisible to `[]`. Recursive indicators (EMA, RSI, ATR, cumulative sums, anchored values) start from a different seed, so values near the start differ from a full-history run. Useful only to stay under the 40 s limit (T1). | [DOC] DECL ; REF. [COMPILE] accepts 0 and 5000 (tests A, C) |
| `calc_bars_count` on `request.security()` / `request.security_lower_tf()` / `request.seed()` | simple int, default = number of chart bars | "Determines the maximum number of recent historical bars that the function can request. ... The maximum number of bars that the function can attempt to retrieve depends on the intrabar limit of the user's plan." | See row R7 for the two-calls rule | [DOC] REF ; [COMPILE] test A |
| `max_bars_back` | const int, 0 to 5000, default automatic | "Sets the minimum length of all the script's historical buffers ... By default, Pine's runtime system automatically calculates appropriate historical buffer sizes for each series while loading a script. Manually setting buffer sizes is necessary only in rare cases where automatic size detection fails." | Applies to **every** series, so it costs memory: "increasing the size of every historical buffer in a script can negatively impact its runtime performance and memory consumption" (ERR RE10143). Prefer the function `max_bars_back(series, n)` on the specific series (`time` for drawings anchored in the past on realtime bars). It "cannot set the buffer sizes for some built-in variables that are derived from other built-ins (hl2, hlc3, etc.)". | [DOC] REF ; DECL ; ERR RE10143. [COMPILE] 5000 accepted (test A), 5001 rejected with CE10041 (test G) |
| `timeframe` | const string, default "" (chart timeframe) | "sets the script’s main timeframe. It enables the script to perform calculations on the data for a different timeframe than that of the chart without requiring `request.*()` function calls." Adds a "Timeframe" input in a "Calculation" group. | **Documented restriction: "An argument is allowed for this parameter only if the script does not use drawing types or alert() function calls."** (REF). DECL: "only if the script does not use drawing objects or alert() function calls, because scripts cannot evaluate outputs from such code on other datasets." L&B: "drawing objects will not work when using the `timeframe` parameter". So a script that uses `alert()`, labels, lines, boxes or tables cannot use `timeframe`. `alertcondition()` is not named in the restriction. | [DOC] REF ; DECL ; L&B. [COMPILE] `timeframe` + `alertcondition()` + plots compiles (test C). The lint endpoint also accepted `timeframe` + `alert()` (test D) and `timeframe` + `label.new()` (test E) with 0 errors: see conflict K3 in section 8 |
| `timeframe_gaps` | const bool, default **true**, allowed only together with `timeframe` | "If true, the indicator displays values only on the chart bars where new higher-timeframe data is available, and na on all other bars. If false, the indicator displays the last retrieved values on all chart bars where new data is not available." Adds a "Wait for timeframe closes" input. | Help Center: with the box checked, "higher timeframe values only come in ... when the higher timeframe completes. This has the advantage of avoiding repainting in real-time." Unchecked: "the indicator will produce non-repainting values on historical bars, but repainting values in real time." So `timeframe_gaps = false` repaints on the live bar. The user can change both settings in the dialog, so the script cannot guarantee the non-repainting mode. | [DOC] REF ; DECL ; HC-MTF. [COMPILE] `timeframe_gaps = false` and `= true` accepted (tests C, D, E) |
| `timeframe.main_period`, `syminfo.main_tickerid` | variables | "reference the ticker ID and timeframe from the script’s main context, even if the script uses them in the `expression` argument of a `request.*()` call." | Use these, not `timeframe.period`, when code may run inside a request | [DOC] RN Nov 2024 |
| `dynamic_requests` | const bool, default true | "the compiler analyzes the script to determine whether dynamic requests are necessary. If unnecessary for the script, the compiler automatically turns the feature off to optimize performance." (MIG6) | See B6 and conflict K2 | [DOC] MIG6 ; DECL |
| `max_lines_count`, `max_labels_count`, `max_boxes_count` | 1 to 500, default about 50 | "accept an “int” value from 1 to 500 ... The default for each parameter is 50." "The limits defined by these parameters are approximate." | For exact control, delete via `line.all`, `label.all`, `box.all` | [DOC] DECL ; [COMPILE] 500 accepted (test A) |
| `max_polylines_count` | 1 to 100, default about 50 | "accepts an “int” value from 1 to 100" | | [DOC] DECL ; [COMPILE] 100 accepted (test A) |
| `behind_chart` | const bool, default true | Added Oct 2024. "Controls whether all plots and drawings appear behind the chart display (if true) or in front of it (if false)." Only with `overlay = true`. | | [DOC] REF ; [COMPILE] test A |
| `overlay`, `scale`, `behind_chart` | | "Changes to this argument apply only after the user adds the script to the chart again." | Re-add the indicator after changing these | [DOC] REF |

Consequence for an alert-driven, no-repaint design (my reading of the rows above): because we need `alert()` messages and a table/labels, the `timeframe` parameter is not available to us. Higher-timeframe values must come from `request.security()` (bounded by R1: 40 unique requests), and the indicator should be written to run on the chart timeframe.

---

## 7. What `pine_compile.py` does and does not prove

The tool posts to `pine-facade.tradingview.com/pine-facade/translate_light`. The raw response for a clean script contains only `variables2`, `functions2`, `types`, `enums` (editor metadata); there is no compiled program, plot list or input list. [COMPILE] (call 7)

| Check | Caught by the tool today? | Evidence |
|---|---|---|
| Unknown identifiers, wrong argument types | Yes | [COMPILE] test A run 1 (CE10123) |
| Qualifier violations: series value into a "simple" or "const" parameter | Yes for values derived from series expressions, `:=` with a series right-hand side, or reassignment inside an `if` | [COMPILE] tests Q and R (CE10123) |
| Qualifier violation: global `var x = 0` followed by `x += 1`, passed to a "simple int" parameter | **No** | [COMPILE] test R line 5, test I1 |
| Range checks on declaration arguments (`max_bars_back`) | Yes | [COMPILE] test G (CE10041) |
| bool/na rules, int-as-bool | Yes | [COMPILE] tests B, R |
| Import of a library that is not published | Yes | [COMPILE] test H |
| History-dependent call in a lazily evaluated expression | Yes, as warning CW10002 | [COMPILE] test A |
| Plot count above 64 | **No** | [COMPILE] test C |
| `timeframe` argument together with `alert()` or drawings | **No** | [COMPILE] tests D, E |
| `dynamic_requests = false` with a request inside an `if` | **No** | [COMPILE] test K |
| Reporting of multiple errors | Sometimes only the first error is returned (test B: 1 of about 11), sometimes several (tests G, Q, R) | [COMPILE] |
| Token limit, 40 s execution limit, 500 ms loop limit, memory limit, request limit, history-buffer errors, realtime behaviour, repainting | Not checkable (they need the script on a chart) | tool docstring; LIM |

So "compiles OK" means "parses and type-checks". The three "No" rows and the last row must be verified on a real chart.

---

## 8. Conflicts between sources (both sides shown)

| # | Topic | Side A | Side B | Status |
|---|---|---|---|---|
| K1 | Mutated variable passed to a "simple" parameter | MIG6 [DOC]: for `var seriesLen = 0` / `seriesLen += 1` / `ta.ema(close, seriesLen)`, "In v6, `seriesLen` is correctly parsed as a “series int” type, and raises a compilation error" | [COMPILE] test R: exactly that code produced **no** error, while `len2 := close > open ? 5 : 10` and `len3 := len3 + 1` inside `if` were rejected with CE10123. Test I1 (`var int serLen = 1` / `serLen += 1`) also passed. | Unresolved. Either the full compiler rejects what the lint endpoint accepts, or the manual is out of date. Rule for us: never pass a variable that is reassigned anywhere to a "simple" parameter. |
| K2 | `dynamic_requests = false` with `request.security()` inside `if` | DECL [DOC]: "If we change the `dynamic_requests` argument to `false`, the request.security() call causes a compilation error" | [COMPILE] test K: 0 errors, 0 warnings | Unresolved; probably a later compiler stage. Not important if we keep the default `true`. |
| K3 | `timeframe` argument with `alert()` / drawings | REF [DOC]: "An argument is allowed for this parameter only if the script does not use drawing types or alert() function calls." | [COMPILE] tests D and E: 0 errors, 0 warnings | Unresolved where and how it is enforced. Treat the documented restriction as binding. |
| K4 | 64-plot limit | LIM [DOC]: exceeding it gives a "runtime error message" | [COMPILE] test C: 65 plot counts pass lint | Consistent with enforcement after lint. Count plots by hand. |
| K5 | Collection size scope | ARR [DOC]: "The total number of elements in any array cannot exceed 100,000." | DBG [DOC]: "the maximum number of elements across all instances of each collection type is 100,000" | Unresolved (row C3). |
| K6 | History depth of built-in price/time series | LIM [DOC]: OHLC and time "can reference up to 10,000 bars" | EXEC [DOC]: their buffers "can store data for more than 5000 bars" (no number); `max_bars_back()` accepts at most 5000 [COMPILE] | Not contradictory, but the 10,000 figure appears only in LIM. Do not design around offsets above 5000. |
| K7 | `request.footprint()` count | LIM [DOC]: "only one unique call" | REF [DOC]: "cannot include more than one request.footprint() call"; OTF [DOC]: multiple calls raise "a runtime error" | Wording differs ("unique" vs any). Use exactly one call. |
| K8 | An `indicator()` `symbol` argument | RN Nov 2024 [DOC]: main context is the chart "unless the script is an indicator() that includes `symbol` or `timeframe` arguments in its declaration statement" | REF and DECL [DOC]: the `indicator()` signature has no `symbol` parameter | Unresolved; looks like a slip in the release note. Not tested with the compiler. |
| K9 | Lazy-evaluation warning code | The CW10003 page (https://www.tradingview.com/pine-script-docs/errors/CW10003/) [DOC] documents that warning for calls inside conditional structures or loops and says "A similar warning also occurs if a ternary or and/or operation executes a history-dependent function call conditionally" | [COMPILE] the and/or case returned code CW10002 | Consistent (two sibling warnings); only CW10003 has a manual page. |

---

## 9. Compiler log (15 calls, all on 2026-11-10)

| # | File | Result | What it establishes |
|---|---|---|---|
| 1 | `a_features.pine` (first run) | FAIL: `CE10123 Cannot call "array.binary_search_leftmost" with argument "val"="call "Rec.new" (Rec)". An argument of "Rec" type was used but a "series int" is expected.` plus CW10002 | My test was wrong: `val` must be the field's numeric value |
| 2 | `a_features.pine` (fixed) | OK, 1 warning (CW10002 on `close > open and ta.rsi(close, 14) > 50`) | Exist and type-check in v6: `once`; multiline strings; `active` on inputs; `plot(..., linestyle = plot.linestyle_dashed)`; `time("1M", bars_back = 0, timeframe_bars_back = 1)`; `syminfo.isin`; `syminfo.current_contract`; `bid`; `ask`; `request.security()` in a `for ... in` loop with series symbol and `calc_bars_count = 500`; `request.security()` inside `if`; UDT `array.sort(sort_field = "price")` and `binary_search_leftmost(close, sort_field = "price")`; `box.set_xloc()`; integer text sizes; `text_formatting`; `log.info()`; `alertcondition()` and `alert(..., alert.freq_once_per_bar_close)` in one script; `indicator(max_labels_count = 500, max_lines_count = 500, max_boxes_count = 500, max_polylines_count = 100, max_bars_back = 5000, calc_bars_count = 0, dynamic_requests = true, behind_chart = false)` |
| 3 | `b_breaking.pine` | FAIL: only the first error returned: `CE10173 Cannot assign a value of the "simple na" type to the "b1" variable. The variable is declared with the "const bool" type.` | bool cannot be `na`; the endpoint may return only the first error |
| 4 | `c_decl.pine` | OK, 0 warnings | `timeframe = "1D", timeframe_gaps = false, max_bars_back = 5000, calc_bars_count = 5000` with `alertcondition()`, `bgcolor()` and 63 `plot()` calls (65 plot counts) and `int i1 = 5 / 2` all pass lint |
| 5 | `d_tf_alert.pine` | OK | `timeframe = "1D", timeframe_gaps = true` + `alert()` passes lint |
| 6 | `e_tf_label.pine` | OK | `timeframe = "1D"` + `label.new()` passes lint |
| 7 | raw response of #5 | `success: true`; result keys `variables2`, `functions2`, `types`, `enums` | The endpoint is a lint/type-check service |
| 8 | `g_mbb.pine` | FAIL: `CE10041 Invalid value "5001" for "max_bars_back" parameter of the "indicator()" function. It must be between 0 and 5000` and `CE10041 Invalid value "5001" for "num" parameter of the "max_bars_back()" function. It must be between 0 and 5000` | Range 0-5000 for both |
| 9 | `h_import.pine` | FAIL: `The user 'zzqqnouser12345' does not have a published library titled 'NoSuchLibraryQq'` | Unpublished library paths cannot be imported |
| 10 | `j_library.pine` | OK | `library()` with `export const float`, `export type`, `export enum`, exported function containing `request.security()`, exported method containing `alert()`, exported function with `series`/`simple` parameter qualifiers |
| 11 | `n_footprint.pine` | OK | `request.footprint(100, 70, 300)`; `footprint.delta/poc/total_volume/rows/get_row_by_price/buy_volume/sell_volume/vah/val`; `volume_row.up_price/down_price/total_volume/delta/buy_volume/sell_volume/has_buy_imbalance/has_sell_imbalance` |
| 12 | `k_nodyn.pine` | OK | Lint does not reject a request inside `if` with `dynamic_requests = false` (conflict K2) |
| 13 | `i1_series_len.pine` | OK | `var int serLen = 1` / `serLen += 1` / `ta.ema(close, serLen)` passes lint (conflict K1) |
| 14 | `q_qualifiers.pine` | FAIL: `CE10123 Cannot call "ta.ema" with argument "length"="dynLen". An argument of "series int" type was used but a "simple int" is expected.` and `CE10123 Cannot call "plot" with argument "title"=... An argument of "series string" type was used but a "const string" is expected.` | Qualifier checks are active in the endpoint |
| 15 | `r_mutable.pine` | FAIL with 4 errors at lines 8, 12, 13, 15 (all CE10123); line 5 (the manual's own `seriesLen` example) not flagged | Details in K1, B1, B2 |

---

## 10. Design rules that follow directly from the verified facts

| Rule | Basis |
|---|---|
| Write `//@version=6`; expect no v7 migration work for now. | Section 1 [DOC] |
| Budget per indicator on Premium: 40 s total execution, 500 ms per loop per bar, 64 plot counts, 40 unique requests, 127 request tuple elements, 100K intrabars, 20K chart bars, 5000 bars of `[]` history, 500 labels/lines/boxes, 100 polylines, 9 tables, 40,960-character strings, 100,256 tokens. | Section 3 [DOC] |
| Use `alert()` for rich messages (no plot cost, one alert slot for all calls); each `alertcondition()` costs one plot count and one alert slot when activated. | Rows V1, V2 [DOC] |
| Do not use `indicator(timeframe = ...)` in any script that calls `alert()` or draws labels/lines/boxes/tables. | Section 6 [DOC]; lint will not warn (K3) |
| Compute all `ta.*` and other history-dependent values unconditionally in the global scope; never on the right of `and`/`or`, inside a ternary branch, an `if`, or a loop. Treat CW10002/CW10003 as build failures. | B4, B19 [DOC] + [COMPILE] |
| No three-state booleans; no numeric conditions; test `na` with `na()`. | B1-B3 [DOC] + [COMPILE] |
| Wrap every integer division in `int()` or `math.floor()`. | B5 [DOC]; lint accepts `int x = 5 / 2` silently [COMPILE] |
| Lengths for `ta.ema/rsi/atr/rma/macd` must be inputs or constants, never reassigned variables. | B8, K1 |
| Compare timeframes as `"1D"`, `"1W"`, `"60"`, `"240"`. | B9, TF [DOC] |
| If a script references more history on realtime bars than on historical bars (or draws into the past on realtime bars), add `max_bars_back(series, n)` for that series; avoid the blanket `max_bars_back` parameter. | H3, B20 [DOC] |
| `calc_bars_count > 0` changes warm-up and `bar_index`; if used, the research code must mimic the same truncated start or parity checks will fail. | Section 6 [DOC] |
| With dynamic requests, every symbol/timeframe that might be needed live must already have been requested on historical bars. | R5 [DOC] |
| `request.footprint()` (buy/sell volume, delta, POC, value area) is available on Premium, one call per script; on daily and higher bars its total volume can differ from `volume`. Whether it returns data for a given US stock and how far back is unverified. | R6 [DOC] |
| After a clean lint, still verify on a chart: plot count, token size, load time, realtime behaviour. | Section 7 [COMPILE] |

---

## 11. Not verified today

| Item | Why / what is missing |
|---|---|
| Any runtime behaviour (values of `5 / 2` assigned to an `int`, `once` on live bars, lazy evaluation effects, negative array indices, dynamic `for` bounds, `timeframe.period` strings) | The tool only lints; no chart session was available |
| Whether the full compiler (on "Add to chart") rejects conflicts K1, K2, K3, and the exact error texts | Lint endpoint accepted them; the manual says they are errors |
| Exact error text and stage for exceeding 64 plot counts, 40 requests, 127 tuple elements, 100,256 tokens, 500 ms loops, 40 s execution | Not reproducible with lint |
| Numeric memory limit | Not published by TradingView |
| Maximum number of inputs | No statement found in LIM, the Inputs page, the FAQ or REF; a web search found none either |
| Maximum table rows/columns/cells; maximum label/tooltip text length | Not found in the pages read today |
| Whether the 100,000-element limit is per collection or per collection type (K5) | Manual pages disagree |
| Whether an `indicator()` `symbol` parameter exists (K8) | Not in REF/DECL; not compiled |
| Availability, history depth and symbol coverage of `request.footprint()` data for US stocks on 1h/4h/D/W | Manual only says it returns `na` when unavailable |
| Whether TradingView plans a v7 | Nothing in official pages; absence is not proof |
| Alert delivery limits (message length, webhook rules, expiry) | Outside this topic; only the plan counts and the 15-alerts-in-3-minutes rule were read |
| Pricing-page values are those displayed on 2026-11-10 to an anonymous US visitor | Plans and quotas can change; re-check before relying on 40 s / 400 alerts / 25 indicators |
