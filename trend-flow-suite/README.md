# trend-flow-suite

A personal indicator suite for trading US stocks on 1h, 4h, daily and weekly charts (TradingView, Pine v6).
It comes with a Python research harness that tests every rule against out-of-sample data and controls for overfitting.

**Status:** Phase 0 and Phase 1 (Volume Flow v2) are built; both Pine scripts await a compile check in TradingView. See [docs/00_roadmap.md](docs/00_roadmap.md).

## Contents

| Path | What it is |
|---|---|
| `pine/vfi_faithful_v6.pine` | Phase 0: the LazyBear/LucF Volume Flow Indicator, ported to Pine v6 with 8 defects fixed |
| `pine/volume_flow_v2.pine` | Phase 1: lower pane, flow ratio, volume asymmetry, climax/absorption/divergence warnings |
| `docs/00_roadmap.md` | Architecture, phases, assumptions, open decisions |
| `docs/01_vfi_critique.md` | Measured critique of the original VFI |
| `docs/02_research_protocol.md` | How rules are tested and accepted, and why brute-force optimisation is not used |
| `docs/03_volume_flow_v2.md` | Volume Flow v2: definitions, design evidence, pre-registered hypotheses |
| `research/tfs/` | Python package: shared core (Pine twins), VFI and Volume Flow v2 references, backtests, PBO / Deflated Sharpe / null tests |
| `research/tools/parity_check.py` | Checks TradingView's exported values against the Python reference |
| `research/experiments/` | E01 VFI diagnostics; E02 brute-force overfitting study; E03 Volume Flow v2 diagnostics |
| `research/results/` | JSON outputs of the experiments |

## Quick start

```bash
cd research
pip install -r requirements.txt
python -m pytest -q                         # 27 tests
python -m experiments.e02_overfitting       # about 2 minutes
```

To use a Pine script, open TradingView's Pine Editor, paste the file from `pine/`, then
**Save** and **Add to chart**. Use a symbol that has volume (SPY rather than SPX).

## Conventions

- No look-ahead: signals fire on closed bars only, and nothing is plotted back in time.
- Every rule has a Python reference and is tested out of sample before it is trusted.

*Personal research tool, not investment advice.*
