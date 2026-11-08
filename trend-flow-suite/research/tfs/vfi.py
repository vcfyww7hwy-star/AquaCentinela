"""Reference implementation of the Volume Flow Indicator (VFI).

Lineage: Katsanos (TASC, June 2004) -> LazyBear (TradingView, 18 Jun 2014) -> LucF (2018).
Replicates Pine semantics so that values can be compared bar-for-bar with TradingView:
  math.sum(x, n)    rolling sum including the current bar
  ta.sma(v, n)[1]   previous bar's simple average
  ta.stdev(x, 30)   population standard deviation (biased=true), current bar included
  ta.ema(x, n)      alpha = 2 / (n + 1)

Expects a DataFrame with lower-case columns: open, high, low, close, volume.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SMOOTHING = ("none", "sma3", "ema3")  # LucF default / LazyBear option / Katsanos 2004 original


def vfi(df: pd.DataFrame, length: int = 130, coef: float = 0.2, vcoef: float = 2.5,
        smoothing: str = "none") -> pd.DataFrame:
    """Return a frame with typical price, average volume, per-bar contribution and the VFI."""
    if smoothing not in SMOOTHING:
        raise ValueError(f"smoothing must be one of {SMOOTHING}")
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    inter = np.log(tp) - np.log(tp.shift(1))
    vinter = inter.rolling(30).std(ddof=0)
    cutoff = coef * vinter * df["close"]
    vave = df["volume"].rolling(length).mean().shift(1)
    vmax = vave * vcoef
    vc = np.minimum(df["volume"], vmax)
    mf = tp - tp.shift(1)
    vcp = pd.Series(np.where(mf > cutoff, vc, np.where(mf < -cutoff, -vc, 0.0)), index=df.index)
    vcp[cutoff.isna() | vmax.isna()] = np.nan
    raw = vcp.rolling(length).sum() / vave.where(vave > 0)
    if smoothing == "sma3":
        out = raw.rolling(3).mean()
    elif smoothing == "ema3":
        out = raw.ewm(span=3, adjust=False).mean()
    else:
        out = raw
    return pd.DataFrame({"tp": tp, "vave": vave, "vcp": vcp, "vfi": out})


def change_decomposition(frame: pd.DataFrame, length: int = 130) -> pd.DataFrame:
    """Exact split of the bar-to-bar VFI change (unsmoothed VFI):
        dVFI_t = new_bar + leaving_bar + renormalisation
    new_bar      =  vcp_t / vave_t
    leaving_bar  = -vcp_{t-length} / vave_t       (the bar that drops out of the window)
    renorm       =  S_{t-1} * (1/vave_t - 1/vave_{t-1})
    """
    s = frame["vcp"].rolling(length).sum()
    vave = frame["vave"]
    out = pd.DataFrame({
        "new_bar": frame["vcp"] / vave,
        "leaving_bar": -frame["vcp"].shift(length) / vave,
        "renorm": s.shift(1) * (1.0 / vave - 1.0 / vave.shift(1)),
        "d_vfi": frame["vfi"].diff(),
    })
    return out.dropna()
