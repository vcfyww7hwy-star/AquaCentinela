# Roadmap and decisions

## Suite (v2, 10 Nov 2026)

```
pine/trend_setups.pine           overlay: long-term trend as a risk switch, structure, setup D (dip in an
                                 uptrend), stops, sizing, alerts
pine/trend_setups_strategy.pine  the same rules for TradingView's Strategy Tester (generated)
pine/relative_volume.pine        pane: volume relative to normal, absorption at lows
pine/vfi_faithful_v6.pine        the original VFI, defects fixed (baseline, optional)
research/                        Python twins of every calculation, tests, experiments E01–E09
```

## Phases

| Phase | Deliverable | Status |
|---|---|---|
| 0 | VFI ported to Pine v6, defects D1–D8 fixed | Built; compile check pending |
| R | Research toolkit: Pine-twin maths, backtests, overfitting statistics | Built; 94 tests pass |
| 1 | Volume pane | **Rebuilt as Relative Volume** after E05/E08 (v1 "Volume Flow v2" compiled in TradingView on 9 Nov; the rebuild has not been compiled) |
| 2–3 | Trend & Setups and its strategy version | **Rebuilt as v2** after E05–E09; compile check pending |
| 4 | Validation on real stocks | **Done on daily bars** (E05–E09: four sets, about 1.7 million stock-days, 1999–2018). Result: no confirmed trading edge; one small confirmed regularity; the long-term trend works as a risk switch. See `06_validation_lite.md` |
| 5 | Playbook | Rewritten for v2 (`05_playbook.md`) |

## What is still open

1. **Compile check** of the three changed scripts in TradingView, then a parity check on an export.
2. **Intraday and weekly validation.** Needs 1h data (not in the public sets used).
3. **A survivorship-free dataset** to trust absolute return levels and to re-test rule D.
4. **Forward test:** log live D signals for three to six months before relying on them.

## Working assumptions

Adopted Nov 2026; change any of them at will.

- US stocks, regular trading hours only, **long-only** first.
- Benchmark SPY, with an optional sector ETF.
- Pine v6.
- The design must work on the Basic plan: at most 2 indicators per chart, no lower-timeframe data required.

## Open decisions

1. TradingView plan (indicators per chart, custom intervals such as 65 and 195 minutes).
2. Whether to buy data for intraday and survivorship-free tests (see `02_research_protocol.md`, section 6).
