"""Earnings announcement events from two free sources.

    sovai/earnings_surprise (Hugging Face)   announcement date (date_pub), actual and estimated EPS,
                                             2017-01 .. 2024-10, no time of day
    DoltHub post-no-preference/earnings      earnings_calendar: date and when (before open / after
                                             close / blank), 2020-01 ..; eps_history: reported and
                                             estimated EPS per fiscal period

Checked on the overlap 2020-2022 (dates only): of the DoltHub events that have a sovai event within
10 days, 90% fall on the same day and 94% within one day.

Output (dates up to 2022-12-30 only; the rest goes to a sealed file for the lockbox):
    events_devval.parquet:  symbol, date, when (BMO / AMC / ""), eps_act, eps_est, src
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("/home/user/data_raw")
OUT = Path("/home/user/data/earnings")
DEVVAL_END = pd.Timestamp("2022-12-30")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = pd.read_parquet(RAW / "sovai_earnings_surprise.parquet",
                        columns=["ticker", "date_pub", "actual_earning_result", "estimated_earning"])
    s = s.dropna(subset=["date_pub"])
    s["date"] = pd.to_datetime(s["date_pub"]).dt.normalize().astype("datetime64[ns]")
    s = s.drop_duplicates(["ticker", "date"]).rename(
        columns={"ticker": "symbol", "actual_earning_result": "eps_act", "estimated_earning": "eps_est"})
    s = s[["symbol", "date", "eps_act", "eps_est"]]

    cal = pd.read_csv(RAW / "dolt_export/earnings/earnings_calendar.csv", keep_default_na=False, parse_dates=["date"])
    cal = cal.rename(columns={"act_symbol": "symbol"})
    cal["date"] = cal["date"].astype("datetime64[ns]")
    cal["when"] = cal["when"].map({"Before market open": "BMO", "After market close": "AMC"}).fillna("")
    cal = cal.drop_duplicates(["symbol", "date"])

    eh = pd.read_csv(RAW / "dolt_export/earnings/eps_history.csv", keep_default_na=False, parse_dates=["period_end_date"])
    eh = eh.rename(columns={"act_symbol": "symbol", "reported": "eps_act_d", "estimate": "eps_est_d"})
    for c in ("eps_act_d", "eps_est_d"):
        eh[c] = pd.to_numeric(eh[c], errors="coerce")
    eh["period_end_date"] = eh["period_end_date"].astype("datetime64[ns]")
    eh = eh.sort_values("period_end_date")

    # DoltHub calendar: attach the most recent fiscal period that ended 10..120 days before the date
    cal = cal.sort_values("date")
    c2 = pd.merge_asof(cal, eh, left_on="date", right_on="period_end_date", by="symbol",
                       direction="backward", tolerance=pd.Timedelta(days=120))
    c2.loc[(c2["date"] - c2["period_end_date"]).dt.days < 10, ["eps_act_d", "eps_est_d"]] = np.nan

    # merge: a sovai event within 3 days of a DoltHub event is the same event (DoltHub date and time win)
    s = s.sort_values("date")
    m = pd.merge_asof(c2, s.rename(columns={"date": "date_s"}), left_on="date", right_on="date_s", by="symbol",
                      direction="nearest", tolerance=pd.Timedelta(days=3))
    m["eps_act"] = m["eps_act"].fillna(m["eps_act_d"])
    m["eps_est"] = m["eps_est"].fillna(m["eps_est_d"])
    m["src"] = np.where(m["date_s"].notna(), "dolt+sovai", "dolt")
    used = set(zip(m.loc[m["date_s"].notna(), "symbol"], m.loc[m["date_s"].notna(), "date_s"]))
    s_only = s[[(a, b) not in used for a, b in zip(s["symbol"], s["date"])]].copy()
    # drop sovai-only events that sit within 10 days of a DoltHub event of the same symbol (same event, date differs)
    near = pd.merge_asof(s_only, cal[["symbol", "date"]].rename(columns={"date": "date_c"}), left_on="date",
                         right_on="date_c", by="symbol", direction="nearest", tolerance=pd.Timedelta(days=10))
    s_only = near[near["date_c"].isna()].drop(columns=["date_c"])
    s_only["when"] = ""
    s_only["src"] = "sovai"
    ev = pd.concat([m[["symbol", "date", "when", "eps_act", "eps_est", "src"]],
                    s_only[["symbol", "date", "when", "eps_act", "eps_est", "src"]]], ignore_index=True)
    ev = ev.sort_values(["symbol", "date"]).reset_index(drop=True)
    # two events of one symbol closer than 20 days: keep the first (duplicates / pre-announcements)
    gap = ev.groupby("symbol")["date"].diff().dt.days
    ev = ev[gap.isna() | (gap >= 20)].reset_index(drop=True)

    dv = ev[ev["date"] <= DEVVAL_END]
    dv.to_parquet(OUT / "events_devval.parquet", index=False)
    ev.to_parquet(OUT / "LOCKBOX_SEALED_events_full.parquet", index=False)
    by_year = dv.groupby(dv["date"].dt.year).agg(n=("symbol", "size"), symbols=("symbol", "nunique"),
                                                 with_time=("when", lambda x: int((x != "").sum())),
                                                 with_eps=("eps_act", lambda x: int(x.notna().sum())))
    print("events (dev+val):", len(dv))
    print(by_year.to_string())
    print("sources:", dv["src"].value_counts().to_dict())


if __name__ == "__main__":
    main()
