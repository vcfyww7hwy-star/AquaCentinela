# Verification of the Pine scripts

Status on 12 Nov 2026 (UTC). The ladder is the one fixed in `00_protocol.md`, section 7.

| Level | What it proves | `sl_risk_desk.pine` (v2.2) | `sl_portfolio_desk.pine` (v1.1) | `sl_odds_check.pine` |
|---|---|---|---|---|
| 1 Compiles under TradingView's compiler | Syntax and types | **Done**: 0 errors, 0 warnings | **Done**: 0 / 0 | **Done**: 0 / 0 |
| 1b Constants | The numbers typed into the script are the ones that were tested | **Done**: identical to the lockbox tables | **Done**: identical to the constants committed before their check | **Done** |
| 2a Transliteration | The formulas, as written in the script, equal the research code on real bars | **Done**: 0 difference on about 82,000 daily bars of seven symbols (band variable, coverage flags, envelope); stop outcomes identical to the research simulator on every bar | **Done** for the book's scale: the transliteration gives the same s_p as the calibration formula (difference below 1e-12) | Rests on the same simulator |
| 2c Independent review | Four reviewers with different lenses (runtime, data requests and alerts, rendering, logic) read both indicators against TradingView's documentation; a skeptic tried to refute each finding | See "Independent review" below | same | not reviewed in this round |
| 2b Executes in an open-source Pine runtime (PineTS) | The script itself runs and produces those numbers | **Not done: blocked.** The session's safety classifier refused to execute the third-party package. Needs the owner's permission | Not done | Not done |
| 3 Matches on TradingView | The script running on TradingView produces the research numbers on TradingView's bars | **Waiting for an export** (steps below) | Cannot be checked from one export (the chart file holds one symbol); check by eye against the brokerage statement | n/a |
| 4 Does not repaint | A later export reproduces the earlier one for closed bars | Waiting for a second export on a later day | n/a | n/a |
| 5 Strategy twin agrees | The Strategy Tester's trades equal the research simulator's, trade for trade | n/a | n/a | **Waiting for an export** (steps below) |

What has NOT been shown: that any script has run on a chart. Level 1 is a compile, not an
execution. Things only a chart can show: runtime errors, how the table, cone and labels look, the
behaviour of `earnings.future_time` (for the chart symbol and, in the portfolio script, for other
symbols), the lower-timeframe request used on weekly charts, alert delivery. Treat the first load
as a test and send a screenshot.

## First load on a chart, 13 Nov 2026 (owner's screenshot)

Both indicators were added to a 1-minute chart of BINANCE:SPYUSDT.P, a crypto perpetual contract
and not the SPY ETF. SL Risk Desk 2.2 ran: the table rendered with its PLAN, RANGE and EVENTS
sections, "Universe: OUTSIDE" (correct for a crypto contract), "Earnings: no date on file" and the
index row. SL Portfolio Desk 1.1 stopped on bar 0 with its own guard, "use a daily chart (for
example SPY)", as designed for a non-daily chart. Not yet seen: either script on a daily chart of
a US stock, the cone, position mode, the Portfolio Desk's table, alerts.

## Independent review (level 2c), 12 Nov 2026

