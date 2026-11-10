# trend-flow-suite

A personal indicator suite for trading US stocks on 1h, 4h, daily and weekly charts (TradingView, Pine v6).
It comes with a Python research harness that tests every rule against out-of-sample data and controls for overfitting.

**Status (10 Nov 2026):** v2. The suite was rebuilt after testing its first version on about 1.6 million
stock-days of real data. The honest summary: no rule here has a confirmed trading edge; the long-term
trend works as a risk switch; dips inside long-term uptrends bounce briefly. The three changed
TradingView scripts still need a compile check. See [docs/06_validation_lite.md](docs/06_validation_lite.md).

## Contents

| Path | What it is |
|---|---|
| `pine/trend_setups.pine` | Trend & Setups v2 (overlay): long-term trend as a risk switch, structure, setup D (dip in an uptrend), stop orders, sizing, alerts |
| `pine/trend_setups_strategy.pine` | The same rules for TradingView's Strategy Tester (generated from the indicator; do not edit) |
| `pine/relative_volume.pine` | Relative Volume (pane): volume relative to normal for the time of day, absorption at lows |
| `pine/vfi_faithful_v6.pine` | The LazyBear/LucF Volume Flow Indicator ported to Pine v6 with 8 defects fixed (baseline) |
| `docs/00_roadmap.md` | What exists, what is open |
| `docs/01_vfi_critique.md` | Measured critique of the original VFI |
| `docs/02_research_protocol.md` | How rules are tested, and why brute-force optimisation is not used |
| `docs/03_relative_volume.md` | Volume pane: what was removed and why |
| `docs/04_trend_setups.md` | Trend & Setups v2: definitions, setups, evidence |
| `docs/05_playbook.md` | How to use the suite |
| `docs/06_validation_lite.md` | The tests on real stocks: plan, results, decisions |
| `research/tfs/` | Python package: twins of every Pine calculation, backtests, overfitting statistics |
| `research/tools/` | `parity_check.py` (TradingView export vs Python), `build_strategy.py` (generates the strategy script) |
| `research/experiments/` | E01–E04 (first version), E05–E09 (validation on real stocks) |
| `research/results/` | JSON outputs of the experiments |

## Quick start

```bash
cd research
pip install -r requirements.txt
python -m pytest -q                         # 94 tests
python -m experiments.e02_overfitting       # about 2 minutes, bundled data
# E05–E09 need the public Kaggle sets named in docs/06_validation_lite.md (not in this repository)
```

To use a Pine script, open TradingView's Pine Editor and create a new indicator. **Select all of the
starter template and delete it first.** Otherwise TradingView reports error CE10243, "Scripts must
contain one declaration statement". Then paste the file from `pine/`, **Save** and **Add to chart**.
Use a symbol that has volume (SPY rather than SPX).

## Conventions

- No look-ahead: signals fire on closed bars only, and nothing is plotted back in time.
- Every rule has a Python reference and is tested out of sample before it is trusted.

*Personal research tool, not investment advice.*
