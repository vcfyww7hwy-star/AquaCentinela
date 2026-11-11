# Playbook: using SL Risk Desk and SL Odds Check

Final, 11 Nov 2026 (UTC). Evidence labels: **[D]** demonstrated out of sample (frozen before, and
passed on, the data set aside for 2023-2026); **[S]** suggestive; **[U]** untested. Sources:
`RESEARCH_LOG.md` entries 5-7, `02_research_map.md`.

## What the scripts are, and are not

They do not tell you what to buy or when. In this research no chart rule that does so survived
data it had not seen (`02_research_map.md`, section 1). What survived is the arithmetic of risk,
and that is what the scripts put on the chart: size, stop, the odds that the stop is noise, how
far the price usually travels, earnings, and the index state.

Where the stock comes from is your decision (a thesis, a sector view, a fundamental reason). The
forward test at the end measures whether that decision adds anything.

## Install

1. TradingView > Pine Editor > Open > New indicator. Delete the template, paste the whole of
   **SL Risk Desk**, Save (name it), **Add to chart**.
2. New strategy > paste **SL Odds Check** > Save > Add to chart, on a separate daily chart. It is
   an audit tool; remove it when you have looked.
3. First load is a test (the scripts compile; they have not been run on a chart yet). If the editor
   or the chart shows an error, copy the message and the line number.

## Configure SL Risk Desk

| Input | Default | What to put |
|---|---|---|
| Account equity | 100,000 | Your trading account, in the chart's currency |
| Risk per trade, % of equity | 0.75 | What you accept to lose if the stop fills at its price. About 1 trade in 100 loses more than 1.5 times this, because prices gap through stops [D] |
| Stop distance, in daily ATR(14) | 3 | 1 to 4. See "Choosing the stop" |
| Holding period, daily bars | 10 | 5, 10 or 20: the horizon you plan to hold |
| Largest position, % of equity | 20 | A cap for quiet stocks, where the risk budget would buy too much |
| Alert: send the plan at each daily close | off | Turn on for a stock you intend to buy at the next open |
| I hold this stock / entry price / stop price / entry date | off | Fill in after you buy; the script then tracks R, days held and the stop |
| Index reference | AMEX:SPY | Leave |

## Reading the table

| Row | Meaning | Label |
|---|---|---|
| Daily ATR(14) | The yardstick. Everything else is in these units | arithmetic |
| Tested universe | "inside": a stock at $5 or more that trades $20M a day or more (60-day median). Outside it the odds below were not tested | - |
| Stop | Price k ATR below the last price, and how often such a stop is hit within the holding period by a stock bought for no reason at all | **[D]** at k = 1, 1.5, 2, 2.5, 3, 4 (within 1.7 points on 2023-26); in between, a straight line |
| Size | Shares = risk budget / (k x ATR), capped by the largest position | arithmetic |
| 90% band, middle half | Where the close lands h bars from now: 9 times in 10 inside the outer lines, 1 time in 2 inside the inner ones. In R units too | **[D]** (2023-26: 89.6-89.9% and 48.8-50.0%) |
| This chart's record | The same three figures measured on this symbol's own history. A symbol whose 90% band held 84% of the time jumps more than most | measurement |
| Earnings | Sessions to the next report and whether it falls inside the holding period | date from TradingView |
| Earnings night | Odds of an opening gap against you of more than 1, 2, 3 ATR: about 20%, 10%, 5%. Ordinary night, beyond 2 ATR: about 0.1-0.3% | multiple (at least 20 times) **[D]**; exact odds **[U]** (by year 15-27%, 5-15%, 3-8%) |
| Index | SPY above or below its 200-day average. Below: the index has been about twice as volatile. It has NOT meant lower returns, and in 2023-26 it did not mean more losing stocks | volatility **[S]**; the rest failed |
| Position | R now, day n of h, your stop | arithmetic |

On a daily chart the lines run from today's close to the band h bars ahead. On other timeframes
they mark the levels. All values are daily values: on a 1h or 4h chart they are those of the last
completed day; on a weekly chart those of the last daily bar.

## Choosing the stop

| Stop | Hit within 10 bars by noise [D] | What the evidence says |
|---|---|---|
| 1 ATR | 60% | You will be stopped out of most trades for no reason |
| 2 ATR | 32% | One trade in three |
| 3 ATR | 17% | One in six. Against no stop at all it gave up 0.6-1.1 bp per day held in three samples and gained 0.3 in the fourth; never significant [S] |
| 4 ATR | 8% | One in twelve |

