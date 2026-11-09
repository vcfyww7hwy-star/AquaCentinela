# Playbook: using the suite (draft, Phase 5)

This is a draft until Phase 4 has validated the setups. Until then, the rules below are a
disciplined way to *use* the tools, not proof that they make money. Trade small.

## Chart set-up (once)

1. Use a US stock or ETF chart with regular trading hours only (ETH off).
2. Add **Trend & Setups** (overlay) and **Volume Flow v2** (pane).
3. In Trend & Setups → Risk, set your **Account size** and **Risk per trade %** (start with 0.5–1%).
4. Optional: if your plan allows custom timeframes, use 65-minute bars instead of 1h and
   195-minute bars instead of 4h, which gives equal-length bars.
5. Alerts:
   - Create one alert per symbol with the condition **Trend & Setups → "Any alert() function call"**.
     It sends the entry, stop and size, or the exit and its R.
   - Optionally, add **Volume Flow v2 → VF2 bearish divergence** for trade management.

## Timeframe roles

| You trade on | Check first (context) | Use for |
|---|---|---|
| Weekly | Monthly | Position trades (months) |
| Daily | Weekly | Swing trades (2–8 weeks) |
| 4h / 195-min | Daily | Shorter swings (3–10 days) |
| 1h / 65-min | 4h or Daily | Entries for daily setups; short trades (1–3 days) |

The table on the chart shows all four regimes at once. **Best conditions:** this chart and its
context both *Up* or *Strong up*, and relative strength vs SPY *Up*.

## Before entering (checklist)

1. **Trend:** the table shows *Up* (S1), or not *Down* (S2). For S3, a confirmed reversal from a downtrend.
2. **Context:** not *Down*.
3. **Relative strength vs SPY:** not *Down*. Leaders beat laggards.
4. **Volume Flow v2:**
   - slow line above 0, or rising toward it;
   - no purple distribution tint;
   - no buying climax in the last few bars.
5. **Extension:** below about +2.5 ATR in the table. Don't chase extended moves.
6. **Earnings:** no report before your expected exit. If there is one, skip or halve the size.
7. **Take the label's numbers:** entry at the close, stop as shown, size as shown. Don't move the stop down.

## Managing the trade

- **The pink line is your stop.** It starts at the initial stop and trails 3 ATR below the highest
  high. Exit on a close below it, or when the trend turns *Down* (an X label appears).
- **Volume Flow v2 warnings** (buying climax, absorption at the top, bearish "D", distribution tint):
  consider taking partial profit or tightening to the last swing low. They are not reasons to short.
- **A triangle above the bars** means the last swing low broke while the trend was still up. Tighten
  the stop to just under the new swing structure, or exit if it is a daily-chart break on a 1h trade.

## Record-keeping (so Phase 4 can learn from your trades)

Log every signal you take *and* every signal you skip, with the reason:
- date, symbol, timeframe, setup;
- entry, stop, exit;
- R result;
- whether the VF2 or context filters disagreed.

Twenty to thirty logged trades already tell us more about these rules in your hands than any
single backtest.
