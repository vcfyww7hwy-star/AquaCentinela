# swing-lab

Research and TradingView scripts for swing trading US-listed stocks (positions held days to weeks;
1h, 4h, daily and weekly charts). Successor to `trend-flow-suite/`, which is left as it was.

**Status, 12 Nov 2026 (UTC): research closed, three scripts written, not yet run on a chart.**

## The result in six lines

1. About 64,000 tests on 1998-2026, two pre-registered looks at validation data (2018-2022,
   survivorship-free), one look at data set aside from the start (2023 - 9 Nov 2026).
2. **No rule that picks stocks or times entries survived.** The best candidate (a gap up on heavy
   volume that holds: +89, +47 and +68 bp over 10 bars in three samples) was -7 bp on the fourth.
3. **Demonstrated out of sample:** how far a stock moves in ATR units (the 90% band held 89.6-89.9%
   and the 50% band 48.8-50.0% on 2023-26), how often a stop k ATR away is hit by noise (18-cell
   table, within 1.7 points), and that an earnings night is far more dangerous than an ordinary
   one (104 times for a 2-ATR adverse gap; the criterion was 20).
4. Suggestive only: the index is about twice as volatile below its 200-day average; tight stops
   and moving-average exits earn less per day held.
5. The product is therefore a risk desk, not a signal: `pine/sl_risk_desk.pine` (one stock: size,
   stop, range cone, earnings, index), `pine/sl_portfolio_desk.pine` (the whole book in one table
   and one alert), and `pine/sl_odds_check.pine`, a strategy that lets the stop-out odds be
   audited in TradingView's own Strategy Tester.
6. All three compile under TradingView's compiler with 0 errors and 0 warnings; the arithmetic of
   the two indicators equals the research code in a transliteration test; both were read by
   independent reviewers. None has run on a chart: `docs/03_verification.md` says what is still
   owed and how to close it.

## Read in this order

| File | What it is |
|---|---|
| `docs/02_research_map.md` | Every idea tried, how close it came, its final status |
| `docs/PLAYBOOK.md` | Installing and using the scripts; the forward test |
| `docs/03_verification.md` | What has and has not been verified; the exports that close the gap |
| `docs/RESEARCH_LOG.md` | Everything, in order, with outcomes and trial counts (entries 1-7) |
| `docs/00_protocol.md` | The rules fixed before any outcome was seen, and three dated amendments |
| `docs/03_preregistration_val.md`, `04_preregistration_earnings.md`, `05_preregistration_lockbox.md` | What was promised before each look |
| `docs/01_data_inventory.md` | Data sources, measured defects, gaps |
| `docs/01_pine_capabilities.md` | The TradingView and Pine facts the build relied on |
| `registry/` | Machine-readable record of every evaluated outcome; `lockbox.json` records each reading of the set-aside data |

## Layout

```
docs/            protocol, pre-registrations, log, map, playbook, verification; _raw/ holds the source reports
research/        swinglab/ (package), data_build/, experiments/, confirm/ (the three confirmation runs), results/, tests/
pine/            sl_risk_desk.pine, sl_portfolio_desk.pine, sl_odds_check.pine
tools/           pine_compile.py (TradingView compiler), parity_check.py, preview/ (schematic images), pinets_harness/ (not run)
registry/        trials*.jsonl, lockbox.json
```

## Checks

```bash
cd swing-lab
python tools/pine_compile.py pine/sl_risk_desk.pine pine/sl_portfolio_desk.pine pine/sl_odds_check.pine
python tools/parity_check.py self AAPL NVDA GE KO --k 3 --hold 10
python tools/parity_check.py book AAPL NVDA XOM JPM KO GE --hold 10
python -m research.tests.test_no_lookahead && python -m research.tests.test_delisting
```

Data are not in the repository (`research/data_build/` rebuilds them from DoltHub, Yahoo, the
Kenneth French library, FINRA and two earnings-date sources).

Personal research tool. Not investment advice.
