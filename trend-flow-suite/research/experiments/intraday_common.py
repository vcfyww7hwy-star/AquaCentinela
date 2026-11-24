"""Loading and cleaning of the public intraday sample used by E19, E24 and E26.

Source: 5-minute bars built from 1-minute Yahoo bars (GitHub, MapleFrogStudio DATA-YYYY-MM),
regular session. The source carries corrupted volume: single 1-minute bars with prints of several
hundred thousand or million shares, so that the intraday sum exceeds the official daily volume. It
comes in episodes by listing group: NASDAQ names from late Sep 2025 to mid Mar 2026 (20-30% of
ticker-days above 1.2 x the daily volume), NYSE names on some days of Jan, May and Aug 2026 and on
40-58% of ticker-days from 6 Oct 2026 on. Found on 24 Nov 2026 (E26); the first run of E19 used
31 Aug - 6 Nov 2026 uncleaned.
Cleaning: sessions from 6 Oct 2026 are dropped. A ticker-day is "corrupted" when its intraday volume
is above the official daily volume. Kept: tickers that have daily bars to check against and at most
5% corrupted days; of those, the days that are not corrupted and have a daily bar. A corrupted print
smaller than the usual gap between the two (the intraday bars normally sum to about 0.82 of the
daily volume) cannot be detected this way, which is why habitually corrupted tickers are dropped
whole.
"""
from __future__ import annotations

import glob
import pathlib

import numpy as np
import pandas as pd

END = pd.Timestamp("2026-10-06")


def load_clean(bars_dir, daily_file):
    """(bars, daily, info). bars: ticker, ts, day, mins, open, high, low, close, volume (regular session);
    daily: ticker, day, dvol for the same tickers (full history)."""
    b = pd.concat([pd.read_parquet(f, columns=["ticker", "ts", "open", "high", "low", "close", "volume"])
                   for f in sorted(glob.glob(str(pathlib.Path(bars_dir) / "bars5m_*.parquet")))], ignore_index=True)
    b["ticker"] = b["ticker"].astype(str)
    b = b.drop_duplicates(["ticker", "ts"], keep="last")
    b["day"] = b["ts"].dt.normalize()
    b["mins"] = (b["ts"].dt.hour * 60 + b["ts"].dt.minute) - 570              # minutes after 09:30
    b = b[(b["mins"] >= 0) & (b["mins"] < 390) & (b["day"] < END)]
    dly = pd.read_parquet(daily_file, columns=["ticker", "date", "volume"])
    dly["ticker"] = dly["ticker"].astype(str)
    dly = dly[dly["ticker"].isin(set(b["ticker"].unique()))].rename(columns={"date": "day", "volume": "dvol"})
    iv = b.groupby(["ticker", "day"])["volume"].sum().rename("iv").reset_index().merge(dly, on=["ticker", "day"], how="left")
    iv["ratio"] = iv["iv"] / iv["dvol"].replace(0, np.nan)
    chk = iv[iv["ratio"].notna()]
    bad_rate = (chk["ratio"] > 1.0).groupby(chk["ticker"]).mean()
    good = set(bad_rate.index[bad_rate <= 0.05])
    ok = iv["ratio"].notna() & (iv["ratio"] <= 1.0) & iv["ticker"].isin(good)
    q = pd.PeriodIndex(chk["day"], freq="Q").astype(str)
    info = {"tickers_in_source": int(iv["ticker"].nunique()), "tickers_with_daily_bars": int(len(bad_rate)),
            "tickers_kept": int(len(good)), "ticker_days_with_daily_bars": int(len(chk)),
            "corrupted_pct_of_checked_ticker_days": round(100 * float((chk["ratio"] > 1.0).mean()), 2),
            "corrupted_pct_by_quarter": {k: round(100 * float(v), 2) for k, v in (chk["ratio"] > 1.0).groupby(q).mean().items()},
            "kept_ticker_days": int(ok.sum()), "sessions": int(b["day"].nunique()),
            "first": str(b["day"].min())[:10], "last": str(b["day"].max())[:10]}
    b = b.merge(iv.loc[ok, ["ticker", "day"]], on=["ticker", "day"], how="inner")
    return b, dly, info
