# VFI [LazyBear/LucF]: critique summary (Nov 2026)

All numbers are reproducible with `research/experiments/e01_vfi_diagnostics/`. Data: S&P 500 and
NASDAQ Composite daily 2000–2018, GOOG daily 2005–2013 (bundled sample data). Regime tests are
illustrative: three series, one era.

## What it computes

```
TP = hlc3;  σ = stdev30(ln TP − ln TP[1]);  cut = k·σ·close     (k = 0.1 intraday, 0.2 D/W)
V̄ = SMA130(V)[1];  Vc = min(V, m·V̄)                            (m = 3.5 intraday, 2.5 D/W)
s = +1 if ΔTP > cut, −1 if ΔTP < −cut, else 0
VFI = Σ(s·Vc over 130 bars) / V̄                                  (no smoothing by default)
```

With default settings this is **not** Katsanos' VFI. His formula ends with a 3-bar EMA; LazyBear
defaults to none and offers SMA(3).

## Defects (fixed in `pine/vfi_faithful_v6.pine`)

| ID | Defect | Consequence |
|---|---|---|
| D1 | Volume-cutoff input titles swapped (the "Intraday" input drives D/W) | Edits silently change the wrong timeframe |
| D2 | Sell level titled "Buy Level" | Duplicate labels |
| D3 | Zero-cross dots drawn with `offset=-1` | Visual look-ahead of one bar |
| D4 | VFI colour logic inverted below zero | Bearish strength misread |
| D5 | Unsmoothed / SMA(3) instead of EMA(3) | Not the published indicator |
| D6 | Signals and alerts evaluated intrabar | Signals appear and vanish |
| D7 | No guard for missing volume | Division by zero |
| D8 | Pine v1/v2 syntax | No access to modern features |

## Structural findings (measured)

- **Window artifact.** Of the variance of daily VFI changes, 48–54% comes from the bar *leaving* the
  130-bar window. The VFI moves against the day's own flow on 20–21% of days. 25% of zero-line
  crosses occur on bars whose own flow is neutral or opposite.
- **Big Swing.** On D/W a single bar contributes at most 2.5 < 3.0, so every Big Swing needs the
  leaving bar (58/58 events on GOOG).
- **Information content.** VFI ≈ (up − down bars) + 130·Cov(direction, volume)/V̄.
  - Correlation with a volume-free copy: 0.94–0.98.
  - Correlation with the 130-bar return: 0.84–0.92.
  - Volume flips the regime call on only 7–12% of days.
- **Classification.** The ±0.2σ dead band zeroes about 16% of bars (theory: 15.9%), so magnitude is
  discarded. The volume cap binds on 0–1.6% of daily bars.
- **Signals.**
  - MA20 crosses fire 26–29 times a year and were the worst rule in all three series.
  - 58–67% of Buy/Sell signals repeat the previous direction.
  - The ±2 band covers 8–9% of the VFI's range.
  - Zero-crosses come 24–48 sessions after major S&P turns.
- **Kernels at equal lag** (S&P zero-line switches 2000–2018): boxcar 112, EMA 162, two-pole 36, Hann 38.
  Fewer whipsaws did *not* consistently raise Sharpe, so every fix must be validated
  (see `02_research_protocol.md`).
- **Intraday.**
  - One switch covers four timeframes.
  - TradingView truncates the last session bar (a 30-min "1h" bar).
  - Volume is U-shaped, and the closing auction is ~9% of daily notional on a typical day (BMLL, Jun 2025).

  Prefer 65-min and 195-min bars, plus time-of-day volume normalisation.

## Sources

- Katsanos, "Using Money Flow to Stay with the Trend", TASC V.22:6, Jun 2004.
- LazyBear, TradingView script, 18 Jun 2014.
- TradingView Pine v6 release notes, 10 Dec 2024.
- BMLL closing-auction study, Jun 2025.
- Jain & Joh, JFQA 23(3), 1988.
- Easley, López de Prado & O'Hara, RFS 25(5), 2012; JFE 120(2), 2016.
- Chakrabarty, Pascual & Shkilko, JFM 25, 2015.
- Levine & Pedersen, FAJ 72(3), 2016.
- Marshall, Cahan & Cahan, JEF 15(2), 2008.
- Park & Irwin, JES 21(4), 2007.
