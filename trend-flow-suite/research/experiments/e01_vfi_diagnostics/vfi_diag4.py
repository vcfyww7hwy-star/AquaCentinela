import json, sys, importlib.util
import numpy as np, pandas as pd
spec = importlib.util.spec_from_file_location("d1", sys.argv[1]); d1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(d1)
data = d1.load(); out = {}
def schmitt(s, band):
    st = 0; res = []
    for v in s.values:
        if np.isnan(v): res.append(0.0); continue
        if st <= 0 and v > band: st = 1
        elif st >= 0 and v < -band: st = -1
        res.append(float(st))
    return pd.Series(res, index=s.index)
for k in ("SPX_D", "NASDAQ_D", "GOOG_D"):
    df = data[k]; o = d1.vfi(df); x = (o.vcp / o.vave)
    box = x.rolling(130).sum()                                   # = VFI (identical up to re-normalisation)
    two = x.ewm(span=65, adjust=False).mean().ewm(span=65, adjust=False).mean() * 130
    close = df.Close.reindex(o.index); row = {}
    for name, s in (("boxcar(VFI)", box), ("2-pole", two)):
        s = s.iloc[260:]; c = close.reindex(s.index); sd = s.std()
        row[name] = {"no_band": d1.regime_backtest(c, s), "band_0.25sd": d1.regime_backtest(c, schmitt(s, 0.25 * sd))}
    out[k] = row
print(json.dumps(out, indent=1))
