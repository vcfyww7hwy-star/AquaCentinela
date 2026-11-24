# PineTS harness: written, never run

`run.mjs` would execute the Pine scripts in PineTS (LuxAlgo's open-source Pine runtime, AGPL-3.0,
npm package `pinets`) on local daily bars and print their plots as JSON, so that
`tools/parity_check.py` could compare the output of the real script with the research code before
anything is pasted into TradingView (level 2b of `docs/03_verification.md`).

**Status: not executed.** In the session that wrote it, running a third-party package was refused
by the session's safety classifier, and the refusal was not worked around. The files are kept so
that the step takes minutes once the repository owner allows it. Until then treat `run.mjs` as
untested code.

To run it (owner's decision):

```bash
npm install pinets@0.13.1 --ignore-scripts          # anywhere outside the repository
export PINETS_ENTRY=/path/to/node_modules/pinets/dist/pinets.min.es.js
python tools/pinets_harness/export_bars.py AAPL NVDA GE KO SPY
node tools/pinets_harness/run.mjs pine/sl_risk_desk.pine NASDAQ:AAPL --out tools/pinets_harness/out/AAPL.json
```

Bars and outputs are not committed (`.gitignore`).
