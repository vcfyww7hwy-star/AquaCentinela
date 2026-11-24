# Playbook: using the suite (v2)

Read this with the evidence in mind (`06_validation_lite.md`): no rule in this suite has a confirmed
trading edge. The tools organise three things that the tests do support: staying out when the
long-term trend is down, buying weakness instead of strength inside uptrends, and capping the loss
on every trade. Trade small, and keep records.

## Chart set-up (once)

1. Use a US stock or ETF chart with regular trading hours only (extended hours off).
2. Add **Trend & Setups v2** (on the price chart) and **Relative Volume v4** (pane). When you paste a
   script into a new Pine Editor tab, select all and delete TradingView's starter template first;
   otherwise you get error CE10243 (two declaration statements).
3. In Trend & Setups v2 → Risk and exits, set **Account size** and **Risk per trade (%)**. Start
   with 0.5–1%. Leave **Largest position** at 25% or lower.
4. Alerts, one per symbol: condition **Trend & Setups v2 → "Any alert() function call"** sends each
   entry (with stop and size) and each exit. Add **"T&S2 long-term trend turned down"** for the
   stocks you hold.

Only the Daily chart with the Weekly long-term trend is tested. On 1h, 4h and Weekly charts the
same logic runs, but nothing there is validated.

## Reading the chart

| Element | Meaning | What to do with it |
|---|---|---|
| Baseline colour and the first table row | Long-term trend: Up (blue), Neutral (grey), Down (orange) | **Down = stand aside.** No new longs; consider closing. This is the best-supported rule in the suite |
| Shaded background | Long-term trend is Down | Same |
| "This chart", 1h / 4h / Daily / Weekly rows | Trend state per timeframe | Information. It did not predict returns in tests |
| Market, Strength vs market | The benchmark's trend; the stock relative to it | Information |
| 5-bar move | The last five bars' return in risk units | At −1.5σ or lower inside a long-term uptrend, the D setup fires |
| Green **D** | Dip in a long-term uptrend, bought at this close | Candidate entry. Label shows entry, stop, 1R and size |
| Pink line | The stop order level for the tracked trade | Move your stop order to it after each bar. It only goes up |
| Pink **X** | Exit: stop, trailing stop, long-term trend turned down, or time exit | Close the trade |
| Small green dot | A setup fired while a trade was already being tracked | Information |
| "If I buy this close" | Stop (2 ATR) and size for an entry on the current bar | Use it for entries you choose yourself |
| Relative Volume columns | This bar's volume ÷ normal for this stock and time of day. Stronger colour = unusual for this stock (about the busiest 4% of bars); grey = bar in progress | Context only. It does not predict direction |
| Orange line (intraday) | Session pace: volume so far ÷ normal by this time of day | How the day is running. Near the close it equals the day's relative volume |
| Tinted background in the volume pane | Quarterly expiry or Russell reconstitution day | Heavy volume that day is mostly mechanical: about 37% of stocks trade at unusual volume, against 3.5% on other days. No volume alert is sent that day (input) |

## Data feed checks (once, about fifteen minutes over two days)

TradingView's default US feed without paid exchange data comes from the Cboe exchanges, about a
tenth of the market's volume. What that does to the volume you see is not documented, and the script
cannot see which feed it runs on. Check it:

1. **Which feed.** Look at the marker beside the symbol name on the chart: a red Cboe marker, or a
   "D" for delayed, means you are not on the primary exchange's real-time data.
2. **Closed daily bars.** Compare yesterday's daily volume of two large stocks with your broker's
   figure. Within about 5% is fine; a ratio near 0.1 means partial volume.
3. **The bar in progress.** At a fixed time (say 11:00 New York) compare today's volume on the daily
   chart with your broker's cumulative volume. A ratio near 0.1 means the live bar is partial.
4. **Intraday history.** On a 1h chart with regular trading hours the last table row shows
   yesterday's bars ÷ yesterday's daily bar. 0.6 to 1 is normal, because the daily bar includes the
   closing auction (about 0.45 the day after a quarterly expiry). Below 0.3 means the intraday
   history is partial.
5. **The bar at the moment it closes.** Just after the close (16:05 New York) write down today's
   daily volume of three stocks. Read the same three bars the next morning. If the next-day figures
   are more than about 5% higher, a daily bar closes with less volume than the chart later shows, and
   the alerts on daily bars will fire less often than the chart suggests. In that case set "Unusual
   volume at zV ≥" a little lower for alerts (1.75), or rely on the next morning's Pine Screener run.

If check 2, 3 or 4 fails, the real-time NASDAQ, NYSE and NYSE Arca data cost about 3 dollars a month
each (confirm on TradingView's page). Until the checks pass, read relative volume on closed bars
only and do not rely on its alerts.

## Volume alerts

- **One line with the numbers.** Create an alert on Relative Volume v4 with the condition "Any
  alert() function call". Each unusual-volume bar then sends one line: relative volume, zV, the bar's
  move in % and σ, the close and the stock's dollar volume per day. The inputs choose unusual or
  extreme volume, and whether the session pace is included.
- **Separate conditions.** "RVOL4 unusual volume", "RVOL4 extreme volume" and "RVOL4 session pace"
  can be chosen one by one; their messages carry the same numbers, unformatted.
- **Session pace (1h chart, regular hours).** An early warning that the day is running hot: once per
  session, when the volume so far is 2.5 spreads above normal for that time of day. About 4 stocks
  in 100 alert on a day; 63% of those days end with unusual volume on the daily chart.
- **Fewer alerts.** On a normal day about 4 stocks in 100 have unusual volume. The input "Volume
  alert only if the bar moved at least" thins them: 1.5σ keeps 53%, 2σ keeps 42%. It only reduces the
  count; bars that pass were not found to continue or reverse.
- **Pine Screener.** Columns RVOL, zV, Move, Pace, Pace z, Bars since unusual, Turnover per day.
  Filter on "Bars since unusual" (0 after the close, 1 while a bar is in progress = the last closed
  bar was unusual): the live bar's own values are partial. Use it on 1h and above.
- **What an alert means.** Something happened in that stock: look at the news and at the chart. It
  says nothing about direction.

## Before taking a D signal

1. Long-term trend is **Up** (the signal requires it).
2. The move is a dip, not a collapse: check the news. A dip on an earnings miss or a guidance cut is
   a different thing from a market-wide wobble.
3. "Next earnings" in the table is not within the next few days, or you accept the gap risk.
4. Use the label's numbers. Place the stop as a real order.
5. You already hold fewer positions than your limit, and they are not all the same sector: dips
   arrive together, and so do the losses when a dip keeps going (2001, 2002, 2008).

## Managing the trade

- After each bar, move the stop order up to the pink line.
- After a bar of unusual volume, keep using the stop from the pink line: the ATR already widened
  with that bar, and tests found no reason to widen it further.
- Exit on the X. If the long-term trend turns Down, exit at that close.
- The tested bounce is strongest in the first five bars. If the trade has gone nowhere after two
  weeks, the reason you entered has expired; the optional time exit automates this.

## Records

Log every signal you take and every one you skip: date, symbol, setup, entry, stop, exit, R, and
why you skipped. Thirty logged trades will say more about these rules in your hands than any
backtest in this repository.
