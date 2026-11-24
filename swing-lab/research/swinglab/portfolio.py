"""Portfolio simulator: what the trader's account would have done.

The event studies answer "does this signal carry information?". This answers the question that
matters for money: a book of a few positions, chosen from the day's candidates, sized by risk,
entered at the next open, protected by stop orders, with costs - against the benchmarks a
sceptic would choose (SPY bought and held; the same rules with random selection).

Daily cycle (protocol section 5)
    close of t      exits by rule are decided; free slots are filled from the day's candidates in
                    descending score; size = risk_frac * equity / (stop_k * ATR), capped by
                    max_weight * equity and by cash (no leverage)
    open of t+1     exits and entries are executed at the open, each paying `cost_bp`
    during t+1      a resting stop exits at the stop, or at the open if the bar opens below it
                    (gap-through); stop fills pay `stop_extra_bp` more
    close of t+1    trailing stops are raised; equity is marked

`exposure[t]` in [0, 1] (the regime dial) scales the number of slots that may be filled; it never
forces a sale unless `force_exit` is set.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import engine as E


@dataclass
class PortfolioResult:
    equity: pd.Series
    trades: pd.DataFrame
    stats: dict


def run(S, score: np.ndarray, entry_ok: np.ndarray, *, n_slots: int = 8, risk_frac: float = 0.0075,
        stop_k: float = 2.5, trail_k: float = 0.0, max_hold: int = 20, exit_sig: np.ndarray | None = None,
        exposure: np.ndarray | None = None, force_exit: bool = False, max_weight: float = 0.25,
        cost_bp: float = 5.0, stop_extra_bp: float = 10.0, haircut: float = -0.30,
        atr: np.ndarray | None = None, rows: np.ndarray | None = None, start_equity: float = 100_000.0,
        seed: int | None = None) -> PortfolioResult:
    P = S.P
    rows = S.rows if rows is None else rows
    r = np.flatnonzero(rows)
    t0, t1 = int(r[0]), int(r[-1])
    atr = S.atr(14) if atr is None else atr
    div = _div(P)
    cost, sx = cost_bp / 1e4, stop_extra_bp / 1e4
    rng = np.random.default_rng(seed) if seed is not None else None
    cash = start_equity
    pos: dict[int, dict] = {}
    eq = np.full(len(S.dates), np.nan)
    trades = []
    pending_exit: set[int] = set()
    pending_entry: list[tuple[int, float, float]] = []     # (col, stop distance, target value)

    def close_pos(n, px, t, reason, extra=0.0):
        nonlocal cash
        p = pos.pop(n)
        proceeds = p["sh"] * px * (1.0 - cost - extra)
        cash += proceeds
        cost_in = p["sh"] * p["entry"] * (1.0 + cost)
        trades.append((n, p["t_in"], t, (proceeds + p["divs"]) / cost_in - 1.0,
                       (px - p["entry"]) / p["risk"], t - p["t_in"] + 1, reason, cost_in))

    for t in range(t0, t1 + 1):
        # ---- open of t: execute what was decided at the close of t-1
        for n in list(pending_exit):
            if n in pos and np.isfinite(P.o[t, n]):
                close_pos(n, P.o[t, n], t, "rule")
                pending_exit.discard(n)
        equity_open = cash + sum(p["sh"] * (P.o[t, n] if np.isfinite(P.o[t, n]) else P.cf[t - 1, n]) for n, p in pos.items())
        for n, dist, _ in pending_entry:
            if n in pos or not np.isfinite(P.o[t, n]) or dist <= 0:
                continue
            px = P.o[t, n]
            sh = risk_frac * equity_open / dist
            sh = min(sh, max_weight * equity_open / px, max(cash, 0.0) / (px * (1.0 + cost)))
            if sh * px < 0.01 * equity_open:
                continue
            cash -= sh * px * (1.0 + cost)
            pos[n] = {"sh": sh, "entry": px, "risk": dist, "stop": px - dist, "t_in": t, "hi": px, "divs": 0.0}
        pending_entry = []
        # ---- during t: dividends, stops, delisting
        for n in list(pos):
            p = pos[n]
            if P.last[n] < t and not P.alive[n]:
                px = P.cf[min(P.last[n], t), n] * ((1.0 + haircut) if P.cause[n] else 1.0)
                close_pos(n, px, t, "delist")
                continue
            if not np.isfinite(P.c[t, n]):
                continue
            if t > p["t_in"] and div[t, n] > 0:
                p["divs"] += p["sh"] * div[t, n]
                cash += p["sh"] * div[t, n]
            if t > p["t_in"] and P.o[t, n] <= p["stop"]:
                close_pos(n, P.o[t, n], t, "gap_stop", sx)
            elif P.l[t, n] <= p["stop"]:
                close_pos(n, p["stop"], t, "stop", sx)
        # ---- close of t: mark, trail, decide
        equity = cash + sum(p["sh"] * P.cf[t, n] for n, p in pos.items())
        eq[t] = equity
        for n, p in pos.items():
            if trail_k > 0 and np.isfinite(P.c[t, n]) and np.isfinite(atr[t, n]):
                p["hi"] = max(p["hi"], P.c[t, n])
                p["stop"] = max(p["stop"], p["hi"] - trail_k * atr[t, n])
            if max_hold > 0 and t - p["t_in"] + 1 >= max_hold:
                pending_exit.add(n)
            if exit_sig is not None and exit_sig[t, n]:
                pending_exit.add(n)
        exp_t = 1.0 if exposure is None else float(np.clip(exposure[t], 0.0, 1.0)) if np.isfinite(exposure[t]) else 0.0
        allowed = int(round(n_slots * exp_t))
        if force_exit and len(pos) - len(pending_exit) > allowed:
            keep = sorted((n for n in pos if n not in pending_exit), key=lambda n: -score[t, n] if np.isfinite(score[t, n]) else 1e9)
            for n in keep[allowed:]:
                pending_exit.add(n)
        free = allowed - (len(pos) - len(pending_exit))
        if free > 0 and t < t1:
            cand = np.flatnonzero(entry_ok[t] & np.isfinite(atr[t]) & (atr[t] > 0))
            cand = np.array([n for n in cand if n not in pos], dtype=int)
            if len(cand):
                if rng is not None:
                    order = rng.permutation(len(cand))
                else:
                    sc = np.where(np.isfinite(score[t, cand]), score[t, cand], -np.inf)
                    order = np.argsort(-sc, kind="mergesort")
                for n in cand[order][:free]:
                    pending_entry.append((int(n), stop_k * atr[t, n], 0.0))
    # liquidate at the last close
    for n in list(pos):
        close_pos(n, P.cf[t1, n], t1, "end")
    e = pd.Series(eq[t0:t1 + 1], index=pd.DatetimeIndex(S.dates[t0:t1 + 1])).ffill()
    tr = pd.DataFrame(trades, columns=["col", "t_in", "t_out", "ret", "R", "bars", "reason", "value_in"])
    return PortfolioResult(e, tr, stats(e, tr))


def stats(e: pd.Series, tr: pd.DataFrame | None = None) -> dict:
    ret = e.pct_change().dropna()
    yrs = len(ret) / 252.0
    cagr = (e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan
    vol = ret.std() * np.sqrt(252)
    dd = (e / e.cummax() - 1).min()
    out = {"cagr": round(100 * cagr, 2), "vol": round(100 * vol, 2),
           "sharpe": round(float(ret.mean() / ret.std() * np.sqrt(252)), 2) if ret.std() > 0 else np.nan,
           "maxdd": round(100 * dd, 1), "years": round(yrs, 2)}
    if tr is not None and len(tr):
        out.update({"trades": int(len(tr)), "trades_per_year": round(len(tr) / yrs, 1),
                    "win": round(float((tr["ret"] > 0).mean()), 3), "avg_ret_bp": round(1e4 * tr["ret"].mean(), 1),
                    "avg_R": round(float(tr["R"].mean()), 3), "avg_bars": round(float(tr["bars"].mean()), 1),
                    "turnover_per_year": round(float(tr["value_in"].sum() / e.mean() / yrs), 1),
                    "exit_mix": {k: round(float(v), 3) for k, v in tr["reason"].value_counts(normalize=True).items()}})
    return out


def benchmark(S, col: int | None = None, rows: np.ndarray | None = None) -> dict:
    """Buy and hold of one security (default SPY), dividends reinvested."""
    rows = S.rows if rows is None else rows
    r = np.flatnonzero(rows)
    col = S.spy if col is None else col
    e = pd.Series(S.P.tri[r[0]:r[-1] + 1, col], index=pd.DatetimeIndex(S.dates[r[0]:r[-1] + 1]))
    return stats(e)


def _div(P: E.Prepared) -> np.ndarray:
    prev = E.lag(P.cf, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        d = P.tri / E.lag(P.tri, 1) * prev - P.cf
    return np.where(np.isfinite(d) & (d > 1e-9), d, 0.0)
