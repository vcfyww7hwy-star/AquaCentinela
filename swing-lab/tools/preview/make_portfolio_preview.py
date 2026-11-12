#!/usr/bin/env python3
"""Schematic preview of SL Portfolio Desk's table, with the script's own arithmetic on real daily bars.

NOT a TradingView screenshot. Positions are illustrative: each is "bought" at the open n bars ago,
sized as SL Risk Desk would have sized it that day (0.75% risk, stop 3 ATR below the fill).
Earnings sessions are illustrative (the research data hold no future dates).

    python tools/preview/make_portfolio_preview.py     -> tools/preview/out/portfolio_desk.html
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import parity_check as PC  # noqa: E402
from research.swinglab import pinelike as ta  # noqa: E402

ACC, STOP, GOOD, WARN = "#4C8BF5", "#E5484D", "#2EBD85", "#F0A030"
BG, FG, MUTED = "#131722", "#D1D4DC", "#787B86"
BOOK = [("AAPL", 6, 31), ("NVDA", 3, 48), ("MSFT", 10, 27), ("JPM", 8, 23), ("UNH", 4, 6), ("AMZN", 7, 35)]     # symbol, bars held, sessions to earnings (illustrative)
EQUITY, HOLD, K = 100000.0, 10, 3.0


def main() -> None:
    syms = [b[0] for b in BOOK]
    frames = {s: PC.load_yahoo(s).set_index("date") for s in syms}
    idx = None
    for f in frames.values():
        idx = f.index if idx is None else idx.intersection(f.index)
    idx = idx.sort_values()[-400:]
    col = lambda n: np.column_stack([frames[s].loc[idx, n].to_numpy(dtype=float) for s in syms])
    O, Hh, Ll, C = col("open"), col("high"), col("low"), col("close")
    A = ta.atr(Hh, Ll, C, 14)
    R = np.log(C / ta.shift(C, 1))
    qty, entry, stop, held = [], [], [], []
    for j, (_, n, _) in enumerate(BOOK):
        e = O[-n, j]                                   # filled at the open n bars ago (entry day = day 1)
        a = A[-n - 1, j]                               # ATR known the evening before
        qty.append(np.floor(min(EQUITY * 0.0075 / (K * a), EQUITY * 0.20 / C[-n - 1, j])))
        entry.append(e)
        stop.append(e - K * a)
        held.append(float(n))
    tw = PC.book_twin(C[-1], Ll[-1], A[-1], R[-60:], np.array(qty), np.array(entry), np.array(stop), np.array(held), equity=EQUITY, hold=HOLD)
    lo, hlo, hhi, hi = tw["band"]
    th = lambda t, al="right": f'<td class="c" style="text-align:{al}">{t}</td>'
    rows = [f'<tr><td class="h" colspan="7">SL PORTFOLIO DESK&nbsp;&nbsp;·&nbsp;&nbsp;{tw["n_active"]} positions&nbsp;&nbsp;·&nbsp;&nbsp;hold {HOLD} bars</td></tr>',
            "<tr>" + th("Position", "left") + th("% of equity") + th("Result") + th("Day") + th("At risk") + th("Earnings") + th("Status", "center") + "</tr>"]
    for r in tw["rows"]:
        sym, _, sess = BOOK[r["i"]]
        inside = sess <= HOLD
        st, sc = ("STOP TOUCHED", STOP) if r["touched"] else ("EARNINGS", WARN) if inside else ("TIME UP", WARN) if r["time_up"] else ("ok", GOOD)
        rc = GOOD if r["r"] >= 0 else STOP
        rows.append(f'<tr><td>{sym}</td><td class="n">{r["pct"]:.1f}%</td><td class="n" style="color:{rc}">{r["r"]:+.2f} R</td>'
                    f'<td class="n" style="color:{WARN if r["time_up"] else FG}">{r["day"]:.0f} / {HOLD}</td><td class="n">{r["at_risk"]:.2f}%</td>'
                    f'<td class="n" style="color:{STOP if inside else FG}">{sess}</td><td class="chip" style="color:{sc};background:{sc}26">{st}</td></tr>'.replace("-", "−"))
    wide = lambda k, v, tag="", c=FG: f'<tr><td class="k">{k}</td><td colspan="5" style="color:{c}">{v}</td><td class="t" style="color:{GOOD if tag else MUTED}">{tag}</td></tr>'
    rows += ['<tr><td class="s" colspan="7">BOOK</td></tr>',
             wide("Invested", f'{100 * tw["exposure"]:.1f}% of equity&nbsp;&nbsp;·&nbsp;&nbsp;result so far {tw["result"]:+,.0f}'.replace("-", "−")),
             wide("Open risk", f'{100 * tw["open_risk"]:.2f}% of equity if every stop fills at its price&nbsp;&nbsp;·&nbsp;&nbsp;limit 6%'),
             wide("Range, 9 in 10", f'{100 * lo:.1f}% to +{100 * hi:.1f}% of equity&nbsp;&nbsp;·&nbsp;&nbsp;{lo * EQUITY:,.0f} to +{hi * EQUITY:,.0f}'.replace("-", "−"), "C"),
             wide("Range, 1 in 2", f'{100 * hlo:.1f}% to +{100 * hhi:.1f}% of equity'.replace("-", "−"), "C"),
             wide("Diversification", f'behaves like {tw["n_eff"]:.1f} independent positions, of {tw["n_active"]}&nbsp;&nbsp;·&nbsp;&nbsp;average correlation {tw["rho_avg"]:.2f}'),
             '<tr><td class="f" colspan="7">C checked once on 2023-26&nbsp;&nbsp;·&nbsp;&nbsp;daily values, final at the close&nbsp;&nbsp;·&nbsp;&nbsp;hover a cell</td></tr>']
    out = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:{BG};font-family:Inter,'Helvetica Neue',Arial,'DejaVu Sans',sans-serif;}}
#wrap{{display:inline-block;padding:26px 30px 16px 30px;background:{BG};}}
table{{border:1px solid rgba(209,212,220,.22);background:rgba(19,23,34,.94);border-collapse:collapse;font-size:13px;color:{FG};}}
td{{padding:5px 12px;white-space:nowrap;}}
.h{{background:{ACC};color:#fff;font-weight:600;}} .s{{background:rgba(76,139,245,.12);color:{ACC};}} .k,.c{{color:{MUTED};}}
.n{{text-align:right;}} .t{{text-align:center;font-weight:600;}} .f{{color:{MUTED};font-size:11px;}} .chip{{text-align:center;font-weight:600;font-size:12px;}}
#cap{{color:{MUTED};font-size:11.5px;margin-top:10px;max-width:760px;line-height:1.45;}}
</style></head><body><div id="wrap"><table>{''.join(rows)}</table>
<div id="cap">Schematic drawn from the script's arithmetic on daily bars to {idx[-1].date()} (Yahoo). Not a TradingView screenshot. Positions and earnings dates are illustrative: each position is "bought" at the open n bars ago and sized as SL Risk Desk would have sized it.</div>
</div></body></html>"""
    outdir = Path(__file__).resolve().parent / "out"
    outdir.mkdir(exist_ok=True)
    (outdir / "portfolio_desk.html").write_text(out)
    print("wrote portfolio_desk.html | exposure", round(100 * tw["exposure"], 1), "open risk", round(100 * tw["open_risk"], 2), "band", [round(100 * x, 2) for x in tw["band"]],
          "n_eff", round(tw["n_eff"], 2), "rho", round(tw["rho_avg"], 2))
    for r in tw["rows"]:
        print("  ", BOOK[r["i"]][0], {k: (round(float(v), 2) if isinstance(v, (float, np.floating)) else v) for k, v in r.items()})


if __name__ == "__main__":
    main()
