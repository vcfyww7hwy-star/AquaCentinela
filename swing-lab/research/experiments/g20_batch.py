"""G20 batch - six families in compact form (main-loop versions of f01, f14, f06, f05, f07, f13).

Each family is a builder returning named boolean signals; `compact.run` prints one line per signal
with DEV and CTX side by side (XS view: signal minus control on the same day, from the next open).
Controls are stated per family. Development samples only.

    python -m research.experiments.g20_batch [dips resid breakouts volume gaps strange]
"""
from __future__ import annotations

import sys

import numpy as np

from research.experiments.compact import run
from research.swinglab import engine as E
from research.swinglab import pinelike as ta


def _bars(S):
    c = S.P.cf
    o = np.where(np.isfinite(S.P.o), S.P.o, c)
    h = np.where(np.isfinite(S.P.h), S.P.h, c)
    l = np.where(np.isfinite(S.P.l), S.P.l, c)
    v = np.where(np.isfinite(S.P.v), S.P.v, np.nan)
    return o, h, l, c, v


# --------------------------------------------------------------------------- G01 dips in trends
def dips(S):
    o, h, l, c, v = _bars(S)
    U = S.uni
    up = c > ta.sma(c, 200)
    UP, DN = U & up, U & ~up & np.isfinite(ta.sma(c, 200))
    z1, z3, z5, z10 = S.z(1), S.z(3), S.z(5), S.z(10)
    rsi2 = ta.rsi(c, 2)
    down = c < ta.shift(c, 1)
    d3 = down & ta.shift(down, 1).astype(bool) & ta.shift(down, 2).astype(bool)
    d4 = d3 & ta.shift(down, 3).astype(bool)
    bb_lo = ta.sma(c, 20) - 2 * ta.stdev(c, 20)
    atr = S.atr(14)
    pull = (ta.highest(h, 20) - c) / atr
    near = c >= 0.85 * ta.highest(h, 252)
    mz5 = z5[:, [S.spy]]
    relv = v / ta.shift(ta.median(v, 20), 1)
    rv3 = ta.sma(relv, 3)
    minz1 = ta.lowest(z1, 5)
    d = {
        "z5<=-1.5 in uptrend            (ctl: uptrend)": (UP & (z5 <= -1.5), UP),
        "z5<=-2 in uptrend": (UP & (z5 <= -2), UP),
        "z3<=-2 in uptrend": (UP & (z3 <= -2), UP),
        "z10<=-2 in uptrend": (UP & (z10 <= -2), UP),
        "RSI(2)<10 in uptrend": (UP & (rsi2 < 10), UP),
        "RSI(2)<5 in uptrend": (UP & (rsi2 < 5), UP),
        "3 down closes in uptrend": (UP & d3, UP),
        "4 down closes in uptrend": (UP & d4, UP),
        "close under lower Bollinger(20,2) in uptrend": (UP & (c < bb_lo), UP),
        "pullback >=3 ATR from 20-bar high, within 15% of 252 high": (UP & (pull >= 3) & near, UP),
        "orderly dip: z5<=-1.5, no -3s day in it, uptrend": (UP & (z5 <= -1.5) & (minz1 > -3), UP),
        "dip on dry volume (3-bar rel. volume <0.8), uptrend": (UP & (z5 <= -1.5) & (rv3 < 0.8), UP),
        "dip on heavy volume (3-bar rel. volume >1.5), uptrend": (UP & (z5 <= -1.5) & (rv3 > 1.5), UP),
        "stock-only dip: z5<=-1.5, SPY z5>-0.5, uptrend": (UP & (z5 <= -1.5) & (mz5 > -0.5), UP),
        "market dip: z5<=-1.5 and SPY z5<=-1.5, uptrend": (UP & (z5 <= -1.5) & (mz5 <= -1.5), UP),
        "z5<=-1.5 in DOWNtrend          (ctl: downtrend)": (DN & (z5 <= -1.5), DN),
        "RSI(2)<10 in DOWNtrend": (DN & (rsi2 < 10), DN),
        "z5>=+1.5 in uptrend (strength)": (UP & (z5 >= 1.5), UP),
        "z5>=+1.5 in DOWNtrend (bounce)": (DN & (z5 >= 1.5), DN),
    }
    return d


