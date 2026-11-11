"""G03 + G04 - What to hold: momentum, 52-week high, trend quality, lottery and low-volatility
features (compact main-loop version of families f03 and f04). DEV and CTX only.

Absolute thresholds first (a single chart can compute them); cross-sectional quintiles after
(they need a screener). Horizons 5, 20, 60 bars from the next open.
"""
from __future__ import annotations

import numpy as np

from research.experiments.compact import run
from research.swinglab import engine as E
from research.swinglab import pinelike as ta


def build(S):
    c = S.P.cf
    hi = np.where(np.isfinite(S.P.h), S.P.h, c)
    lo = np.where(np.isfinite(S.P.l), S.P.l, c)
    U = S.uni
    with np.errstate(divide="ignore", invalid="ignore"):
        mom = ta.shift(c, 21) / ta.shift(c, 252) - 1           # 12-1 momentum
        mom6 = ta.shift(c, 21) / ta.shift(c, 126) - 1
        prox = c / ta.highest(hi, 252)                          # closeness to the 252-bar high
        up_from_low = c / ta.lowest(lo, 252)
    s50, s150, s200 = ta.sma(c, 50), ta.sma(c, 150), ta.sma(c, 200)
    template = (c > s50) & (s50 > s150) & (s150 > s200) & (s200 > ta.shift(s200, 20)) & (up_from_low >= 1.3) & (prox >= 0.75)
    lc = np.log(c)
    slope = ta.linreg_slope(lc, 126)
    # R-squared of the 126-bar log-price trend = corr(time, log price)^2 = slope^2 * var(t) / var(log price)
    var_t = (126 ** 2 - 1) / 12.0
    r2 = np.clip(slope ** 2 * var_t / np.maximum(ta.stdev(lc, 126) ** 2, 1e-12), 0, 1)
    r = S.P.ret
    updays = ta.rolling_sum((r > 0).astype(float), 252) / 252
    dndays = ta.rolling_sum((r < 0).astype(float), 252) / 252
    fip = np.sign(c / ta.shift(c, 252) - 1) * (dndays - updays)   # information discreteness: negative = smooth
    spy = c[:, [S.spy]]
    with np.errstate(divide="ignore", invalid="ignore"):
        rs126 = (c / ta.shift(c, 126)) - (spy / ta.shift(spy, 126))
        rsline = c / spy
    rs_newhigh = rsline >= ta.highest(rsline, 252)
    px_newhigh = c >= ta.highest(c, 252)
    sig_ann = 0.757 * S.atr(14) / c * np.sqrt(252)               # annualised volatility forecast (G12)
    max21 = ta.highest(np.where(np.isfinite(r), np.exp(r) - 1, np.nan), 21)
    lottery = (sig_ann >= 0.60) & (max21 >= 0.10)
    d = {}
    for lab, m in (("mom12-1 < -20%", mom < -0.2), ("mom12-1 -20%..0", (mom >= -0.2) & (mom < 0)), ("mom12-1 0..+20%", (mom >= 0) & (mom < 0.2)),
                   ("mom12-1 +20..+50%", (mom >= 0.2) & (mom < 0.5)), ("mom12-1 > +50%", mom >= 0.5)):
        d[lab] = U & m
    for lab, m in (("within 5% of 252-day high", prox >= 0.95), ("5-15% below high", (prox < 0.95) & (prox >= 0.85)),
                   ("15-30% below high", (prox < 0.85) & (prox >= 0.70)), ("more than 30% below high", prox < 0.70)):
        d[lab] = U & m
    d["above 200-day average"] = U & (c > s200)
    d["trend template (50>150>200 rising, near high)"] = U & template
    d["smooth uptrend: slope>0 and R2>=0.8 (126 bars)"] = U & (slope > 0) & (r2 >= 0.8)
    d["rough uptrend: slope>0 and R2<0.4"] = U & (slope > 0) & (r2 < 0.4)
    d["up 12m with smooth path (FIP <= -0.05)"] = U & (c > ta.shift(c, 252)) & (fip <= -0.05)
    d["up 12m with jumpy path (FIP >= +0.02)"] = U & (c > ta.shift(c, 252)) & (fip >= 0.02)
    d["beat SPY by 15%+ over 126 bars"] = U & (rs126 >= 0.15)
    d["lagged SPY by 15%+ over 126 bars"] = U & (rs126 <= -0.15)
    d["RS line at 252-bar high"] = U & rs_newhigh
    d["RS line at high, price not yet"] = U & rs_newhigh & ~px_newhigh
    d["vol forecast >= 60% a year"] = U & (sig_ann >= 0.60)
    d["vol forecast <= 20% a year"] = U & (sig_ann <= 0.20)
    d["MAX21 >= 10% (a 10% up day in the last month)"] = U & (max21 >= 0.10)
    d["lottery: vol >= 60% and MAX21 >= 10%"] = U & lottery
    d["price as traded < $10"] = U & (S.c_raw < 10)
    good = (mom >= 0) & (prox >= 0.85) & ~lottery & (c > s200)
    d["QUALITY: mom>=0, within 15% of high, above 200d, not lottery"] = U & good
    d["JUNK: mom<0, 30%+ below high, below 200d"] = U & (mom < 0) & (prox < 0.70) & (c < s200)
    # cross-sectional quintiles (need a screener)
    for nm, feat in (("mom12-1", mom), ("closeness to high", prox), ("vol forecast", sig_ann), ("mom6-1", mom6)):
        rk = E.xs_rank(feat, U)
        d[f"[screener] {nm}: top quintile"] = U & (rk > 0.8)
        d[f"[screener] {nm}: bottom quintile"] = U & (rk <= 0.2)
    return d


def extra(S):
    """Tail risk by group: probability of a loss worse than 15% within 20 bars."""
    c = S.P.cf
    f20 = S.fwd(20)
    sig_ann = 0.757 * S.atr(14) / c * np.sqrt(252)
    r = S.P.ret
    max21 = ta.highest(np.where(np.isfinite(r), np.exp(r) - 1, np.nan), 21)
    hi = np.where(np.isfinite(S.P.h), S.P.h, c)
    prox = c / ta.highest(hi, 252)
    out = {}
    for lab, m in (("universe", S.uni), ("lottery", S.uni & (sig_ann >= 0.6) & (max21 >= 0.10)), ("vol<=20%", S.uni & (sig_ann <= 0.2)),
                   ("within 5% of high", S.uni & (prox >= 0.95)), ("30%+ below high", S.uni & (prox < 0.70))):
        x = f20[m]
        x = x[np.isfinite(x)]
        out[lab] = {"p_loss15": round(float(np.mean(x < -0.15)), 4), "p_gain15": round(float(np.mean(x > 0.15)), 4),
                    "median_bp": round(1e4 * float(np.median(x)), 1), "mean_bp": round(1e4 * float(np.mean(x)), 1)}
    print(f"  [{S.sample}] 20-bar outcome by group: " + "; ".join(f"{k}: P(<-15%) {100 * v['p_loss15']:.1f}% P(>+15%) {100 * v['p_gain15']:.1f}% mean {v['mean_bp']:+.0f}bp" for k, v in out.items()))
    return out


if __name__ == "__main__":
    run("g03", "G03_selection", build, hs=(5, 20, 60), extra=extra)
