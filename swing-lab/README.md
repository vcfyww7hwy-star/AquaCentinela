# swing-lab

Research and TradingView scripts for swing trading US-listed stocks (positions held days to weeks;
1h, 4h, daily and weekly charts). Successor to `trend-flow-suite/`, which is left as it was.

**Status, 10 Nov 2026:** set-up. Data located, protocol frozen, compiler loop working. No market
hypothesis has been tested yet and nothing here is a trading recommendation.

## Read in this order

| File | What it is |
|---|---|
| `docs/RESEARCH_LOG.md` | Everything tried, in order, with outcomes and running trial counts |
| `docs/00_protocol.md` | How a finding earns the right to be traded: partitions, lockbox, costs, statistics |
| `docs/01_data_inventory.md` | Data sources, measured defects, gaps |
| `docs/01_pine_capabilities.md` | What a Pine script on a Premium plan can and cannot compute (from current documentation) |
| `docs/02_research_map.md` | What the literature and practitioners establish, and the ranked hypothesis list |
| `registry/trials.jsonl` | Machine-readable record of every evaluated outcome |

## Layout

```
docs/            protocol, log, maps; _raw/ holds the individual research reports
research/        swinglab/ (package), data_build/ (dataset construction), experiments/, results/
pine/            TradingView scripts (each verified to a stated level, see protocol §7)
tools/           pine_compile.py (TradingView compiler check), parity tools
registry/        trials.jsonl, lockbox.json
```

## Compile-check a script

```bash
python swing-lab/tools/pine_compile.py swing-lab/pine/<script>.pine
```

Personal research tool. Not investment advice.
