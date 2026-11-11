"""Code audit (auditor tag "auditc"): independent re-implementation and look-ahead probes.

Run from swing-lab/:   python -m research.experiments.audit_code

What it does, on DEVELOPMENT rows only (2011-01-03..2018-06-29; arrays are cut at the last DEV row
before anything is computed, so no price after 2018-06-29 is ever read):

  1. Re-derives, from the WRITTEN definitions (research log entry 4, candidates.SPEC, the
     docstring of engine.vol_ewma), with pandas rolling functions and none of the project's
     helpers: the tradable universe, the volatility forecast, the forward total return from the
     next open, and the candidates E1 / A1 / A4 / A8. Compares the cross-sectional effect with
     research/results/g30_attack.json.
  2. Repeats the measurement on a corrected calendar (rows on which the market was closed removed,
     volume medians over real bars) to size the defects found.
  3. Probes: adv60 alignment, the `bad` flag, phantom rows, split/volume consistency, duplicated
     securities, price rounding, the non-standard skewness, VAL holidays (dates only).
  4. Lists random E1 / A1 events and counts one-day moves beyond 40%.

Imports from the project: swinglab.data.load_panel (raw arrays, dates) and swinglab.registry
(to count the cells looked at). Nothing from study / candidates / pinelike / engine.

    python -m research.experiments.audit_code --sim

runs seven synthetic scenarios through trades.simulate and engine.fwd_ret_open. That mode alone
imports the project's engine and trades, because there the simulator is the object under test.
"""
from __future__ import annotations

import json
import os
import time
import warnings
from pathlib import Path

os.environ["SWINGLAB_REGISTRY_TAG"] = "auditc"

import numpy as np
import pandas as pd

from research.swinglab.data import load_panel
from research.swinglab.registry import log_trial

warnings.filterwarnings("ignore")
DEV_END = np.datetime64("2018-06-29")
STOCK = ("common", "adr", "prior_use", "unknown")
LOGGED = {"E1_episodic_pivot": 56.7, "A1_shock_down_on_volume": -49.3, "A4_gap_down_weak_close": -40.1,
          "A8_pop_fade": -9.7}
HOR = {"E1_episodic_pivot": 10, "A1_shock_down_on_volume": 20, "A4_gap_down_weak_close": 20, "A8_pop_fade": 5}
OUT: dict = {}


# ------------------------------------------------------------------------------------ statistics
def nw_t(x: np.ndarray, lags: int) -> tuple[float, float, int]:
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 20:
        return float("nan"), float("nan"), n
    m = x.mean()
    e = x - m
    var = e @ e / n
    for k in range(1, min(lags, n - 1) + 1):
        var += 2.0 * (1.0 - k / (lags + 1.0)) * (e[k:] @ e[:-k]) / n
    return float(m), float(m / np.sqrt(var / n)), n


