# Roadmap and decisions

## Suite (v2, 10 Nov 2026)

```
pine/trend_setups.pine           overlay: long-term trend as a risk switch, structure, setup D (dip in an
                                 uptrend), stops, sizing, alerts
pine/trend_setups_strategy.pine  the same rules for TradingView's Strategy Tester (generated)
pine/relative_volume.pine        pane v4: unusual volume, session pace, liquidity, alerts
pine/vfi_faithful_v6.pine        the original VFI, defects fixed (baseline, optional)
research/                        Python twins of every calculation, tests, experiments E01–E09
```

## Phases

| Phase | Deliverable | Status |
|---|---|---|
| 0 | VFI ported to Pine v6, defects D1–D8 fixed | Built; compile check pending |
| R | Research toolkit: Pine-twin maths, backtests, overfitting statistics | Built; 94 tests pass |
| 1 | Volume pane | **Relative Volume v4** (24 Nov 2026), after two external reviews and tests E10–E26, including 2018–2026 data and about a year of real intraday bars. Not yet compiled in TradingView |
| 2–3 | Trend & Setups and its strategy version | **Rebuilt as v2** after E05–E09; compile check pending |
| 4 | Validation on real stocks | **Done on daily bars** (E05–E09: four sets, about 1.6 million stock-days, 1999–2018). Result: no confirmed trading edge; one small confirmed regularity; the long-term trend works as a risk switch. See `06_validation_lite.md` |
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
- The owner's plan is Premium (20,000 bars, 40 data requests per script). The panes still need no lower-timeframe data.

## Open decisions

1. Whether to buy real-time US exchange data in TradingView, depending on the data feed checks in the playbook.
2. Whether to buy data for intraday and survivorship-free tests (see `02_research_protocol.md`, section 6).
