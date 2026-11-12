# Playbook: using SL Risk Desk, SL Portfolio Desk and SL Odds Check

12 Nov 2026 (UTC). Evidence tags, the same letters the scripts print: **D** demonstrated out of
sample (frozen before, and passed on, the data set aside for 2023-2026); **C** checked once on
2023-2026 with constants committed beforehand, outside the pre-registered list; **S** suggestive;
**U** untested. Sources: `RESEARCH_LOG.md` entries 5-8, `02_research_map.md`.

## What the scripts are, and are not

They do not tell you what to buy or when. In this research no chart rule that does so survived
data it had not seen (`02_research_map.md`, section 1). What survived is the arithmetic of risk,
and that is what the scripts put on the chart.

| Script | Question it answers | Where |
|---|---|---|
| **SL Risk Desk** (indicator) | One stock: how many shares, where the stop goes and how often noise hits it, how far the price usually travels, earnings, index state. After you buy: R, day count, stop | The chart of the stock; any timeframe |
| **SL Portfolio Desk** (indicator) | The whole book: every position's R, day, money still at risk and earnings; total exposure and open risk; how far the book usually moves; how many independent bets it really is | Any one daily chart, for example SPY |
| **SL Odds Check** (strategy) | An audit: reruns the stop-out experiment in TradingView's Strategy Tester on any symbol | A daily chart; remove it after looking |

Where the stock comes from is your decision (a thesis, a sector view, a fundamental reason). The
forward test at the end measures whether that decision adds anything.

## Install

1. TradingView > Pine Editor > Open > New indicator. Delete the template, paste the whole of
   **SL Risk Desk**, Save, **Add to chart**.
2. The same for **SL Portfolio Desk**, on a daily chart of SPY (any symbol works).
3. Open > New strategy > paste **SL Odds Check** > Save > Add to chart, on a daily chart.
4. The first load is a test: the scripts compile and their arithmetic is checked, but they have
   not run on a chart yet. If the editor or the chart shows an error, copy the message and the
   line number.

## SL Risk Desk: what you see

Schematics drawn from the script's own arithmetic on real bars (not TradingView screenshots):
`img/risk_desk_plan.png` before a trade, `img/risk_desk_position.png` once you hold.

| # | Element | How to read it | Tag |
|---|---|---|---|
| 1 | **The cone** to the right of the last bar | Where the close lands at the end of the holding period. Solid outer lines: 9 closes in 10 fall between them. Dotted inner lines: 1 close in 2. Each line carries its price; the outer ones also their distance in R. On a daily chart the cone runs h bars ahead; on other timeframes it is a block of levels | D |
| 2 | **The red dashed line** | The stop: k ATR below the last price before the trade, your own stop once you hold | arithmetic |
| 3 | **The amber dashed line** inside the cone | The next earnings report, shown when it falls inside the holding period | date from TradingView |
| 4 | **The table** | The same things in numbers, in sections: PLAN (or POSITION), RANGE, EVENTS. Hover a row for its meaning. The letter at the right of a row is its evidence tag | - |
| 5 | **Entry line, shaded bars, "day h"** (position mode) | The price you paid, the bars you have held, and the bar on which the holding period ends | arithmetic |
| 6 | **The envelope** (off by default) | The 90% band drawn h bars ago, plotted at the bar it was aiming at; a dot marks a close outside it, about 1 bar in 10. A report card for the bands, not a signal. It widens the price scale | measurement |

If the cone is cut off at the right edge, drag the chart to the left or raise Settings > Canvas >
Margins > Right margin to about 25 bars.

### The table, row by row

