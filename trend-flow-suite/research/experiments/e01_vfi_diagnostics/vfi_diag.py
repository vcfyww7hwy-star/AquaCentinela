"""
Faithful Python replication of 'Volume Flow Indicator [LazyBear]LF' (LucF mod, Pine v1/v2)
plus structural diagnostics. Daily/weekly use the non-intraday branch: coef=0.2, vcoef=2.5.

Pine semantics replicated:
  sum(x,n)      -> rolling sum incl. current bar
  sma(v,n)[1]   -> previous bar's SMA
  stdev(x,30)   -> population std (ddof=0) incl. current bar
  ema(x,n)      -> alpha = 2/(n+1)
"""
import sys, json, math
import numpy as np, pandas as pd
from scipy.stats import norm

SP = "/usr/local/lib/python3.13/site-packages"

def load():
    g = pd.read_csv(f"{SP}/backtesting/test/GOOG.csv", index_col=0, parse_dates=True)
    out = {"GOOG_D": g[["Open", "High", "Low", "Close", "Volume"]].astype(float)}
    for name, path in [("SPX_D", f"{SP}/arch/data/sp500/sp500.csv.gz"),
                       ("NASDAQ_D", f"{SP}/arch/data/nasdaq/nasdaq.csv.gz")]:
        d = pd.read_csv(path)
        d["Date"] = pd.to_datetime(d["Date"], format="%m/%d/%Y")
        d = d.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]].astype(float)
        out[name] = d
    # weekly resample (Fri), OHLCV
    for k in list(out):
        d = out[k]
        w = pd.DataFrame({"Open": d.Open.resample("W-FRI").first(),
                          "High": d.High.resample("W-FRI").max(),
                          "Low": d.Low.resample("W-FRI").min(),
                          "Close": d.Close.resample("W-FRI").last(),
                          "Volume": d.Volume.resample("W-FRI").sum()}).dropna()
        out[k.replace("_D", "_W")] = w
    return out

def vfi(df, length=130, coef=0.2, vcoef=2.5, smooth=False, ma_s=20, ma_l=100):
    tp = (df.High + df.Low + df.Close) / 3.0
    inter = np.log(tp) - np.log(tp.shift(1))
    vinter = inter.rolling(30).std(ddof=0)
    cutoff = coef * vinter * df.Close
    vave = df.Volume.rolling(length).mean().shift(1)
    vmax = vave * vcoef
    vc = np.minimum(df.Volume, vmax)
    mf = tp - tp.shift(1)
    vcp = pd.Series(np.where(mf > cutoff, vc, np.where(mf < -cutoff, -vc, 0.0)), index=df.index)
    vcp[cutoff.isna() | vmax.isna()] = np.nan
    S = vcp.rolling(length).sum()
    v = S / vave
    if smooth:
        v = v.rolling(3).mean()
    out = pd.DataFrame({"tp": tp, "z": mf / (vinter * df.Close), "vave": vave, "vc": vc,
                        "capped": df.Volume > vmax, "vcp": vcp, "S": S, "vfi": v})
    out["vfima"] = v.ewm(span=ma_s, adjust=False).mean()
    out["vfimal"] = v.ewm(span=ma_l, adjust=False).mean()
    return out.dropna(subset=["vfi"])

def crosses(a, b):
    up = (a > b) & (a.shift(1) <= b.shift(1))
    dn = (a < b) & (a.shift(1) >= b.shift(1))
    return up, dn

def decomposition(df, o, length=130):
    """dVFI_t = A (new bar) + B (bar leaving window) + C (re-normalisation by moving vave)."""
    vcp = o.vcp
    vave = o.vave
    A = vcp / vave
    B = -vcp.shift(length) / vave
    C = o.S.shift(1) * (1.0 / vave - 1.0 / vave.shift(1))
    d = o.vfi.diff()
    X = pd.DataFrame({"A": A, "B": B, "C": C, "d": d}).dropna()
    resid = (X.A + X.B + X.C - X.d).abs().max()
    var = X.d.var()
    cov = X[["A", "B", "C"]].cov()
    # variance attribution (A, B, C) incl. half of covariances
    share = {}
    for k in "ABC":
        share[k] = float((cov.loc[k, k] + sum(cov.loc[k, j] for j in "ABC" if j != k)) / var)
    return X, resid, share