# --------------------------------------------------------------------------- G14 stock versus market
def resid(S):
    o, h, l, c, v = _bars(S)
    U = S.uni
    r = np.where(np.isfinite(S.P.ret), S.P.ret, 0.0)
    m = r[:, [S.spy]]
    n = 126
    cov = ta.sma(r * m, n) - ta.sma(r, n) * ta.sma(m, n)
    var = ta.sma(m * m, n) - ta.sma(m, n) ** 2
    beta = ta.shift(cov / np.maximum(var, 1e-12), 1)                 # beta known before today
    e = r - beta * m                                                  # residual daily return
    sde = ta.shift(ta.stdev(e, 63), 1)
    rz1 = e / sde
    rz5 = ta.rolling_sum(e, 5) / (ta.shift(ta.stdev(e, 63), 5) * np.sqrt(5))
    up_mkt, dn_mkt = m >= 0.005, m <= -0.005
    resil = ta.rolling_sum((dn_mkt & (r > 0)).astype(float), 20)
    weak = ta.rolling_sum((up_mkt & (r < 0)).astype(float), 20)
    corr = cov / np.sqrt(np.maximum(var, 1e-12) * np.maximum(ta.sma(r * r, n) - ta.sma(r, n) ** 2, 1e-12))
    z1 = S.z(1)
    mz1 = z1[:, [S.spy]]
    up = c > ta.sma(c, 200)
    return {
        "residual z5 <= -2 (stock-specific 5-bar fall)": U & (rz5 <= -2),
        "residual z5 >= +2 (stock-specific 5-bar rise)": U & (rz5 >= 2),
        "residual z1 <= -3": U & (rz1 <= -3),
        "residual z1 >= +3": U & (rz1 >= 3),
        "residual z5 <= -2 in uptrend": (U & up & (rz5 <= -2), U & up),
        "resilient: up on >=4 of the market's down days (20 bars)": U & (resil >= 4),
        "weak: down on >=4 of the market's up days (20 bars)": U & (weak >= 4),
        "low correlation with SPY (<0.2 over 126 bars)": U & (corr < 0.2),
        "high correlation with SPY (>0.7)": U & (corr > 0.7),
        "laggard: SPY z1>=+1.5 but stock z1<0.5": U & (mz1 >= 1.5) & (z1 < 0.5),
        "held up: SPY z1<=-1.5 but stock z1>-0.5": U & (mz1 <= -1.5) & (z1 > -0.5),
        "beta > 1.5": U & (beta > 1.5),
        "beta < 0.5": U & (beta < 0.5),
    }


# --------------------------------------------------------------------------- G06 breakouts
def breakouts(S):
    o, h, l, c, v = _bars(S)
    U = S.uni
    atr = S.atr(14)
    d = {}
    v50 = ta.shift(ta.sma(v, 50), 1)
    loc = (c - l) / np.maximum(h - l, 1e-12)
    for n in (20, 55, 252):
        prev_hi = ta.shift(ta.highest(c, n), 1)
        brk = c > prev_hi
        first = brk & (ta.rolling_sum(ta.shift(brk.astype(float), 1), 10) == 0)
        nearhi = U & (c >= 0.97 * prev_hi)                         # control: at or near the same high
        d[f"new {n}-bar closing high (first in 10)   (ctl: within 3% of that high)"] = (U & first, nearhi)
        d[f"  {n}-bar breakout on volume >=1.5x 50-bar average"] = (U & first & (v >= 1.5 * v50), nearhi)
        d[f"  {n}-bar breakout, close in top quarter of the bar"] = (U & first & (loc >= 0.75), nearhi)
        if n == 55:
            rng20 = ta.shift(ta.highest(h, 20) - ta.lowest(l, 20), 1) / ta.shift(atr, 1)
            d["  55-bar breakout from a tight base (prior 20-bar range <=4 ATR)"] = (U & first & (rng20 <= 4), nearhi)
            d["  55-bar breakout from a wide base (prior 20-bar range >=8 ATR)"] = (U & first & (rng20 >= 8), nearhi)
            atr_ratio = S.atr(5) / S.atr(50)
            d["  55-bar breakout after contraction (ATR5/ATR50 <0.75 the day before)"] = (U & first & (ta.shift(atr_ratio, 1) < 0.75), nearhi)
            failed = ta.shift(first.astype(float), 2).astype(bool) & (c < ta.shift(prev_hi, 2))
            d["FAILED 55-bar breakout: back under the level 2 bars later (ctl: universe)"] = U & failed
            spy = c[:, [S.spy]]
            mdown = (spy < ta.sma(spy, 200))
            d["  55-bar breakout while SPY is below its 200-day"] = (U & first & mdown, nearhi & mdown)
    d["within 3% of 252-bar high, no breakout today (ctl: universe)"] = U & (c >= 0.97 * ta.shift(ta.highest(c, 252), 1)) & ~(c > ta.shift(ta.highest(c, 252), 1))
    d["inside day then close above the mother bar's high (ctl: universe)"] = U & ta.shift((h < ta.shift(h, 1)) & (l > ta.shift(l, 1)), 1).astype(bool) & (c > ta.shift(h, 2))
    return d