| Row | Meaning | Tag |
|---|---|---|
| **Buy** | Shares = risk budget / stop distance, capped by the largest position; then its value and its share of equity. Every position risks the same money whatever the stock | arithmetic |
| **Stop** | The stop price if you were filled at the last price, and the distance to keep below your actual fill | arithmetic |
| **At risk** | What the trade loses if the stop fills at its price. About 15% of stops fill below it and about 1 trade in 100 loses more than 1.5 times this | D |
| **Stop hit by noise** | How often a stop at this distance is hit inside the holding period by a stock bought for no reason at all | D at 1, 1.5, 2, 2.5, 3, 4 ATR (within 1.7 points on 2023-26); a straight line in between |
| **9 in 10** | The outer lines of the cone, as prices and in R (against the planned stop before the trade, against your entry and stop once you hold) | D (89.6-89.9% on 2023-26) |
| **1 in 2** | The dotted lines of the cone | D (48.8-50.0%) |
| **This stock** | The same three figures measured on this symbol's own history: how often its 90% band held, its middle half, and how often this stop was hit. Below 85% on the first, the stock jumps more than most | measurement |
| **Earnings** | Sessions to the next report, and whether it falls inside the holding period | date from TradingView |
| **Earnings night** | About 1 report in 10 opens more than 2 ATR against the holder (1 in 5 beyond 1 ATR, 1 in 20 beyond 3 ATR; by year 15-27%, 5-15%, 3-8%) | the multiple over an ordinary night (at least 20 times) is D; the exact odds are U |
| **Index** | SPY above or below its 200-day average. Below, the index has been about twice as volatile. It has NOT meant lower returns, and on 2023-26 it did not mean more losing stocks | S |
| **Universe** | "inside": a stock at $5 or more with $20M or more traded a day (60-day median). Outside it the odds were not tested | - |
| **Now**, **Entry / stop**, **Result** (position mode) | R = (price - entry) / (entry - stop); day n of h, day 1 being the entry day; money so far and at the stop | arithmetic |

All values are daily values: on a 1h or 4h chart those of the last completed day, on a weekly
chart those of the last daily bar.

### Inputs

| Group | Input | Default | What to put |
|---|---|---|---|
| 1 Plan | Account equity | 100,000 | Your trading account, in the chart's currency |
| | Risk per trade, % of equity | 0.75 | What you accept to lose if the stop fills at its price |
| | Stop distance, in daily ATR(14) | 3 | 1 to 4. See "Choosing the stop" |
| | Holding period, daily bars | 10 | 5, 10 or 20 |
| | Largest position, % of equity | 20 | A cap for quiet stocks |
| 2 Open position | I hold this stock; entry price; stop price; shares held; entry date | off | Fill in after you buy |
| 3 Alerts | Send the plan at each daily close | off | On for a stock you will buy at the next open |
| 4 Look | Cone, envelope, stop level; table Full / Compact / Off; position; text size; colours | cone and stop on, envelope off, Full, bottom left | Compact once you know the table |
| 5 Market | Index reference | AMEX:SPY | Leave |

## The routine, step by step

**Before buying** (the evening before, daily chart of the stock)

1. Read **Universe**: if it says OUTSIDE, the odds below do not apply.
2. Read **Earnings**: if it says INSIDE the period, decide now (see "Earnings").
3. Read **Buy** and **Stop**: that is the order ticket. Buy that many shares at the open; place the
   stop the stated distance below your actual fill.
4. Look at the cone against your target. If the target is beyond the 95% line, it is a 1-in-20
   outcome within this holding period: lengthen the period or lower the target.
5. Turn on "Send the plan at each daily close" and create the alert if you want the ticket on your
   phone at the close.

**After the fill**

6. Settings > Open position: tick "I hold this stock", type the entry price, the stop price
   (fill minus the distance), the shares and the date. The table switches to POSITION.
7. Delete the old alert and create a new one (an alert keeps the inputs it was created with).
8. Add the position to SL Portfolio Desk.

**While holding** (alerts do the watching)

9. "Traded at or below your stop": check that the broker's stop executed.
10. "Earnings inside the holding period": decide per "Earnings".
11. "Holding period complete": exit, or decide deliberately to start a new period, with a new
    stop and a new day 1.

