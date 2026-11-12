#!/usr/bin/env python3
"""Parity checks: is the Pine script the same mathematics as the research code, bar for bar?

Three checks, from the weakest to the strongest.

  constants   The numbers typed into the Pine files are read out of the Pine source and compared
              with the frozen tables that were tested on the lockbox (research/confirm/prereg_lockbox.py).

  self        A line-by-line Python transliteration of the Pine script's daily core (`pine_twin`,
              below, each line next to the Pine statement it copies) is run on real daily bars and
              compared with the research code that produced the published numbers: the band
              variable of g50_calibration.band_y and the stop outcomes of swinglab.trades.simulate.
              This catches off-by-one errors in the Pine design. It does not execute Pine.

  tv-csv      The file TradingView exports from a chart that carries the indicator ("Export chart
              data") holds TradingView's own bars and the script's own plotted values. The same
              research code is run on those bars and compared with those values. This is the check
              that counts: it executes the real script on the real platform.

  tv-trades   The Strategy Tester's "List of trades" export of SL Odds Check is compared, trade for
              trade, with swinglab.trades.simulate run on the chart's exported bars.

Usage (from swing-lab/):
    python tools/parity_check.py constants
    python tools/parity_check.py self AAPL NVDA GE KO --k 3 --hold 10
    python tools/parity_check.py book AAPL NVDA XOM JPM KO GE --hold 10
    python tools/parity_check.py tv-csv path/to/export.csv --k 3 --hold 10 --equity 100000 --risk 0.75 --maxpos 20
    python tools/parity_check.py tv-trades path/to/chart.csv path/to/trades.csv --k 2 --hold 10
Exit code 0 when every comparison is inside its tolerance.
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research.confirm import prereg_lockbox as LB  # noqa: E402
from research.swinglab import engine as E  # noqa: E402
from research.swinglab import pinelike as ta  # noqa: E402
from research.swinglab import trades as TR  # noqa: E402

PINE_DESK = ROOT / "pine" / "sl_risk_desk.pine"
PINE_ODDS = ROOT / "pine" / "sl_odds_check.pine"
PINE_BOOK = ROOT / "pine" / "sl_portfolio_desk.pine"
BOOK_CONSTANTS = ROOT / "research" / "confirm" / "portfolio_band_constants.json"
KS = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0)


# ------------------------------------------------------------------------------------ constants
def _pine_array(src: str, name: str) -> list[float]:
    m = re.search(rf"array<float>\s+{name}\s*=\s*array\.from\(([^)]*)\)", src)
    if not m:
        raise ValueError(f"array {name} not found in the Pine source")
    return [float(x) for x in m.group(1).split(",")]


def _pine_ternary(src: str, name: str) -> dict[int, float]:
    m = re.search(rf"float\s+{name}\s*=\s*(.+)", src)
    line = m.group(1)
    t = re.match(r"i_hold == 5 \?\s*(-?[\d.]+)\s*:\s*i_hold == 10 \?\s*(-?[\d.]+)\s*:\s*(-?[\d.]+)", line)
    if t:
        return {5: float(t.group(1)), 10: float(t.group(2)), 20: float(t.group(3))}
    v = float(re.match(r"(-?[\d.]+)", line).group(1))
    return {5: v, 10: v, 20: v}


def check_constants() -> bool:
    ok = True
    for f in (PINE_DESK, PINE_ODDS):
        src = f.read_text()
        for h, nm in ((5, "p5"), (10, "p10"), (20, "p20")):
            got = _pine_array(src, nm)
            want = [LB.PRODUCT_STOP_TABLE[f"k{k}_h{h}"] for k in KS]
            same = got == want
            ok &= same
            print(f"  {f.name:<22s} stop odds, {h:>2d} bars: {'identical to the lockbox table' if same else f'DIFFERENT {got} vs {want}'}")
    src = PINE_DESK.read_text()
    q = {nm: _pine_ternary(src, nm) for nm in ("Q05", "Q25", "Q75", "Q95")}
    for h in (5, 10, 20):
        got = (q["Q05"][h], q["Q25"][h], q["Q75"][h], q["Q95"][h])
        same = got == LB.PRODUCT_BANDS[h]
        ok &= same
        print(f"  {PINE_DESK.name:<22s} band quantiles, {h:>2d} bars: {'identical to the lockbox bands' if same else f'DIFFERENT {got} vs {LB.PRODUCT_BANDS[h]}'}")
    if PINE_BOOK.exists():
        import json
        src = PINE_BOOK.read_text()
        want = json.loads(BOOK_CONSTANTS.read_text())["bands"]
        q = {nm: _pine_ternary(src, nm) for nm in ("PQ05", "PQ25", "PQ75", "PQ95")}
        for h in (5, 10, 20):
            got = [q["PQ05"][h], q["PQ25"][h], q["PQ75"][h], q["PQ95"][h]]
            same = got == want[str(h)]
            ok &= same
            print(f"  {PINE_BOOK.name:<22s} book band, {h:>2d} bars: {'identical to the committed constants' if same else f'DIFFERENT {got} vs {want[str(h)]}'}")
    return ok


# ------------------------------------------------------------------------------------ the Pine twin
def stop_odds(k: float, h: int) -> float:
    """f_stopOdds of sl_risk_desk.pine."""
    p = [LB.PRODUCT_STOP_TABLE[f"k{x}_h{h}"] for x in KS]
    kk = max(1.0, min(4.0, k))
    res = p[5]
    for i in range(5):
        k0, k1 = KS[i], KS[i + 1]
        if k0 <= kk <= k1:
            res = p[i] + (p[i + 1] - p[i]) * (kk - k0) / (k1 - k0)
            break
    return res


def pine_twin(o, h, l, c, v, *, k: float, hold: int, equity: float, risk_pct: float, max_pos: float) -> dict:
    """sl_risk_desk.pine on a daily chart, statement by statement. Arrays are [T, 1]."""
    q05, q25, q75, q95 = LB.PRODUCT_BANDS[hold]
    # f_core()
    a = ta.atr(h, l, c, 14)                                          # float a  = ta.atr(14)
    dv = ta.median(c * v, 60)                                        # float dv = ta.median(close * volume, 60)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = np.log(c / ta.shift(c, hold)) / (ta.shift(a, hold) / ta.shift(c, hold) * np.sqrt(hold))    # float y = math.log(c / c[i_hold]) / (a[i_hold] / c[i_hold] * math.sqrt(i_hold))
    have = np.isfinite(y)                                            # bool have = not na(y)
    with np.errstate(divide="ignore", invalid="ignore"):
        u_ago = ta.shift(a, hold) / ta.shift(c, hold) * np.sqrt(hold)                              # float uAgo = a[i_hold] / c[i_hold] * math.sqrt(i_hold)
        e05, e25 = ta.shift(c, hold) * np.exp(q05 * u_ago), ta.shift(c, hold) * np.exp(q25 * u_ago)     # float e05 = c[i_hold] * math.exp(Q05 * uAgo) ...
        e75, e95 = ta.shift(c, hold) * np.exp(q75 * u_ago), ta.shift(c, hold) * np.exp(q95 * u_ago)
    n = np.cumsum(have, axis=0).astype(float)                        # float n = ta.cum(have ? 1.0 : 0.0)
    f90 = have & (y >= q05) & (y <= q95)
    f50 = have & (y >= q25) & (y <= q75)
    in90 = np.cumsum(f90, axis=0).astype(float)                      # float in90 = ta.cum(have and y >= Q05 and y <= Q95 ? 1.0 : 0.0)
    in50 = np.cumsum(f50, axis=0).astype(float)                      # float in50 = ta.cum(have and y >= Q25 and y <= Q75 ? 1.0 : 0.0)
    lowest = ta.lowest(l, hold)                                      # float lowest = ta.lowest(low, i_hold)
    stop_lvl = ta.shift(o, hold - 1) - k * ta.shift(a, hold)         # float stopLvl = open[i_hold - 1] - i_stopK * a[i_hold]
    have_s = np.isfinite(stop_lvl)                                   # bool haveS = not na(stopLvl)
    n_s = np.cumsum(have_s, axis=0).astype(float)                    # float nS = ta.cum(haveS ? 1.0 : 0.0)
    fhit = have_s & (lowest <= stop_lvl)
    hits = np.cumsum(fhit, axis=0).astype(float)                     # float hits = ta.cum(haveS and lowest <= stopLvl ? 1.0 : 0.0)
    # the plan
    px = c                                                           # float px = close
    stop_dist = k * a                                                # float stopDist = i_stopK * atrD
    stop_px = px - stop_dist                                         # float stopPx = px - stopDist
    risk_cash = equity * risk_pct / 100.0                            # float riskCash = i_equity * i_riskPct / 100.0
    with np.errstate(divide="ignore", invalid="ignore"):
        shares_raw = np.where(stop_dist > 0, risk_cash / stop_dist, np.nan)      # float sharesRaw = stopDist > 0 ? riskCash / stopDist : na
        shares_cap = np.where(px > 0, equity * max_pos / 100.0 / px, np.nan)     # float sharesCap = px > 0 ? i_equity * i_maxPos / 100.0 / px : na
        shares = np.floor(np.fmin(shares_raw, shares_cap))           # float shares = math.floor(math.min(sharesRaw, sharesCap))
        shares = np.where(np.isfinite(shares_raw) & np.isfinite(shares_cap), shares, np.nan)       # math.min returns na if either is na
        pos_pct = 100.0 * shares * px / equity                       # float posPct = 100.0 * posValue / i_equity
        unit = a / c * np.sqrt(hold)                                 # float unit = atrD / closeD * math.sqrt(i_hold)
        cov90 = np.where(n > 0, 100.0 * in90 / n, np.nan)            # float cov90 = nAud > 0 ? 100.0 * in90 / nAud : na
        cov50 = np.where(n > 0, 100.0 * in50 / n, np.nan)
        cov_stop = np.where(n_s > 0, 100.0 * hits / n_s, np.nan)
    return {
        "Daily ATR14": a, "ATR pct of price": 100.0 * a / c, "Stop price": stop_px, "Shares": shares, "Position pct of equity": pos_pct,
        "Stop odds pct": np.full(c.shape, 100.0 * stop_odds(k, hold)),
        "Band 5pct": px * np.exp(q05 * unit), "Band 25pct": px * np.exp(q25 * unit), "Band 75pct": px * np.exp(q75 * unit), "Band 95pct": px * np.exp(q95 * unit),
        "Record 90 band pct": cov90, "Record 50 band pct": cov50, "Record stop hit pct": cov_stop, "Record windows": np.where(n > 0, n, 0.0),
        "Median dollar volume M": dv / 1e6,
        "Envelope 5pct": e05, "Envelope 25pct": e25, "Envelope 75pct": e75, "Envelope 95pct": e95,
        "_y": y, "_f90": f90, "_f50": f50, "_fhit": fhit, "_have_s": have_s,
    }


def book_twin(closes: np.ndarray, lows: np.ndarray, atrs: np.ndarray, rets: np.ndarray, qty, entry, stop, held, *, equity: float, hold: int, heat_max: float = 6.0) -> dict:
    """sl_portfolio_desk.pine on its last bar, statement by statement.
    closes, lows, atrs: [N] values of the last bar; rets: [60, N] the last 60 daily log returns (rows oldest first);
    qty, entry, stop, held: [N] inputs and day counts."""
    import json
    q05, q25, q75, q95 = json.loads(BOOK_CONSTANTS.read_text())["bands"][str(hold)]
    N = len(closes)
    sqrt_h = np.sqrt(hold)                                                           # float sqrtH = math.sqrt(i_hold)
    active = [bool(qty[i] > 0 and np.isfinite(closes[i]) and np.isfinite(atrs[i])) for i in range(N)]      # f_active(i)
    exposure = sum(qty[i] * closes[i] / equity for i in range(N) if active[i])       # exposure += QTY.get(i) * CLS.get(i) / i_equity
    open_risk = sum(qty[i] * max(closes[i] - stop[i], 0.0) / equity for i in range(N) if active[i] and stop[i] > 0)   # openRisk += ...
    result = sum(qty[i] * (closes[i] - entry[i]) for i in range(N) if active[i] and entry[i] > 0)
    wu = [qty[i] * atrs[i] * sqrt_h / equity if active[i] else 0.0 for i in range(N)]                      # WU.set(i, QTY.get(i) * ATR.get(i) * sqrtH / i_equity)

    def corr(i, j):                                                                  # f_corr(i, j)
        x, y = rets[:, i], rets[:, j]
        m = np.isfinite(x) & np.isfinite(y)
        n = int(m.sum())
        if n < 20:
            return 0.3
        x, y = x[m], y[m]
        vx, vy = (x * x).mean() - x.mean() ** 2, (y * y).mean() - y.mean() ** 2
        return ((x * y).mean() - x.mean() * y.mean()) / np.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.3

    var_p, rho_sum, pairs = 0.0, 0.0, 0
    for i in range(N):
        if wu[i] > 0:
            var_p += wu[i] * wu[i]                                                   # varP += WU.get(i) * WU.get(i)
            for j in range(i + 1, N):
                if wu[j] > 0:
                    rho = corr(i, j)
                    var_p += 2.0 * wu[i] * rho * wu[j]                               # varP += 2.0 * WU.get(i) * rho * WU.get(j)
                    rho_sum += rho
                    pairs += 1
    s_p = np.sqrt(var_p) if var_p > 0 else np.nan                                    # float sP = varP > 0 ? math.sqrt(varP) : na
    rows = []
    for i in range(N):
        if not active[i]:
            continue
        risk = entry[i] - stop[i]
        r_now = (closes[i] - entry[i]) / risk if risk > 0 and stop[i] > 0 else np.nan      # f_r(i)
        rows.append({"i": i, "pct": 100.0 * qty[i] * closes[i] / equity, "r": r_now, "day": held[i],
                     "at_risk": 100.0 * qty[i] * max(closes[i] - stop[i], 0.0) / equity if stop[i] > 0 else np.nan,
                     "time_up": held[i] >= hold, "touched": held[i] >= 1 and stop[i] > 0 and lows[i] <= stop[i]})
    return {"rows": rows, "n_active": sum(active), "exposure": exposure, "open_risk": open_risk, "result": result, "s_p": s_p,
            "band": (s_p * q05, s_p * q25, s_p * q75, s_p * q95), "n_eff": sum(wu) ** 2 / var_p if var_p > 0 else np.nan,
            "rho_avg": rho_sum / pairs if pairs else np.nan, "hot": 100.0 * open_risk > heat_max, "wu": wu}


def check_book(symbols, a) -> bool:
    """The book twin's scale s_p against the formula the band was calibrated with (g70: einsum over the correlation matrix)."""
    frames = {s_: load_yahoo(s_).set_index("date") for s_ in symbols}
    idx = None
    for f in frames.values():
        idx = f.index if idx is None else idx.intersection(f.index)
    idx = idx.sort_values()[-400:]
    C = np.column_stack([frames[s_].loc[idx, "close"].to_numpy(dtype=float) for s_ in symbols])
    Hh = np.column_stack([frames[s_].loc[idx, "high"].to_numpy(dtype=float) for s_ in symbols])
    Ll = np.column_stack([frames[s_].loc[idx, "low"].to_numpy(dtype=float) for s_ in symbols])
    A = ta.atr(Hh, Ll, C, 14)
    R = np.log(C / ta.shift(C, 1))
    atrp = A[-1] / C[-1]
    w = np.minimum(0.0025 / atrp, 0.20)                       # the weights of g70's "risk" scheme
    qty = w * a.equity / C[-1]
    tw = book_twin(C[-1], Ll[-1], A[-1], R[-60:], qty, C[-1] * 0.99, C[-1] * 0.93, np.full(len(symbols), 3.0), equity=a.equity, hold=a.hold)
    wu = w * atrp * np.sqrt(a.hold)
    s_ref = float(np.sqrt(np.einsum("i,ij,j->", wu, np.corrcoef(R[-60:], rowvar=False), wu)))
    ok = abs(tw["s_p"] - s_ref) / s_ref < 1e-12
    print(f"  book of {len(symbols)}: scale s_p, Pine twin {tw['s_p']:.10f}  calibration formula {s_ref:.10f}  {'ok' if ok else 'FAIL'}"
          f"   (behaves like {tw['n_eff']:.2f} independent positions; average correlation {tw['rho_avg']:.2f})")
    return ok


