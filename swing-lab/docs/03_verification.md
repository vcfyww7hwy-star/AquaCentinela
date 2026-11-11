# Verification of the Pine scripts

Status on 11 Nov 2026 (UTC). The ladder is the one fixed in `00_protocol.md`, section 7.

| Level | What it proves | `sl_risk_desk.pine` | `sl_odds_check.pine` |
|---|---|---|---|
| 1 Compiles under TradingView's compiler | Syntax and types | **Done**: 0 errors, 0 warnings | **Done**: 0 errors, 0 warnings |
| 1b Constants | The numbers typed into the script are the ones tested on the lockbox | **Done**: read from the Pine source by `tools/parity_check.py constants`; identical | **Done** |
| 2a Transliteration | The formulas, as written in the script, equal the research code on real bars | **Done**: 0 difference on about 82,000 daily bars of seven symbols (AAPL, NVDA, GE, KO, TSLA, MSFT, XOM), three parameter sets (band variable, both coverage flags); stop outcomes identical to the research simulator on 100.000% of bars | Rests on the same simulator |
| 2b Executes in an open-source Pine runtime (PineTS) | The script itself runs and produces those numbers | **Not done: blocked.** The session's safety classifier refused to execute the third-party package. Needs the owner's permission | Not done, same reason |
| 3 Matches on TradingView | The script running on TradingView produces the research numbers on TradingView's bars | **Waiting for an export** (steps below) | n/a |
| 4 Does not repaint | A later export reproduces the earlier one for closed bars | Waiting for a second export on a later day | n/a |
| 5 Strategy twin agrees | The Strategy Tester's trades equal the research simulator's, trade for trade | n/a | **Waiting for an export** (steps below) |

What has NOT been shown: that either script has run on a chart. Level 1 is a compile, not an
execution. Things only a chart can show: runtime errors, how the table and lines look, the
behaviour of `earnings.future_time`, the lower-timeframe request used on weekly charts, alert
delivery. Treat the first load as a test.

## Level 1 and 2a: reproduce

```bash
cd swing-lab
python tools/pine_compile.py pine/sl_risk_desk.pine pine/sl_odds_check.pine
python tools/parity_check.py self AAPL NVDA GE KO --k 3 --hold 10
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
