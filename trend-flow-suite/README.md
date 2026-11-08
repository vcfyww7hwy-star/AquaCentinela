# trend-flow-suite

A personal indicator suite for trading US stocks on 1h, 4h, daily and weekly charts (TradingView, Pine v6).
It comes with a Python research harness that tests every rule against out-of-sample data and controls for overfitting.

**Status:** Phase 0 is built and the research foundation is in place. See [docs/00_roadmap.md](docs/00_roadmap.md).

## Contents

| Path | What it is |
|---|---|
| `pine/vfi_faithful_v6.pine` | Phase 0: the LazyBear/LucF Volume Flow Indicator, ported to Pine v6 with 8 defects fixed |
| `docs/00_roadmap.md` | Architecture, phases, assumptions, open decisions |
| `docs/01_vfi_critique.md` | Measured critique of the original VFI |
| `docs/02_research_protocol.md` | How rules are tested and accepted, and why brute-force optimisation is not used |
| `research/tfs/` | Python package: VFI reference (Pine-equivalent), vectorised backtests, PBO / Deflated Sharpe / null tests |
| `research/experiments/` | E01 VFI diagnostics; E02 brute-force overfitting study |
| `research/results/` | JSON outputs of the experiments |

## Quick start

```bash
cd research
pip install -r requirements.txt
python -m pytest -q                         # 9 tests
python -m experiments.e02_overfitting       # about 2 minutes
```

To use the Pine script, open TradingView's Pine Editor, paste `pine/vfi_faithful_v6.pine`, then
**Save** and **Add to chart**. Use a symbol that has volume (SPY rather than SPX).

## Conventions

- No look-ahead: signals fire on closed bars only, and nothing is plotted back in time.
- Every rule has a Python reference and is tested out of sample before it is trusted.

*Personal research tool, not investment advice.*
