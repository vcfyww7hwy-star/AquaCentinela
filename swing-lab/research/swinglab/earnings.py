"""Earnings events aligned to a Study.

    ev = load(S)     -> dict of [T, N] arrays:
        ann      bool   the announcement falls on this trading day (or, if the calendar date is
                        not a trading day, on the next one)
        when     int8   0 unknown, 1 before the open, 2 after the close
        surp     float  (actual - estimate) / max(|estimate|, 0.05)      (NaN if unknown)
        react    bool   the REACTION bar: the first bar whose close contains the news.
                        before open -> the announcement day; after close -> the next bar;
                        unknown time -> the announcement day if its volume is at least twice its
                        20-bar median (the reaction is visibly under way), otherwise the next bar.
                        Decided with data available at that bar's close: no look-ahead.

Only events up to 2022-12-30 are loaded. A Study limits outcomes to its own sample anyway.
Coverage starts in January 2017, so in the DEV sample earnings exist for 2017-01..2018-06 only,
and not at all in CTX.

In Pine: request.earnings() changes value on the bar of the report; the time of day is not
given, so the same volume rule identifies the reaction bar.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import pinelike as ta

EVENTS = Path("/home/user/data/earnings/events_devval.parquet")
EVENTS_SEALED = Path("/home/user/data/earnings/LOCKBOX_SEALED_events_full.parquet")   # read only by a LOCKBOX Study


def load(S) -> dict:
    ev = pd.read_parquet(EVENTS_SEALED if S.sample == "LOCKBOX" else EVENTS)
    ev["date"] = ev["date"].astype("datetime64[ns]")
    dates = pd.DatetimeIndex(S.dates)
    T, N = S.P.c.shape
    ents = S.ents
    first = pd.to_datetime(ents["first"]).to_numpy() if "first" in ents else None
    last = pd.to_datetime(ents["last"]).to_numpy() if "last" in ents else None
    by_sym: dict[str, list[int]] = {}
    for j, sym in enumerate(ents["symbol"]):
        by_sym.setdefault(sym, []).append(j)
    ann = np.zeros((T, N), dtype=bool)
    when = np.zeros((T, N), dtype=np.int8)
    surp = np.full((T, N), np.nan)
    rows = np.searchsorted(dates.values, ev["date"].to_numpy(), side="left")
    wcode = ev["when"].map({"BMO": 1, "AMC": 2}).fillna(0).to_numpy(dtype=np.int8)
    act, est = ev["eps_act"].to_numpy(dtype=float), ev["eps_est"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        sp = (act - est) / np.maximum(np.abs(est), 0.05)
    evd = ev["date"].to_numpy()
    for i, sym in enumerate(ev["symbol"].to_numpy()):
        t = rows[i]
        if t >= T or sym not in by_sym:
            continue
        for j in by_sym[sym]:
            if first is not None and not (first[j] <= evd[i] <= last[j] + np.timedelta64(5, "D")):
                continue
            ann[t, j] = True
            when[t, j] = wcode[i]
            surp[t, j] = sp[i]
            break
    relvol = S.P.v / ta.shift(ta.median(np.where(np.isfinite(S.P.v), S.P.v, np.nan), 20), 1)
    same_day = ann & ((when == 1) | ((when == 0) & (relvol >= 2.0)))
    next_day = ann & ~same_day
    react = same_day.copy()
    react[1:] |= next_day[:-1]
    surp_react = np.where(same_day, surp, np.nan)
    surp_react[1:] = np.where(next_day[:-1], surp[:-1], surp_react[1:])
    return {"ann": ann, "when": when, "surp": surp, "react": react, "surp_react": surp_react, "relvol": relvol}
