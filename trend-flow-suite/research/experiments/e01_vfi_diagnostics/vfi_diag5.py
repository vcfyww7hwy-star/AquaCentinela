import json, sys, importlib.util
import numpy as np, pandas as pd
from scipy.stats import norm
spec = importlib.util.spec_from_file_location("d1", sys.argv[1]); d1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(d1)
data = d1.load(); out = {"theory_pct_zeroed_k0.2": round(100*(2*norm.cdf(0.2)-1),1), "theory_pct_zeroed_k0.1": round(100*(2*norm.cdf(0.1)-1),1)}
for k in ("SPX_D","NASDAQ_D","GOOG_D"):
    o = d1.vfi(data[k]); v = o.vfi
    buy = (v > 2) & (v.shift(1) <= 2); sell = (v < -2) & (v.shift(1) >= -2)
    seq = pd.Series(np.where(buy, 1, np.where(sell, -1, 0)), index=v.index); seq = seq[seq != 0]
    rep = (seq == seq.shift(1)).iloc[1:]
    out[k] = {"pct_time_inside_+-2_band": round(100*float((v.abs() < 2).mean()),1),
              "band_width_as_pct_of_p05_p95_range": round(100*4/float(v.quantile(.95)-v.quantile(.05)),1),
              "buy_sell_signals": int(len(seq)), "pct_repeated_same_direction": round(100*float(rep.mean()),1)}
print(json.dumps(out, indent=1))
