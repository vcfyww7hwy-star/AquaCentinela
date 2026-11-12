#!/usr/bin/env python3
"""Schematic preview of SL Risk Desk, drawn from real daily bars with the script's own arithmetic.

This is NOT a TradingView screenshot. It is an HTML/SVG drawing of what the script computes and
where it puts it, so the usage guide can point at each element. The numbers come from
tools/parity_check.pine_twin (the line-by-line transliteration of the script) on Yahoo daily bars.

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


def fmt(x, d=2):
    return f"{x:,.{d}f}"


def main(sym: str, mode: str, env: bool = False) -> None:
    k, hold, equity, risk_pct, max_pos = 3.0, 10, 100000.0, 0.75, 20.0
    d = PC.load_yahoo(sym)
    col = lambda n: d[n].to_numpy(dtype=float).reshape(-1, 1)
    o, h, l, c, v = col("open"), col("high"), col("low"), col("close"), col("volume")
    tw = PC.pine_twin(o, h, l, c, v, k=k, hold=hold, equity=equity, risk_pct=risk_pct, max_pos=max_pos)
    T = len(d)
    s = slice(T - NBARS, T)
    O, Hh, Ll, C = o[s, 0], h[s, 0], l[s, 0], c[s, 0]
    e05, e25, e75, e95 = (tw[n][s, 0] for n in ("Envelope 5pct", "Envelope 25pct", "Envelope 75pct", "Envelope 95pct"))
    px = C[-1]
    atr = tw["Daily ATR14"][-1, 0]
    lo05, lo25, hi75, hi95 = (tw[n][-1, 0] for n in ("Band 5pct", "Band 25pct", "Band 75pct", "Band 95pct"))
    stop = tw["Stop price"][-1, 0]
    shares = tw["Shares"][-1, 0]
    q05, q25, q75, q95 = LB.PRODUCT_BANDS[hold]
    p_stop = PC.stop_odds(k, hold)
    cov90, cov50, cov_stop = tw["Record 90 band pct"][-1, 0], tw["Record 50 band pct"][-1, 0], tw["Record stop hit pct"][-1, 0]
    r_lo, r_hi = q05 * np.sqrt(hold) / k, q95 * np.sqrt(hold) / k
    last_date = d["date"].iloc[-1].date()

    # position mode: an illustrative entry 6 bars ago at that bar's open, stop 3 ATR (of the bar before) below it
    held, e_idx = 6, NBARS - 6
    entry = O[e_idx]
    atr_e = tw["Daily ATR14"][T - 6 - 1, 0]
    stop_e = entry - k * atr_e
    r_now = (px - entry) / (entry - stop_e)

    ys = [Ll.min(), Hh.max(), lo05, hi95, stop] + ([np.nanmin(e05), np.nanmax(e95)] if env else [])
    if mode == "position":
        ys += [stop_e]
    y0, y1 = min(ys), max(ys)
    pad = 0.06 * (y1 - y0)
    y0, y1 = y0 - pad, y1 + pad
    pw, ph = W - PL - PR, H - PT - PB
    bw = pw / (NBARS + FUT)
    X = lambda i: PL + (i + 0.5) * bw
    Y = lambda p: PT + (y1 - p) / (y1 - y0) * ph
    svg = []
    add = svg.append
    # grid and price axis
    step = float(np.round((y1 - y0) / 8 / 5) * 5) or 1.0
    g = np.ceil(y0 / step) * step
    while g < y1:
        add(f'<line x1="{PL}" x2="{W - PR}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" stroke="{GRID}"/>')
        add(f'<text x="{W - PR + 8}" y="{Y(g) + 4:.1f}" fill="{MUTED}" font-size="12">{fmt(g)}</text>')
        g += step
    for i in range(0, NBARS, 10):
        add(f'<text x="{X(i):.1f}" y="{H - 12}" fill="{MUTED}" font-size="12" text-anchor="middle">{d["date"].iloc[T - NBARS + i].strftime("%d %b")}</text>')
    # envelope
    ok = np.isfinite(e05)
    idx = np.flatnonzero(ok)
    outer = " ".join(f"{X(i):.1f},{Y(e95[i]):.1f}" for i in idx) + " " + " ".join(f"{X(i):.1f},{Y(e05[i]):.1f}" for i in idx[::-1])
    inner = " ".join(f"{X(i):.1f},{Y(e75[i]):.1f}" for i in idx) + " " + " ".join(f"{X(i):.1f},{Y(e25[i]):.1f}" for i in idx[::-1])
    if env:
        add(f'<polygon points="{outer}" fill="{ACC}" fill-opacity="0.06"/>')
        for e in (e05, e95):
            add(f'<polyline points="{" ".join(f"{X(i):.1f},{Y(e[i]):.1f}" for i in idx)}" fill="none" stroke="{ACC}" stroke-opacity="0.40"/>')
    if mode == "position":
        add(f'<rect x="{X(e_idx) - bw / 2:.1f}" y="{PT}" width="{(NBARS - e_idx) * bw:.1f}" height="{ph}" fill="{ACC}" fill-opacity="0.05"/>')
    # candles and outside-close dots
    for i in range(NBARS):
        colr = UP if C[i] >= O[i] else DN
        add(f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(Hh[i]):.1f}" y2="{Y(Ll[i]):.1f}" stroke="{colr}"/>')
        top, bot = Y(max(O[i], C[i])), Y(min(O[i], C[i]))
        add(f'<rect x="{X(i) - bw * 0.32:.1f}" y="{top:.1f}" width="{bw * 0.64:.1f}" height="{max(bot - top, 1):.1f}" fill="{colr}"/>')
        if env and np.isfinite(e95[i]) and C[i] > e95[i]:
            add(f'<circle cx="{X(i):.1f}" cy="{Y(Hh[i]) - 9:.1f}" r="3" fill="{WARN}"/>')
        if env and np.isfinite(e05[i]) and C[i] < e05[i]:
            add(f'<circle cx="{X(i):.1f}" cy="{Y(Ll[i]) + 9:.1f}" r="3" fill="{WARN}"/>')
    xl, xr = X(NBARS - 1), X(NBARS - 1 + hold)
    # cone
    add(f'<polygon points="{xl:.1f},{Y(px):.1f} {xr:.1f},{Y(hi95):.1f} {xr:.1f},{Y(lo05):.1f}" fill="{ACC}" fill-opacity="0.10"/>')
    add(f'<polygon points="{xl:.1f},{Y(px):.1f} {xr:.1f},{Y(hi75):.1f} {xr:.1f},{Y(lo25):.1f}" fill="{ACC}" fill-opacity="0.16"/>')
    for lv, dash, op in ((hi95, "", 0.7), (lo05, "", 0.7), (hi75, "2 4", 0.45), (lo25, "2 4", 0.45)):
        add(f'<line x1="{xl:.1f}" y1="{Y(px):.1f}" x2="{xr:.1f}" y2="{Y(lv):.1f}" stroke="{ACC}" stroke-opacity="{op}" stroke-dasharray="{dash}"/>')
    lab = lambda y, t, colr, op=1.0: add(f'<text x="{xr + 8:.1f}" y="{Y(y) + 4:.1f}" fill="{colr}" fill-opacity="{op}" font-size="12.5">{t}</text>')
    if mode == "position":
        r_lo, r_hi = (lo05 - entry) / (entry - stop_e), (hi95 - entry) / (entry - stop_e)
    lab(hi95, f"95%   {fmt(hi95)}   {r_hi:+.2f} R".replace("-", "−"), ACC)
    lab(hi75, f"75%   {fmt(hi75)}", ACC, 0.65)
    lab(lo25, f"25%   {fmt(lo25)}", ACC, 0.65)
    lab(lo05, f"5%   {fmt(lo05)}   {r_lo:+.2f} R".replace("-", "−"), ACC)
    # earnings marker (illustrative date, 7 sessions ahead)
    xe = X(NBARS - 1 + 7)
    add(f'<line x1="{xe:.1f}" x2="{xe:.1f}" y1="{Y(hi95):.1f}" y2="{Y(lo05):.1f}" stroke="{WARN}" stroke-dasharray="5 4"/>')
    add(f'<rect x="{xe - 34:.1f}" y="{Y(hi95) - 26:.1f}" width="68" height="20" rx="3" fill="{WARN}" fill-opacity="0.2"/>')
    add(f'<text x="{xe:.1f}" y="{Y(hi95) - 12:.1f}" fill="{WARN}" font-size="12.5" text-anchor="middle">Earnings</text>')
    # stop, entry, R levels
    if mode == "plan":
        add(f'<line x1="{X(NBARS - 5):.1f}" x2="{xr:.1f}" y1="{Y(stop):.1f}" y2="{Y(stop):.1f}" stroke="{STOP}" stroke-width="2" stroke-dasharray="7 5"/>')
        add(f'<text x="{X(NBARS - 5) - 6:.1f}" y="{Y(stop) + 17:.1f}" fill="{STOP}" font-size="12.5" text-anchor="end">Stop   {fmt(stop)}   ·   {k:g} ATR</text>')
    else:
        r1 = entry - stop_e
        add(f'<line x1="{X(e_idx):.1f}" x2="{xr:.1f}" y1="{Y(stop_e):.1f}" y2="{Y(stop_e):.1f}" stroke="{STOP}" stroke-width="2" stroke-dasharray="7 5"/>')
        add(f'<text x="{X(e_idx) - 6:.1f}" y="{Y(stop_e) + 17:.1f}" fill="{STOP}" font-size="12.5" text-anchor="end">Stop   {fmt(stop_e)}</text>')
        add(f'<line x1="{X(e_idx):.1f}" x2="{xr:.1f}" y1="{Y(entry):.1f}" y2="{Y(entry):.1f}" stroke="{ACC}"/>')
        add(f'<text x="{X(e_idx) - 6:.1f}" y="{Y(entry) + 4:.1f}" fill="{ACC}" font-size="12.5" text-anchor="end">Entry   {fmt(entry)}</text>')
        xt = X(e_idx + hold - 1)
        add(f'<line x1="{xt:.1f}" x2="{xt:.1f}" y1="{Y(hi95):.1f}" y2="{Y(stop_e):.1f}" stroke="{FG}" stroke-opacity="0.45" stroke-dasharray="2 4"/>')
        add(f'<text x="{xt:.1f}" y="{Y(stop_e) + 18:.1f}" fill="{FG}" fill-opacity="0.7" font-size="12.5" text-anchor="middle">day {hold}</text>')
    # last price tag on the axis
    add(f'<rect x="{W - PR}" y="{Y(px) - 10:.1f}" width="{PR - 6}" height="20" fill="{UP if C[-1] >= O[-1] else DN}"/>')
    add(f'<text x="{W - PR + 8}" y="{Y(px) + 4:.1f}" fill="#fff" font-size="12">{fmt(px)}</text>')

    # ---- table
    def row(k_, v_, tag="", colr=FG):
        tc = GOOD if tag == "D" else WARN if tag == "S" else MUTED
        return f'<tr><td class="k">{k_}</td><td style="color:{colr}">{v_}</td><td class="t" style="color:{tc}">{tag}</td></tr>'
    sec = lambda t: f'<tr><td class="s" colspan="3">{t}</td></tr>'
    rows = [f'<tr><td class="h">SL RISK DESK</td><td class="h" colspan="2">{sym}&nbsp;&nbsp;·&nbsp;&nbsp;hold {hold} bars&nbsp;&nbsp;·&nbsp;&nbsp;stop {k:g} ATR</td></tr>']
    if mode == "plan":
        rows += [sec("PLAN&nbsp;&nbsp;&nbsp;if bought at the next open"),
                 row("Buy", f"{shares:,.0f} shares&nbsp;&nbsp;·&nbsp;&nbsp;{shares * px:,.0f} USD&nbsp;&nbsp;·&nbsp;&nbsp;{100 * shares * px / equity:.1f}%"),
                 row("Stop", f"{fmt(stop)}&nbsp;&nbsp;·&nbsp;&nbsp;{fmt(k * atr)} below the fill"),
                 row("At risk", f"{shares * k * atr:,.0f} USD&nbsp;&nbsp;·&nbsp;&nbsp;{100 * shares * k * atr / equity:.2f}% of equity"),
                 row("Stop hit by noise", f"{100 * p_stop:.0f}% within {hold} bars", "D")]
    else:
        rows += [sec("POSITION"),
                 row("Now", f"{r_now:+.2f} R&nbsp;&nbsp;·&nbsp;&nbsp;day {held} of {hold}", "", GOOD if r_now >= 0 else FG),
                 row("Entry / stop", f"{fmt(entry)} / {fmt(stop_e)}&nbsp;&nbsp;·&nbsp;&nbsp;1 R = {fmt(entry - stop_e)}")]
    rows += [sec(f"RANGE&nbsp;&nbsp;&nbsp;close in {hold} bars"),
             row("9 in 10", f"{fmt(lo05)} – {fmt(hi95)}&nbsp;&nbsp;·&nbsp;&nbsp;{r_lo:+.2f} R / {r_hi:+.2f} R".replace("-", "−"), "D"),
             row("1 in 2", f"{fmt(lo25)} – {fmt(hi75)}", "D"),
             row("This stock", f"90%: {cov90:.1f}&nbsp;&nbsp;·&nbsp;&nbsp;50%: {cov50:.1f}&nbsp;&nbsp;·&nbsp;&nbsp;stop: {cov_stop:.1f}"),
             sec("EVENTS"),
             row("Earnings", "~7 sessions&nbsp;&nbsp;·&nbsp;&nbsp;INSIDE the period", "", STOP),
             row("Earnings night", "1 in 10 gaps over 2 ATR", "U", WARN),
             row("Index", "SPY above its 200-day avg", "S"),
             row("Universe", "inside"),
             '<tr><td class="f" colspan="3">D demonstrated&nbsp;&nbsp;·&nbsp;&nbsp;S suggestive&nbsp;&nbsp;·&nbsp;&nbsp;U untested&nbsp;&nbsp;·&nbsp;&nbsp;hover a row</td></tr>']
    # numbered callouts
    def tagc(n, x, y):
        return f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#fff"/><text x="{x:.1f}" y="{y + 4.5:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="#111">{n}</text></g>'
    calls = [tagc(1, (xl + xr) / 2 - 22, Y((px + hi95) / 2) - 22), tagc(2, X(NBARS - 5) + 30, Y(stop if mode == "plan" else stop_e) - 16), tagc(3, xe + 46, Y(hi95) - 16)]
    if env:
        calls.append(tagc(6, X(NBARS - 30), Y(e95[NBARS - 30]) - 16))
    if mode == "position":
        calls.append(tagc(5, X(e_idx) - 14, Y(entry) - 18))
    out = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:{BG};font-family:Inter,'Helvetica Neue',Arial,'DejaVu Sans',sans-serif;}}
#wrap{{position:relative;width:{W}px;height:{H}px;}}
#card{{position:absolute;left:{PL + 10}px;bottom:{PB + 34}px;border:1px solid rgba(209,212,220,.22);background:rgba(19,23,34,.94);border-collapse:collapse;font-size:12.5px;color:{FG};}}
#card td{{padding:4px 10px;white-space:nowrap;}}
#card .h{{background:{ACC};color:#fff;font-weight:600;}}
#card .s{{background:rgba(76,139,245,.12);color:{ACC};}}
#card .k{{color:{MUTED};}}
#card .t{{text-align:center;font-weight:600;}}
#card .f{{color:{MUTED};font-size:10.5px;}}
#cap{{position:absolute;right:{PR + 10}px;bottom:{PB + 8}px;color:{MUTED};font-size:11.5px;text-align:right;}}
#n4{{position:absolute;left:{PL - 4}px;bottom:{PB + 22}px;}}
</style></head><body><div id="wrap">
<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg">{''.join(svg)}{''.join(calls)}</svg>
<table id="card">{''.join(rows)}</table>
<svg id="n4" width="26" height="26">{tagc(4, 13, 13)}</svg>
<div id="cap">Schematic drawn from the script's arithmetic on {sym} daily bars to {last_date} (Yahoo). Not a TradingView screenshot. Earnings date and, in position mode, the entry are illustrative.</div>
</div></body></html>"""
    outdir = Path(__file__).resolve().parent / "out"
    outdir.mkdir(exist_ok=True)
    name = f"risk_desk_{mode}{'_envelope' if env else ''}.html"
    (outdir / name).write_text(out)
    print("wrote", outdir / name, "| px", round(px, 2), "atr", round(atr, 2), "shares", shares, "stop", round(stop, 2), "band", round(lo05, 2), round(hi95, 2), "| r_now", round(r_now, 2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "AAPL", sys.argv[2] if len(sys.argv) > 2 else "plan", "--envelope" in sys.argv)