A 2-ATR stop gave up 0.6-1.6 bp per day held against no stop, and an exit on a close under the
20-day average 1-3.8 bp, in all four samples; the differences never reached significance [S]. A stop is insurance against the
tail. It does not improve the average, and it does not bound the loss: 15% of stop exits were
filled below the stop, and the worst trade in the 2023-26 simulation lost 132 times its planned
risk [D].

Because the stop is k ATR and the size is risk / (k ATR), a wider stop means fewer shares and the
same money at risk. The cost of a wide stop is a smaller position, not a bigger loss.

## What the bands are for

- **A target check.** With a 3-ATR stop and 10 bars, the 95% line is at +1.16 R. A plan that needs
  +2 R in two weeks needs a 1-in-100 outcome [U]. Either hold longer (20 bars: +1.65 R at the 95% line)
  or accept that the target is a hope.
- **A sanity check on news.** A close outside the 90% band happens 1 time in 10 by chance. Outside
  it, something happened; inside it, probably nothing did.
- They are symmetric around a small positive drift and they say nothing about direction.

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

When SPY is below its 200-day average, expect index moves about twice as large [S]. Sizing by ATR
already absorbs most of this stock by stock, since ATR rises with it. The script therefore
reports the state and does not change the size. Over a century the rule "own stocks only above the
200-day average" cut the worst drawdown from -84% to -40% (Kenneth French library, 1926-2022,
context only) and it has cost return in every bull decade.

## Alerts (you cannot watch the screen)

One alert per chart covers everything the script sends:

1. Alert > Condition: **SL Risk Desk** > **Any alert() function call**.
2. Trigger: **Once per bar close** is built in; leave the default options.
3. Expiration: open-ended. Notifications: app and e-mail.

| Message | Fires | Use |
|---|---|---|
| Plan for the next open | Each daily close, when "send the plan" is on and no position is entered | The order ticket for tomorrow: shares and stop distance. Place the stop relative to your actual fill |
| Earnings inside the holding period | The first bar on which the next report comes within h sessions | Decide per the table above |
| Index closed above / below its 200-day average | On the change | Information |
| Traded at or below your stop | Any bar whose low touches the stop you entered | A backstop. The real stop is an order at your broker |
| Holding period complete | The daily close of day h | Exit, or decide to start a new period with new numbers |

An alert is a snapshot: it keeps the inputs it was created with. After you enter a position,
fill in the position inputs and **create a new alert** (delete the old one). The earnings date is
read when the alert is created; after that report has passed, recreate the alert.

Limits on Premium (TradingView's pricing page, read 10-11 Nov 2026): 400 technical alerts; each
chart's alert counts as one.

## Scanning a watchlist

The Pine Screener (Products > Screeners > Pine) can run SL Risk Desk over a watchlist. Useful
columns: "Inside tested universe", "ATR pct of price", "Sessions to earnings", "Shares", "Record
90 band pct". It computes on the last 500 bars only and ignores the position and index inputs.
Not tested yet.

## A weekly routine (15 minutes)

1. Open positions: read the Position row. Day h reached, or earnings inside the window: act.
2. Candidates (from your own thesis): check "Tested universe" and "Earnings"; turn on the plan
   alert for the ones you will buy.
3. After a fill: enter the entry price, the stop (fill minus the distance in the alert) and the
   date; recreate the alert.
4. Log every closed trade (below).

## The forward test: does your selection add anything?

A stock bought at random, with a 3-ATR stop, held 10 bars, net of costs, returned +0.01 R on
average with a standard deviation of 0.76 R (2018-2026, 54,509 simulated trades; 20 bars: +0.05 R,
standard deviation 1.04 R) [U]. Your trades have to beat that.

Log one row per closed trade: date in, date out, symbol, entry, stop, exit, **R = (exit - entry) /
(entry - stop)**. Keep a running score:

> score = sum of R - 0.115 x number of trades

| Score | Conclusion (fixed in advance; 5% chance of a false "edge", 20% of a false "no edge") |
|---|---|
| Rises above **+13** | Evidence that your selection is worth about +0.2 R a trade or more |
| Falls below **-7** | Evidence that it adds nothing over a random stock: stop trading the method, keep the risk rules |
| In between | Keep going; no conclusion yet |

This is a sequential probability ratio test of a mean of +0.03 R against +0.20 R with a standard
deviation of 0.9 R. Expect it to take roughly 90 to 160 trades. That is the honest sample size: nobody
can tell a real swing-trading edge from luck in 20 trades.

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
| Tight stops and moving-average exits "to protect profits" | Lower return per day held [S] |
| Trusting a backtest on today's index members | The rules above looked strong for two decades on survivors |