# ------------------------------------------------------------------------------------ the research side
def prepared(o, h, l, c, v, ncols: int = 1) -> E.Prepared:
    """An engine.Prepared for one security, repeated in `ncols` columns (no dividends, still trading)."""
    rep = lambda x: np.repeat(np.asarray(x, dtype=float).reshape(-1, 1), ncols, axis=1)
    o, h, l, c, v = rep(o), rep(h), rep(l), rep(c), rep(v)
    T = c.shape[0]
    prev = E.lag(c, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = np.log(c / prev)
        gross = np.where(np.isfinite(prev), c / prev, 1.0)
    return E.Prepared(o, h, l, c, c.copy(), v, ret, np.cumprod(gross, axis=0), np.full(ncols, T - 1), np.zeros(ncols, dtype=int),
                      np.zeros(ncols, dtype=bool), np.ones(ncols, dtype=bool))


def research_band(P: E.Prepared, hold: int):
    """y and its validity exactly as research/experiments/g50_calibration.band_y computes them
    (signal bar t), without the universe and sample masks, which do not apply to one chart."""
    from research.experiments.g50_calibration import band_y
    T = P.c.shape[0]
    S = SimpleNamespace(P=P, uni=np.ones(P.c.shape, dtype=bool), rows=np.ones(T, dtype=bool), _last_row=T - 1,
                        atr=lambda n: ta.atr(P.h, P.l, P.cf, n))
    y, ok = band_y(S, hold)
    return y[:, 0], ok[:, 0]


def research_stops(o, h, l, c, v, k: float, hold: int) -> np.ndarray:
    """For every signal bar t: was a stop k ATR below the next open hit within `hold` bars,
    according to swinglab.trades.simulate? The simulator takes one position at a time, so the
    security is copied into hold+1 columns whose entries are staggered. Returns float [T]:
    1 stopped, 0 not, NaN where the simulator made no trade."""
    nc = hold + 1
    P = prepared(o, h, l, c, v, nc)
    T = P.c.shape[0]
    atr = ta.atr(P.h, P.l, P.cf, 14)
    sig = np.zeros((T, nc), dtype=bool)
    for r in range(nc):
        sig[r::nc, r] = True
    tr = TR.simulate(P, sig, atr, rows=np.ones(T, dtype=bool), stop_k=k, max_hold=hold, cost_bp=0, stop_extra_bp=0)
    out = np.full(T, np.nan)
    out[tr["entry"].to_numpy() - 1] = tr["reason"].isin(["stop", "gap_stop"]).to_numpy().astype(float)
    return out


def compare(name: str, got: np.ndarray, want: np.ndarray, tol: float, rel: bool = True, skip: int = 0) -> bool:
    g, w = np.asarray(got, dtype=float)[skip:], np.asarray(want, dtype=float)[skip:]
    both = np.isfinite(g) & np.isfinite(w)
    only = int((np.isfinite(g) != np.isfinite(w)).sum())
    if both.sum() == 0:
        print(f"    {name:<26s} nothing to compare")
        return False
    d = np.abs(g[both] - w[both])
    if rel:
        d = d / np.maximum(np.abs(w[both]), 1e-12)
    worst = float(d.max())
    ok = worst <= tol and only == 0
    print(f"    {name:<26s} bars {int(both.sum()):>6d}   largest {'relative' if rel else 'absolute'} difference {worst:.2e}   defined on one side only: {only:<4d} {'ok' if ok else 'FAIL'}")
    return ok


# ------------------------------------------------------------------------------------ self
def load_yahoo(sym: str) -> pd.DataFrame:
    frames = []
    for f in sorted(glob.glob("/home/user/data/yahoo_daily/1d_*.parquet")):
        d = pd.read_parquet(f)
        d = d[d["symbol"] == sym]
        if len(d):
            frames.append(d)
    d = pd.concat(frames).drop_duplicates("date").sort_values("date").dropna(subset=["open", "high", "low", "close"])
    return d.reset_index(drop=True)


def check_self(symbols, a) -> bool:
    ok = True
    for sym in symbols:
        d = load_yahoo(sym)
        col = lambda k: d[k].to_numpy(dtype=float).reshape(-1, 1)
        o, h, l, c, v = col("open"), col("high"), col("low"), col("close"), col("volume")
        print(f"  {sym}: {len(d)} daily bars, {d['date'].iloc[0].date()} to {d['date'].iloc[-1].date()}")
        tw = pine_twin(o, h, l, c, v, k=a.k, hold=a.hold, equity=a.equity, risk_pct=a.risk, max_pos=a.maxpos)
        T = len(d)
        # band variable: Pine's value on bar T is the research value of signal bar T - hold
        y_ref, ok_ref = research_band(prepared(o, h, l, c, v), a.hold)
        y_shift = np.full(T, np.nan)
        y_shift[a.hold:] = np.where(ok_ref, y_ref, np.nan)[:T - a.hold]
        ok &= compare("band variable y", tw["_y"][:, 0], y_shift, 1e-12)
        q05, q25, q75, q95 = LB.PRODUCT_BANDS[a.hold]
        ok &= compare("inside the 90% band", tw["_f90"][:, 0].astype(float), np.where(np.isfinite(y_shift), (y_shift >= q05) & (y_shift <= q95), 0.0), 0, rel=False)
        ok &= compare("inside the middle half", tw["_f50"][:, 0].astype(float), np.where(np.isfinite(y_shift), (y_shift >= q25) & (y_shift <= q75), 0.0), 0, rel=False)
        # the plotted envelope says the same thing as the coverage flag: inside the 90% band <=> envelope low <= close <= envelope high
        inside_env = (c[:, 0] >= tw["Envelope 5pct"][:, 0]) & (c[:, 0] <= tw["Envelope 95pct"][:, 0])
        ok &= compare("envelope vs 90% flag", np.where(np.isfinite(y_shift), inside_env, 0.0).astype(float),
                      np.where(np.isfinite(y_shift), (y_shift >= q05) & (y_shift <= q95), 0.0), 0, rel=False)
        # stop outcome: Pine's flag on bar T is the simulator's outcome for the signal of bar T - hold
        st = research_stops(o[:, 0], h[:, 0], l[:, 0], c[:, 0], v[:, 0], a.k, a.hold)
        st_shift = np.full(T, np.nan)
        st_shift[a.hold:] = st[:T - a.hold]
        pine_flag = np.where(tw["_have_s"][:, 0], tw["_fhit"][:, 0].astype(float), np.nan)
        m = np.isfinite(st_shift) & np.isfinite(pine_flag)
        agree = float((pine_flag[m] == st_shift[m]).mean())
        good = agree == 1.0
        ok &= good
        print(f"    {'stop hit, vs the simulator':<26s} bars {int(m.sum()):>6d}   identical outcomes {100 * agree:.3f}%   stopped {100 * st_shift[m].mean():.1f}%  (displayed {100 * stop_odds(a.k, a.hold):.1f}%) {'ok' if good else 'FAIL'}")
        cov = tw["Record 90 band pct"][-1, 0], tw["Record 50 band pct"][-1, 0]
        print(f"    this symbol's record: 90% band held {cov[0]:.1f}%, middle half {cov[1]:.1f}%")
    return ok


# ------------------------------------------------------------------------------------ TradingView exports
def read_tv_chart(path: str) -> pd.DataFrame:
    d = pd.read_csv(path)
    d.columns = [str(x).strip() for x in d.columns]
    t = d["time"]
    d["time"] = pd.to_datetime(t, unit="s", utc=True) if np.issubdtype(t.dtype, np.number) else pd.to_datetime(t, utc=True)
    return d


def check_tv_csv(path: str, a) -> bool:
    d = read_tv_chart(path)
    print(f"  {path}: {len(d)} bars, {d['time'].iloc[0]} to {d['time'].iloc[-1]}")
    step = d["time"].diff().dt.total_seconds().median()
    if not 80000 <= step <= 90000 * 4:
        print("  This export is not from a daily chart. Export a DAILY chart: on other timeframes the script shows the same daily values with a one-day lag.")
        return False
    col = lambda k: d[k].to_numpy(dtype=float).reshape(-1, 1)
    o, h, l, c = col("open"), col("high"), col("low"), col("close")
    vname = next((k for k in d.columns if k.lower() == "volume"), None)
    v = col(vname) if vname else np.full(c.shape, np.nan)
    tw = pine_twin(o, h, l, c, v, k=a.k, hold=a.hold, equity=a.equity, risk_pct=a.risk, max_pos=a.maxpos)
    ok = True
    warm = 300            # ATR is a recursive average: if the chart had more history than the export, the two need ~300 bars to agree
    for name, tol in (("Daily ATR14", 1e-6), ("ATR pct of price", 1e-6), ("Stop price", 1e-6), ("Shares", 0.0), ("Position pct of equity", 1e-6),
                      ("Stop odds pct", 1e-9), ("Band 5pct", 1e-6), ("Band 25pct", 1e-6), ("Band 75pct", 1e-6), ("Band 95pct", 1e-6),
                      ("Envelope 5pct", 1e-6), ("Envelope 25pct", 1e-6), ("Envelope 75pct", 1e-6), ("Envelope 95pct", 1e-6)):
        if name not in d.columns:
            print(f"    {name:<26s} not in the export (is the indicator on the chart and visible?)")
            ok = False
            continue
        ok &= compare(name, d[name].to_numpy(dtype=float), tw[name][:, 0], tol if tol else 0.5, rel=tol != 0.0, skip=warm)
    if vname and "Median dollar volume M" in d.columns:
        ok &= compare("Median dollar volume M", d["Median dollar volume M"].to_numpy(dtype=float), tw["Median dollar volume M"][:, 0], 1e-6, skip=warm)
    # the record counts start at the script's first bar, which may be earlier than the export's: compare bar-by-bar increments
    if {"Record windows", "Record 90 band pct", "Record 50 band pct", "Record stop hit pct"} <= set(d.columns):
        n_tv = d["Record windows"].to_numpy(dtype=float)
        for lab, key, flag in (("90% band, per bar", "Record 90 band pct", "_f90"), ("middle half, per bar", "Record 50 band pct", "_f50")):
            cnt = np.round(d[key].to_numpy(dtype=float) * n_tv / 100.0)
            inc = np.diff(cnt, prepend=np.nan)
            ok &= compare(lab, inc, tw[flag][:, 0].astype(float), 0, rel=False, skip=warm)
        # stop record has its own window count (one bar fewer); recover it from the twin's offset
        ns_tw = np.cumsum(tw["_have_s"][:, 0])
        offset = np.nanmedian(n_tv - np.cumsum(np.isfinite(tw["_y"][:, 0])))
        cnt = np.round(d["Record stop hit pct"].to_numpy(dtype=float) * (ns_tw + offset) / 100.0)
        ok &= compare("stop hit, per bar", np.diff(cnt, prepend=np.nan), tw["_fhit"][:, 0].astype(float), 0, rel=False, skip=warm)
    return ok


def check_tv_trades(chart_csv: str, trades_csv: str, a) -> bool:
    d = read_tv_chart(chart_csv)
    col = lambda k: d[k].to_numpy(dtype=float)
    o, h, l, c = col("open"), col("high"), col("low"), col("close")
    P = prepared(o, h, l, c, np.ones_like(c))
    T = len(d)
    atr = ta.atr(P.h, P.l, P.cf, 14)
    sim = TR.simulate(P, np.ones((T, 1), dtype=bool), atr, rows=np.ones(T, dtype=bool), stop_k=a.k, max_hold=a.hold, cost_bp=0, stop_extra_bp=0)
    days = d["time"].dt.tz_convert("America/New_York").dt.date.to_numpy()
    mine = pd.DataFrame({"entry_day": days[sim["entry"].to_numpy()], "exit_day": days[sim["exit"].to_numpy()],
                         "stopped": sim["reason"].isin(["stop", "gap_stop"]).to_numpy()})
    t = pd.read_csv(trades_csv)
    t.columns = [str(x).strip() for x in t.columns]
    tcol = next(k for k in t.columns if k.lower().startswith("date"))
    typ = next(k for k in t.columns if k.lower() == "type")
    sigc = next(k for k in t.columns if k.lower() == "signal")
    num = next(k for k in t.columns if k.lower().startswith("trade"))
    t["day"] = pd.to_datetime(t[tcol]).dt.date
    ent = t[t[typ].str.lower().str.contains("entry")].set_index(num)
    ext = t[t[typ].str.lower().str.contains("exit")].set_index(num)
    tv = pd.DataFrame({"entry_day": ent["day"], "exit_day": ext["day"], "stopped": ext[sigc].astype(str).str.strip().eq("Stop")}).dropna().reset_index(drop=True)
    # the strategy starts on the chart's first bar, the export may start later: align on common entry days
    m = mine.merge(tv, on="entry_day", suffixes=("_research", "_tv"))
    if m.empty:
        print("  no common entry dates: are both files from the same symbol and the same daily chart?")
        return False
    same_exit = float((m["exit_day_research"] == m["exit_day_tv"]).mean())
    same_stop = float((m["stopped_research"] == m["stopped_tv"]).mean())
    print(f"  trades: TradingView {len(tv)}, research simulator {len(mine)}, matched on entry date {len(m)}")
    print(f"  same exit date {100 * same_exit:.2f}%   same exit type {100 * same_stop:.2f}%   stopped: TradingView {100 * tv['stopped'].mean():.1f}%, simulator {100 * mine['stopped'].mean():.1f}%")
    return len(m) >= 0.9 * min(len(tv), len(mine)) and same_exit >= 0.99 and same_stop >= 0.99


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["constants", "self", "book", "tv-csv", "tv-trades"])
    ap.add_argument("items", nargs="*")
    ap.add_argument("--k", type=float, default=3.0)
    ap.add_argument("--hold", type=int, default=10, choices=[5, 10, 20])
    ap.add_argument("--equity", type=float, default=100000.0)
    ap.add_argument("--risk", type=float, default=0.75)
    ap.add_argument("--maxpos", type=float, default=20.0)
    a = ap.parse_args()
    if a.mode == "constants":
        ok = check_constants()
    elif a.mode == "self":
        ok = check_constants() and check_self(a.items or ["AAPL", "NVDA", "GE", "KO"], a)
    elif a.mode == "book":
        ok = check_constants() and check_book(a.items or ["AAPL", "NVDA", "XOM", "JPM", "KO", "GE"], a)
    elif a.mode == "tv-csv":
        ok = all([check_tv_csv(p, a) for p in a.items])
    else:
        ok = check_tv_trades(a.items[0], a.items[1], a)
    print("PARITY", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