**After closing**

12. Untick "I hold this stock", remove the row from SL Portfolio Desk, log the trade's R.

## Choosing the stop

| Stop | Hit within 10 bars by noise (D) | What the evidence says |
|---|---|---|
| 1 ATR | 60% | You will be stopped out of most trades for no reason |
| 2 ATR | 32% | One trade in three |
| 3 ATR | 17% | One in six. Against no stop at all it gave up 0.6-1.1 bp per day held in three samples and gained 0.3 in the fourth; never significant (S) |
| 4 ATR | 8% | One in twelve |

A 2-ATR stop gave up 0.6-1.6 bp per day held against no stop, and an exit on a close under the
20-day average 1-3.8 bp, in all four samples; the differences never reached significance (S). A
stop is insurance against the tail. It does not improve the average, and it does not bound the
loss: 15% of stop exits were filled below the stop, and the worst trade in the 2023-26 simulation
lost 132 times its planned risk (D).

Because the stop is k ATR and the size is risk / (k ATR), a wider stop means fewer shares and the
same money at risk. The cost of a wide stop is a smaller position, not a bigger loss.

## What the cone is for

- **A target check.** With a 3-ATR stop and 10 bars, the 95% line is at +1.16 R. A plan that needs
  +2 R in two weeks needs a 1-in-100 outcome (U). Either hold longer (20 bars: +1.65 R at the 95%
  line) or accept that the target is a hope.
- **A sanity check on news.** A close outside the 90% band happens 1 time in 10 by chance. Outside
  it, something happened; inside it, probably nothing did.
- It is nearly symmetric around a small positive drift and says nothing about direction.

## Earnings

A report inside the holding period changes the trade. About 1 report in 10 opens more than 2 ATR
against the holder: with a 3-ATR stop that is -0.67 R or worse before the stop can act, and 1 in
20 opens beyond the stop itself. Three consistent choices:

| Choice | When |
|---|---|
| Exit before the report | The default if the report was not the reason for the trade |
| Hold with half size | If you want the exposure: size as if the stop were 6 ATR |
| Hold full size | Only if you accept a 1-in-20 loss of more than 1 R on that night |

There is no evidence in this research that the reaction can be traded after the fact: strong
positive reactions drifted +71 bp over 20 bars on 2018-22 and +7 bp on 2023-26; bad ones did not
keep falling.

## The index state

When SPY is below its 200-day average, expect index moves about twice as large (S). Sizing by ATR
already absorbs most of this stock by stock, since ATR rises with it. The script therefore
reports the state and does not change the size. Over a century the rule "own stocks only above the
200-day average" cut the worst drawdown from -84% to -40% (Kenneth French library, 1926-2022,
context only) and it has cost return in every bull decade.

## SL Portfolio Desk

Schematic: `img/portfolio_desk.png`.

Put it on one daily chart. Settings > Inputs: for each position the symbol, then shares, entry and
stop on one line, then the entry date. A row is on when its shares are above 0.

