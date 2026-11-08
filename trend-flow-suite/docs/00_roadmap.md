# Roadmap and decisions

## Suite architecture

```
shared core (volatility, kernels, trend z-score, flow, swing structure, time-of-day volume, MTF helpers)
├── A  "Trend & Setups"   overlay: regime, ATR bands, structure, anchored VWAP, relative strength,
│                         higher-timeframe table, setups S1–S3, position sizing, alerts
├── B  "Volume Flow v2"   pane: relative volume, bounded flow ratio, volume asymmetry,
│                         climax/absorption/dry-up events, divergences
├── A′ strategy twin      Pine strategy() for single-symbol checks
└── research/             Python: same maths, multi-symbol validation (docs/02_research_protocol.md)
```

## Phases

| Phase | Deliverable | Status | Done when |
|---|---|---|---|
| 0 | `pine/vfi_faithful_v6.pine`: faithful port, defects D1–D8 fixed | **Built**; needs a compile check in TradingView | Matches the Python reference bar for bar |
| R | Research foundation: VFI reference, validation statistics, E01 diagnostics, E02 overfitting study | **Built**; 9 unit tests pass | — |
| 1 | Volume Flow v2 (pane) and shared core | Next | Parity and no-repaint tests pass; H2/H5 pre-registered |
| 2 | Trend & Setups: trend engine, structure, AVWAP, RS, MTF table | Planned | TrendScore ≈ N(0,1) on shuffled returns |
| 3 | Setups S1–S3, risk, alerts, strategy twin | Planned | Identical signals in indicator and strategy |
| 4 | Validation on a stock universe per the protocol | Needs data | Acceptance criteria met |
| 5 | Playbook per timeframe, v1.0 freeze | Planned | Owner sign-off |

## Working assumptions

Adopted Nov 2026; change any of them at will.

- US stocks, regular trading hours only, **long-only** first.
- Benchmark SPY, with an optional sector ETF.
- Pine v6.
- The design must work on the Basic plan: at most 2 indicators per chart, no lower-timeframe data required.

## Open decisions

1. TradingView plan. This sets indicators per chart, intrabar depth, `request.footprint()`
   (Premium/Ultimate only), history depth and custom intervals (65/195-min).
2. Data source for Phase 4 (see protocol §6).
3. Target holding periods per timeframe. Proposal: 1h 1–3 days, 4h 3–10 days, D 2–8 weeks, W months.