def regime_backtest(close, sig, cost_bps=5.0):
    """long when sig>0 (decided at close t, held t+1); flat otherwise."""
    r = close.pct_change()
    pos = (sig > 0).astype(float).shift(1).fillna(0.0)
    turn = pos.diff().abs().fillna(0.0)
    strat = pos * r - turn * cost_bps / 1e4
    strat = strat.dropna()
    eq = (1 + strat).cumprod()
    yrs = len(strat) / 252.0
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = strat.std() * math.sqrt(252)
    dd = (eq / eq.cummax() - 1).min()
    return {"CAGR%": round(100 * cagr, 2), "Vol%": round(100 * vol, 2),
            "Sharpe": round(strat.mean() / strat.std() * math.sqrt(252), 2),
            "MaxDD%": round(100 * dd, 1), "Switches/yr": round(turn.sum() / yrs, 1),
            "Exposure%": round(100 * pos.mean(), 1)}

def main():
    data = load()
    R = {}
    for name, df in data.items():
        intr = False  # D and W -> non-intraday branch
        o = vfi(df)
        res = {"bars": int(len(o)), "from": str(o.index.min().date()), "to": str(o.index.max().date())}
        valid = o.vcp.notna()
        res["pct_bars_zeroed_by_threshold"] = round(100 * float((o.vcp[valid] == 0).mean()), 1)
        res["pct_bars_volume_capped"] = round(100 * float(o.capped[valid].mean()), 1)
        res["vfi_p05_p50_p95"] = [round(float(x), 1) for x in o.vfi.quantile([.05, .5, .95])]
        # decomposition
        X, resid, share = decomposition(df, o)
        res["decomp_identity_max_abs_err"] = float(resid)
        res["var_share_new_bar_A"] = round(share["A"], 3)
        res["var_share_dropoff_B"] = round(share["B"], 3)
        res["var_share_renorm_C"] = round(share["C"], 3)
        res["corr(dVFI, new-bar term)"] = round(float(X.d.corr(X.A)), 3)
        nz = X[X.A != 0]
        res["pct_days_VFI_moves_against_todays_flow"] = round(100 * float((np.sign(nz.d) == -np.sign(nz.A)).mean()), 1)
        # big swings (|dVFI|>3)
        big = X[X.d.abs() > 3.0]
        res["big_swings_n"] = int(len(big))
        if len(big):
            res["big_swings_pct_today_bar_neutral_or_opposite"] = round(100 * float(((big.A == 0) | (np.sign(big.A) != np.sign(big.d))).mean()), 1)
            res["big_swings_pct_dropoff_larger_than_today"] = round(100 * float((big.B.abs() > big.A.abs()).mean()), 1)
        # zero crosses explained by today's bar?
        up0, dn0 = crosses(o.vfi, pd.Series(0.0, index=o.index))
        zc = X.loc[X.index.intersection(o.index[up0 | dn0])]
        res["zero_crosses_n"] = int((up0 | dn0).sum())
        if len(zc):
            res["zero_crosses_pct_today_bar_neutral_or_opposite"] = round(100 * float(((zc.A == 0) | (np.sign(zc.A) != np.sign(zc.d))).mean()), 1)
        # signal frequencies per year
        yrs = len(o) / (252.0 if name.endswith("_D") else 52.0)
        upm, dnm = crosses(o.vfi, o.vfima)
        buy = (o.vfi > 2) & (o.vfi.shift(1) <= 2)
        sell = (o.vfi < -2) & (o.vfi.shift(1) >= -2)
        res["signals_per_year"] = {
            "MA20_cross": round(float((upm | dnm).sum()) / yrs, 1),
            "zero_cross": round(float((up0 | dn0).sum()) / yrs, 1),
            "buy_sell_levels": round(float((buy | sell).sum()) / yrs, 1),
            "big_swing": round(float(len(big)) / yrs, 1)}
        # information content: volume-free twin and price momentum
        tp = o.tp
        sgn = np.sign(o.vcp)  # same thresholding, volume removed
        novol = sgn.rolling(130).sum()
        mom = np.log(df.Close).diff(130).reindex(o.index)
        sma_dev = (df.Close / df.Close.rolling(130).mean() - 1).reindex(o.index)
        J = pd.DataFrame({"vfi": o.vfi, "novol": novol, "mom": mom, "smadev": sma_dev}).dropna()
        res["corr_VFI_vs_volume_free_twin"] = round(float(J.vfi.corr(J.novol)), 3)
        res["corr_VFI_vs_130bar_log_return"] = round(float(J.vfi.corr(J.mom)), 3)
        res["corr_VFI_vs_price_dev_from_SMA130"] = round(float(J.vfi.corr(J.smadev)), 3)
        # sign agreement (regime) between VFI and pure-price filters
        res["sign_agreement_VFI_vs_momentum_%"] = round(100 * float((np.sign(J.vfi) == np.sign(J.mom)).mean()), 1)
        # length sensitivity of fixed thresholds (+-2 levels, big swing 3.0)
        sens = {}
        for L in (50, 130, 200):
            oL = vfi(df, length=L)
            dL = oL.vfi.diff()
            yrsL = len(oL) / (252.0 if name.endswith("_D") else 52.0)
            sens[L] = {"vfi_p05_p95": [round(float(x), 1) for x in oL.vfi.quantile([.05, .95])],
                       "big_swings_per_yr": round(float((dL.abs() > 3).sum()) / yrsL, 1)}
        res["length_sensitivity"] = sens
        # boxcar vs exponential accumulator with same mean lag (span=130 -> mean lag 64.5 bars)
        lam = 1 - 2 / 131.0
        x = (o.vcp / o.vave).fillna(0.0)
        # leaky integrator scaled to be comparable to a 130-bar sum
        E = x.ewm(alpha=1 - lam, adjust=False).mean() * 130
        cmp = pd.DataFrame({"vfi": o.vfi, "E": E, "x": x}).iloc[200:]
        upE, dnE = crosses(cmp.E, pd.Series(0.0, index=cmp.index))
        upV, dnV = crosses(cmp.vfi, pd.Series(0.0, index=cmp.index))
        res["exp_vs_boxcar"] = {
            "corr(change, today's flow) boxcar": round(float(cmp.vfi.diff().corr(cmp.x)), 3),
            "corr(change, today's flow) exponential": round(float(cmp.E.diff().corr(cmp.x)), 3),
            "zero_crosses boxcar": int((upV | dnV).sum()),
            "zero_crosses exponential": int((upE | dnE).sum()),
            "corr(levels)": round(float(cmp.vfi.corr(cmp.E)), 3)}
        # regime backtests (illustrative only), daily series
        if name.endswith("_D"):
            close = df.Close.reindex(o.index)
            bt = {"BuyHold": regime_backtest(close, pd.Series(1.0, index=o.index)),
                  "VFI>0": regime_backtest(close, o.vfi),
                  "VFI>EMA20(VFI)": regime_backtest(close, o.vfi - o.vfima),
                  "Mom130>0": regime_backtest(close, mom.reindex(o.index).fillna(0)),
                  "Close>SMA130": regime_backtest(close, sma_dev.reindex(o.index).fillna(0))}
            res["regime_backtest_5bps"] = bt
        R[name] = res
    print(json.dumps(R, indent=1, default=str))

if __name__ == "__main__":
    main()