Four reviewers read SL Risk Desk 2.1 and SL Portfolio Desk 1.0 against TradingView's
documentation, each with one lens: runtime errors and limits; data requests, repainting, alerts
and earnings; rendering on a chart; logic against the research files. A skeptic then tried to
refute every finding of the first two lenses. The skeptics for the rendering and logic lenses did
not run (the account's usage limit ended the workflow), so those findings were judged by the
author alone. In all: 52 findings, 19 verdicts (16 confirmed, 3 left open, none refuted). The raw
results are in `_raw/pine_review_2026-11-12.json`.

| What was found | Severity | Status |
|---|---|---|
| Portfolio Desk merged the cells of one persistent table again on every update, which the reference manual documents as a runtime error: the table and the book's only alert would have stopped at the first live tick | blocker | Fixed: a fresh table on every update |
| Risk Desk drew a held position's lines up to 400 bars back on realtime bars without reserving the `time` buffer: "historical offset beyond the buffer" error | major | Fixed: `max_bars_back(time, 500)` |
| Entry date compared as an instant with the bar's opening time: on a chart in an American time zone the entry day was dropped and every day count was one short (both scripts) | major | Fixed: compared by calendar day (`time_tradingday`), default at noon UTC |
| Weekly and monthly charts measured days to earnings from the end of the week: a report due this week read "no date on file" | major | Fixed: measured from now |
| "Earnings inside the holding period" was tested against a full new period, not the days a position has left (both scripts) | major | Fixed |
| A stop raised to or above the entry switched position mode off (Risk Desk) or read as a set-up error (Portfolio Desk), and silently changed 1 R | major | Fixed: a first stop, which defines 1 R, and an optional "stop now" |
| Cone tags crossed by the cone's own lines; the earnings label on top of the 95% tag; the price scale making no room for the cone or the stop | major | Fixed: tags at the cone's two corners, earnings marker placed in bars at mid-height, two invisible scale anchors |
| Long texts in merged cells, which take their width from their neighbours and not from their text | major | Fixed: no merged cells in the Risk Desk; short texts in the Portfolio Desk |
| Stop message repeated at every bar; stale earnings date read as "no date"; positions without data or without a stop vanishing from the book; day count one short on intraday charts; "inside" universe for non-US stocks; NaN with fewer than 15 daily bars; colours unreadable on a light chart; inputs flooding the status line; the diversification warning firing for every ordinary book | minor | Fixed |
| Tag D shown for stop distances that were never tested; "1 trade in 100" stated for every stop | cosmetic | Fixed |
| On an intraday chart, after the close, daily values are one day behind the daily chart | minor | Kept (the documented non-repainting form); wording corrected; the guide says to plan on the daily chart |
| `earnings.future_time` read for ANOTHER symbol through `request.security()`: no documentation either way | open | Cannot be settled without a chart. First-load check written into the playbook; the column fails visibly (a dash) and is to be removed if it does not work |
| History of a variable first read on a realtime bar inside a lazy `and` | open | Hardened: the previous-bar states are now read on every bar |

Not adopted: making the Data Window plots non-editable (it is not documented that such plots are
still written to the chart export, which the parity check needs).

Still unverified, and only a chart can show them: whether a second identical merge is in fact an
error (moot after the fix); the exact default size of the `time` buffer; whether fully transparent
plots move the price scale (if not, the scale anchors do nothing); the positions of labels;
`time_tradingday` on the bars of the entry day; everything listed under "What has NOT been shown".

## Level 1 and 2a: reproduce

```bash
cd swing-lab
python tools/pine_compile.py pine/sl_risk_desk.pine pine/sl_odds_check.pine
python tools/parity_check.py self AAPL NVDA GE KO --k 3 --hold 10
python tools/parity_check.py book AAPL NVDA XOM JPM KO GE --hold 10
```

## Level 3: what to export, and how it is checked

1. Open a **daily** chart of a liquid US stock (for example AAPL). Standard candles, regular
   session, no dividend adjustment.
2. Add **SL Risk Desk** with its default inputs. Leave it visible.
3. Add the built-in **Volume** indicator if it is not on the chart (the export then carries a
   `Volume` column, which checks the liquidity figure too).
4. Scroll or zoom out until the first bar of the stock's history is loaded.
5. Chart menu (top left, the layout name) > **Export chart data** > Time format: **ISO time** >
   Export.
6. Send the CSV. Repeat for two more symbols if you can (one volatile, for example NVDA or TSLA).

The check:

```bash
python tools/parity_check.py tv-csv path/to/export.csv --k 3 --hold 10 --equity 100000 --risk 0.75 --maxpos 20
```

It recomputes every plotted value from the bars in the same file with the research code and
reports the largest difference per series. Pass: relative differences under 1e-6 after the first
300 bars, identical share counts, identical per-bar coverage and stop flags.

## Level 4: repainting

Export the same chart again on a later day and send both files. Every bar that was closed at the
time of the first export must carry the same values in the second.

By construction: the daily-chart path uses only the chart's own closed bars; the intraday path
requests daily values as `expression[1]` with `lookahead_on`, the documented non-repainting form;
alerts are sent with `alert.freq_once_per_bar_close` inside `barstate.isconfirmed`. One known
exception is by design: the earnings date comes from `earnings.future_time`, which TradingView
fetches when the script loads; "sessions to earnings" on past bars is measured against today's
next date and means nothing there.

## Level 5: the strategy twin

1. Daily chart of the same stock. Add **SL Odds Check** (inputs: 2 ATR, 10 bars).
2. Strategy Tester > Properties: commission 0, slippage 0, "Recalculate" options off, bar magnifier
   off.
3. Strategy Tester > **List of trades** > export (the download icon).
4. Export the chart data as in level 3.
5. Send both files.

```bash
python tools/parity_check.py tv-trades path/to/chart.csv path/to/trades.csv --k 2 --hold 10
```

Pass: at least 99% of trades with the same exit date and the same exit type as the research
simulator run on the exported bars. Differences are expected only where TradingView's broker
rounds a stop to the tick.

## A tighter loop, if wanted

Two options need a decision by the repository owner:

| Option | What it gives | What it needs |
|---|---|---|
| PineTS (LuxAlgo, AGPL-3.0, npm) | Executes the real scripts here, on the research bars, before anything is pasted | Permission to run that third-party package in this container. `tools/pinets_harness/` is written and has never been run |
| Browser automation under the owner's TradingView login | Pastes the script, adds it to a chart, exports the CSV and reads compiler and runtime errors without manual steps | The owner's decision; it operates his account |
