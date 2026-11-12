#!/usr/bin/env python3
"""Schematic preview of SL Risk Desk, drawn from real daily bars with the script's own arithmetic.

This is NOT a TradingView screenshot. It is an HTML/SVG drawing of what the script computes and
where it puts it, so the usage guide can point at each element. The numbers come from
tools/parity_check.pine_twin (the line-by-line transliteration of the script) on Yahoo daily bars.
Fonts, spacing and the exact position of labels on TradingView will differ.

    python tools/preview/make_preview.py AAPL plan       -> tools/preview/out/risk_desk_plan.html
    python tools/preview/make_preview.py AAPL position   -> tools/preview/out/risk_desk_position.html
    node tools/preview/render.cjs                         -> docs/img/*.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import parity_check as PC  # noqa: E402
from research.confirm import prereg_lockbox as LB  # noqa: E402

ACC, STOP, GOOD, WARN = "#4C8BF5", "#E5484D", "#2EBD85", "#F0A030"
BG, FG, MUTED, GRID = "#131722", "#D1D4DC", "#787B86", "#1E222D"
UP, DN = "#26A69A", "#EF5350"
W, H = 1500, 800
PL, PR, PT, PB = 16, 96, 18, 34          # plot margins
NBARS, FUT = 70, 16
DOT = "&nbsp;·&nbsp;"


def fmt(x, d=2):
    return f"{x:,.{d}f}"


def sgn(x):
    return f"{x:+.2f}".replace("-", "−")


def main(sym: str, mode: str) -> None:
    k, hold, equity, risk_pct, max_pos = 3.0, 10, 100000.0, 0.75, 20.0
    d = PC.load_yahoo(sym)
    col = lambda n: d[n].to_numpy(dtype=float).reshape(-1, 1)
    o, h, l, c, v = col("open"), col("high"), col("low"), col("close"), col("volume")
    tw = PC.pine_twin(o, h, l, c, v, k=k, hold=hold, equity=equity, risk_pct=risk_pct, max_pos=max_pos)
    T = len(d)
    s = slice(T - NBARS, T)
    O, Hh, Ll, C = o[s, 0], h[s, 0], l[s, 0], c[s, 0]
    px = C[-1]
    atr = tw["Daily ATR14"][-1, 0]
    lo05, lo25, hi75, hi95 = (tw[n][-1, 0] for n in ("Band 5pct", "Band 25pct", "Band 75pct", "Band 95pct"))
    stop = tw["Stop price"][-1, 0]
    shares = tw["Shares"][-1, 0]
    q05, q25, q75, q95 = LB.PRODUCT_BANDS[hold]
    p_stop = PC.stop_odds(k, hold)
    cov90, cov50, cov_stop = tw["Record 90 band pct"][-1, 0], tw["Record 50 band pct"][-1, 0], tw["Record stop hit pct"][-1, 0]
    last_date = d["date"].iloc[-1].date()
    sess_e = 7                                         # illustrative: sessions to the next report

    # position mode: an illustrative entry 6 bars ago at that bar's open, first stop 3 ATR (of the bar before) below it
    held, e_idx = 6, NBARS - 6
    entry = O[e_idx]
    stop_e = entry - k * tw["Daily ATR14"][T - 6 - 1, 0]
    r_now = (px - entry) / (entry - stop_e)
    pos = mode == "position"
    stop_shown = stop_e if pos else stop
    r_of = (lambda lv: (lv - entry) / (entry - stop_e)) if pos else (lambda lv: (lv - px) / (k * atr))
    e_inside = sess_e <= (max(hold - held, 0) if pos else hold)

    ys = [Ll.min(), Hh.max(), lo05, hi95, stop_shown]
    y0, y1 = min(ys), max(ys)
    pad = 0.07 * (y1 - y0)
    y0, y1 = y0 - pad, y1 + pad
    pw, ph = W - PL - PR, H - PT - PB
    bw = pw / (NBARS + FUT)
    X = lambda i: PL + (i + 0.5) * bw
    Y = lambda p: PT + (y1 - p) / (y1 - y0) * ph
    svg = []
    add = svg.append
    step = float(np.round((y1 - y0) / 8 / 5) * 5) or 1.0
    g = np.ceil(y0 / step) * step
    while g < y1:
        add(f'<line x1="{PL}" x2="{W - PR}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" stroke="{GRID}"/>')
        add(f'<text x="{W - PR + 8}" y="{Y(g) + 4:.1f}" fill="{MUTED}" font-size="12">{fmt(g)}</text>')
        g += step
    for i in range(0, NBARS, 10):
        add(f'<text x="{X(i):.1f}" y="{H - 12}" fill="{MUTED}" font-size="12" text-anchor="middle">{d["date"].iloc[T - NBARS + i].strftime("%d %b")}</text>')
    if pos:
        add(f'<rect x="{X(e_idx) - bw / 2:.1f}" y="{PT}" width="{(NBARS - e_idx) * bw:.1f}" height="{ph}" fill="{ACC}" fill-opacity="0.08"/>')
    for i in range(NBARS):
        colr = UP if C[i] >= O[i] else DN
        add(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(Hh[i]):.1f}" y2="{Y(Ll[i]):.1f}" stroke="{colr}"/>')
        top, bot = Y(max(O[i], C[i])), Y(min(O[i], C[i]))
        add(f'<rect x="{X(i) - bw * 0.32:.1f}" y="{top:.1f}" width="{bw * 0.64:.1f}" height="{max(bot - top, 1):.1f}" fill="{colr}"/>')
    xl, xr = X(NBARS - 1), X(NBARS - 1 + hold)
    # cone
    add(f'<polygon points="{xl:.1f},{Y(px):.1f} {xr:.1f},{Y(hi95):.1f} {xr:.1f},{Y(lo05):.1f}" fill="{ACC}" fill-opacity="0.10"/>')
    add(f'<polygon points="{xl:.1f},{Y(px):.1f} {xr:.1f},{Y(hi75):.1f} {xr:.1f},{Y(lo25):.1f}" fill="{ACC}" fill-opacity="0.16"/>')
    for lv, dash, op in ((hi95, "", 0.7), (lo05, "", 0.7), (hi75, "2 4", 0.45), (lo25, "2 4", 0.45)):
        add(f'<line x1="{xl:.1f}" y1="{Y(px):.1f}" x2="{xr:.1f}" y2="{Y(lv):.1f}" stroke="{ACC}" stroke-opacity="{op}" stroke-dasharray="{dash}"/>')
    # two tags at the cone's corners, running left from its end
    tag = lambda y, t: add(f'<text x="{xr - 4:.1f}" y="{y:.1f}" fill="{ACC}" font-size="12.5" text-anchor="end">{t}</text>')
    tag(Y(hi95) - 22, f"95%&#160;&#160;{fmt(hi95)}")
    tag(Y(hi95) - 7, f"75%&#160;&#160;{fmt(hi75)}")
    y_low = Y(min(lo05, stop_shown))
    tag(y_low + 17, f"25%&#160;&#160;{fmt(lo25)}")
    tag(y_low + 32, f"5%&#160;&#160;{fmt(lo05)}")
    # earnings marker, placed in bars
    xe = X(NBARS - 1 + sess_e)
    add(f'<line x1="{xe:.1f}" x2="{xe:.1f}" y1="{Y(hi95):.1f}" y2="{Y(lo05):.1f}" stroke="{WARN}" stroke-dasharray="5 4"/>')
    add(f'<rect x="{xe - 33:.1f}" y="{Y(px) - 11:.1f}" width="66" height="21" rx="3" fill="{BG}"/>')
    add(f'<rect x="{xe - 33:.1f}" y="{Y(px) - 11:.1f}" width="66" height="21" rx="3" fill="{WARN}" fill-opacity="0.25"/>')
    add(f'<text x="{xe:.1f}" y="{Y(px) + 4:.1f}" fill="{WARN}" font-size="12.5" text-anchor="middle">Earnings</text>')
    # stop, entry
    x_from = X(e_idx) if pos else X(NBARS - 5)
    add(f'<line x1="{x_from:.1f}" x2="{xr:.1f}" y1="{Y(stop_shown):.1f}" y2="{Y(stop_shown):.1f}" stroke="{STOP}" stroke-width="2" stroke-dasharray="7 5"/>')
    add(f'<text x="{x_from - 6:.1f}" y="{Y(stop_shown) + 17:.1f}" fill="{STOP}" font-size="12.5" text-anchor="end">Stop&#160;&#160;{fmt(stop_shown)}{"" if pos else f"&#160;&#160;·&#160;&#160;{k:g} ATR"}</text>')
    if pos:
        add(f'<line x1="{x_from:.1f}" x2="{xr:.1f}" y1="{Y(entry):.1f}" y2="{Y(entry):.1f}" stroke="{ACC}"/>')
        add(f'<text x="{x_from - 6:.1f}" y="{Y(entry) - 7:.1f}" fill="{ACC}" font-size="12.5" text-anchor="end">Entry</text>')
        xt = X(e_idx + hold - 1)
        add(f'<line x1="{xt:.1f}" x2="{xt:.1f}" y1="{Y(max(hi95, entry)):.1f}" y2="{Y(stop_e):.1f}" stroke="{FG}" stroke-opacity="0.45" stroke-dasharray="2 4"/>')
        add(f'<text x="{xt + 6:.1f}" y="{Y(entry) - 7:.1f}" fill="{FG}" fill-opacity="0.7" font-size="12.5">day {hold}</text>')
    add(f'<rect x="{W - PR}" y="{Y(px) - 10:.1f}" width="{PR - 6}" height="20" fill="{UP if C[-1] >= O[-1] else DN}"/>')
    add(f'<text x="{W - PR + 8}" y="{Y(px) + 4:.1f}" fill="#fff" font-size="12">{fmt(px)}</text>')

    # ---- table
    def row(k_, v_, tag_="", colr=FG):
        tc = GOOD if tag_ == "D" else WARN if tag_ == "S" else MUTED
        return f'<tr><td class="k">{k_}</td><td style="color:{colr}">{v_}</td><td class="t" style="color:{tc}">{tag_}</td></tr>'
    sec = lambda t, note="": f'<tr class="s"><td><b>{t}</b></td><td>{note}</td><td></td></tr>'
    rows = [f'<tr class="h"><td><b>SL RISK DESK</b></td><td>{sym}{DOT}hold {hold}{DOT}stop {k:g} ATR</td><td></td></tr>']
    if pos:
        rows += [sec("POSITION"),
                 row("Now", f"{sgn(r_now)} R{DOT}day {held}/{hold}", "", GOOD if r_now >= 0 else FG),
                 row("Entry / stop", f"{fmt(entry)} / {fmt(stop_e)}{DOT}1 R = {fmt(entry - stop_e)}")]
    else:
        rows += [sec("PLAN", "if bought at the next open"),
                 row("Buy", f"{shares:,.0f} shares{DOT}{shares * px:,.0f} USD{DOT}{100 * shares * px / equity:.1f}%"),
                 row("Stop", f"{fmt(stop)}{DOT}{fmt(k * atr)} below the fill"),
                 row("At risk", f"{shares * k * atr:,.0f} USD{DOT}{100 * shares * k * atr / equity:.2f}% of equity"),
                 row("Stop hit by noise", f"{100 * p_stop:.0f}% within {hold} bars", "D")]
    rows += [sec("RANGE", f"close in {hold} bars"),
             row("9 in 10", f"{fmt(lo05)} – {fmt(hi95)}{DOT}{sgn(r_of(lo05))} R / {sgn(r_of(hi95))} R", "D"),
             row("1 in 2", f"{fmt(lo25)} – {fmt(hi75)}", "D"),
             row("This stock", f"90%: {cov90:.1f}{DOT}50%: {cov50:.1f}{DOT}stop: {cov_stop:.1f}"),
             sec("EVENTS"),
             row("Earnings", f"~{sess_e} sessions{DOT}{'INSIDE the period' if e_inside else 'outside the period'}", "", STOP if e_inside else FG),
             row("Earnings night", "1 in 10 gaps over 2 ATR", "U", WARN if e_inside else FG),
             row("Index", "SPY above its 200-day avg", "S"),
             row("Universe", "inside"),
             f'<tr class="f"><td>D demonstrated</td><td>S suggestive{DOT}U untested{DOT}hover a row</td><td></td></tr>']

    def tagc(n, x, y):
        return f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#fff"/><text x="{x:.1f}" y="{y + 4.5:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="#111">{n}</text></g>'
    calls = [tagc(1, xl + (xr - xl) * 0.42, Y(px + (hi95 - px) * 0.42) - 24), tagc(2, x_from + 34, Y(stop_shown) - 17), tagc(3, xe + 50, Y(px))]
    if pos:
        calls.append(tagc(5, X(e_idx) + 10, PT + 16))
    out = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:{BG};font-family:Inter,'Helvetica Neue',Arial,'DejaVu Sans',sans-serif;}}
#wrap{{position:relative;width:{W}px;height:{H}px;}}
#card{{position:absolute;left:{PL + 10}px;bottom:{PB + 34}px;border:1px solid rgba(209,212,220,.22);background:rgba(19,23,34,.94);border-collapse:collapse;font-size:12.5px;color:{FG};}}
#card td{{padding:4px 10px;white-space:nowrap;}}
#card .h td{{background:{ACC};color:#fff;}}
#card .s td{{background:rgba(76,139,245,.12);color:{ACC};}}
#card .k{{color:{MUTED};}}
#card .t{{text-align:center;font-weight:600;}}
#card .f td{{color:{MUTED};font-size:10.5px;}}
#cap{{position:absolute;right:{PR + 10}px;bottom:{PB + 8}px;color:{MUTED};font-size:11.5px;text-align:right;}}
#n4{{position:absolute;left:{PL - 4}px;bottom:{PB + 22}px;}}
</style></head><body><div id="wrap">
<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg">{''.join(svg)}{''.join(calls)}</svg>
<table id="card">{''.join(rows)}</table>
<svg id="n4" width="26" height="26">{tagc(4, 13, 13)}</svg>
<div id="cap">Schematic drawn from the script's arithmetic on {sym} daily bars to {last_date} (Yahoo). Not a TradingView screenshot. Earnings date{" and entry" if pos else ""} illustrative.</div>
</div></body></html>"""
    outdir = Path(__file__).resolve().parent / "out"
    outdir.mkdir(exist_ok=True)
    name = f"risk_desk_{mode}.html"
    (outdir / name).write_text(out)
    print("wrote", outdir / name, "| px", round(px, 2), "atr", round(atr, 2), "shares", shares, "stop", round(stop, 2), "band", round(lo05, 2), round(hi95, 2), "| r_now", round(r_now, 2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "AAPL", sys.argv[2] if len(sys.argv) > 2 else "plan")
