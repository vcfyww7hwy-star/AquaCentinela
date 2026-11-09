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
| R | Research foundation: VFI reference, validation statistics, E01 diagnostics, E02 overfitting study | **Built** | — |
| 1 | `pine/volume_flow_v2.pine` and shared core: Volume Flow v2 (pane) | **Built**; 27 unit tests pass; H2, H5–H7 pre-registered; needs a compile check and a parity check in TradingView | Parity on a real export |
| 2 | `pine/trend_setups.pine`: trend engine, structure, AVWAP, RS, MTF table | **Built**; trend score sd 0.97–0.98 on shuffled returns (E04); needs a compile check | TrendScore ≈ N(0,1) on shuffled returns ✓ |
| 3 | Setups S1–S3, risk, alerts, `pine/trend_setups_strategy.pine` | **Built**; the strategy is generated from the indicator and a test enforces sync; H1, H3, H8–H10 pre-registered | Identical signals in indicator and strategy ✓ (by construction) |
| 4 | Validation on a stock universe per the protocol | **Blocked: needs a data source** (see Open decisions) | Acceptance criteria met |
| 5 | `docs/05_playbook.md` per timeframe; v1.0 freeze | **Draft** | Owner sign-off after Phase 4 |

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
