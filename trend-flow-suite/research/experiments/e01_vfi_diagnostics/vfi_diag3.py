import json, sys, importlib.util
import numpy as np, pandas as pd
spec = importlib.util.spec_from_file_location("d1", sys.argv[1]); d1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(d1)
data = d1.load(); out = {}
# A) Regime test: VFI>0 vs its volume-free twin >0 (identical thresholding, volume removed)
for k in ("SPX_D", "NASDAQ_D", "GOOG_D"):
    df = data[k]; o = d1.vfi(df)
    novol = np.sign(o.vcp).rolling(130).sum()
    close = df.Close.reindex(o.index)
    out[k] = {"VFI>0": d1.regime_backtest(close, o.vfi),
              "VolumeFreeTwin>0": d1.regime_backtest(close, novol.fillna(0)),
              "regime_sign_agreement_%": round(100*float((np.sign(o.vfi)==np.sign(novol)).loc[novol.notna()].mean()),1)}
# B) Step response (bars to reach 50% / 90% of a unit step) at equal mean lag
N=130; T=400; x=pd.Series(np.r_[np.zeros(200), np.ones(T)])
w=np.hanning(N+2)[1:-1]; w=w/w.sum()
resp={"boxcar":x.rolling(N).mean(),"ema_span130":x.ewm(span=N,adjust=False).mean(),
      "2pole_span65x2":x.ewm(span=65,adjust=False).mean().ewm(span=65,adjust=False).mean(),
      "hann130":x.rolling(N).apply(lambda a: float(np.dot(a,w[::-1])),raw=True)}
out["step_response_bars"]={k:{"t50":int((v.iloc[200:]>=0.5).values.argmax()),"t90":int((v.iloc[200:]>=0.9).values.argmax()),
     "weight_on_newest_bar":round(float(v.iloc[200]),5)} for k,v in resp.items()}
print(json.dumps(out,indent=1))
