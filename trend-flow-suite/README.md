# trend-flow-suite

A personal indicator suite for trading US stocks on 1h, 4h, daily and weekly charts (TradingView, Pine v6).
It comes with a Python research harness that tests every rule against out-of-sample data and controls for overfitting.

**Status:** Phases 0–3 are built: the fixed VFI, Volume Flow v2, and Trend & Setups (with its strategy version). All Pine scripts await a compile check in TradingView. Phase 4 (validation) needs a stock data source. See [docs/00_roadmap.md](docs/00_roadmap.md).

## Contents

| Path | What it is |
|---|---|
| `pine/vfi_faithful_v6.pine` | Phase 0: the LazyBear/LucF Volume Flow Indicator, ported to Pine v6 with 8 defects fixed |
| `pine/volume_flow_v2.pine` | Phase 1: lower pane, flow ratio, volume asymmetry, climax/absorption/divergence warnings |
| `pine/trend_setups.pine` | Phases 2–3: price overlay, calibrated trend regime, context and relative strength, swings, anchored VWAP, setups S1–S3, stops, sizing, alerts |
| `pine/trend_setups_strategy.pine` | Strategy version for TradingView's Strategy Tester (generated from the indicator; do not edit) |
| `docs/00_roadmap.md` | Architecture, phases, assumptions, open decisions |
| `docs/01_vfi_critique.md` | Measured critique of the original VFI |
| `docs/02_research_protocol.md` | How rules are tested and accepted, and why brute-force optimisation is not used |
| `docs/03_volume_flow_v2.md` | Volume Flow v2: definitions, design evidence, pre-registered hypotheses |
| `docs/04_trend_setups.md` | Trend & Setups: definitions, setups, evidence, pre-registered hypotheses |
| `docs/05_playbook.md` | How to use the suite: set-up, timeframes, entry checklist, trade management (draft) |
| `research/tfs/` | Python package: shared core (Pine twins), VFI, Volume Flow v2 and Trend & Setups references, backtests, PBO / Deflated Sharpe / null tests |
| `research/tools/parity_check.py` | Checks TradingView's exported values against the Python reference |
| `research/tools/build_strategy.py` | Generates the strategy script from the indicator so the two never drift apart |
| `research/experiments/` | E01 VFI diagnostics; E02 brute-force overfitting study; E03 Volume Flow v2 diagnostics; E04 Trend & Setups smoke test |
| `research/results/` | JSON outputs of the experiments |

## Quick start

```bash
cd research
pip install -r requirements.txt
python -m pytest -q                         # 44 tests
python -m experiments.e02_overfitting       # about 2 minutes
```

To use a Pine script, open TradingView's Pine Editor, paste the file from `pine/`, then
**Save** and **Add to chart**. Use a symbol that has volume (SPY rather than SPX).

## Conventions

- No look-ahead: signals fire on closed bars only, and nothing is plotted back in time.
- Every rule has a Python reference and is tested out of sample before it is trusted.

*Personal research tool, not investment advice.*