| Column | Meaning |
|---|---|
| % of equity | Shares x last close / account equity |
| Result | R = (close - entry) / (entry - stop) |
| Day | Daily bars since the entry date, entry day = 1, of the holding period |
| At risk | What the position still loses if its stop fills at its price, as % of equity |
| Earnings | Sessions to the next report; red when inside the holding period |
| Status | STOP TOUCHED (today's low reached the stop), EARNINGS, TIME UP, or ok |

| Book row | Meaning | Tag |
|---|---|---|
| Invested | Sum of the positions over equity; above 100% the book is leveraged | arithmetic |
| Open risk | What the book loses from here if every stop fills at its price; the alert limit is an input (default 6%) | arithmetic; stops gap (D) |
| Range, 9 in 10 and 1 in 2 | How far the whole book usually moves over the holding period if nothing is sold, from each position's ATR and the correlations of the last 60 days | C: on 2023-26 the bands held 88.9-90.2% and 45.9-49.8% for books of 2 to 10 positions. The band does not capture the crash tail: in 2018-22 the 5% line should have been about 15% lower |
| Diversification | The number of independent positions the book behaves like, and the average correlation. Ten positions that behave like three are three bets | arithmetic |

How to use the numbers:

- **Open risk** is the first limit. With 0.75% a trade, eight fresh positions are 6%.
- **Diversification** is the second. If the book "behaves like" fewer than half its positions, the
  next trade in the same group adds risk without adding a bet: skip it or halve it.
- **Range** tells you what a normal fortnight looks like for the book, so that a normal loss is
  not mistaken for a problem.

## Alerts (you cannot watch the screen)

| Alert | Create it on | Covers |
|---|---|---|
| One for the book | The chart with SL Portfolio Desk > Alert > Condition: SL Portfolio Desk > **Any alert() function call** | Every position: stop touched, holding period complete, earnings entering the window; and the book's open risk crossing your limit. One message per day at most |
| One per candidate | The stock's chart with SL Risk Desk, "Send the plan" on > **Any alert() function call** | The order ticket at each daily close, earnings entering the window, the index changing state |

Options for both: open-ended expiration; notifications to the app and e-mail. Messages are sent
once, at the close of the bar.

An alert is a snapshot: it keeps the inputs it was created with. After you change the positions,
**delete the alert and create it again**. The earnings date is read when the alert is created;
after that report has passed, recreate the alert.

Limits on Premium (TradingView's pricing page, read 10-11 Nov 2026): 400 technical alerts; each
alert above counts as one.

## Scanning a watchlist

The Pine Screener (Products > Screeners > Pine) can run SL Risk Desk over a watchlist. Useful
columns: "Inside tested universe", "ATR pct of price", "Sessions to earnings", "Shares", "Record
90 band pct". It computes on the last 500 bars only and ignores the position and index inputs.
Not tested yet.

## The forward test: does your selection add anything?

A stock bought at random, with a 3-ATR stop, held 10 bars, net of costs, returned +0.01 R on
average with a standard deviation of 0.76 R (2018-2026, 54,509 simulated trades; 20 bars: +0.05 R,
standard deviation 1.04 R) (U). Your trades have to beat that.

Log one row per closed trade: date in, date out, symbol, entry, stop, exit, **R = (exit - entry) /
(entry - stop)**. Keep a running score:

> score = sum of R - 0.115 x number of trades

| Score | Conclusion (fixed in advance; 5% chance of a false "edge", 20% of a false "no edge") |
|---|---|
| Rises above **+13** | Evidence that your selection is worth about +0.2 R a trade or more |
| Falls below **-7** | Evidence that it adds nothing over a random stock: stop trading the method, keep the risk rules |
| In between | Keep going; no conclusion yet |

This is a sequential probability ratio test of a mean of +0.03 R against +0.20 R with a standard
deviation of 0.9 R. Expect it to take roughly 90 to 160 trades. That is the honest sample size:
nobody can tell a real swing-trading edge from luck in 20 trades.

A second, quicker check is the stop itself: with a 3-ATR stop and 10 bars, about 1 trade in 6
should be stopped. If after 60 trades more than 1 in 3 were, the entries are being made at bad
moments (or the stops are being moved).

## What not to do, on this evidence

| Habit | Finding |
|---|---|
| Buying sharp dips in strong stocks | Paid before 2010; zero to negative since, in liquid names and in thinner ones |
| Buying breakouts and new highs on volume | No edge over the stocks next to them |
| Buying the day after a gap up on volume | The best candidate of the search: dead on 2023-26 |
| Selling the morning after a bad report or a crash day | No further underperformance on fresh data |
| Reading volume patterns, squeezes, short-sale volume | Nothing |
| Tight stops and moving-average exits "to protect profits" | Lower return per day held (S) |
| Trusting a backtest on today's index members | The rules above looked strong for two decades on survivors |
