"""Follow-up diagnostics: big-swing mechanics, kernel comparison + hysteresis, lag at major turns."""
import json, math
import numpy as np, pandas as pd
import importlib.util, sys
spec = importlib.util.spec_from_file_location("d1", sys.argv[1]); d1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(d1)

data = d1.load()
out = {}

# 1) Big swings: with vcoef=2.5 a single bar contributes at most 2.5 -> |dVFI|>3 needs the dropped bar.
g = data["GOOG_D"]; o = d1.vfi(g); X, _, _ = d1.decomposition(g, o)
big = X[X.d.abs() > 3]
out["GOOG_big_swings"] = {
    "n": int(len(big)),
    "max_abs_new_bar_term": round(float(X.A.abs().max()), 3),
    "pct_where_dropped_bar_pushes_same_way_by>=0.5": round(100 * float(((np.sign(big.B) == np.sign(big.d)) & (big.B.abs() >= 0.5)).mean()), 1)}

# 2) typical-price vs close classification disagreement
for k in ("SPX_D", "GOOG_D"):
    df = data[k]; tp = (df.High + df.Low + df.Close) / 3
    s1 = np.sign(tp.diff()); s2 = np.sign(df.Close.diff())
    m = (s1 != 0) & (s2 != 0)
    out[f"{k}_pct_days_sign(d_hlc3)!=sign(d_close)"] = round(100 * float((s1[m] != s2[m]).mean()), 1)

# 3) Kernel comparison at equal mean lag (~64.5 bars) + hysteresis
def kernels(x):
    N = 130
    box = x.rolling(N).mean()
    ema = x.ewm(span=N, adjust=False).mean()
    dema = x.ewm(span=65, adjust=False).mean().ewm(span=65, adjust=False).mean()  # 2-pole, mean lag ~64
    w = np.hanning(N + 2)[1:-1]; w = w / w.sum()                                      # symmetric taper, mean lag 64.5
    hann = x.rolling(N).apply(lambda a: float(np.dot(a, w[::-1])), raw=True)
    return {"boxcar": box, "ema": ema, "2pole": dema, "hann": hann}

def switches(s, band=0.0):
    """regime switches with symmetric hysteresis band (Schmitt trigger) in units of s."""
    st, n = 0, 0
    for v in s.dropna().values:
        if st <= 0 and v > band: n += (st != 0); st = 1
        elif st >= 0 and v < -band: n += (st != 0); st = -1
    return n

for k in ("SPX_D", "NASDAQ_D", "GOOG_D"):
    df = data[k]; o = d1.vfi(df)
    x = (o.vcp / o.vave)
    K = kernels(x)
    idx = K["hann"].dropna().index[10:]
    row = {}
    for name, s in K.items():
        s = s.reindex(idx)
        sd = s.std()
        row[name] = {"zero_cross_switches": switches(s, 0.0),
                     "switches_band_0.10sd": switches(s, 0.10 * sd),
                     "switches_band_0.25sd": switches(s, 0.25 * sd),
                     "mean_lag_bars": {"boxcar": 64.5, "ema": 64.5, "2pole": 64.0, "hann": 64.5}[name]}
    out[f"{k}_kernel_switches"] = row

# 4) Lag at major SPX turning points (daily and weekly): first zero-cross after the turn
turns = {"top_2000-03-24": ("2000-03-24", -1), "bottom_2002-10-09": ("2002-10-09", 1),
         "top_2007-10-09": ("2007-10-09", -1), "bottom_2009-03-09": ("2009-03-09", 1)}
for k, bars_per_yr in (("SPX_D", 252), ("SPX_W", 52)):
    df = data[k]; o = d1.vfi(df)
    mom = np.log(df.Close).diff(130).reindex(o.index)
    res = {}
    for lbl, (dt, sgn) in turns.items():
        t0 = pd.Timestamp(dt)
        after = o.loc[o.index >= t0]
        def first_cross(series):
            s = series.loc[series.index >= t0]
            hit = s[(np.sign(s) == sgn)]
            if len(hit) == 0: return None
            t1 = hit.index[0]
            px_move = 100 * (df.Close.loc[t1] / df.Close.loc[df.index[df.index.get_indexer([t0], method="nearest")[0]]] - 1)
            return {"date": str(t1.date()), "bars_after_turn": int(np.sum((series.index > t0) & (series.index <= t1))),
                    "price_move_since_turn_%": round(float(px_move), 1)}
        res[lbl] = {"VFI": first_cross(o.vfi), "Mom130": first_cross(mom)}
    out[f"{k}_lag_at_turns"] = res

print(json.dumps(out, indent=1, default=str))
