"""Frozen candidate definitions.

One function per candidate. The same function is used for the robustness attacks on development
data and, later, for the single pre-registered validation run, so that "the definition tested" and
"the definition confirmed" cannot drift apart. Every definition:

  * is computed at the close of bar t from data up to t (ratios of split-adjusted prices only;
    the LEVEL of an adjusted price is never used, because it encodes future splits);
  * is Pine-computable from the chart's OHLCV (plus SPY where stated);
  * returns (signal, control) as boolean [T, N] arrays; control None means the whole universe.

`SPEC` gives, for each candidate: the horizon in bars, the predicted sign of the cross-sectional
(XS) effect from the next open, the intended use, and a one-line Pine recipe.
"""
from __future__ import annotations

import numpy as np

from . import pinelike as ta


class Feat:
    """Features shared by the candidates, computed once per Study."""

    def __init__(self, S):
        P = S.P
        c = P.cf
        self.S, self.c = S, c
        self.o = np.where(np.isfinite(P.o), P.o, c)
        self.h = np.where(np.isfinite(P.h), P.h, c)
        self.l = np.where(np.isfinite(P.l), P.l, c)
        self.v = np.where(np.isfinite(P.v), P.v, np.nan)
        self.U = S.uni
        self.z1, self.z3, self.z5 = S.z(1), S.z(3), S.z(5)
        pc = ta.shift(c, 1)
        volp = ta.shift(S.vol, 1)
        with np.errstate(divide="ignore", invalid="ignore"):
            self.on = np.log(self.o / pc)                       # overnight log return
            self.intr = np.log(c / self.o)                      # intraday log return
            self.gz = self.on / volp                            # opening gap in sigma units
            self.relv = self.v / ta.shift(ta.median(self.v, 20), 1)   # volume / median of the previous 20 bars
            self.loc = (c - self.l) / np.maximum(self.h - self.l, 1e-12)
        self.s50, self.s200 = ta.sma(c, 50), ta.sma(c, 200)
        self.up = c > self.s200
        self.dn = ~self.up & np.isfinite(self.s200)
        self.atr = S.atr(14)
        with np.errstate(divide="ignore", invalid="ignore"):
            self.prox = c / ta.highest(self.h, 252)
            self.mom = ta.shift(c, 21) / ta.shift(c, 252) - 1


def ep(F):                 # E1
    return F.U & (F.gz >= 3) & (F.relv >= 3) & (F.loc >= 2 / 3), None


def shock_down_vol(F):     # A1
    return F.U & (F.z1 <= -3) & (F.relv >= 3), None


def bounce_in_downtrend(F):  # A2
    return F.U & F.dn & (F.z5 >= 1.5), F.U & F.dn


def unfilled_gap_up(F):    # A3  (excluding episodic pivots, which are tested separately)
    e, _ = ep(F)
    return F.U & (F.l > ta.shift(F.h, 1)) & ~e, None


def gap_down_weak_close(F):  # A4
    return F.U & (F.gz <= -1) & (F.c < F.o), None


def tug_of_war(F):         # A5
    con20, cin20 = ta.rolling_sum(F.on, 20), ta.rolling_sum(F.intr, 20)
    return F.U & (con20 >= 0.05) & (cin20 <= -0.05), None


def failed_breakout(F):    # A6
    prev_hi = ta.shift(ta.highest(F.c, 55), 1)
    brk = F.c > prev_hi
    first = brk & (ta.rolling_sum(ta.shift(brk.astype(float), 1), 10) == 0)
    return F.U & ta.shift(first.astype(float), 2).astype(bool) & (F.c < ta.shift(prev_hi, 2)), None


def junk(F):               # A7
    return F.U & (F.mom < 0) & (F.prox < 0.70) & F.dn, None


def pop_fade(F):           # A8
    return F.U & (F.z3 > 1) & (F.z3 <= 2), None


def stretched_down(F):     # A9
    return F.U & ((F.c - F.s50) / F.atr <= -4), None