def xs_effect(fwd: np.ndarray, sig: np.ndarray, uni: np.ndarray, h: int) -> dict:
    """Per day: mean outcome of signal names minus mean outcome of universe names; mean over days."""
    ok = np.isfinite(fwd)
    s, u = sig & ok, uni & ok
    ns, nu = s.sum(1), u.sum(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        ms = np.where(ns >= 1, np.where(s, fwd, 0.0).sum(1) / ns, np.nan)
        mu = np.where(nu >= 20, np.where(u, fwd, 0.0).sum(1) / nu, np.nan)
    d = ms - mu
    m, t, days = nw_t(d, 2 * h)
    return {"bp": round(1e4 * m, 2), "t": round(t, 2), "events": int(ns[np.isfinite(d)].sum()), "days": days,
            "pooled_bp": round(1e4 * float(np.nansum(np.where(s, fwd - mu[:, None], 0.0)) / max(ns[np.isfinite(mu)].sum(), 1)), 2)}


# ------------------------------------------------------------------------------------ volatility
def vol_forecast(ret: np.ndarray, span: int = 20, warm: int = 20, floor: float = 0.002) -> np.ndarray:
    """Re-derived from the docstring of engine.vol_ewma: sqrt of an EMA (alpha = 2/(span+1)) of
    squared log returns; once `warm` returns have been seen each new squared return is capped at
    25x the running estimate (itself floored at floor^2); NaN until `warm` returns exist; missing
    returns leave the estimate unchanged. Value on row t uses returns up to and including t."""
    a = 2.0 / (span + 1.0)
    T, N = ret.shape
    s = np.full(N, np.nan)
    n = np.zeros(N, dtype=np.int64)
    out = np.full((T, N), np.nan)
    f2 = floor * floor
    for t in range(T):
        x = ret[t] * ret[t]
        ok = np.isfinite(x)
        xc = np.where(n >= warm, np.fmin(x, 25.0 * np.fmax(s, f2)), x)
        new = np.where(np.isnan(s), x, a * xc + (1.0 - a) * s)
        s = np.where(ok, new, s)
        n = n + ok
        out[t] = np.where(n >= warm, np.sqrt(np.fmax(s, f2)), np.nan)
    return out


def median_prev_bars(v: pd.DataFrame, n: int) -> pd.DataFrame:
    """Median of the previous n REAL bars of each security (rows without a bar are skipped, as on
    a TradingView chart, where such rows do not exist)."""
    a = v.to_numpy()
    order = np.argsort(np.isnan(a), axis=0, kind="stable")          # real bars first, in time order
    comp = np.take_along_axis(a, order, axis=0)
    med = pd.DataFrame(comp).rolling(n, min_periods=n).median().shift(1).to_numpy()
    out = np.full(a.shape, np.nan)
    np.put_along_axis(out, order, med, axis=0)
    out[np.isnan(a)] = np.nan
    return pd.DataFrame(out, index=v.index, columns=v.columns)


# ------------------------------------------------------------------------------------ pipeline
def build(raw: dict, dates: np.ndarray, ents: pd.DataFrame, *, keep_rows: np.ndarray | None = None,
          relv_bars: bool = False, tag: str = "") -> dict:
    t0 = time.time()
    if keep_rows is not None:
        raw = {k: x[keep_rows] for k, x in raw.items()}
        dates = dates[keep_rows]
    T = len(dates)
    typ = ents["type"].isin(STOCK).to_numpy()
    tc = np.flatnonzero(typ)
    bad = raw["bad"][:, tc] != 0
    c0, v0 = raw["c"][:, tc], raw["v"][:, tc]
    # --- universe, from the written rule: price as traded >= 5, median dollar volume of the last
    #     60 rows (current bar included, at least 40 bars) >= 20M, stock types, good bar
    adv = pd.DataFrame(c0 * v0).rolling(60, min_periods=40).median().to_numpy()
    uni = (adv >= 20e6) & (raw["c_raw"][:, tc] >= 5.0) & ~bad & np.isfinite(c0)
    cols = tc[uni.any(axis=0)]
    sel = np.isin(tc, cols)
    uni, adv, bad = uni[:, sel], adv[:, sel], bad[:, sel]
    idx = pd.DatetimeIndex(dates)

    def frame(k):
        x = raw[k][:, cols].copy()
        x[bad] = np.nan
        return pd.DataFrame(x, index=idx)

    o, h, l, c, v = (frame(k) for k in ("o", "h", "l", "c", "v"))
    div = np.nan_to_num(raw["div"][:, cols])
    craw = raw["c_raw"][:, cols]
    cf = c.ffill()
    pc = cf.shift(1)
    ret = np.log(c / pc)                                        # NaN where no bar today
    sigma = pd.DataFrame(vol_forecast(ret.to_numpy()), index=idx)
    s1 = sigma.shift(1)                                         # known before today's move
    z1 = ret / s1
    z3 = np.log(cf / cf.shift(3)) / (sigma.shift(3) * np.sqrt(3.0))
    gz = np.log(o / pc) / s1
    med = median_prev_bars(v, 20) if relv_bars else v.rolling(20, min_periods=20).median().shift(1)
    relv = v / med
    rng = h - l
    loc = ((c - l) / rng).where(rng > 0, 0.0)
    U = uni
    sig = {
        "E1_episodic_pivot": U & (gz >= 3).to_numpy() & (relv >= 3).to_numpy() & (loc >= 2 / 3).to_numpy(),
        "A1_shock_down_on_volume": U & (z1 <= -3).to_numpy() & (relv >= 3).to_numpy(),
        "A4_gap_down_weak_close": U & (gz <= -1).to_numpy() & (c < o).to_numpy(),
        "A8_pop_fade": U & (z3 > 1).to_numpy() & (z3 <= 2).to_numpy(),
    }
    # --- forward total return, open of t+1 to close of t+h, dividends from t+2 on (a buyer at the
    #     open of an ex-date does not receive that dividend); rows without a bar carry the position
    gross = ((c + div) / pc).where(c.notna() & pc.notna(), 1.0)
    lg = np.log(gross)
    day1 = np.log(c / o)
    has = c.notna().to_numpy()
    last = np.where(has.any(0), T - 1 - has[::-1].argmax(0), -1)
    e = ents.iloc[cols]
    ended_in_dev = (e["last"].to_numpy().astype("datetime64[D]") < dates[-1])      # metadata only
    ar = np.arange(len(cols))
    lc = craw[np.clip(last, 0, T - 1), ar]
    cfa = cf.to_numpy()
    r60 = cfa[np.clip(last, 0, T - 1), ar] / cfa[np.clip(last - 60, 0, T - 1), ar] - 1.0
    cause = ended_in_dev & ((lc < 2.0) | (r60 < -0.5))
    rows = np.arange(T)[:, None]

    def fwd(hh: int) -> np.ndarray:
        rest = lg.rolling(hh - 1, min_periods=hh - 1).sum().shift(-hh) if hh > 1 else 0.0
        f = (np.exp(day1.shift(-1) + rest) - 1.0).to_numpy()
        hit = cause[None, :] & (last[None, :] >= rows + 1) & (last[None, :] < rows + hh)
        return np.where(hit, (1.0 + f) * 0.70 - 1.0, f)

    res = {}
    fw = {}
    for name, hh in HOR.items():
        if hh not in fw:
            fw[hh] = fwd(hh)
        res[name] = xs_effect(fw[hh], sig[name], U, hh)
    print(f"[{tag}] rows {T}, securities {len(cols)}, universe cells {int(U.sum())}, {time.time() - t0:.0f}s")
    return dict(dates=dates, cols=cols, uni=U, adv=adv, o=o, h=h, l=l, c=c, v=v, cf=cf, pc=pc, ret=ret, sigma=sigma,
                z1=z1, z3=z3, gz=gz, relv=relv, loc=loc, sig=sig, fwd=fw, res=res, craw=craw, ents=e.reset_index(drop=True),
                last=last, cause=cause, bad=bad, typ_cols=tc, adv_all_sel=sel)


def show(title: str, res: dict, log_as: str) -> None:
    print(f"\n{title}")
    print(f"{'candidate':<26s} {'h':>3s} {'mine bp':>9s} {'t':>6s} {'events':>8s} {'days':>6s} {'pooled':>8s} {'logged':>8s} {'diff':>7s}")
    for k, r in res.items():
        print(f"{k:<26s} {HOR[k]:>3d} {r['bp']:>+9.1f} {r['t']:>+6.2f} {r['events']:>8d} {r['days']:>6d} {r['pooled_bp']:>+8.1f} "
              f"{LOGGED[k]:>+8.1f} {r['bp'] - LOGGED[k]:>+7.1f}")
        log_trial("AUDITC", "audit_code", f"{k} {log_as}", "DEV", "xs_bp", r["bp"], tstat=r["t"], n=r["events"],
                  params={"h": HOR[k]}, note="independent re-implementation by the code auditor")


# ------------------------------------------------------------------------------------ main
def main() -> None:
    p = load_panel()
    te = int(np.searchsorted(p.dates, DEV_END, side="right"))          # rows [0, te) are DEV
    dates = p.dates[:te]
    ents = p.ents
    raw = {k: np.asarray(getattr(p, k)[:te], dtype=np.float64) for k in ("o", "h", "l", "c", "v", "c_raw", "div", "bad")}
    adv_file = np.asarray(p.adv60[:te], dtype=np.float64)
    src = ents["src"].to_numpy()
    has0 = np.isfinite(raw["c"])

    # ---------------------------------------------------------------- 1. as the project defines it
    B = build(raw, dates, ents, tag="as-coded calendar")
    show("1. Independent re-implementation, same calendar as the project (DEV)", B["res"], "replication")
    OUT["replication"] = B["res"]

    # ---------------------------------------------------------------- probe (c): adv60 alignment
    tc = B["typ_cols"]
    mine = pd.DataFrame(raw["c"][:, tc] * raw["v"][:, tc]).rolling(60, min_periods=40).median()
    f = adv_file[:, tc]
    both = np.isfinite(mine.to_numpy()) & np.isfinite(f)
    rel = np.abs(mine.to_numpy()[both] / f[both] - 1)
    ex = mine.shift(1).to_numpy()
    both2 = np.isfinite(ex) & np.isfinite(f)
    rel2 = np.abs(ex[both2] / f[both2] - 1)
    OUT["adv60"] = {"cells": int(both.sum()), "nan_mismatch": int((np.isfinite(mine.to_numpy()) != np.isfinite(f)).sum()),
                    "incl_current_bar_max_rel_diff": float(np.nanmax(rel)), "incl_current_bar_share_gt_1e-5": float((rel > 1e-5).mean()),
                    "excl_current_bar_share_gt_1e-5": float((rel2 > 1e-5).mean())}
    print("\n(c) adv60 file vs my trailing median INCLUDING the current bar:", OUT["adv60"])

    # ---------------------------------------------------------------- probe: phantom rows
    ny = has0[:, src == "yahoo"].sum(1)
    nd = has0[:, src == "dolthub"].sum(1)
    med_y = pd.Series(ny).rolling(41, center=True, min_periods=5).median().to_numpy()
    closed = ny < 0.5 * med_y
    ph = np.flatnonzero(closed)
    print("\nRows on which the market was closed but the panel has a row (Yahoo bars / DoltHub bars):")
    for r in ph:
        print(f"   row {r:>4d}  {dates[r]}  {pd.Timestamp(dates[r]).day_name():<9s} yahoo {ny[r]:>5d}  dolthub {nd[r]:>5d}")
    # what the DoltHub bars on those rows look like
    dcol = np.flatnonzero(src == "dolthub")
    stale = tot = zero_v = 0
    for r in ph:
        cc, pv = raw["c"][r, dcol], raw["c"][r - 1, dcol]
        m = np.isfinite(cc) & np.isfinite(pv)
        tot += int(m.sum())
        stale += int((np.abs(cc[m] / pv[m] - 1) < 1e-6).sum())
        zero_v += int((raw["v"][r, dcol][m] == 0).sum())
    OUT["phantom_rows"] = {"dates": [str(dates[r]) for r in ph], "dolthub_bars": tot, "close_equals_previous_close": stale,
                           "zero_volume": zero_v}
    print("   DoltHub bars on those rows:", tot, "| close == previous close:", stale, "| zero volume:", zero_v)
    # blackout of the volume median: rows within 20 after a phantom row
    black = np.zeros(te, dtype=bool)
    for r in ph:
        black[r:r + 21] = True
    U, relv = B["uni"], B["relv"].to_numpy()
    ysel = (B["ents"]["src"] == "yahoo").to_numpy()
    nan_relv = U & ~np.isfinite(relv)
    OUT["relv_blackout"] = {
        "universe_cells": int(U.sum()), "relv_nan_cells": int(nan_relv.sum()),
        "relv_nan_share": round(float(nan_relv.sum() / U.sum()), 4),
        "rows_in_blackout": int(black.sum()), "share_of_dev_rows": round(float(black.mean()), 4),
        "relv_nan_in_blackout_rows": int(nan_relv[black].sum()),
    }
    for k in ("E1_episodic_pivot", "A1_shock_down_on_volume"):
        s = B["sig"][k]
        OUT["relv_blackout"][k] = {"events_total": int(s.sum()), "in_blackout_rows": int(s[black].sum()),
                                   "in_blackout_from_yahoo": int(s[black][:, ysel].sum()),
                                   "outside_from_dolthub_share": round(float(s[~black][:, ~ysel].sum() / max(s[~black].sum(), 1)), 3)}
    print("   volume-median blackout:", json.dumps(OUT["relv_blackout"]))
    # events lost because the next row is a phantom row (no bar at t+1 for Yahoo names)
    before = np.zeros(te, dtype=bool)
    before[ph - 1] = True
    OUT["events_on_row_before_phantom"] = {k: int(B["sig"][k][before].sum()) for k in HOR}
    print("   signals on the row before a phantom row (outcome is NaN for Yahoo names):", OUT["events_on_row_before_phantom"])

    # ---------------------------------------------------------------- 2. corrected calendar
    C = build(raw, dates, ents, keep_rows=~closed, relv_bars=True, tag="market-closed rows removed, medians over real bars")
    show("2. Same definitions on the corrected calendar (closed-market rows removed; volume median over real bars)",
         C["res"], "corrected calendar")
    OUT["corrected_calendar"] = C["res"]
    C2 = build(raw, dates, ents, keep_rows=~closed, relv_bars=False, tag="market-closed rows removed only")
    show("2b. Closed-market rows removed, volume median still NaN-poisoned by other holes", C2["res"], "rows removed only")
    OUT["rows_removed_only"] = C2["res"]
    C3 = build(raw, dates, ents, relv_bars=True, tag="as-coded calendar, volume median over real bars")
    show("2c. Calendar as coded, only the volume median repaired (isolates the 20-row blackout)", C3["res"], "median repaired only")
    OUT["median_repaired_only"] = C3["res"]
    del C3
    # by source, corrected calendar
    ys = (C["ents"]["src"] == "yahoo").to_numpy()
    OUT["by_source_corrected"] = {}
    print("\n   Corrected calendar, signal names split by data source (control = whole universe):")
    for k in ("E1_episodic_pivot", "A1_shock_down_on_volume"):
        hh = HOR[k]
        a = xs_effect(C["fwd"][hh], C["sig"][k] & ys[None, :], C["uni"], hh)
        b = xs_effect(C["fwd"][hh], C["sig"][k] & ~ys[None, :], C["uni"], hh)
        OUT["by_source_corrected"][k] = {"yahoo": a, "dolthub": b}
        print(f"   {k:<26s} yahoo {a['bp']:+7.1f} bp (t {a['t']:+.2f}, n {a['events']})   dolthub {b['bp']:+7.1f} bp (t {b['t']:+.2f}, n {b['events']})")
        for nm, r in (("yahoo", a), ("dolthub", b)):
            log_trial("AUDITC", "audit_code", f"{k} corrected calendar, {nm} names only", "DEV", "xs_bp", r["bp"], tstat=r["t"],
                      n=r["events"], params={"h": hh})
    del C2

    # ---------------------------------------------------------------- probe: the `bad` flag
    badm = raw["bad"] != 0
    typ = ents["type"].isin(STOCK).to_numpy()
    elig = badm & (adv_file >= 20e6) & (raw["c_raw"] >= 5) & typ[None, :]
    rr, cc = np.nonzero(elig)
    rows_bad = []
    for r, cix in zip(rr, cc):
        pv = raw["c"][r - 1, cix] if r > 0 else np.nan
        nx = raw["c"][r + 1, cix] if r + 1 < te else np.nan
        rows_bad.append({"symbol": ents["symbol"].iloc[cix], "date": str(dates[r]), "prev_close": round(float(pv), 3),
                         "close": round(float(raw["c"][r, cix]), 3), "next_close": round(float(nx), 3),
                         "ret_pct": round(float(100 * (raw["c"][r, cix] / pv - 1)), 1), "volume": float(raw["v"][r, cix])})
    OUT["bad_flag"] = {"bad_bars_dev_all": int(badm.sum()), "bad_bars_in_universe_filters": int(elig.sum()), "bars": rows_bad}
    print("\n`bad` flag (uses the NEXT close): bars in DEV", int(badm.sum()), "| of them passing the universe filters:", int(elig.sum()))
    for b in rows_bad:
        print("  ", b)

    # ---------------------------------------------------------------- probe: split / volume consistency
    fac = raw["c_raw"] / raw["c"]
    with np.errstate(divide="ignore", invalid="ignore"):
        jump = np.abs(np.log(fac[1:] / fac[:-1]))
    rr, cc = np.nonzero(np.nan_to_num(jump) > np.log(1.4))
    dv = raw["c"] * raw["v"]
    lr, lf, ls, in_uni = [], [], [], 0
    for r, cix in zip(rr + 1, cc):
        if r < 12 or r + 11 >= te:
            continue
        a, b = np.nanmedian(dv[r - 10:r, cix]), np.nanmedian(dv[r:r + 10, cix])
        if np.isfinite(a) and np.isfinite(b) and a > 0 and b > 0:
            lr.append(np.log(b / a))
            in_uni += int(adv_file[r, cix] >= 20e6)
            lf.append(np.log(fac[r, cix] / fac[r - 1, cix]))
            ls.append(src[cix])
    lr, lf, ls = np.array(lr), np.array(lf), np.array(ls)
    OUT["split_volume"] = {"split_events_checked": int(len(lr)), "in_liquid_names": in_uni,
                           "median_log_dollar_volume_after_over_before": round(float(np.median(lr)), 3),
                           "share_abs_log_gt_0.69": round(float((np.abs(lr) > 0.69).mean()), 3)}
    for sname in ("yahoo", "dolthub"):
        m = ls == sname
        # slope of log(dollar volume after/before) on log(factor after/before): 0 if volume is adjusted
        # consistently with price, -1 if volume was left unadjusted, +1 if adjusted twice
        OUT["split_volume"][sname] = {"n": int(m.sum()), "forward_splits": int((lf[m] < 0).sum()),
                                      "slope": round(float(np.polyfit(lf[m], lr[m], 1)[0]), 3) if m.sum() > 5 else None,
                                      "median_fwd": round(float(np.median(lr[m & (lf < 0)])), 3) if (m & (lf < 0)).sum() else None,
                                      "median_rev": round(float(np.median(lr[m & (lf > 0)])), 3) if (m & (lf > 0)).sum() else None}
    print("\nSplit dates (adjustment factor changes by >= 1.4x): dollar volume after / before:", OUT["split_volume"])

    # ---------------------------------------------------------------- probe: duplicated securities in the universe
    dup = 0
    checked = 0
    pairs = {}
    bsym = B["ents"]["symbol"].to_numpy()
    bmid = B["ents"]["mid"].to_numpy()
    for r in range(60, te):
        m = np.flatnonzero(B["uni"][r])
        key = pd.Series(list(zip(np.round(B["craw"][r, m], 3), B["v"].to_numpy()[r, m])))
        d_ = key.duplicated(keep=False).to_numpy()
        dup += int(key.duplicated().sum())
        checked += len(m)
        if d_.any():
            for kk in set(key[d_]):
                nm = " = ".join(sorted(bmid[m[(key == kk).to_numpy()]]))
                pairs[nm] = pairs.get(nm, 0) + 1
    pairs = {k_: n_ for k_, n_ in sorted(pairs.items(), key=lambda kv: -kv[1]) if n_ >= 20}
    OUT["duplicates"] = {"universe_stock_days_checked": checked, "stock_days_duplicating_another_name": dup,
                         "pairs_with_20_or_more_identical_days": pairs}
    print("Securities that appear twice inside the universe (same price as traded and same volume on the same day):", OUT["duplicates"])
    # one suspected unadjusted split among the extreme A1 events
    cx = np.flatnonzero((ents["symbol"] == "NXGN").to_numpy() & (ents["src"] == "dolthub").to_numpy())
    if len(cx):
        r0_ = int(np.searchsorted(dates, np.datetime64("2011-10-27")))
        print("\nNXGN (then Quality Systems, QSII) around 2011-10-27: date, adjusted close, price as traded, share volume")
        OUT["nxgn_2011"] = []
        for r in range(r0_ - 6, r0_ + 7):
            row_ = [str(dates[r]), round(float(raw["c"][r, cx[0]]), 2), round(float(raw["c_raw"][r, cx[0]]), 2), int(raw["v"][r, cx[0]])]
            OUT["nxgn_2011"].append(row_)
            print("  ", row_)

    # ---------------------------------------------------------------- probe: price rounding in strongly adjusted names
    cu = B["c"].to_numpy()
    f_adj = cu / B["craw"]
    m_big = B["uni"] & (f_adj < 0.25)
    m_one = B["uni"] & (np.abs(f_adj - 1) < 1e-4)

    def cents(x):
        return float((np.abs(x * 100 - np.round(x * 100)) < 2e-3).mean()) if len(x) else float("nan")

    OUT["rounding"] = {"cells_factor_lt_0.25": int(m_big.sum()), "share_on_cent_grid_factor_lt_0.25": round(cents(cu[m_big]), 3),
                       "share_on_cent_grid_unadjusted": round(cents(cu[m_one]), 3)}
    print("Adjusted closes that sit on a 1-cent grid:", OUT["rounding"])

    # ---------------------------------------------------------------- probe: first universe row; holes
    first_u = int(np.flatnonzero(B["uni"].any(1))[0])
    OUT["first_universe_row"] = {"row": first_u, "date": str(dates[first_u])}
    print("First row with any universe name:", OUT["first_universe_row"], "| bool(NaN) =", bool(np.array([np.nan]).astype(bool)[0]))
    life = (np.arange(te)[:, None] >= np.where(has0.any(0), has0.argmax(0), te)[None, :]) & \
           (np.arange(te)[:, None] <= np.where(has0.any(0), te - 1 - has0[::-1].argmax(0), -1)[None, :])
    holes = life & ~has0
    OUT["holes"] = {"cells_inside_listing_span": int(life.sum()), "holes": int(holes.sum()),
                    "holes_on_closed_market_rows": int(holes[closed].sum()),
                    "holes_elsewhere_with_adv60_ge_20M": int((holes[~closed] & (adv_file[~closed] >= 20e6)).sum())}
    print("Holes:", OUT["holes"])

    # ---------------------------------------------------------------- probe: E3 / A10 skewness as coded vs as written
    r0 = B["ret"].fillna(0.0)
    m60 = r0.rolling(60, min_periods=60).mean()
    sd = r0.rolling(60, min_periods=60).std(ddof=0)
    hyb = ((r0 - m60) ** 3).rolling(60, min_periods=60).mean() / np.maximum(sd ** 3, 1e-18)      # as coded
    e2 = (r0 ** 2).rolling(60, min_periods=60).mean()
    e3 = (r0 ** 3).rolling(60, min_periods=60).mean()
    std_skew = (e3 - 3 * m60 * e2 + 2 * m60 ** 3) / np.maximum(sd ** 3, 1e-18)                    # textbook, last 60 returns
    nb = B["c"].notna().cumsum().to_numpy()                                                    # real bars so far
    U = B["uni"]
    OUT["skew"] = {}
    for lab, thr, sgn in (("E3 skew<=-1", -1, -1), ("A10 skew>=+1", 1, 1)):
        a = U & ((hyb.to_numpy() <= thr) if sgn < 0 else (hyb.to_numpy() >= thr))
        b = U & ((std_skew.to_numpy() <= thr) if sgn < 0 else (std_skew.to_numpy() >= thr))
        OUT["skew"][lab] = {"as_coded": int(a.sum()), "textbook": int(b.sum()), "both": int((a & b).sum()),
                            "as_coded_with_under_120_real_bars": int((a & (nb < 120)).sum()),
                            "as_coded_with_under_61_real_bars": int((a & (nb < 61)).sum())}
    print("Skewness signal cells, as coded vs textbook 60-bar skewness:", json.dumps(OUT["skew"]))

    # ---------------------------------------------------------------- probe: VAL calendar, DATES ONLY
    nyse_closed = ["2018-07-04", "2018-09-03", "2018-11-22", "2018-12-05", "2018-12-25", "2019-01-01", "2019-01-21",
                   "2019-02-18", "2019-04-19", "2019-05-27", "2019-07-04", "2019-09-02", "2019-11-28", "2019-12-25",
                   "2020-01-01", "2020-01-20", "2020-02-17", "2020-04-10", "2020-05-25", "2020-07-03", "2020-09-07",
                   "2020-11-26", "2020-12-25", "2021-01-01", "2021-01-18", "2021-02-15", "2021-04-02", "2021-05-31",
                   "2021-07-05", "2021-09-06", "2021-11-25", "2021-12-24", "2022-01-17", "2022-02-21", "2022-04-15",
                   "2022-05-30", "2022-06-20", "2022-07-04", "2022-09-05", "2022-11-24", "2022-12-26"]
    all_dates = set(str(d) for d in p.dates)
    present = [d for d in nyse_closed if d in all_dates]
    wk = [str(d) for d in p.dates[te:] if pd.Timestamp(d).dayofweek >= 5]
    OUT["val_calendar_dates_only"] = {"nyse_holidays_present_as_rows": present, "weekend_rows": wk}
    print("\nValidation-period calendar (dates.npy only, no prices read): NYSE holidays present as rows:", present,
          "| weekend rows:", wk)

    # ---------------------------------------------------------------- probe: other volume / gap features on phantom rows
    vb = B["v"]
    v50 = vb.rolling(50, min_periods=50).mean().shift(1).to_numpy()
    U = B["uni"]
    hf, lf_ = B["h"].fillna(B["cf"]), B["l"].fillna(B["cf"])
    a3 = U & (lf_ > hf.shift(1)).to_numpy()
    after = np.zeros(te, dtype=bool)
    after[ph + 1] = True
    OUT["other_candidates_on_phantom_rows"] = {
        "E2_volume_filter_undefined_share_of_universe_cells": round(float((U & ~np.isfinite(v50)).sum() / U.sum()), 4),
        "A3_low_above_prior_high_cells_per_row_normal": round(float(a3[~after].sum(1).mean()), 1),
        "A3_cells_per_row_on_the_row_after_a_phantom_row": round(float(a3[after].sum(1).mean()), 1),
        "universe_names_per_row_normal": round(float(U[~closed].sum(1)[60:].mean()), 0),
        "universe_names_on_phantom_rows": [int(x) for x in U[closed].sum(1)],
    }
    print("\nOther candidates on/around phantom rows:", json.dumps(OUT["other_candidates_on_phantom_rows"]))

    # ---------------------------------------------------------------- probe: the two data sources
    ysb = (B["ents"]["src"] == "yahoo").to_numpy()
    f20 = B["fwd"][20]
    okf = np.isfinite(f20) & U
    OUT["sources"] = {"universe_cell_share_dolthub": round(float(U[:, ~ysb].sum() / U.sum()), 3),
                      "mean_fwd20_bp_yahoo_names": round(float(1e4 * f20[okf & ysb[None, :]].mean()), 1),
                      "mean_fwd20_bp_dolthub_names": round(float(1e4 * f20[okf & ~ysb[None, :]].mean()), 1)}
    ysc = (C["ents"]["src"] == "yahoo").to_numpy()
    for k in ("E1_episodic_pivot", "A1_shock_down_on_volume"):
        hh = HOR[k]
        a = xs_effect(C["fwd"][hh], C["sig"][k] & ysc[None, :], C["uni"] & ysc[None, :], hh)
        b = xs_effect(C["fwd"][hh], C["sig"][k] & ~ysc[None, :], C["uni"] & ~ysc[None, :], hh)
        OUT["sources"][k + " within-source control"] = {"yahoo": a, "dolthub": b}
        for nm, r in (("yahoo", a), ("dolthub", b)):
            log_trial("AUDITC", "audit_code", f"{k} corrected calendar, {nm} names vs {nm} control", "DEV", "xs_bp", r["bp"],
                      tstat=r["t"], n=r["events"], params={"h": hh})
    print("Data sources:", json.dumps(OUT["sources"]))

    # stale bars: a bar identical to the previous one (same close and same volume), by source, outside phantom rows
    cA, vA = B["c"].to_numpy(), B["v"].to_numpy()
    same = np.zeros_like(U)
    same[1:] = (cA[1:] == cA[:-1]) & (vA[1:] == vA[:-1])
    nc_ = U & ~closed[:, None]
    OUT["sources"]["stale_bars_outside_phantom_rows"] = {
        "yahoo": int((same & nc_)[:, ysb].sum()), "dolthub": int((same & nc_)[:, ~ysb].sum()),
        "dolthub_universe_cells": int(nc_[:, ~ysb].sum())}
    print("Bars identical to the previous bar (close and volume), universe, outside phantom rows:",
          OUT["sources"]["stale_bars_outside_phantom_rows"])
    # context sample: does its calendar contain closed-market rows? (development data)
    try:
        cdir = Path("/home/user/data/panel/ctx")
        cc_ = np.load(cdir / "c.npy", mmap_mode="r")
        nb_ = np.isfinite(np.asarray(cc_)).sum(1)
        med_ = pd.Series(nb_).rolling(41, center=True, min_periods=5).median().to_numpy()
        cd_ = np.load(cdir / "dates.npy").astype("datetime64[D]")
        thin = np.flatnonzero(nb_ < 0.5 * med_)
        OUT["ctx_calendar"] = {"rows": int(len(nb_)), "rows_with_under_half_the_usual_bars": [(str(cd_[i]), int(nb_[i])) for i in thin]}
        print("CTX calendar:", OUT["ctx_calendar"])
    except Exception as exc:  # noqa: BLE001
        print("CTX calendar probe failed:", exc)

    # ---------------------------------------------------------------- probe: A1 events that look like unadjusted splits
    s = B["sig"]["A1_shock_down_on_volume"]
    rr, cc = np.nonzero(s)
    og = np.log(B["o"].to_numpy()[rr, cc] / B["pc"].to_numpy()[rr, cc])
    intr = np.abs(np.log(B["c"].to_numpy()[rr, cc] / B["o"].to_numpy()[rr, cc]))
    cand = []
    for i in range(len(rr)):
        for kx in (1.5, 2.0, 3.0, 4.0, 5.0, 10.0):
            if abs(og[i] + np.log(kx)) < 0.03 and intr[i] < 0.10:
                r, cix = rr[i], cc[i]
                cand.append({"symbol": bsym[cix], "src": B["ents"]["src"].iloc[cix], "date": str(dates[r]), "ratio": kx,
                             "prev_close": round(float(B["pc"].to_numpy()[r, cix]), 3), "open": round(float(B["o"].to_numpy()[r, cix]), 3),
                             "close": round(float(B["c"].to_numpy()[r, cix]), 3), "relv": round(float(B["relv"].to_numpy()[r, cix]), 1),
                             "volume_next5_over_prev5": round(float(np.nanmedian(B["v"].to_numpy()[r + 1:r + 6, cix]) /
                                                                    np.nanmedian(B["v"].to_numpy()[max(r - 5, 0):r, cix])), 2)})
    OUT["a1_split_like"] = cand
    print("\nA1 events whose opening gap equals a split ratio (1.5, 2, 3, 4, 5, 10) within 3% and that barely move intraday:")
    print(pd.DataFrame(cand).to_string(index=False) if cand else "   none")

    # ---------------------------------------------------------------- 3. event listings
    rng = np.random.default_rng(20261111)
    sym = B["ents"]["symbol"].to_numpy()
    srcc = B["ents"]["src"].to_numpy()
    typc = B["ents"]["type"].to_numpy()
    A = {k: B[k].to_numpy() for k in ("o", "h", "l", "c", "v", "pc", "relv", "gz", "z1")}
    OUT["events"] = {}
    for k in ("E1_episodic_pivot", "A1_shock_down_on_volume"):
        hh = HOR[k]
        s = B["sig"][k]
        rr, cc = np.nonzero(s)
        day = A["c"][rr, cc] / A["pc"][rr, cc] - 1
        big = np.abs(day) > 0.40
        fw = B["fwd"][hh][rr, cc]
        info = {"events": int(len(rr)), "abs_day_return_gt_40pct": int(big.sum()), "abs_day_return_gt_25pct": int((np.abs(day) > 0.25).sum()),
                "outcome_missing": int((~np.isfinite(fw)).sum()),
                "by_source": {a: int((srcc[cc] == a).sum()) for a in ("yahoo", "dolthub")},
                "by_type": {a: int((typc[cc] == a).sum()) for a in STOCK},
                "price_as_traded_under_10": int((B["craw"][rr, cc] < 10).sum()),
                "median_day_return_pct": round(float(100 * np.median(day)), 2),
                "outcome_pct_quantiles_1_5_50_95_99": [round(float(x), 1) for x in 100 * np.nanquantile(fw, [0.01, 0.05, 0.5, 0.95, 0.99])],
                "outcomes_beyond_+-50pct": int((np.abs(fw) > 0.5).sum())}
        pick = np.sort(rng.choice(len(rr), size=15, replace=False))

        def row(i):
            r, cix = rr[i], cc[i]
            return {"symbol": sym[cix], "src": srcc[cix][0], "date": str(dates[r]), "prev_close": round(float(A["pc"][r, cix]), 3),
                    "open": round(float(A["o"][r, cix]), 3), "high": round(float(A["h"][r, cix]), 3),
                    "low": round(float(A["l"][r, cix]), 3), "close": round(float(A["c"][r, cix]), 3),
                    "px_traded": round(float(B["craw"][r, cix]), 2), "volume": int(A["v"][r, cix]),
                    "relv": round(float(A["relv"][r, cix]), 1), "gap_sigma": round(float(A["gz"][r, cix]), 1),
                    "z1": round(float(A["z1"][r, cix]), 1), "day_ret_pct": round(float(100 * day[i]), 1),
                    f"fwd{hh}_pct": None if not np.isfinite(fw[i]) else round(float(100 * fw[i]), 1)}

        info["sample"] = [row(i) for i in pick]
        info["beyond_40pct"] = [row(i) for i in np.flatnonzero(big)[:40]]
        OUT["events"][k] = info
        print(f"\n3. {k}: {len(rr)} events; |one-day return| > 40%: {int(big.sum())}; > 25%: {info['abs_day_return_gt_25pct']}; "
              f"by source {info['by_source']}; by type {info['by_type']}; outcome quantiles % {info['outcome_pct_quantiles_1_5_50_95_99']}")
        print(pd.DataFrame(info["sample"]).to_string(index=False))
        if big.sum():
            print(f"   events with |one-day return| > 40% (first 40):")
            print(pd.DataFrame(info["beyond_40pct"]).to_string(index=False))

    # influence of the tails on the two small-sample candidates (corrected calendar and as coded)
    OUT["tail_influence"] = {}
    for k in ("E1_episodic_pivot", "A1_shock_down_on_volume"):
        hh = HOR[k]
        f = B["fwd"][hh]
        clip = np.clip(f, -0.5, 0.5)
        r = xs_effect(clip, B["sig"][k], B["uni"], hh)
        OUT["tail_influence"][k] = {"outcomes_clipped_at_+-50pct": r}
        log_trial("AUDITC", "audit_code", f"{k} replication, outcomes clipped at +-50%", "DEV", "xs_bp", r["bp"], tstat=r["t"],
                  n=r["events"], params={"h": hh})
        print(f"\n   {k}: outcomes clipped at +-50%: {r['bp']:+.1f} bp (t {r['t']:+.2f})")

    Path(__file__).resolve().parents[1].joinpath("results", "audit_code.json").write_text(json.dumps(OUT, indent=1, default=str))


def sim_tests() -> None:
    """Synthetic checks of trades._sim and engine.fwd_ret_open (this mode, and only this mode, imports
    the project's engine and trades: the simulator itself is the object under test)."""
    from types import SimpleNamespace

    from research.swinglab import engine as E
    from research.swinglab import trades as TR
    T, N = 30, 7
    o = np.full((T, N), 100.0)
    h, l, c = o.copy(), o.copy(), o.copy()
    div = np.zeros((T, N))
    craw = np.full((T, N), 100.0)
    o[8, 0], h[8, 0], l[8, 0], c[8, 0] = 90, 91, 89, 90                 # 0: opens through the stop
    o[9:, 0] = h[9:, 0] = l[9:, 0] = c[9:, 0] = 90
    l[8, 1], c[8, 1] = 94, 96                                           # 1: trades through the stop intraday
    h[15, 2], c[15, 2] = 103, 103                                       # 2: time exit at the close of the 10th bar
    div[6, 3], div[9, 3] = 1.0, 2.0                                     # 3: dividend on the entry bar and on a later bar
    for a in (o, h, l, c):                                              # 4: stops trading after row 9, price as traded 1.5
        a[10:, 4] = np.nan
    craw[:, 4] = 1.5
    l[6, 5] = 94                                                        # 5: stop touched on the entry bar
    h[8, 6], l[8, 6] = 106, 94                                          # 6: stop and target inside one bar
    pan = SimpleNamespace(o=o, h=h, l=l, c=c, v=np.full((T, N), 1e6), div=div, c_raw=craw, bad=np.zeros((T, N)))
    P = E.prepare(pan)
    sig = np.zeros((T, N), dtype=bool)
    sig[5] = True
    atr = np.full((T, N), 2.5)
    rows = np.ones(T, dtype=bool)
    tr = TR.simulate(P, sig, atr, rows=rows, stop_k=2.0, target_r=1.0, max_hold=10, cost_bp=5, stop_extra_bp=10)
    print(tr.to_string())
    f10 = E.fwd_ret_open(P, 10)[5]
    print("fwd_ret_open(10) at the signal row:", np.round(f10, 4))
    exp = {0: ("gap_stop", 90 / 100 - 1 - 0.002), 1: ("stop", -0.05 - 0.002), 2: ("time", 0.03 - 0.001), 3: ("time", 0.02 - 0.001),
           4: ("delist", 0.7 - 1 - 0.001), 5: ("stop", -0.05 - 0.002), 6: ("stop", -0.05 - 0.002)}
    ok = True
    for n, (reason, ret) in exp.items():
        row = tr[tr["col"] == n].iloc[0]
        good = row["reason"] == reason and abs(row["ret"] - ret) < 1e-9 and row["entry"] == 6
        ok &= bool(good)
        print(f"  scenario {n}: expected {reason} {ret:+.4f}  got {row['reason']} {row['ret']:+.4f}  {'ok' if good else 'MISMATCH'}")
    ok &= abs(f10[3] - 0.02) < 1e-9 and abs(f10[4] - (-0.30)) < 1e-9 and abs(f10[2] - 0.03) < 1e-9
    # sample-end rule: with the sample ending at row 13 the time exit (row 15) is dropped, the stop-outs are kept
    rows2 = np.arange(T) <= 13
    tr2 = TR.simulate(P, sig, atr, rows=rows2, stop_k=2.0, target_r=1.0, max_hold=10, cost_bp=5, stop_extra_bp=10)
    print("sample ends at row 13: trades kept:", dict(zip(tr2["col"], tr2["reason"])), "-> the two time exits are dropped, every stop-out is kept")
    print("SIMULATOR CHECKS:", "all as documented" if ok else "MISMATCH")


if __name__ == "__main__":
    import sys
    if "--sim" in sys.argv:
        sim_tests()
    else:
        main()
