"""Turn the raw DoltHub daily table into clean, split-adjusted, per-entity series.

Input  (CSV exported from DoltHub `post-no-preference/stocks`):
    ohlcv.csv     date, act_symbol, open, high, low, close, volume     (raw prices, as traded)
    split.csv     act_symbol, ex_date, to_factor, for_factor            (incomplete, some errors)
    dividend.csv  act_symbol, ex_date, amount
    symbol.csv    act_symbol, security_name, listing_exchange, is_etf, last_seen ...

Output:
    daily.parquet     one row per (entity, date): split-adjusted o/h/l/c/v, raw close, dividend,
                      split ratio, quality flag
    entities.parquet  one row per entity: symbol, first/last date, bars, type, whether it ended
    splits_applied.parquet   every split applied or rejected, with the evidence
    qa.json           counts for the data inventory

Definitions
-----------
Entity   A maximal run of bars of one symbol with no gap longer than MAX_GAP trading days. A symbol
         that disappears and comes back later is treated as a different security (ticker reuse).
Split    Applied only when the PRICE confirms it:
         - an event from the table, if close[t-1]/open[t] agrees with the stated ratio (searching
           a few bars around the stated date);
         - an event not in the table, if the overnight ratio sits on a clean small-integer ratio
           AND share volume moves the way a split implies AND dollar volume does not explode
           (a crash on news fails the volume tests).
Bad tick A close that jumps more than 50% and comes straight back next bar.

Nothing here looks at returns as outcomes; it is mechanical cleaning. It does process all dates,
including the lockbox period, because splits must be applied backwards from the latest bar.
Memory: works on numpy arrays (about 3 GB peak for 30 million rows).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

MAX_GAP = 20            # trading days; a longer absence starts a new entity
TABLE_TOL = 0.20        # |log(observed/stated)| allowed for a table split
DETECT_TOL = 0.03       # |log(observed/clean ratio)| for a split not in the table
DETECT_MIN = float(np.log(1.45))
# Ratios below 3:2 are not detected from price alone: a 20-25% overnight fall on news is too
# common, and the volume test cannot tell it from a 5:4 or 4:3 split. (First run, 10 Nov 2026:
# 4,537 of 6,759 detections were 5:4 or 4:3, mostly in illiquid names - false positives.)
WHITELIST_FWD = [3 / 2, 2, 5 / 2, 3, 4, 5, 6, 7, 8, 10, 15, 20, 25, 30, 40, 50]
WHITELIST_REV = [1 / x for x in (2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 25, 30, 35, 40, 50, 60, 75,
                                 80, 100, 150, 200, 250)]

NON_COMMON = re.compile(
    r"(warrant|\bunits?\b|\brights?\b|preferred|depositary shares? each representing|notes? due|"
    r"debenture|subordinated|senior notes|%|contingent value|exchange[- ]traded notes?|\bETNs?\b|"
    r"when[- ]issued)", re.I)
LEVERAGED = re.compile(r"(\b[1-4](\.\d)?x\b|-1x|ultra|leveraged|inverse|\bbull\b|\bbear\b|\bshort\b)", re.I)


def classify(name: str, is_etf: int) -> str:
    name = name or ""
    if is_etf == 1:
        return "etf_levinv" if LEVERAGED.search(name) else "etf"
    if NON_COMMON.search(name):
        return "other"
    if re.search(r"american depositary|\bADS\b|\bADR\b", name, re.I):
        return "adr"
    return "common"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/home/user/data_raw/dolt_export")
    ap.add_argument("--out", default="/home/user/data/daily")
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    qa: dict = {}

    # ---------------------------------------------------------------- load (lean)
    d = pd.read_csv(src / "ohlcv.csv", dtype={"act_symbol": "category", "open": "float64", "high": "float64",
                                              "low": "float64", "close": "float64", "volume": "float64"},
                    parse_dates=["date"], keep_default_na=False,
                    na_values={c: [""] for c in ("open", "high", "low", "close", "volume")})
    qa["rows_raw"] = int(len(d))
    sym_names = np.asarray(d["act_symbol"].cat.categories, dtype=object)
    sym = d["act_symbol"].cat.codes.to_numpy().astype(np.int32)
    cal = np.sort(d["date"].unique())
    tpos = np.searchsorted(cal, d["date"].to_numpy()).astype(np.int32)
    O, H, L, C, V = (d[c].to_numpy() for c in ("open", "high", "low", "close", "volume"))
    del d

    ok = (O > 0) & (H > 0) & (L > 0) & (C > 0) & np.isfinite(V)
    qa["rows_nonpositive_dropped"] = int((~ok).sum())
    order = np.lexsort((tpos, sym))
    order = order[ok[order]]
    sym, tpos, O, H, L, C, V = (x[order] for x in (sym, tpos, O, H, L, C, V))
    del order, ok
    # duplicates (same symbol and date): keep the last
    dup = np.r_[(sym[1:] == sym[:-1]) & (tpos[1:] == tpos[:-1]), False]
    if dup.any():
        keep = ~dup
        sym, tpos, O, H, L, C, V = (x[keep] for x in (sym, tpos, O, H, L, C, V))
    qa["rows_duplicate_dropped"] = int(dup.sum())
    n = len(sym)

    hi = np.maximum(H, np.maximum(O, C))
    lo = np.minimum(L, np.minimum(O, C))
    qa["rows_hl_repaired"] = int(((hi > H) | (lo < L)).sum())
    H, L = hi, lo
    del hi, lo

    # ---------------------------------------------------------------- entities
    new_sym = np.r_[True, sym[1:] != sym[:-1]]
    gap = np.r_[0, np.diff(tpos)]
    new_ent = new_sym | (gap > MAX_GAP)
    eid = (np.cumsum(new_ent) - 1).astype(np.int32)
    n_ent = int(eid[-1]) + 1
    ent_start = np.flatnonzero(new_ent)
    ent_end = np.r_[ent_start[1:], n]              # exclusive
    ent_sym = sym[ent_start]
    # ordinal of the entity within its symbol
    first_of_sym = np.r_[True, ent_sym[1:] != ent_sym[:-1]]
    grp_start = np.maximum.accumulate(np.where(first_of_sym, np.arange(n_ent), 0))
    ent_k = np.arange(n_ent) - grp_start
    ent_name = np.array([f"{sym_names[s]}#{k}" for s, k in zip(ent_sym, ent_k)], dtype=object)
    qa["symbols"] = int(len(np.unique(sym)))
    qa["entities"] = n_ent
    qa["symbols_with_reuse"] = int((ent_k == 1).sum())

    # ---------------------------------------------------------------- overnight ratio
    prevC = np.r_[np.nan, C[:-1]]
    prevC[new_ent] = np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        logr = np.log(prevC / O)                 # > 0: price fell overnight (forward split)
    DV = C * V

    def evidence(r: int) -> tuple[float, float]:
        """(share-volume ratio after/before, dollar-volume spike on the bar) around row r."""
        s, e = ent_start[eid[r]], ent_end[eid[r]]
        pre = V[max(s, r - 10):r]
        post = V[r:min(e, r + 10)]
        dpre = DV[max(s, r - 20):r]
        if len(pre) < 5 or len(post) < 5 or len(dpre) < 5:
            return np.nan, np.nan
        mp, mq, md = np.median(pre), np.median(post), np.median(dpre)
        if mp <= 0 or md <= 0:
            return np.nan, np.nan
        return float(mq / mp), float(DV[r] / md)

    # ---------------------------------------------------------------- splits
    sp = pd.read_csv(src / "split.csv", dtype={"act_symbol": object}, parse_dates=["ex_date"], keep_default_na=False)
    sp["ratio"] = sp["to_factor"].astype(float) / sp["for_factor"].astype(float)
    sp = sp[(sp["ratio"] > 0) & (sp["ratio"] != 1)].drop_duplicates(["act_symbol", "ex_date", "ratio"])
    qa["split_table_rows"] = int(len(sp))
    code_of = {s: i for i, s in enumerate(sym_names)}
    # row range of each symbol
    sym_first = np.flatnonzero(new_sym)
    sym_last = np.r_[sym_first[1:], n]
    sym_range = {int(sym[i]): (int(i), int(j)) for i, j in zip(sym_first, sym_last)}

    split_ratio = np.ones(n)
    records = []
    used = np.zeros(n, dtype=bool)
    n_conf = n_rej = 0
    for s_name, ex, ratio in sp[["act_symbol", "ex_date", "ratio"]].itertuples(index=False):
        code = code_of.get(s_name)
        if code is None or code not in sym_range:
            n_rej += 1
            records.append((s_name, pd.NaT, ratio, np.nan, "table_rejected", f"stated {ex.date()}: symbol absent"))
            continue
        i0, i1 = sym_range[code]
        tp = int(np.searchsorted(cal, np.datetime64(ex)))
        j = i0 + int(np.searchsorted(tpos[i0:i1], tp))
        best, best_score = -1, np.inf
        for r in range(max(j - 3, i0 + 1), min(j + 4, i1)):
            if used[r] or not np.isfinite(logr[r]):
                continue
            err = abs(logr[r] - np.log(ratio))
            score = err + 0.02 * abs(r - j)
            # the tolerance shrinks for small ratios, otherwise any ordinary overnight move would
            # "confirm" a 21:20 stock dividend that never happened
            tol = min(TABLE_TOL, max(0.02, 0.5 * abs(np.log(ratio))))
            if err <= tol and score < best_score:
                best, best_score = r, score
        if best < 0:
            n_rej += 1
            records.append((s_name, pd.NaT, ratio, np.nan, "table_rejected", f"stated {ex.date()}: price does not confirm"))
        else:
            used[best] = True
            split_ratio[best] = ratio
            n_conf += 1
            records.append((s_name, cal[tpos[best]], ratio, float(np.exp(logr[best])), "table", f"stated {ex.date()}"))
    qa["split_table_confirmed"] = n_conf
    qa["split_table_rejected"] = n_rej

    wl = np.array(WHITELIST_FWD + WHITELIST_REV)
    wl_log = np.log(wl)
    cand = np.flatnonzero(np.isfinite(logr) & (np.abs(logr) >= DETECT_MIN) & ~used)
    qa["overnight_moves_over_45pct"] = int(len(cand))
    n_det = 0
    for r in cand:
        i = int(np.argmin(np.abs(wl_log - logr[r])))
        if abs(wl_log[i] - logr[r]) > DETECT_TOL:
            continue
        ratio = float(wl[i])
        vr, ds = evidence(int(r))
        if not (np.isfinite(vr) and np.isfinite(ds)) or vr <= 0:
            continue
        if ratio > 1:
            # forward split: share volume rises by about the ratio; dollar volume stays calm.
            # 3:2 gets the strictest test because a 33% fall on news is the likeliest impostor.
            if ratio < 1.9:
                if abs(wl_log[i] - logr[r]) > 0.015 or abs(np.log(vr / ratio)) > np.log(1.5) or ds > 1.8:
                    continue
            elif abs(np.log(vr / ratio)) > np.log(1.8) or ds > 4.0:
                continue
        else:
            # reverse split: share volume falls by roughly the ratio; a price jump on news would
            # come with exploding dollar volume
            if abs(np.log(vr / ratio)) > np.log(4.0) or ds > 6.0:
                continue
        used[r] = True
        split_ratio[r] = ratio
        n_det += 1
        records.append((sym_names[sym[r]], cal[tpos[r]], ratio, float(np.exp(logr[r])), "detected",
                        f"v_ratio={vr:.2f} dv_spike={ds:.2f}"))
    qa["split_detected_not_in_table"] = n_det

    # adjustment: a split on row t divides every EARLIER bar of the entity by its ratio
    lr = np.log(split_ratio)
    rc = np.r_[np.cumsum(lr[::-1])[::-1], 0.0]          # rc[i] = sum of lr[j] for j >= i
    adj = np.exp(rc[1:n + 1] - rc[ent_end[eid]])        # sum over later rows in the same entity
    o, h, l, c = O / adj, H / adj, L / adj, C / adj
    v = V * adj

    # ---------------------------------------------------------------- dividends
    dvd = pd.read_csv(src / "dividend.csv", dtype={"act_symbol": object}, parse_dates=["ex_date"], keep_default_na=False)
    dvd["amount"] = pd.to_numeric(dvd["amount"], errors="coerce")
    dvd = dvd[dvd["amount"] > 0].groupby(["act_symbol", "ex_date"], as_index=False)["amount"].sum()
    dcode = dvd["act_symbol"].map(code_of)
    dvd = dvd[dcode.notna()]
    dcode = dcode.dropna().astype(np.int64).to_numpy()
    dt = np.searchsorted(cal, dvd["ex_date"].to_numpy())
    on_cal = (dt < len(cal))
    on_cal[on_cal] &= cal[dt[on_cal]] == dvd["ex_date"].to_numpy()[on_cal]
    key_data = sym.astype(np.int64) * 100_000 + tpos
    key_div = dcode[on_cal] * 100_000 + dt[on_cal]
    pos = np.searchsorted(key_data, key_div)
    hit = (pos < n)
    hit[hit] &= key_data[pos[hit]] == key_div[hit]
    div = np.zeros(n)
    div[pos[hit]] = dvd["amount"].to_numpy()[on_cal][hit]
    prev_c = np.r_[np.nan, c[:-1]]
    prev_c[new_ent] = np.nan
    # The table is in adjusted terms (vendor's latest adjustment), so it pairs with the adjusted
    # close. A "dividend" above 25% of price is treated as a table error or a special distribution.
    too_big = div > 0.25 * np.where(np.isfinite(prev_c), prev_c, np.inf)
    qa["dividends_matched"] = int((div > 0).sum())
    qa["dividends_ignored_too_large"] = int(too_big.sum())
    div[too_big] = 0.0

    # ---------------------------------------------------------------- bad ticks
    next_c = np.r_[c[1:], np.nan]
    next_c[ent_end - 1] = np.nan
    with np.errstate(divide="ignore", invalid="ignore"):
        jump = np.abs(np.log(c / prev_c))
        back = np.abs(np.log(next_c / prev_c))
    bad = (jump > 0.5) & (back < 0.12)
    qa["bad_tick_bars"] = int(bad.sum())
    qa["abs_logret_gt_0.7_after_adjust"] = int((jump > 0.7).sum())

    # ---------------------------------------------------------------- write
    daily = pd.DataFrame({
        "eid": eid, "date": cal[tpos],
        "o": o, "h": h, "l": l, "c": c, "v": v, "c_raw": C,
        "div": div.astype(np.float32), "split_ratio": split_ratio.astype(np.float32),
        "bad": bad.astype(np.int8),
    })
    daily.to_parquet(out / "daily.parquet", index=False)
    del daily

    symtab = pd.read_csv(src / "symbol.csv", dtype={"act_symbol": object, "security_name": object}, keep_default_na=False)
    symtab["is_etf"] = pd.to_numeric(symtab["is_etf"], errors="coerce").fillna(0).astype(int)
    symtab = symtab.drop_duplicates("act_symbol").rename(columns={"act_symbol": "symbol"})
    symtab["type"] = [classify(nm, e) for nm, e in zip(symtab["security_name"], symtab["is_etf"])]
    ent = pd.DataFrame({
        "eid": np.arange(n_ent), "entity": ent_name, "symbol": sym_names[ent_sym],
        "first": cal[tpos[ent_start]], "last": cal[tpos[ent_end - 1]],
        "bars": ent_end - ent_start, "last_close_raw": C[ent_end - 1],
    })
    ent = ent.merge(symtab[["symbol", "security_name", "listing_exchange", "is_etf", "type", "last_seen"]],
                    on="symbol", how="left")
    ent["type"] = ent["type"].fillna("unknown")
    end = cal[-1]
    ent["ended"] = ent["last"] < (end - np.timedelta64(10, "D"))
    ent["is_last_entity_of_symbol"] = ent.groupby("symbol")["first"].transform("max") == ent["first"]
    ent.to_parquet(out / "entities.parquet", index=False)
    qa["entities_ended_before_dataset_end"] = int(ent["ended"].sum())
    qa["entity_types"] = {k: int(x) for k, x in ent["type"].value_counts().items()}

    spl = pd.DataFrame(records, columns=["symbol", "date", "ratio", "observed", "source", "evidence"])
    spl.to_parquet(out / "splits_applied.parquet", index=False)
    qa["date_min"], qa["date_max"] = str(pd.Timestamp(cal[0]).date()), str(pd.Timestamp(end).date())
    qa["rows_out"] = n
    (out / "qa.json").write_text(json.dumps(qa, indent=1))
    print(json.dumps(qa, indent=1))


if __name__ == "__main__":
    main()