# --------------------------------------------------------------------------- G05 volume
def volume(S):
    o, h, l, c, v = _bars(S)
    U = S.uni
    z1 = S.z(1)
    relv = v / ta.shift(ta.median(v, 20), 1)
    pr50 = ta.percentrank(v, 50)
    r = S.P.ret
    upv = ta.rolling_sum(np.where(r > 0, v, 0.0), 20) / ta.rolling_sum(v, 20)
    vtrend = ta.sma(v, 20) / ta.sma(v, 100)
    upday = c > ta.shift(c, 1)
    max_dn_vol = ta.shift(ta.highest(np.where(~upday, v, 0.0), 10), 1)
    acc = ta.rolling_sum(((c / ta.shift(c, 1) - 1 >= 0.002) & (v > ta.shift(v, 1))).astype(float), 25)
    dist = ta.rolling_sum(((c / ta.shift(c, 1) - 1 <= -0.002) & (v > ta.shift(v, 1))).astype(float), 25)
    obv = np.nancumsum(np.where(np.isfinite(r), np.sign(r) * np.where(np.isfinite(v), v, 0.0), 0.0), axis=0)
    obv_hi = obv >= ta.highest(obv, 126)
    px_hi = c >= ta.highest(c, 126)
    s50 = ta.sma(c, 50)
    turn_hi = E.xs_rank(ta.sma(v * c, 20) / np.maximum(S.adv60, 1.0), U) > 0.8
    return {
        "volume >=3x median, price flat (|z1|<0.5)": U & (relv >= 3) & (np.abs(z1) < 0.5),
        "volume in top 10% of own 50 days, |z1|<1 (high-volume premium)": U & (pr50 >= 90) & (np.abs(z1) < 1),
        "volume in bottom 10% of own 50 days": U & (pr50 <= 10),
        "up-volume share (20 bars) >= 0.65": U & (upv >= 0.65),
        "up-volume share (20 bars) <= 0.35": U & (upv <= 0.35),
        "volume trend: 20-bar average >= 1.5x the 100-bar": U & (vtrend >= 1.5),
        "volume trend: 20-bar average <= 0.7x the 100-bar": U & (vtrend <= 0.7),
        "pocket pivot: up day, volume > largest down-day volume of prior 10, above 50-day": U & upday & (v > max_dn_vol) & (c > s50),
        "accumulation: >=6 up-on-higher-volume days in 25": U & (acc >= 6),
        "distribution: >=6 down-on-higher-volume days in 25": U & (dist >= 6),
        "OBV at 126-bar high, price not": U & obv_hi & ~px_hi,
        "price at 126-bar high, OBV not": U & px_hi & ~obv_hi,
        "up day z1>=+1 on volume >=2x": U & (z1 >= 1) & (relv >= 2),
        "up day z1>=+1 on volume <0.8x": U & (z1 >= 1) & (relv < 0.8),
        "down day z1<=-1 on volume >=2x": U & (z1 <= -1) & (relv >= 2),
        "down day z1<=-1 on volume <0.8x": U & (z1 <= -1) & (relv < 0.8),
    }


