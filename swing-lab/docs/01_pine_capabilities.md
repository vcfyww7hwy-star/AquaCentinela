# What TradingView and Pine can do for this trader: the facts the build used

Synthesis, 11 Nov 2026 (UTC), of four reports in `_raw/` (`pine_language.md`, `pine_requests.md`,
`pine_plans.md`, `pine_strategy.md`). Those reports were written on 10-11 Nov 2026 from
TradingView's own documentation, pricing page and help centre, with small compile tests against
the live compiler. Tags: **[DOC]** quoted from documentation; **[COMPILE]** confirmed by the
compiler; **[MEASURED]** measured on public TradingView data that day. Nothing here was verified
on a logged-in chart. The synthesis agents planned for this file did not finish (usage limit), so
this is a selection, not a complete digest: the raw reports hold the quotes and URLs.

## Language and limits

| Fact | Tag |
|---|---|
| Current language version: Pine Script v6 | [DOC], [COMPILE] |
| Premium: up to 40 unique `request.*()` calls per script; 20,000 bars on an intraday chart; all history on daily and above | [DOC] |
| A tuple or a user function may be the expression of `request.security()`; both scripts use this | [COMPILE] |
| The documented non-repainting form for a higher timeframe is `expression[1]` with `lookahead = barmerge.lookahead_on` | [DOC] |
| Requesting "1D" from a weekly chart is a lower-timeframe request: `request.security()` then returns the last daily bar inside the chart bar (`lookahead_off`) | [DOC] |
| `alert()` with `alert.freq_once_per_bar_close`, inside `barstate.isconfirmed`, fires once at a bar's close; alerts fire on realtime bars only | [DOC] |
| An alert runs on a snapshot of the script and its inputs; editing either does not change a running alert | [DOC] |

## Data a script can and cannot see

| Data | Available | Tag |
|---|---|---|
| The chart symbol's OHLCV and any other symbol's, on any supported timeframe | yes | [DOC] |
| Next earnings date: `earnings.future_time` (fetched once when the script loads) | yes, live only | [DOC], [COMPILE] |
| Past earnings: `request.earnings()`, aligned to the bar of publication; time of day not given | yes | [DOC] |
| Fundamentals: `request.financial()` | yes, but not point-in-time: unusable for backtests | [DOC] |
| FINRA daily short-sale volume: `FINRA:<TICKER>_SHORT_VOLUME`, daily, from 2018-08-01 | yes | [DOC]; tested in the research and found useless |
| Short interest, options, analyst revisions, news, order flow | no | [DOC], [COMPILE] (the functions do not exist) |
| Breadth series such as `INDEX:S5TH` | yes, end of day | [DOC] |
| User-supplied data (Pine Seeds) | suspended | [DOC] |

## Bars and feeds

| Fact | Tag |
|---|---|
| Without paid exchange data, US stock charts use the Cboe One feed. Settled daily bars carry consolidated volume; intraday bars carry about 4-12% of it | [DOC], [MEASURED] |
| In the minutes after 16:00 the realtime daily bar can show a slightly different close and a lower volume than the settled bar (AAPL: 355.79 against 355.63) | [MEASURED] |
| A 4h chart of a US stock in the regular session has two bars a day: 09:30-13:30 and 13:30-16:00 | [MEASURED] |

Consequence for the scripts: they take every number from daily bars, use volume only through a
60-day median of daily dollar volume, and define the stop as a distance from the actual fill, so
a few cents of difference in the close do not matter.

## Alerts, screeners, exports (Premium)

| Fact | Tag |
|---|---|
| 400 price alerts, 400 technical alerts, 2 watchlist alerts (up to 1,000 symbols each; cannot be open-ended) | [DOC] |
| All `alert()` calls of one script on one symbol cost one technical alert | [DOC] |
| Pine Screener: runs one indicator over a watchlist; filters on its plots; last 500 bars only; ignores `input.symbol()`, `input.timeframe()` and `input.time()`; scan on demand; no alerts | [DOC] |
| Chart data export (Plus and above): every loaded bar, the main series and every plot of every visible indicator, including plots shown only in the Data Window; not plots set to `display.none` | [DOC] |

## Strategy Tester

| Fact | Tag |
|---|---|
| A market order placed at a bar's close fills at the next bar's open | [DOC] |
| `strategy.exit(..., loss = ticks)` places the stop that distance from the actual fill and it is live from the entry bar | [DOC], [COMPILE] |
| A stop gapped through between bars fills at the open of the bar after the gap | [DOC] |
| `strategy.close(..., immediately = true)` fills at the close of the bar on which it is called | [DOC], [COMPILE] |
| Inside a bar the emulator assumes open, high, low, close when the open is nearer the high, and open, low, high, close otherwise | [DOC] |

`sl_odds_check.pine` uses exactly these four rules, which are also the rules of the research
simulator (`research/swinglab/trades.py`).