def high_on_volume(F):     # E2
    prev_hi = ta.shift(ta.highest(F.c, 252), 1)
    brk = F.c > prev_hi
    first = brk & (ta.rolling_sum(ta.shift(brk.astype(float), 1), 10) == 0)
    v50 = ta.shift(ta.sma(F.v, 50), 1)
    return F.U & first & (F.v >= 1.5 * v50), F.U & (F.c >= 0.97 * prev_hi)


def neg_skew(F):           # E3
    r = np.where(np.isfinite(F.S.P.ret), F.S.P.ret, 0.0)
    m3 = ta.sma((r - ta.sma(r, 60)) ** 3, 60)
    skew = m3 / np.maximum(ta.stdev(r, 60) ** 3, 1e-18)
    return F.U & (skew <= -1), None


def pos_skew(F):           # A10
    r = np.where(np.isfinite(F.S.P.ret), F.S.P.ret, 0.0)
    m3 = ta.sma((r - ta.sma(r, 60)) ** 3, 60)
    skew = m3 / np.maximum(ta.stdev(r, 60) ** 3, 1e-18)
    return F.U & (skew >= 1), None


def spike_in_downtrend(F):  # A11
    return F.U & F.dn & (F.z1 >= 3), F.U & F.dn


SPEC = {
    "E1_episodic_pivot": dict(fn=ep, h=10, sign=+1, use="enter",
                              pine="gap=(open-close[1])/close[1]/sigma[1] >= 3 and volume/median(volume,20)[1] >= 3 and (close-low)/(high-low) >= 2/3"),
    "E2_252high_on_volume": dict(fn=high_on_volume, h=5, sign=+1, use="enter",
                                 pine="close > ta.highest(close,252)[1], first in 10 bars, volume >= 1.5*ta.sma(volume,50)[1]; control: within 3% of that high"),
    "E3_negative_skew": dict(fn=neg_skew, h=60, sign=+1, use="select", pine="skewness of the last 60 daily log returns <= -1"),
    "A1_shock_down_on_volume": dict(fn=shock_down_vol, h=20, sign=-1, use="avoid/exit",
                                    pine="ln(close/close[1])/sigma[1] <= -3 and volume/median(volume,20)[1] >= 3"),
    "A2_bounce_in_downtrend": dict(fn=bounce_in_downtrend, h=10, sign=-1, use="avoid",
                                   pine="close < ta.sma(close,200) and ln(close/close[5])/(sigma[5]*sqrt(5)) >= 1.5; control: below the 200-day"),
    "A3_unfilled_gap_up": dict(fn=unfilled_gap_up, h=5, sign=-1, use="avoid", pine="low > high[1] and not an episodic pivot"),
    "A4_gap_down_weak_close": dict(fn=gap_down_weak_close, h=20, sign=-1, use="avoid/exit",
                                   pine="ln(open/close[1])/sigma[1] <= -1 and close < open"),
    "A5_tug_of_war": dict(fn=tug_of_war, h=5, sign=-1, use="avoid",
                          pine="math.sum(ln(open/close[1]),20) >= 0.05 and math.sum(ln(close/open),20) <= -0.05"),
    "A6_failed_breakout": dict(fn=failed_breakout, h=20, sign=-1, use="exit",
                               pine="first close above ta.highest(close,55)[1] two bars ago, and close now below that level"),
    "A7_junk": dict(fn=junk, h=60, sign=-1, use="avoid",
                    pine="close[21]/close[252] < 1 and close/ta.highest(high,252) < 0.70 and close < ta.sma(close,200)"),
    "A8_pop_fade": dict(fn=pop_fade, h=5, sign=-1, use="avoid chasing", pine="ln(close/close[3])/(sigma[3]*sqrt(3)) in (1, 2]"),
    "A9_stretched_down": dict(fn=stretched_down, h=20, sign=-1, use="avoid", pine="(close - ta.sma(close,50))/ta.atr(14) <= -4"),
    "A10_positive_skew": dict(fn=pos_skew, h=60, sign=-1, use="avoid", pine="skewness of the last 60 daily log returns >= +1"),
    "A11_spike_in_downtrend": dict(fn=spike_in_downtrend, h=5, sign=-1, use="avoid",
                                   pine="close < ta.sma(close,200) and ln(close/close[1])/sigma[1] >= 3; control: below the 200-day"),
}