# --------------------------------------------------------------------------- G07 gaps, overnight, range position
def gaps(S):
    o, h, l, c, v = _bars(S)
    U = S.uni
    pc = ta.shift(c, 1)
    volp = ta.shift(S.vol, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        on = np.log(o / pc)
        intr = np.log(c / o)
    gz = on / volp
    loc = (c - l) / np.maximum(h - l, 1e-12)
    con20, cin20 = ta.rolling_sum(on, 20), ta.rolling_sum(intr, 20)
    strong = loc >= 0.9
    weak = loc <= 0.1
    unfilled_up = l > ta.shift(h, 1)
    unfilled_dn = h < ta.shift(l, 1)
    return {
        "gap up >=1s and closed above the open (gap and go)": U & (gz >= 1) & (c > o),
        "gap up >=1s and closed below the open (gap fade)": U & (gz >= 1) & (c < o),
        "gap down <=-1s and closed below the open": U & (gz <= -1) & (c < o),
        "gap down <=-1s and closed above the open (reversal day)": U & (gz <= -1) & (c > o),
        "unfilled gap up (low above yesterday's high)": U & unfilled_up,
        "unfilled gap down (high below yesterday's low)": U & unfilled_dn,
        "close in top 10% of the day's range": U & strong,
        "close in bottom 10% of the day's range": U & weak,
        "3 closes in a row in the top 10% of range": U & strong & ta.shift(strong, 1).astype(bool) & ta.shift(strong, 2).astype(bool),
        "20-bar overnight return >= +5% and intraday <= -5% (tug of war)": U & (con20 >= 0.05) & (cin20 <= -0.05),
        "20-bar intraday return >= +5% and overnight <= -5%": U & (cin20 >= 0.05) & (con20 <= -0.05),
        "20-bar overnight return >= +8%": U & (con20 >= 0.08),
        "20-bar intraday return >= +8%": U & (cin20 >= 0.08),
    }


def gaps_extra(S):
    """Where the return accrues: mean overnight (close to open) and intraday (open to close)
    return per day for universe stocks and for SPY. The trader who enters at the next open
    skips one overnight return per trade."""
    o, h, l, c, v = _bars(S)
    pc = ta.shift(c, 1)
    on = np.where(S.uni, o / pc - 1, np.nan)
    intr = np.where(S.uni, c / o - 1, np.nan)
    a, b = 1e4 * np.nanmean(on), 1e4 * np.nanmean(intr)
    s_on = 1e4 * np.nanmean((o / pc - 1)[S.rows, S.spy])
    s_in = 1e4 * np.nanmean((c / o - 1)[S.rows, S.spy])
    print(f"  [{S.sample}] mean per day: universe overnight {a:+.2f} bp, intraday {b:+.2f} bp | SPY overnight {s_on:+.2f} bp, intraday {s_in:+.2f} bp")
    return {"uni_overnight_bp": float(a), "uni_intraday_bp": float(b), "spy_overnight_bp": float(s_on), "spy_intraday_bp": float(s_in)}


# --------------------------------------------------------------------------- G13 imports from other fields
def strange(S):
    o, h, l, c, v = _bars(S)
    U = S.uni
    atr = S.atr(14)
    s50, s200 = ta.sma(c, 50), ta.sma(c, 200)
    above50 = c > s50
    age = ta.barssince(above50 & ~ta.shift(above50, 1).astype(bool))          # bars since crossing above the 50-day
    ext = (c - s50) / atr
    z1, z5 = S.z(1), S.z(5)
    # CUSUM on volatility-scaled daily returns with drift allowance 0.5: g = max(0, g[1] + z1 - 0.5)
    g = np.zeros_like(z1)
    state = np.zeros(z1.shape[1])
    for t in range(z1.shape[0]):
        x = np.where(np.isfinite(z1[t]), z1[t], 0.0)
        state = np.maximum(0.0, state + x - 0.5)
        g[t] = state
    alarm = (g >= 4) & (ta.shift(g, 1) < 4)
    r = np.where(np.isfinite(S.P.ret), S.P.ret, 0.0)
    r5 = ta.rolling_sum(r, 5)
    vr5 = ta.stdev(r5, 126) ** 2 / np.maximum(5 * ta.stdev(r, 126) ** 2, 1e-12)        # variance ratio at 5 bars
    ac1 = (ta.sma(r * ta.shift(r, 1), 60) - ta.sma(r, 60) * ta.sma(ta.shift(r, 1), 60)) / np.maximum(ta.stdev(r, 60) ** 2, 1e-12)
    er = np.abs(c - ta.shift(c, 20)) / np.maximum(ta.rolling_sum(np.abs(c - ta.shift(c, 1)), 20), 1e-12)   # Kaufman efficiency ratio
    dd = c / ta.highest(h, 252) - 1
    uw = ta.barssince(c >= ta.highest(h, 252) * 0.999)                                    # bars under water
    m3 = ta.sma((r - ta.sma(r, 60)) ** 3, 60)
    skew = m3 / np.maximum(ta.stdev(r, 60) ** 3, 1e-18)
    vwap60 = ta.rolling_sum(c * v, 60) / ta.rolling_sum(v, 60)
    rnd = np.round(c / 10.0) * 10.0
    crossed_up = (c > rnd) & (ta.shift(c, 1) < rnd) & (S.c_raw >= 20)
    just_below = (c < rnd) & ((rnd - c) <= 0.25 * atr) & (S.c_raw >= 20)
    UP50 = U & above50
    return {
        "trend age 1-5 bars above the 50-day     (ctl: above 50-day)": (UP50 & (age <= 5), UP50),
        "trend age 21-60 bars": (UP50 & (age > 20) & (age <= 60), UP50),
        "trend age over 120 bars": (UP50 & (age > 120), UP50),
        "extended: 4+ ATR above the 50-day": (UP50 & (ext >= 4), UP50),
        "stretched down: 4+ ATR below the 50-day (ctl: universe)": U & (ext <= -4),
        "CUSUM up-alarm (g crosses 4)": U & alarm,
        "variance ratio(5)>=1.2 and z5>=+1.5 (trending stock, new push)": U & (vr5 >= 1.2) & (z5 >= 1.5),
        "variance ratio(5)<=0.8 and z5<=-1.5 (reverting stock, dip)": U & (vr5 <= 0.8) & (z5 <= -1.5),
        "variance ratio(5)>=1.2 and z5<=-1.5 (trending stock, falling)": U & (vr5 >= 1.2) & (z5 <= -1.5),
        "daily autocorrelation >= +0.15 and z1>=+1": U & (ac1 >= 0.15) & (z1 >= 1),
        "daily autocorrelation <= -0.15 and z1<=-1": U & (ac1 <= -0.15) & (z1 <= -1),
        "efficiency ratio(20) >= 0.6, price up": U & (er >= 0.6) & (c > ta.shift(c, 20)),
        "efficiency ratio(20) >= 0.6, price down": U & (er >= 0.6) & (c < ta.shift(c, 20)),
        "under water 60+ bars and 10-20% below the 252 high": U & (uw >= 60) & (dd <= -0.10) & (dd > -0.20),
        "skewness(60) <= -1": U & (skew <= -1),
        "skewness(60) >= +1": U & (skew >= 1),
        "2+ ATR above 60-bar VWAP": U & ((c - vwap60) / atr >= 2),
        "2+ ATR below 60-bar VWAP": U & ((c - vwap60) / atr <= -2),
        "closed up through a multiple of $10": U & crossed_up,
        "closed just under a multiple of $10 (within 0.25 ATR)": U & just_below,
    }


FAMS = {
    "dips": ("g01", "G01_dips", dips, (1, 5, 10), None),
    "resid": ("g14", "G14_resid", resid, (1, 5, 20), None),
    "breakouts": ("g06", "G06_breakouts", breakouts, (5, 20, 60), None),
    "volume": ("g05", "G05_volume", volume, (1, 5, 20), None),
    "gaps": ("g07", "G07_gaps", gaps, (1, 5, 20), gaps_extra),
    "strange": ("g13", "G13_strange", strange, (5, 20, 60), None),
}

if __name__ == "__main__":
    for k in (sys.argv[1:] or list(FAMS)):
        tag, fam, fn, hs, extra = FAMS[k]
        run(tag, fam, fn, hs=hs, extra=extra)
