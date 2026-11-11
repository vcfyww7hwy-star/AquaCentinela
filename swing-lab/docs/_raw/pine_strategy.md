# Strategy Tester semantics and realism (TradingView, Pine Script v6)

Research date: every URL below was fetched on **2026-11-11 UTC** (sandbox clock; the task brief names 2026-11-10 as "today"). The Pine User Manual pages were served with a gzip header reading "last modified: Mon Nov 9 21:23:27 2026". [DOC]
Scope: how the broker emulator fills orders, what the realism settings do, what the limits are, how to write the common swing-trading order logic, and what TradingView itself says makes a backtest unrealistic. Nothing in this file was run on a chart: `[COMPILE]` means "accepted by TradingView's compiler", not "behaves as described at runtime".

Naming note: since July 2026 the docs call the Strategy Tester the **strategy report**, the Bar Magnifier checkbox is the **Bar detalization** menu (Default / High), and "Recalculate" is the **Script execution** menu. RN: "the strategy report interface (formerly known as the Strategy Tester)"; "The former 'Using bar magnifier' checkbox has been changed to a new Bar detalization menu". [DOC]

## 0. Evidence legend and sources

| Tag | Meaning |
|---|---|
| [DOC] | Read today in an official TradingView page (User Manual, Reference Manual, Help Center, TradingView blog) |
| [COMPILE] | Confirmed today with `tools/pine_compile.py` (TradingView's compiler, 11 calls used, log in section 11) |
| [SECONDARY] | Third-party page |
| [MEMORY] | Recalled from training, NOT verified today |

Rows marked **Derived** are my own arithmetic or inference from a [DOC] premise. They are not TradingView statements and were not tested on a chart.

| Short name | URL |
|---|---|
| STR | https://www.tradingview.com/pine-script-docs/concepts/strategies/ |
| FAQ-S | https://www.tradingview.com/pine-script-docs/faq/strategies/ |
| ALR | https://www.tradingview.com/pine-script-docs/concepts/alerts/ |
| FAQ-A | https://www.tradingview.com/pine-script-docs/faq/alerts/ |
| REP | https://www.tradingview.com/pine-script-docs/concepts/repainting/ |
| EXEC | https://www.tradingview.com/pine-script-docs/language/execution-model/ |
| OTF | https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ |
| NSC | https://www.tradingview.com/pine-script-docs/concepts/non-standard-charts-data/ |
| LIM | https://www.tradingview.com/pine-script-docs/writing/limitations/ |
| RN | https://www.tradingview.com/pine-script-docs/release-notes/ |
| MIG6 | https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/ |
| REF | https://www.tradingview.com/pine-script-reference/v6/ (JavaScript app, rendered with Playwright; anchors `#fun_strategy`, `#fun_strategy.entry`, `#fun_strategy.exit`, `#fun_strategy.close`, `#fun_strategy.close_all`, `#fun_strategy.cancel`, `#fun_strategy.risk.*`, `#var_strategy.*`, `#fun_alert`) |
| REF5 | https://www.tradingview.com/pine-script-reference/v5/#fun_strategy |
| HC-BE | https://www.tradingview.com/support/solutions/43000786181-broker-emulator/ |
| HC-DET | https://www.tradingview.com/support/solutions/43000786180-detalization-and-execution/ |
| HC-GEN | https://www.tradingview.com/support/solutions/43000786178-general-settings/ |
| HC-BM | https://www.tradingview.com/support/solutions/43000669285-what-is-bar-magnifier-backtesting-mode/ |
| HC-PROP | https://www.tradingview.com/support/solutions/43000628599-strategy-properties/ |
| HC-LEV | https://www.tradingview.com/support/solutions/43000717375-how-to-simulate-trading-with-leverage-in-pine-script/ |
| HC-DB1 | https://www.tradingview.com/support/solutions/43000666199-what-is-deep-backtesting/ |
| HC-DB2 | https://www.tradingview.com/support/solutions/43000666265-how-deep-backtesting-works/ |
| HC-DB3 | https://www.tradingview.com/support/solutions/43000666266-why-do-the-data-of-the-regular-mode-and-deep-backtesting-not-match/ |
| HC-DB4 | https://www.tradingview.com/support/solutions/43000668210-how-much-data-is-available-for-deep-backtesting/ |
| HC-DB5 | https://www.tradingview.com/support/solutions/43000670566-why-are-the-results-of-deep-backtesting-not-shown-on-the-chart/ |
| HC-SA | https://www.tradingview.com/support/solutions/43000481368-strategy-alerts/ |
| HC-PH | https://www.tradingview.com/support/solutions/43000531021-how-to-use-a-variable-value-in-alert/ |
| HC-PEEK | https://www.tradingview.com/support/solutions/43000614705-strategy-produces-unrealistically-good-results-by-peeking-into-the-future/ |
| HC-NOORD | https://www.tradingview.com/support/solutions/43000478450-i-ve-successfully-added-a-strategy-to-my-chart-but-it-doesn-t-generate-orders/ |
| HC-SPR | https://www.tradingview.com/support/solutions/43000764681-strategy-publishing-rules/ |
| HC-PUB | https://www.tradingview.com/support/solutions/43000590599-script-publishing-rules/ |
| BLOG-BM | https://www.tradingview.com/blog/en/accurate-backtesting-with-bar-magnifier-31746/ (published 2022-05-30) |
| BLOG-DB | https://www.tradingview.com/blog/en/deep-backtesting-is-out-of-beta-41158/ (published 2023-10-16) |

## 1. How the broker emulator simulates trades

### 1.1 When the script runs and when an order can fill

| Setting (`strategy()` parameter, UI name) | Default | What it does | Exact wording | Tag, source |
|---|---|---|---|---|
| Default behaviour | n/a | Script runs once per bar, on the close, on historical AND realtime bars. A market order created there fills at the next bar's open. | "a strategy script executes strictly once per closed bar, regardless of whether a bar is part of the historical dataset or a new bar from the realtime data feed." "each new order in the strategy's simulation has a one-tick delay by default. Therefore, when using these default behaviors, a strategy places orders on a bar only when it reaches the bar's close, and the earliest point at which the broker emulator can fill those orders is at the open of the following bar." | [DOC] STR, "Altering calculation behavior" |
| Why the delay exists | n/a | | "By default, the earliest point at which the broker emulator fills an order is on the next available tick, because creating and filling an order on the same tick is unrealistic." | [DOC] STR, "Orders and trades" |
| `process_orders_on_close` ("Order execution delay": One tick / None) | `false` | `true` lets an order created on a bar's closing tick fill on that same tick (the close). It does not change orders placed before the closing tick. | "If the value is `true`, the broker emulator can fill orders created on a bar's close immediately, on the same tick, rather than waiting for the next available tick. If the value is `false` (the default), the earliest point at which the emulator can fill orders created on a bar's closing tick is on the next tick, at the open of the following bar." REF adds: "If the orders are price-dependent, they will only be filled if the price conditions are met." | [DOC] STR; REF `#fun_strategy` |
| `immediately` on `strategy.close()` / `strategy.close_all()` | `false` | Per-call version of the same thing, for closing market orders only. | "If true, the closing order executes on the same tick when the strategy places it, ignoring the strategy properties that restrict execution to the opening tick of the following bar." | [DOC] REF `#fun_strategy.close` |
| `calc_on_every_tick` ("On realtime bar tick") | `false` | Realtime bars only: run on every tick. No effect on history, so history and realtime diverge. | "If the value is `true`, the script executes to update its calculations on every new tick in an open realtime bar, similar to an indicator." "if a strategy places orders on the ticks within an open bar, it might not be able to reproduce the same orders after reloading." | [DOC] STR |
| `calc_on_order_fills` ("On order fill") | `false` | History and realtime: one extra run on each tick where an order fills. On history the extra run sees the bar's FINAL high/low/close. | "the script performs an additional execution on each tick where the broker emulator fills an order." "enabling some strategies to execute after order fills can cause lookahead bias on historical bars ... built-in variables that store price and volume data for the current bar – including high, low, close, and volume – consistently hold the bar's final values." | [DOC] STR |
| `calc_on_every_history_tick` ("On history bar tick"), added July 2026 | `false` | History only: run on every emulated tick, with high/low/close/volume masked to what was known at that tick. Must be passed by name. Premium or Ultimate, standard charts only. | "If the value is `true`, the script executes to update its calculations on every available tick in each historical bar." "The 'On history bar tick' feature is available only to users who have a Premium or Ultimate plan. Additionally, the feature requires a standard chart type. If the setting is enabled by default, the strategy raises a runtime error if it is not compatible with the user's plan or the current chart." "`barstate.isconfirmed` variable is always `true` on historical bars." | [DOC] STR; RN July 2026; [COMPILE] parameter accepted |
| All three extra-execution settings | n/a | TradingView's own warning. | "Modifying a strategy's 'Script execution' settings can cause repainting in the strategy's calculations and results, because they define different behaviors for historical and realtime bars" | [DOC] STR |

### 1.2 Intrabar price path and gaps (historical bars, default bar detail)

| Rule | Exact wording | Tag, source |
|---|---|---|
| 4 ticks per historical bar | "the broker emulator considers historical bars to have four ticks for filling orders by default (the open, high, low, and close)" | [DOC] EXEC |
| Path when the open is nearer the high | "If the opening price of a bar is closer to the high than it is to the low, the emulator assumes that the market price moved in this order: open → high → low → close." | [DOC] STR, "Broker emulator" |
| Path when the open is nearer the low | "If the opening price of a bar is closer to the low than it is to the high, the emulator assumes that the market price moved in this order: open → low → high → close." | [DOC] STR |
| Open exactly midway between high and low | Not stated in the pages read today. | Not verified |
| No gaps inside a bar | "When filling price-based orders (all orders except market orders), the emulator assumes that no gaps exist inside each chart bar; it considers any price within the bar's range as a valid level for filling pending orders." | [DOC] STR |
| Gap THROUGH an order between bars: fill at the open | "If the market price crosses a price-based order's level during the gap between one bar's closing time and the next bar's opening time, the emulator assumes that intrabar data does not exist within the gap. Rather than filling the order at the specified price in that case, the emulator fills the order at the opening price of the bar following the gap." | [DOC] STR |
| Consequence for a stop-loss | Illustration of the rule above: a long position's stop at 50 with the next bar opening at 47 fills at 47 (worse than the stop); a limit gapped through fills at the open (better than the limit). STR: "Strategies can fill limit orders at better prices and stop orders at worse prices, depending on the range of values available to the broker emulator." | [DOC] STR |
| Realtime bars | "each new update to a realtime bar is a valid tick on which an order can fill." | [DOC] STR |

### 1.3 Order types

| Order | Created by | Fill rule | Tag, source |
|---|---|---|---|
| Market | `strategy.entry/order` with no `limit`/`stop`; `strategy.close`, `strategy.close_all` (always market) | "the broker emulator always executes it on the next available tick" | [DOC] STR |
| Limit | `limit =` | "When the market price reaches a limit order's value, or crosses it in the favorable direction, the broker emulator fills the order at that value or a better price." A limit placed at a WORSE price than the market fills like a market order: "the emulator fills the order on the next available tick rather than waiting". | [DOC] STR |
| Stop | `stop =` | "an instruction to activate a new market or limit order when the market price reaches a specific price or a worse value". "If a strategy generates a stop order at a better value than the current market price, it activates the subsequent order without waiting for the market price to reach that value." | [DOC] STR |
| Stop-limit | `strategy.entry/order` with both `stop` and `limit` | Limit becomes active only after the stop level trades. | [DOC] STR |
| `strategy.exit` with both `limit` and `stop` | n/a | NOT a stop-limit: "calling strategy.exit() with both arguments creates two exit orders: a take-profit order at the `limit` price and a stop-loss order at the `stop` price." Only the first one triggered fills; the other is cancelled. | [DOC] STR |
| `strategy.exit` called before the entry has filled | n/a | "If a call to this command occurs before a created entry order's execution, the strategy waits and does not create the exit orders until after the entry order executes." This is what lets a stop be live from the first tick after the fill. | [DOC] REF `#fun_strategy.exit` |
| Re-issuing an order | same `id` | "If an unfilled order with the same id exists, a call to this command modifies that order." (entry) / "If unfilled exit orders with the same id exist, calls to this command modify those orders." (exit) | [DOC] REF |
| Cancel | `strategy.cancel(id)`, `strategy.cancel_all()` | A market order can be cancelled only in the same execution that created it: "the broker emulator always fills market orders by the next available tick." | [DOC] STR |
| Reversal | `strategy.entry` in the opposite direction | Adds the open position size to the order, so it closes and reverses. `strategy.risk.allow_entry_in()` turns that into close-only. `strategy.order` never reverses automatically; it nets. | [DOC] STR |
| `when =` parameter | removed in v6 | Compiler: `The "strategy.entry" function does not have an argument with the name "when"` | [COMPILE]; [DOC] MIG6 |

### 1.4 Costs and fill assumptions

| Setting | Default | Precise effect | Exact wording | Tag, source |
|---|---|---|---|---|
| `slippage` (ticks, const int) | 0 | Moves the fill price of **market and stop** orders against you by N × `syminfo.mintick`. REF and HC-BE name only market and stop orders; STR's prose says "all order fills" (next row). Constant, not volatility-scaled. | "Slippage expressed in ticks. This value is added to or subtracted from the fill price of market/stop orders to make the fill price less favorable for the strategy. E.g., if syminfo.mintick is 0.01 and slippage is set to 5, a long market order will enter at 5 * 0.01 = 0.05 points above the actual price." | [DOC] REF `#fun_strategy` |
| Slippage side effect | n/a | A slipped fill can be outside the bar's range. | "Because the strategy applies constant slippage to all order fills, some orders can fill outside the candle range in the simulation." | [DOC] STR |
| `commission_type`, `commission_value` | `strategy.commission.percent`, 0 | Three models: percent of order cash value, cash per contract (share), cash per order. Charged on entries and on exits. | "strategy.commission.percent for a percentage of the cash volume of the order, strategy.commission.cash_per_contract for currency per contract, strategy.commission.cash_per_order for currency per order." "Commission is applied on both entries and exits." "If not specified, the strategy applies no commission to filled orders." | [DOC] REF; HC-BE; STR |
| `backtest_fill_limits_assumption` (ticks, const int; UI "Limit order execution") | 0 | A limit fills only if price trades N ticks BEYOND it; the fill price stays the limit price. UI offers only "Requested price" or "Requested price and 1 tick beyond". | "limit orders are only filled if the market price exceeds the order's limit level by the specified number of ticks." "The default argument is 0, meaning that the broker emulator fills any limit order immediately if the price reaches the order's level." "regardless of the fill time, the broker emulator still executes verified limit orders at their specified prices ... it can also cause the orders to execute at times that may not be possible in real-word trading" | [DOC] REF; STR |
| Not modelled | n/a | The `strategy()` signature read today has no parameter for borrow fees, margin interest, partial fills, queue position, or volume-limited fills. | **Derived** from the full parameter list in REF `#fun_strategy`. STR's general warning: "simulated results may not fully account multiple real-world factors that can impact trading performance." | [DOC] premise |

## 2. Bar Magnifier (now "Bar detalization: High", parameter `use_bar_magnifier`)

| Item | Finding | Exact wording | Tag, source |
|---|---|---|---|
| What it changes | The emulator takes O, H, L, C of lower-timeframe bars as the tick sequence inside each historical chart bar, instead of the 4-tick path guess. In TradingView's own example "exit and entry prices are unchanged" but the stop-out moves into the entry bar (HC-BM). | "the broker emulator retrieves open, high, low, and close prices from the bars on a suitable lower timeframe, when possible, to increase the number of ticks available for estimating price action and filling orders on historical bars." | [DOC] STR |
| It also multiplies script executions if extra execution modes are on | | "This setting also allows the script to perform multiple additional executions on each historical bar, depending on the selected Script execution settings." | [DOC] STR |
| Plan | Premium and Ultimate (the user's Premium plan qualifies). | "Users with Premium and Ultimate plans can override the broker emulator's chart-based assumptions and increase the level of intrabar detail on historical bars". REF: "Only Premium and higher-tier plans have access to this feature." | [DOC] STR; REF |
| Default | `false` | REF `use_bar_magnifier`: "The default is false." | [DOC] REF |
| Intrabar timeframe used | 1h chart → 10m; 4h → 30m; 1D → 60m; 3D → 240m; 1W → 1D. (Full table: 1T→1T, 100T→10T, 1000T→100T, 1S→1S, 30S→5S, 1→10S, 5→30S, 10→1, 15→2, 30→5, 60→10, 240→30, 1D→60, 3D→240, 1W→1D; "includes timeframes between it and the next one".) | Table in HC-BM, repeated in HC-DET with tick counts (60m: 24 ticks; 240m: 32; 1D: 96; 1W: 28). STR confirms weekly → daily. | [DOC] HC-BM; HC-DET; STR |
| Older, different table | The 2022 blog lists 60 ≤ T < 240 → 5, 240 ≤ T < D → 15, D → 60, W → 120. Superseded by the Help Center table above; shown because the sources differ. | | [DOC] BLOG-BM (2022) |
| Limit: lower-timeframe bars | 200,000 lower-timeframe bars; earlier chart bars fall back to the default path guess, silently. | STR: "Scripts can request a maximum of 200,000 bars from any lower timeframe. Due to this limitation, the requested datasets for some symbols and timeframes might not include intrabar coverage for early bars on the chart. The broker emulator uses its default assumptions when filling orders on bars that do not have intrabar data on the requested timeframe." HC-BM: "The strategy can't request more than 200,000 bars from the lower timeframe." Rough coverage formula (HC-BM): `last_bar_index - (200000 / Num of Lower Timeframe Bars per Chart Bar)`. | [DOC] STR; HC-BM |
| Possible conflict on that limit | LIM gives plan-dependent intrabar limits for `request.security()` / `request.security_lower_tf()`: "All non-professional plans – Basic, Essential, Plus, and Premium – can request up to 100K bars of data. Expert plans have access to 125K bars of data. Ultimate plans can request 200K lower-timeframe bars." Whether the magnifier on Premium gets 100K or 200K is not stated. | | [DOC] LIM; not resolved |
| **Derived** coverage for this project (US stock, regular session ≈ 6.5 h, Premium = 20,000 chart bars per REP) | 1h chart: about 6 ten-minute bars per chart bar → 200K covers ≈ 33,000 chart bars (all 20,000); 100K covers ≈ 16,700 (the oldest ≈ 3,300 hourly bars would use the path guess). 4h, 1D, 1W: covered under either limit as far as the count goes. Separate limit: intrabars can only exist where TradingView stores intraday history; HC-DB4 says "On intraday timeframes, TradingView keeps a limited amount of data", so old daily bars may have no 60m data. How far back 60m data reaches was not checked. | | Derived; not tested |
| 1T and 1S charts | Unaffected. | "The broker emulator always analyzes one tick per bar on a '1T' chart, and four ticks per bar on a '1S' chart." | [DOC] STR |
| TradingView's advice | Compare Default vs High. | "A significant difference in performance may indicate that your entry or exit logic is fragile under finer price simulation." | [DOC] HC-DET |
| **Derived**: when it matters for swing systems | It matters when two price-based orders can trade in one bar (stop and target; stop-entry then stop-loss) and for built-in trailing stops. With one resting stop per bar and market entries, the path does not decide anything, except that on a weekly chart the daily intrabars expose overnight gaps inside the week (section 1.2: gaps are only assumed away inside a bar). | | Derived; not tested |

## 3. Deep Backtesting

| Aspect | Normal strategy report | Deep Backtesting | Tag, source |
|---|---|---|---|
| Data | Bars loaded on the chart. Plan cap: "20000 historical bars for the Premium plan" (REP). | "all historical data available for the selected symbol, and not only on those loaded on the chart" (HC-DB1); "On daily and daily-based timeframes, charts display all available data, and the Deep Backtesting mode uses this same data." (HC-DB4) | [DOC] |
| How it starts | Default. | Selecting a testing period switches it on: "Selecting a different period from the 'Testing period' menu at the top of the tab activates Deep Backtesting mode" (STR). "When you modify the strategy, click Update report"; stop with "Reset to chart session" (HC-DB2). | [DOC] |
| Plan | Not checked today. | "This feature is available for Premium and higher plan users." (HC-DB2) | [DOC] |
| Bar limit | Chart bars. | "the maximum length of historical data per calculation is 2 million bars. If the period used for a backtest covers more than 2 million bars, the strategy will execute on the most recent 2 million bars within the selected period." (HC-DB4) | [DOC] |
| Order/trade limit | 9000 (see section 4). | "one million trades" (HC-DB2); "When using Deep Backtesting, the order limit is 1,000,000." (LIM); "it maintains information for every closed trade and does not trim any orders from the report." (STR) | [DOC] |
| Where results show | Chart markers and report. | Report only: "Trades calculated when Deep Backtesting is enabled are not displayed on the chart" (HC-DB5). "When using this mode, the strategy's trade markers, plots, alerts, and Pine Logs are calculated using only the available chart data, regardless of the specified testing range." (STR) "Show on chart" and scroll-to-trade are unavailable (STR). | [DOC] |
| Why numbers differ from the normal run | n/a | Different first bar: "in Deep Backtesting, script calculations will start at the beginning of the date range, whereas regular backtesting calculations always begin on the chart's first bar." EMA/RMA-type values differ, so trades can differ even on the same dates. (HC-DB3) | [DOC] |
| Bar Magnifier inside Deep Backtesting | n/a | "it also works when testing on deep history. To ensure that the information from the lower timeframes is enough, we've increased the Bar magnifier's history depth proportionally." Stated in 2023; no current figure found. | [DOC] BLOG-DB (2023) |
| **Derived** relevance | Daily and weekly charts already load all history, so Deep Backtesting adds nothing there except the date picker and the higher trade limit. It matters on 1h charts, where Premium loads 20,000 bars (≈ 11 years at 7 regular-session bars a day). | | Derived |
| Alternative for more history | Bar Replay from the first bar "effectively rolls back the dataset to an earlier point in time" and keeps chart markers. | | [DOC] FAQ-S |

## 4. Limits and defaults that silently change results

### 4.1 `strategy()` defaults (Reference Manual v6, read today) and where official sources disagree

| Parameter | Default per REF v6 | Other official statement | Why it matters | Tag |
|---|---|---|---|---|
| `default_qty_type` | `strategy.percent_of_equity` | REF5 (v5): "The default is strategy.fixed." | Sizing model changes between versions. | [DOC] REF; REF5 |
| `default_qty_value` | 100 | REF5: "The default is 1." | 100% of equity on every entry = fully compounded, all-in. | [DOC] |
| `initial_capital` | "The default is 100000." | HC-PROP: "By default, this value is equal to 1,000,000." REF5: 1000000. | Percent metrics and affordability. | [DOC], sources conflict |
| `pyramiding` | REF: "If the value is 0, only one entry order in the same direction can be opened ... The default is 0." | STR: "The default argument is 1, meaning the strategy can open new positions but cannot add to them". HC-GEN: "1: one entry per direction." | Same behaviour either way: one entry. Wording conflicts. | [DOC], sources conflict |
| `margin_long`, `margin_short` | 100, 100 | MIG6: "In v5, the default value ... is 0". | v6: entries that cannot be paid for are not opened; shorts can be margin-called. | [DOC] |
| `commission_type` / `commission_value` | percent / 0 | | Zero costs unless set. | [DOC] |
| `slippage` | 0 | | | [DOC] |
| `process_orders_on_close` | false | | | [DOC] |
| `calc_on_every_tick`, `calc_on_order_fills`, `calc_on_every_history_tick` | false | | | [DOC] |
| `use_bar_magnifier` | false | | | [DOC] |
| `backtest_fill_limits_assumption` | 0 | | Limits fill on touch. | [DOC] |
| `close_entries_rule` | "FIFO" | | Exits close the oldest trade first, even if `from_entry` names another. | [DOC] |
| `fill_orders_on_standard_ohlc` | false | | Heikin Ashi fills at synthetic prices unless set. | [DOC] |
| `risk_free_rate` | 2 | RN: Sharpe and Sortino "now always use monthly periods". | Sharpe/Sortino inputs. | [DOC] |
| `currency` | REF: `syminfo.currency`; STR: `currency.NONE` (chart currency) | | Same meaning. | [DOC] |
| `calc_bars_count` | 0 (all bars) | | | [DOC] |

The compiler endpoint returns no property metadata, so the real runtime defaults could not be read from it. [COMPILE] (probe compiled; nothing to inspect). **Action: set every one of these explicitly in each strategy.** The two reference scripts below do.

### 4.2 Stored trades and orders

| Statement | Wording | Tag, source |
|---|---|---|
| Limit as "trades" | "By default, strategies preserve information for up to the latest 9000 trades. If a strategy simulates more than 9000 trades, it trims the information for the oldest closed trades" | [DOC] STR |
| Limit as "orders" | "A script can place a maximum of 9000 orders when backtesting strategies. Once it reaches that limit, the earlier orders are trimmed to store the information of new orders." | [DOC] LIM |
| Limit as "orders a strategy can open" | "The maximum number of orders a strategy can open, unless it uses Deep Backtesting mode, is 9000. If the strategy exceeds this limit, it removes the oldest order's information when a new entry appears in the 'List of Trades' tab." | [DOC] REF |
| What trimming affects | Trade list, CSV/XLSX export and `strategy.closedtrades.*()` (return `na`); NOT the Metrics tab or the simulation itself. "it does not affect the data displayed in the 'Metrics' tab or accessed by other `strategy.*` built-ins." `strategy.closedtrades.first_index` gives the oldest kept trade. | [DOC] STR; [COMPILE] variable exists |
| v5 behaviour | Runtime error at 9000 instead of trimming. | [DOC] MIG6; RN Nov 2024 |
| Position cap | "The total position size (number of contracts) cannot exceed 1e12." | [DOC] HC-NOORD |
| **Derived** | Trades vs orders is not reconciled by the docs. A swing system on one symbol makes far fewer than 4,500 round trips, so neither reading binds here. | Derived |

### 4.3 Sizing

| Choice | Meaning | Wording | Tag, source |
|---|---|---|---|
| `strategy.fixed` | Fixed number of shares per order. | "a number of contracts/shares/lots will be used to enter trades." | [DOC] REF |
| `strategy.cash` | Fixed cash amount in account currency; shares = cash / price. | "an amount of cash in the strategy.account_currency will be used to enter trades." | [DOC] REF |
| `strategy.percent_of_equity` | Percent (0-100) of CURRENT equity, so it compounds. | "A percentage of the strategy's current equity: initial capital plus realized and open profit or loss. Orders grow as the strategy earns and shrink as it loses." | [DOC] HC-GEN |
| Explicit `qty =` | Overrides the default for that order. | "If a call to either of these commands specifies a non-na `qty` value, that call ignores the strategy's default quantity type and value". | [DOC] STR |
| Not enough capital | Order is simply not filled; no error. | "It will not enter a trade if it does not have sufficient capital to cover the cost." "Strategies will always try to purchase the specified number of contracts/shares/lots/units and nothing less." | [DOC] HC-NOORD |
| Whole shares | Stocks do not accept fractional sizes. | "an order size of 0.1 is valid for BTCUSD but not for AAPL or EURUSD." | [DOC] HC-NOORD |
| Total loss stops trading | A wiped-out account places no more orders for the rest of the test. | "the account might lack sufficient capital to continue trading the symbol" | [DOC] FAQ-S |
| `strategy.default_entry_qty(fill_price)` | Returns the default size for a given fill price; ignores the open position. | | [DOC] REF; [COMPILE] |

### 4.4 Margin and forced liquidation

| Fact | Wording | Tag, source |
|---|---|---|
| Default 100% (no leverage) in v6 | "The default is 100, in which case the strategy only uses its own funds and the long positions cannot be margin called." | [DOC] REF |
| Shorts can still be liquidated at 100% | "even with no margin used, short positions can be margin called if the loss exceeds available funds." | [DOC] REF |
| Margin 0 disables all checks | "If the value is 0, the strategy does not enforce any limits on position size." "using a margin of 0% is extremely misleading because it is equivalent to infinite leverage" | [DOC] REF; STR |
| Liquidation size | "the emulator immediately liquidates four times the number of contracts/shares/lots/units required to cover the loss" | [DOC] STR |
| Converting a v5 strategy changes results | MIG6 example (100% of equity, long and short, 4h ARM): no margin calls in v5, "14 margin calls" in v6. | [DOC] MIG6 |
| Monitoring | `strategy.margin_liquidation_price`; the report's Capital efficiency section shows the number of margin calls. | [DOC] STR; [COMPILE] |

### 4.5 Pyramiding and exit bookkeeping

| Fact | Wording | Tag, source |
|---|---|---|
| Applies to `strategy.entry` only | "Pyramiding only affects entries made using the strategy.entry() function. It has no effect on orders created using strategy.order()." | [DOC] HC-PROP |
| Can be exceeded | "If multiple calls to this command generate limit, stop, or stop-limit orders on the same tick, the broker emulator fills each one that the price action triggers, regardless of the specified limit." | [DOC] STR |
| `strategy.exit` reserves quantity | "The orders from one strategy.exit() call cannot exit the portion of a position that a previous call already reserved." | [DOC] STR |
| `strategy.exit` without `from_entry` persists | It "creates exit orders for all open trades, even the ones opened after the call, until the position closes." | [DOC] REF |
| v6 change: relative vs absolute levels | With both `loss` and `stop` (or `profit` and `limit`), v6 "uses the one that the market price is expected to trigger first"; v5 always used the absolute one. | [DOC] MIG6 |
| `strategy.position_avg_price` is `na` until a position exists | A stop computed from it is created one bar after the entry, leaving the entry bar unprotected: "This script creates a stop-loss order one bar after the entry order because it uses strategy.position_avg_price". | [DOC] STR |

### 4.6 `strategy.risk.*`

"All risk management commands execute on every tick and order execution event, regardless of any changes to the strategy's calculation behavior. There is no way to deactivate any of these commands on specific script executions." [DOC] STR. All six compile in v6. [COMPILE]

| Function | Effect | Trap for swing systems | Tag |
|---|---|---|---|
| `strategy.risk.allow_entry_in(value)` | Restricts `strategy.entry` direction; an opposite entry only closes. | None; useful for long-only. | [DOC] STR, REF |
| `strategy.risk.max_position_size(contracts)` | Caps position size for `strategy.entry` orders by reducing the order. | Does not affect `strategy.order`. | [DOC] REF |
| `strategy.risk.max_drawdown(value, type, alert_message)` | At the limit: "all pending orders are cancelled, all open positions are closed and no new orders can be placed." | Permanent halt: every later trade in the backtest is missing. | [DOC] REF |
| `strategy.risk.max_cons_loss_days(count, alert_message)` | Same halt after N consecutive losing days. | Permanent halt. | [DOC] REF |
| `strategy.risk.max_intraday_loss(value, type, alert_message)` | Halts "until the end of the current session". | "per chart bar if the chart's timeframe is higher than '1D'" (STR). | [DOC] |
| `strategy.risk.max_intraday_filled_orders(count, alert_message)` | Halts and closes after N fills in a day. | Same per-bar rule above 1D. | [DOC] |

## 5. How to express the common order logic

### 5.1 Idiom table (every code cell is in `idioms.pine`, which compiles with 0 errors and 0 warnings [COMPILE])

Assumed declaration: `process_orders_on_close = false`, all `calc_on_*` false. `atr`, `sig`, `inPos = strategy.position_size > 0`, `stopDist` are computed at global scope.

| Intent | Code | Fill semantics | Basis |
|---|---|---|---|
| Enter at the next open after a signal on the close | `if sig and not inPos` → `strategy.entry("L", strategy.long, qty = q)` | Order created on the signal bar's close; fills at the next bar's open (plus slippage). | [DOC] STR 1.1 |
| Enter on the signal bar's own close (not attainable live) | `strategy(..., process_orders_on_close = true)` | FAQ-S: "the emulator would simulate the order being filled at the previous day's close. This discrepancy can lead to repainting". | [DOC] FAQ-S |
| Resting stop-loss at an absolute price, live from the fill | Same execution as the entry: `strategy.exit("L-stop", from_entry = "L", stop = stopPx)`; re-issue on every bar of the trade | Waits for the entry, then rests. Hit inside a bar → fills at `stopPx`; gapped through → fills at that bar's open. | [DOC] REF exit; STR 1.2 |
| Stop a fixed distance below the ACTUAL fill | `strategy.exit("L-sl", from_entry = "L", loss = stopDist / syminfo.mintick)` | `loss` is "expressed in ticks ... away from the entry price", so it follows the real next-open fill. | [DOC] REF exit |
| Bracket at R multiples | `strategy.exit("L2-br", from_entry = "L2", stop = close - stopDist, limit = close + 2 * stopDist)` | Two orders, first one hit wins. If both lie inside one bar the 4-tick path (or the magnifier) decides. | [DOC] STR |
| ATR trailing stop that only ratchets | `var float trail = na` ... `trail := math.max(trail, close - k * atr)` then `strategy.exit(id, from_entry, stop = trail)` on every bar | Updated on each close, works during the next bar. FAQ-S: "a custom trailing stop must calculate the stop price on each bar that the stop is active, and call the strategy.exit() function on each bar to set the `stop` price." It "avoids repainting". | [DOC] FAQ-S |
| Built-in trailing stop | `strategy.exit(id, from_entry, trail_points = a, trail_offset = b)` (ticks) | Trails intrabar. FAQ-S: "use live price updates in realtime but assumed price movements for historical bars. These assumptions can cause repainting." Prefer the custom ratchet. | [DOC] FAQ-S |
| Time exit after N completed bars | `barsHeld = bar_index - strategy.opentrades.entry_bar_index(0) + 1`; `if barsHeld >= N` → `strategy.close("L")` | Decided on the close of the Nth bar in the trade; fills at the open of bar N+1. | [DOC] FAQ-S (uses `entry_time`); [COMPILE] |
| Time exit after N calendar days | `time_close - strategy.opentrades.entry_time(0) >= N * 86400000` | FAQ-S: "time-based conditions can only be evaluated at the close, so trade times are assessed in multiples of the chart bar's duration." | [DOC] FAQ-S |
| Exit at the next open | `strategy.close("L")` or `strategy.close_all()` | Market order, next bar's open. | [DOC] STR |
| Exit on this bar's close (not attainable live) | `strategy.close("L", immediately = true)` | FAQ-S: "the same prices might not always be attainable in realtime trading. Additionally, this behavior can cause repainting." | [DOC] FAQ-S |
| Fixed-fractional risk | `qty = math.floor(strategy.equity * riskPct / 100 / ((entryRef - stopPx) * syminfo.pointvalue))`, capped by a max position value | FAQ-S method: risk amount = equity × percent; divide by risk per contract. With a next-open entry the entry price is unknown at order time, so the risk is an estimate. | [DOC] FAQ-S |
| Resting entry that expires | `strategy.entry("STP", strategy.long, qty, stop = high + syminfo.mintick)`; after N bars `strategy.cancel("STP")` | Works from the next bar; gap above the trigger → fills at the open. | [DOC] STR |
| Long only | `strategy.risk.allow_entry_in(strategy.direction.long)` | Opposite entries close, never reverse. | [DOC] STR |
| In-sample / out-of-sample split | gate entries with `time >= t0 and time < t1` from `input.time()` | STR recommends IS/OOS testing; FAQ-S has a date-filter entry. | [DOC] STR, FAQ-S |
| `ta.*` inside `a and b` | Compute at global scope first. | v6 `and`/`or` are lazy; the compiler warns CW10002: "The 'ta.sma()' call inside the conditional expression might not execute on every bar". | [COMPILE] |

### 5.2 Reference strategy A (compiles: 0 errors, 0 warnings) [COMPILE]

Market entry at the next open, resting stop, ratcheting ATR stop, time exit, rule exit at next open, fixed-fractional sizing, `alert()` instruction at the signal bar's close plus order-fill messages.

```pine
//@version=6
//@strategy_alert_message {{strategy.order.alert_message}}
// REF-A  Reference strategy A. A semantics demo, NOT a trading system. Long only.
// Shows: signal on a bar's close -> market entry at the next bar's open; a resting stop-loss order; an ATR trailing
// stop that only ratchets up; a time exit after N bars; a rule exit at the next open; fixed-fractional risk sizing.
// Every property that can silently change results is written out instead of being left to a default.
strategy("REF-A next-open entry, resting stop, ratchet ATR trail, time exit, fixed-fractional risk",
     shorttitle = "REF-A", overlay = true,
     initial_capital = 100000, currency = currency.USD,
     default_qty_type = strategy.fixed, default_qty_value = 1,     // not used: every entry passes `qty`
     pyramiding = 1,                                               // one open entry per position
     commission_type = strategy.commission.percent, commission_value = 0.05,
     slippage = 2,                                                 // ticks, on market and stop fills
     margin_long = 100, margin_short = 100,                        // no leverage
     process_orders_on_close = false,                              // an order created on a close fills at the NEXT open
     calc_on_every_tick = false, calc_on_order_fills = false, calc_on_every_history_tick = false,
     use_bar_magnifier = false,                                    // one resting stop per bar: the intrabar path is not needed
     fill_orders_on_standard_ohlc = true,                          // real prices if the chart is Heikin Ashi
     close_entries_rule = "FIFO")

int   donLen    = input.int(20,    "Breakout lookback (bars)", minval = 2)
int   maLen     = input.int(200,   "Trend filter SMA length", minval = 1)
int   atrLen    = input.int(14,    "ATR length", minval = 1)
float initMult  = input.float(2.0, "Initial stop: ATR multiples below the signal close", minval = 0.1, step = 0.1)
float trailMult = input.float(3.0, "Trailing stop: ATR multiples below the close", minval = 0.1, step = 0.1)
int   maxBars   = input.int(15,    "Time exit after N completed bars in the trade", minval = 1)
float riskPct   = input.float(0.5, "Risk per trade, % of sizing base", minval = 0.01, step = 0.05)
float maxPosPct = input.float(25,  "Max position value, % of sizing base", minval = 1, maxval = 100)
bool  compound  = input.bool(true, "Size from current equity (off = from initial capital)")

// Series are computed on every bar at global scope. The strategy runs once per bar, on its close.
float atr     = ta.atr(atrLen)
float trendMa = ta.sma(close, maLen)
float upper   = ta.highest(high, donLen)[1]                        // channel of the previous donLen bars, without this bar

var float stopPx = na                                              // price of the resting stop; it only moves up
bool inPos = strategy.position_size > 0
if not inPos
    stopPx := na                                                   // flat at this close: forget the old stop

// Entry: decided on this bar's close, filled by the broker emulator at the next bar's open.
bool longSig = not inPos and not na(atr) and not na(trendMa) and not na(upper) and close > trendMa and close > upper
bool placed  = false
if longSig
    float initStop  = close - initMult * atr
    float riskPerSh = (close - initStop) * syminfo.pointvalue      // estimate: the real fill is the next open, not this close
    float sizeBase  = compound ? strategy.equity : strategy.initial_capital
    float qtyRisk   = sizeBase * riskPct / 100 / riskPerSh         // shares so that a stop-out costs about riskPct of the base
    float qtyCap    = sizeBase * maxPosPct / 100 / (close * syminfo.pointvalue)
    float qty       = math.floor(math.min(qtyRisk, qtyCap))        // whole shares
    if qty >= 1
        stopPx := initStop
        placed := true
        string msg = "BUY " + syminfo.ticker + " at next open, qty " + str.tostring(qty) + ", stop " + str.tostring(stopPx, format.mintick)
        strategy.entry("L", strategy.long, qty = qty, alert_message = "FILLED " + msg)
        alert(msg, alert.freq_once_per_bar_close)                  // the instruction, sent when the signal bar closes

// Ratchet: the candidate falls when price falls or ATR widens; math.max() never lets the stop move down.
if inPos
    stopPx := math.max(stopPx, close - trailMult * atr)

// Resting stop-loss. On the signal bar the call waits for the entry to fill. On every later bar of the trade the
// same id ("L-stop") is re-issued, which moves the existing order. The new price works from the next bar on.
if placed or inPos
    strategy.exit("L-stop", from_entry = "L", stop = stopPx, comment = "stop",
         alert_message = "STOP HIT " + syminfo.ticker + ", stop was " + str.tostring(stopPx, format.mintick))

// Time exit and rule exit: market orders created on this close, filled at the next bar's open.
int  barsHeld = inPos ? bar_index - strategy.opentrades.entry_bar_index(strategy.opentrades - 1) + 1 : 0
bool timeExit = inPos and barsHeld >= maxBars
bool ruleExit = inPos and close < trendMa
if timeExit or ruleExit
    string why = timeExit ? "time" : "trend"
    strategy.close("L", comment = why, alert_message = "EXITED " + syminfo.ticker + " (" + why + ")")
    alert("SELL " + syminfo.ticker + " at next open (" + why + " exit)", alert.freq_once_per_bar_close)

plot(upper,   "Breakout level", color.new(color.teal, 40))
plot(trendMa, "Trend SMA",      color.new(color.orange, 40))
plot(stopPx,  "Resting stop",   color.red, 2, plot.style_linebr)
```

Reading notes for A (all **Derived** from the [DOC] rules above; not run on a chart):

| Point | Behaviour to expect |
|---|---|
| Stop on the entry bar | The exit call on the signal bar waits for the fill, so the stop is live from the entry bar's open. If that open is already below `stopPx`, the stop is "at a better value than the current market price" and triggers without waiting (section 1.3), i.e. an immediate loss larger than planned. |
| Risk estimate | Size uses the signal close as the entry reference. A gap up at the open makes the real risk per share larger than `riskPct`. |
| Time exit | `maxBars = 15` → close order on the 15th bar's close, fill at the 16th bar's open. |
| Ratchet | The candidate `close - trailMult * atr` is recomputed on each close; `math.max` keeps the higher value; the new level works from the next bar. |
| Costs | 0.05% per side and 2 ticks of slippage are placeholders, not a calibrated cost model. |

### 5.3 Reference strategy B (compiles: 0 errors, 0 warnings) [COMPILE]

Resting buy-stop entry with expiry, another symbol and the weekly timeframe as filters only, structure stop, chandelier ratchet, time exit, sizing from the known trigger-to-stop distance, High bar detail because the entry and the stop can both trade inside one bar.

```pine
//@version=6
//@strategy_alert_message {{strategy.order.alert_message}}
// REF-B  Reference strategy B. A semantics demo, NOT a trading system. Long only.
// Shows: a resting buy-stop ENTRY that expires; another symbol and a higher timeframe used only as filters (orders
// always go to the chart symbol); a structure stop; a chandelier trail that only ratchets up; a time exit at the
// next open; fixed-fractional sizing from the known trigger-to-stop distance.
strategy("REF-B stop entry, market and weekly filters, chandelier ratchet, time exit, fixed-fractional risk",
     shorttitle = "REF-B", overlay = true,
     initial_capital = 100000, currency = currency.USD,
     default_qty_type = strategy.fixed, default_qty_value = 1,     // not used: every entry passes `qty`
     pyramiding = 1,
     commission_type = strategy.commission.cash_per_contract, commission_value = 0.005,
     slippage = 2,
     margin_long = 100, margin_short = 100,
     process_orders_on_close = false,
     calc_on_every_tick = false, calc_on_order_fills = false, calc_on_every_history_tick = false,
     use_bar_magnifier = true,                                     // the entry and the stop can both trade inside one bar
     fill_orders_on_standard_ohlc = true,
     close_entries_rule = "FIFO")

strategy.risk.allow_entry_in(strategy.direction.long)             // long only: an opposite entry can never reverse

string mktSym    = input.symbol("AMEX:SPY", "Market filter symbol")
int    mktLen    = input.int(200,   "Market filter SMA length", minval = 1)
int    wkLen     = input.int(30,    "Weekly trend SMA length", minval = 1)
int    swingLen  = input.int(5,     "Structure stop: lowest low of N bars", minval = 1)
int    atrLen    = input.int(14,    "ATR length", minval = 1)
float  trailMult = input.float(3.0, "Chandelier: ATR multiples below the highest high since entry", minval = 0.1, step = 0.1)
int    validBars = input.int(2,     "Buy-stop stays valid for N bars", minval = 1)
int    maxBars   = input.int(15,    "Time exit after N completed bars in the trade", minval = 1)
float  riskPct   = input.float(0.5, "Risk per trade, % of equity", minval = 0.01, step = 0.05)
float  maxPosPct = input.float(25,  "Max position value, % of equity", minval = 1, maxval = 100)

// Other contexts. They feed the decision; the strategy can place orders on the chart symbol only.
// `[1]` with lookahead_on returns the last COMPLETED bar of the requested context, the same on history and realtime.
float mktClose = request.security(mktSym, timeframe.period, close[1], lookahead = barmerge.lookahead_on)
float mktMa    = request.security(mktSym, timeframe.period, ta.sma(close, mktLen)[1], lookahead = barmerge.lookahead_on)
float wkClose  = request.security(syminfo.tickerid, "1W", close[1], lookahead = barmerge.lookahead_on)
float wkMa     = request.security(syminfo.tickerid, "1W", ta.sma(close, wkLen)[1], lookahead = barmerge.lookahead_on)

float atr      = ta.atr(atrLen)
float swingLow = ta.lowest(low, swingLen)

var bool  pending = false                                          // a buy-stop is resting
var int   setBar  = na
var float trigPx  = na
var float stopPx  = na                                             // resting stop-loss; it only moves up
var float hiSince = na                                             // highest high since entry

bool inPos      = strategy.position_size > 0
bool justClosed = strategy.closedtrades > nz(strategy.closedtrades[1])
if inPos or justClosed                                             // filled (or filled AND stopped inside one bar)
    pending := false
bool expired = pending and bar_index - setBar >= validBars
if expired                                                         // remove the unfilled buy-stop and its waiting exit
    strategy.cancel("B")
    strategy.cancel("B-stop")
    pending := false
if not inPos and not pending
    trigPx  := na
    stopPx  := na
    hiSince := na

// Setup on this bar's close -> resting buy-stop one tick above this bar's high, working from the next bar.
bool filtersOk = mktClose > mktMa and wkClose > wkMa
// `not expired`: do not cancel "B" and place a new "B" in the same execution.
bool setup     = not inPos and not pending and not expired and filtersOk and close > open and not na(atr) and not na(swingLow)
bool placed    = false
if setup
    float trig      = high + syminfo.mintick
    float initStop  = swingLow - 0.25 * atr
    float riskPerSh = (trig - initStop) * syminfo.pointvalue       // exact unless the fill gaps above the trigger
    if riskPerSh > 0
        float qtyRisk = strategy.equity * riskPct / 100 / riskPerSh
        float qtyCap  = strategy.equity * maxPosPct / 100 / (trig * syminfo.pointvalue)
        float qty     = math.floor(math.min(qtyRisk, qtyCap))
        if qty >= 1
            pending := true
            placed  := true
            setBar  := bar_index
            trigPx  := trig
            stopPx  := initStop
            string msg = "BUY-STOP " + syminfo.ticker + " at " + str.tostring(trigPx, format.mintick) + ", qty " + str.tostring(qty) + ", stop " + str.tostring(stopPx, format.mintick) + ", valid " + str.tostring(validBars) + " bars"
            strategy.entry("B", strategy.long, qty = qty, stop = trigPx, alert_message = "FILLED " + msg)
            alert(msg, alert.freq_once_per_bar_close)

// Chandelier ratchet, updated on each close while in the trade.
if inPos
    hiSince := math.max(nz(hiSince, high), high)
    stopPx  := math.max(stopPx, hiSince - trailMult * atr)

// Resting stop-loss, re-issued on every bar while an entry is pending or a position is open.
if placed or pending or inPos
    strategy.exit("B-stop", from_entry = "B", stop = stopPx, comment = "stop",
         alert_message = "STOP HIT " + syminfo.ticker + ", stop was " + str.tostring(stopPx, format.mintick))

// Time exit: market order created on this close, filled at the next bar's open.
int barsHeld = inPos ? bar_index - strategy.opentrades.entry_bar_index(strategy.opentrades - 1) + 1 : 0
if inPos and barsHeld >= maxBars
    strategy.close("B", comment = "time", alert_message = "EXITED " + syminfo.ticker + " (time)")
    alert("SELL " + syminfo.ticker + " at next open (time exit)", alert.freq_once_per_bar_close)

plot(pending ? trigPx : na, "Buy-stop trigger", color.teal, 1, plot.style_linebr)
plot(stopPx,                "Resting stop",     color.red,  2, plot.style_linebr)
bgcolor(filtersOk ? na : color.new(color.gray, 90), title = "Filters off")
```

Reading notes for B (**Derived**; not run on a chart):

| Point | Behaviour to expect |
|---|---|
| Orders only on the chart symbol | SPY and the weekly series are data inputs. There is no order parameter for a symbol (section 8). |
| Non-repainting requests | `expr[1]` with `barmerge.lookahead_on` is the form REP gives for confirmed higher-timeframe values. It is one bar late by construction. Request semantics belong to the companion report `pine_requests.md`. |
| Expiry | `validBars = 2` → the buy-stop can fill during the 2 bars after the setup bar, then is cancelled on the second bar's close. |
| Entry and stop in one bar | With Default detail the 4-tick path decides whether both fill; with High detail the 10m/30m/60m/1D intrabars decide. `justClosed` handles the case of a fill and a stop-out in the same bar. |
| Gap above the trigger | Fill at the open, so the real risk exceeds the sized risk. |

## 6. Sources of unrealistic results named by TradingView itself

| # | Source | TradingView's wording | Tag, source |
|---|---|---|---|
| 1 | Non-standard charts (Heikin Ashi, Renko, Kagi, Line Break, Point & Figure, Range) | "The strategy simulates trades using the chart's synthetic prices, which do not represent real-world market prices. Consequently, running a strategy on a non-standard chart typically produces unrealistic results." REP ranks "strategies that execute on non-standard charts" as "Unacceptable". Only Heikin Ashi has a fix (`fill_orders_on_standard_ohlc = true`); "This option has no effect on other non-standard chart types". | [DOC] STR; REP; FAQ-S |
| 2 | Renko look-ahead | "on a Renko chart the Strategy Backtesting Engine can enter/exit a position at a price that did not exist in reality." | [DOC] HC-PEEK |
| 3 | `request.security()` with `lookahead_on` and no offset | "it will return data from the future on historical bars, which is dangerously misleading." | [DOC] REP; HC-PEEK |
| 4 | `calc_on_order_fills` | "it may produce misleading backtest results, as the logic relies on data that would not be available in live trading until the market reaches the bar's closing tick." The report shows a warning banner when it is on. | [DOC] STR; HC-PEEK |
| 5 | `calc_on_every_tick` | "They will most probably not generate the same order executions, and so repaint. Note that when this happens, it also invalidates backtesting results" | [DOC] REP |
| 6 | `process_orders_on_close` / `immediately` | "entering the position on the same tick that the order is created can be misleading because that would not be possible to accomplish in real trading." | [DOC] HC-PROP; FAQ-S |
| 7 | The three settings together | "To avoid repainting, set the `calc_on_every_tick`, `calc_on_order_fills`, and `process_orders_on_close` parameters to `false` in the strategy() declaration statement." | [DOC] FAQ-S |
| 8 | Repainting inputs: unconfirmed higher-timeframe values, `varip`, `timenow`, `barstate.isnew` | "using unfixed data from a higher timeframe can cause repainting"; `varip` logic "cannot be backtested"; `timenow` scripts "necessarily repaint". | [DOC] FAQ-S; REP |
| 9 | Built-in trailing stops | "assumed price movements for historical bars. These assumptions can cause repainting." | [DOC] FAQ-S |
| 10 | Intrabar path guess | Default fills depend on the open → high → low → close (or low first) assumption; High detail replaces it where intrabar data exists. | [DOC] STR |
| 11 | No trading costs | "Without modeling the potential costs associated with their trades, traders may overestimate a strategy's historical profitability". Publishing rule: "Strategies without commissions or with unrealistic cost assumptions will not be approved". | [DOC] STR; HC-SPR |
| 12 | Too much slippage | "adding excessive simulated slippage can produce unrealistically worse testing results." | [DOC] STR |
| 13 | Limits that fill on touch | "in real-world trading, some limit orders might not fill when the market price reaches the specified value" | [DOC] STR |
| 14 | Unrealistic margin | "A margin of 0 is unrealistic in any circumstance, because it represents infinite leverage." Moderation checks "Adequate capital usage (disabling margin or other manipulations that inflate results are not allowed)". | [DOC] HC-PUB; HC-SPR |
| 15 | Too few trades | "Strategies must be tested on at least 100 trades"; "100 trades on weekly data carry more weight than 100 trades on minute data." | [DOC] HC-SPR |
| 16 | Unrealistic capital | "Use an initial capital amount that is relatively realistic for an average trader." | [DOC] HC-PUB |
| 17 | Selection bias | "cherry-picking" instruments, timeframes or testing ranges. | [DOC] STR |
| 18 | Overfitting | "A strategy that suffers from overfitting often fails to perform well on new, unseen data." Remedy named: in-sample / out-of-sample split. | [DOC] STR |
| 19 | Moving history start | "Strategy results can vary over time depending on where the historical data starts." Premium: 20,000 bars; 30-1439 minute charts align to the start of a year. | [DOC] FAQ-S; REP |
| 20 | Data revisions | "exchanges/brokers sometimes make what are usually small adjustments to bar prices"; history "may also be revised for other reasons, e.g., for stock splits." | [DOC] REP |
| 21 | Deep Backtesting vs chart | Different start bar gives different EMA/RMA values and different trades. | [DOC] HC-DB3 |
| 22 | Plotting in the past (pivots drawn with an offset) | "The display looks great, but it can be misleading." | [DOC] REP |

## 7. Strategy alerts

| Topic | Finding | Wording | Tag, source |
|---|---|---|---|
| Triggers available | Order-fill events (no code needed), `alert()` calls, or both, chosen in the Create Alert dialog. `alertcondition()` does nothing in a strategy. | "Pine Script strategies cannot create alert triggers using the alertcondition() function, but they can create triggers with the alert() function." FAQ-A: other script types "do not raise a compilation error ... but each call has no effect." | [DOC] STR; FAQ-A; [COMPILE] compiles in a strategy |
| Order-fill timing | Fires at the moment the emulator fills, regardless of execution settings. | "Alerts from order fill events execute immediately, regardless of the script's execution settings." | [DOC] STR |
| `alert()` timing in a strategy | Only on a realtime bar's close by default. | "By default, strategy scripts execute alert() function calls only on the close of realtime bars, as if they used the alert.freq_once_per_bar_close frequency, regardless of the `freq` argument in the call." | [DOC] STR |
| History | No notifications for historical fills. | "Notifications are not sent for orders on historical bars. Alerts are only triggered for orders executed in realtime." | [DOC] HC-SA |
| Server copy | The alert runs a frozen copy; later edits or setting changes need a new alert. | "When an alert is created for a strategy, a copy of the strategy is created on our servers. ... you will need to delete the previous alert and create a new one." | [DOC] HC-SA |
| Rate limit | | "the alert will be stopped if it triggers more than 15 times in 3 minutes." | [DOC] HC-SA |
| Alert quota | One strategy alert covers all its order fills. | "if a user creates a strategy alert based on order fill events, it counts as one alert, even though it can fire multiple times with distinct messages from different order executions." | [DOC] FAQ-A |
| `alert_message` | Series string on `strategy.entry`, `strategy.order`, `strategy.exit`, `strategy.close`, `strategy.close_all`; `strategy.exit` also has `alert_profit`, `alert_loss`, `alert_trailing`; `strategy.risk.max_*` take `alert_message`. Shown only if the alert's Message field contains `{{strategy.order.alert_message}}`. | "Variables included in the `alert_message` argument are evaluated when the order is executed, so when the alert triggers." "While other placeholders can be used in the 'Create Alert' dialog box's 'Message' field ... they cannot be used in the argument of `alert_message`." | [DOC] ALR; REF; [COMPILE] |
| Default message | `//@strategy_alert_message <text>` above `strategy()` pre-fills the Message field; it "allows text and strategy placeholders, but not script variables". | | [DOC] STR; FAQ-A; [COMPILE] |
| `disable_alert` | Series bool on every order command; suppresses the fill alert for that order. | | [DOC] REF; FAQ-S; [COMPILE] |
| `process_orders_on_close` and alerts | Still arrives after the close. | "the alerts still occur after the session closes ... real-world orders based on such alerts might not fill until after the market opens again." | [DOC] STR |

Strategy-only placeholders (usable in the Message field and in `//@strategy_alert_message`): [DOC] HC-SA, HC-PH

| Placeholder | Returns |
|---|---|
| `{{strategy.order.action}}` | "buy" or "sell" for the executed order |
| `{{strategy.order.contracts}}` | number of contracts of the executed order |
| `{{strategy.order.price}}` | price at which the order was executed |
| `{{strategy.order.id}}` | ID of the executed order |
| `{{strategy.order.comment}}` | comment of the executed order; the ID if no comment |
| `{{strategy.order.alert_message}}` | the `alert_message` argument |
| `{{strategy.position_size}}` | signed current position size |
| `{{strategy.market_position}}` | "long", "flat" or "short" |
| `{{strategy.market_position_size}}` | absolute current position size |
| `{{strategy.prev_market_position}}` | previous position: "long", "flat" or "short" |
| `{{strategy.prev_market_position_size}}` | absolute previous position size |

General placeholders also work: `{{ticker}}`, `{{exchange}}`, `{{interval}}`, `{{open}}`, `{{high}}`, `{{low}}`, `{{close}}`, `{{volume}}`, `{{time}}`, `{{timenow}}`, `{{plot_0}}`..`{{plot_19}}`, `{{plot("title")}}`, `{{syminfo.currency}}`, `{{syminfo.basecurrency}}`. [DOC] HC-PH

**Derived** for a trader who acts on alerts by hand (not tested): a market order created on a daily close fills, in the simulation, at the next session's open, and that is when its order-fill alert fires, too late to be the instruction. The instruction has to come from an `alert()` call on the signal bar's close (both reference scripts do this); order-fill alerts then serve as confirmations and as stop-hit notices. The server copy also keeps its own simulated position: if the trader skips a trade, the alert's strategy is still "in" it and will send exits for a position that does not exist.

## 8. Other symbols and multi-symbol testing

| Question | Answer | Evidence | Tag |
|---|---|---|---|
| Can a strategy read other symbols or timeframes with `request.security()`? | Yes. | REF-B compiles with a second symbol and a weekly request. OTF describes requesting Renko prices inside a `strategy()` script "to calculate its signals without calculating the strategy results on them". `dynamic_requests` is a `strategy()` parameter. | [COMPILE]; [DOC] OTF, REF |
| How many requests? | Same as indicators. | "A script can use up to 40 unique calls to the functions in the `request.*()` namespace, or up to 64 unique calls if the user has the Ultimate plan." | [DOC] LIM |
| Can it place orders on another symbol? | No. | "Pine strategies run on only the chart asset and cannot open positions in different assets." REF: "Strategies always use the chart's prices to enter and exit positions." Compiler: `The "strategy.entry" function does not have an argument with the name "symbol"`. | [DOC] FAQ-S, REF; [COMPILE] |
| Can it hold long and short at once, or hedge? | No. | "Pine strategies can only have positions open in one direction at a time, either long or short." | [DOC] FAQ-S |
| Can one strategy be backtested across many symbols with shared capital (portfolio backtest)? | No. | "Each Pine Script strategy runs on one dataset at a time." | [DOC] FAQ-S |
| TradingView's stated workaround | Switch the chart symbol by hand, use a watchlist, export each report and compare outside. | "Export the results from the strategy report and use external tools such as spreadsheet software to compare the performance of a strategy on different symbols." Exports: "Download data as XLSX"; trade list as CSV. | [DOC] FAQ-S, STR |
| Can a strategy run on a different timeframe than the chart? | No `timeframe` parameter. | Compiler: `The "strategy" function does not have an argument with the name "timeframe"`. | [COMPILE] |
| Can the Pine Screener run a strategy over a watchlist? | No. | "the Pine Screener supports only indicator scripts that contain at least one `plot*()` or alertcondition() call" | [DOC] RN August 2026 |
| Several strategies on one chart | Allowed, but "The report displays performance results for only one strategy at a time." | | [DOC] STR |
| Can a strategy route orders to a broker or the paper account? | No. | "Pine Script does not support placing orders using the brokers integrated via the Trading Panel, or using TradingView's built-in paper trading account." | [DOC] FAQ-S |
| Portfolio simulation written by hand inside one script (an indicator that requests up to 40 symbols and keeps its own equity) | Possible in principle; it is not the strategy report, has no broker emulator, and inherits every `request.security()` limit. A community script titled "Portfolio Backtester Engine" appeared in a search-result listing (https://tw.tradingview.com/scripts/search/backtesting/page-2); a third-party guide describes the run-per-symbol-and-merge-CSV route (https://pineify.app/tradingview/backtesting/multiple-symbols). Neither page was opened or checked. | Search result titles only | [SECONDARY] |

## 9. Settings this project should use (recommendations derived from sections 1-8)

| Setting | Value | Reason (source row) |
|---|---|---|
| Chart type | Standard candles only | section 6 row 1 |
| `process_orders_on_close`, `calc_on_every_tick`, `calc_on_order_fills` | all `false` | section 6 row 7; matches a signal on the close acted on at the next open |
| `initial_capital`, `default_qty_type`, `default_qty_value` | always explicit; pass `qty` on each entry | section 4.1 (sources conflict) |
| `margin_long`, `margin_short` | 100 | section 4.4; section 6 row 14 |
| `commission_*`, `slippage` | non-zero, justified per instrument | section 6 row 11 |
| `use_bar_magnifier` | `true` whenever two price-based orders can meet in one bar; run both and compare | section 2 |
| Stops | custom ratchet via `strategy.exit(stop =)` re-issued each bar; no built-in trail | section 5.1; section 6 row 9 |
| Sample | at least 100 trades; in-sample / out-of-sample date gate | section 6 rows 15 and 18 |
| History on 1h charts | Deep Backtesting (Premium), knowing its numbers differ from the chart run | section 3 |
| Multi-symbol evidence | run per symbol, export CSV, aggregate outside TradingView | section 8 |
| Alerts | `alert()` on the signal bar's close for the instruction; order fills as confirmation | section 7 |

## 10. Conflicts between official sources (shown, not resolved)

| Topic | Source A | Source B |
|---|---|---|
| Default `initial_capital` | REF v6: 100000 | HC-PROP: 1,000,000 (REF5: 1000000) |
| Default order size | REF v6: `strategy.percent_of_equity`, 100 | REF5: `strategy.fixed`, 1. No release note found for the change. |
| Default `pyramiding` | REF v6: 0 | STR: 1 (same behaviour) |
| 9000 limit counts | STR: trades | LIM and REF: orders |
| Deep Backtesting cap | HC-DB2: "one million trades" | LIM: "order limit is 1,000,000" |
| Magnifier intrabar budget | STR, HC-BM: 200,000 lower-timeframe bars | LIM: 100K intrabars for Premium via `request.*` (may not apply to the magnifier) |
| Magnifier intrabar timeframes | HC-BM, HC-DET (current): 60→10, 240→30, 1D→60, 1W→1D | BLOG-BM (2022): 60→5, 240→15, D→60, W→120 |
| Slippage scope | REF, HC-BE: "market/stop orders", "market and stop orders" | STR: "the strategy applies constant slippage to all order fills" |
| UI names | HC-PROP still says "Recalculate", "Fill orders", "Margin for long positions" | RN July 2026 renamed them (Script execution, Order execution delay, Long leverage) |

## 11. Compiler log (11 of 15 calls used, all on 2026-11-11)

| # | File | Result | What it establishes |
|---|---|---|---|
| 1 | `ref_a.pine` | OK, 0 errors, 0 warnings | Section 5.2 source is valid v6 |
| 2 | `ref_b.pine` | OK, 0 errors, 0 warnings | Section 5.3 source is valid v6; `request.security()` of another symbol and timeframe inside a strategy |
| 3 | `probe_exists.pine` | OK, 0/0 | `calc_on_every_history_tick`, `use_bar_magnifier`, `backtest_fill_limits_assumption`, `fill_orders_on_standard_ohlc`, `close_entries_rule`, `risk_free_rate`, `calc_bars_count`; all six `strategy.risk.*` (with `alert_message`); `strategy.default_entry_qty`, `strategy.closedtrades.first_index`, `strategy.margin_liquidation_price`, `strategy.opentrades.capital_held`, `strategy.convert_to_account/symbol`, `syminfo.mincontract`; `immediately`, `disable_alert`, `alert_profit/loss/trailing`, `comment_profit/loss/trailing`, `trail_price/points/offset`, `oca_name/oca_type`; `//@strategy_alert_message` with all eleven strategy placeholders |
| 4 | `probe_when.pine` | FAIL CE10120 | `when` is gone from `strategy.entry` in v6 |
| 5 | `probe_symbol.pine` | FAIL CE10120 | no `symbol` argument on `strategy.entry` |
| 6 | `probe_tf.pine` | FAIL CE10120 | no `timeframe` argument on `strategy()` |
| 7 | `probe_alertcondition.pine` | OK, 0/0 | `alertcondition()` compiles in a strategy (docs: it has no effect there) |
| 8 | `idioms.pine` (first version) | OK, 0 errors, 2 warnings CW10002 | `ta.*` inside a lazily evaluated `and` |
| 9 | `idioms.pine` (fixed) | OK, 0/0 | every code cell of table 5.1 |
| 10 | `probe_defaults.pine` | OK, 0/0 | bare `strategy("x")` compiles |
| 11 | `probe_defaults.pine` (raw response) | OK | the endpoint returns no property metadata, so runtime defaults cannot be read this way |

## 12. Not verified today

| Item | Status |
|---|---|
| Runtime behaviour of both reference strategies (fills, stop timing, alerts) | Compiled only; never run on a chart |
| Real runtime defaults of `initial_capital`, `default_qty_type`, `default_qty_value` in v6 | Official sources conflict; compiler exposes nothing |
| Path rule when the open is exactly midway between high and low | Not in the pages read |
| Whether the Bar Magnifier's intrabar budget on Premium is 200K or 100K, and its current depth in Deep Backtesting | Sources conflict or are dated (2023) |
| How far back 10m / 30m / 60m data exists for US stocks (decides real magnifier coverage) | Not checked |
| Whether 9000 counts trades or orders | Sources conflict |
| How a percent-of-equity order is sized against the unknown next-open price, and whether commission is reserved in that size | Not found |
| Which print TradingView uses as a US stock's daily open (auction or first trade) and how extended-hours settings change "next bar open" on intraday charts | Not checked; matters when comparing simulated and real fills |
| Dividend and split adjustment effects on simulated fills | Not checked; REF only says strategies "always use the chart's prices" |
| What happens to `use_bar_magnifier = true` on a plan without the feature | Docs state a runtime error only for `calc_on_every_history_tick` |
| Plan table on the pricing page for Deep Backtesting / bar detail | Not opened; plan statements here come from the manual and Help Center |
| Community portfolio-backtest scripts | Listed, not examined |
