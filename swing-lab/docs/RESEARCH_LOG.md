# Research log

Append-only. Newest entries at the bottom. Every hypothesis gets an ID, a status and a reason.
Machine-readable trial records are in `registry/trials.jsonl`; this file is the narrative.

Status words: **OPEN** (registered, not yet tested) · **DEV** (looked at on development data) ·
**VAL-PASS** / **VAL-FAIL** · **DESTROYED** (failed an attack) · **FROZEN** (on the lockbox list) ·
**LOCKBOX-PASS** / **LOCKBOX-FAIL** · **DROPPED** (with reason).

Running totals are restated at each milestone.

---

## 2026-11-10 — Session 2, entry 1: start, environment, data

**Inherited state** (`trend-flow-suite`, 9–10 Nov 2026): about 1.6 million stock-days of daily
large-cap US data, 1999–2018, survivors only. Findings carried forward as priors, not as facts:

- No entry rule (pullback, breakout, reversal) beat random entries in the same uptrends.
- No volume signal predicted direction.
- Dips inside long-term uptrends bounced for 1–5 bars (about +0.12 risk units over 5 bars);
  as a complete stop-based trade it was not confirmed. That test bought at the signal bar's close,
  which a trader working from a bar-close alert cannot do.
- A weekly trend filter cut drawdowns 29–40% at an unchanged Sharpe ratio.
- Its four Pine scripts had never been compiled.

**Done today**

1. Located the repository and branch (`AquaCentinela`, `claude/youthful-hopper-v9kozz`, draft PR 2).
   New work lives in `swing-lab/` on branch `claude/swing-lab`. `trend-flow-suite/` is untouched.
2. Probed the network. Yahoo, Hugging Face, DoltHub, Kenneth French, FRED and TradingView are
   reachable. Details in `01_data_inventory.md`.
3. **Found a free daily dataset that includes delisted companies** (DoltHub `stocks`, 2011 to
   9 Nov 2026) and measured that it is survivorship-free only from mid-2018. Found free earnings
   dates with before-open/after-close timing for 2020–2026.
4. **Compiler access.** TradingView's public lint endpoint compiles Pine v6 from here without a
   login and returns errors and warnings with positions (`tools/pine_compile.py`). Checked on a
   valid script, two broken ones, a v6-feature script and a strategy.
   Side result: the four `trend-flow-suite` scripts compile with 0 errors and 0 warnings.
5. Wrote the protocol (`00_protocol.md`) and froze the partitions **before computing any outcome**:
   DEV 2011-01 – 2018-06 (biased universe), VAL 2018-07 – 2022-12, LOCKBOX 2023-01 – 2026-11.
6. Asked the user, in one message: broker and costs, long/short, number of positions, universe,
   when orders can be placed, earnings policy, TradingView data feed, operating system; and for a
   free Alpaca API key (1-hour bars since 2016). Assumptions in force until answered are in
   protocol §5.
7. Launched a 16-topic parallel study (Pine capabilities from current documentation, literature by
   theme, data vendors), each with an independent verifier. Outputs: `docs/_raw/`,
   `01_pine_capabilities.md`, `02_research_map.md`.

**Trials so far: 0. Hypotheses registered: 0.** Nothing has been tested on market data yet.

**Open risks noted**

- The previous dip rule's entry at the close is not executable from a bar-close alert. Every test
  here enters at the next open unless stated.
- The model running this research has read about 2023–2026 markets (protocol §2.4).
- DoltHub prices are a community dataset. Bad ticks manufacture mean-reversion "edges". A
  cross-check against Yahoo is part of the build, and every reversal-type result is re-run on the
  cross-checked subset.
