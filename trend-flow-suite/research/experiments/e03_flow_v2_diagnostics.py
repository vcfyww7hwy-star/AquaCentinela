"""E03 - Volume Flow v2: calibration and behaviour (descriptive only, Nov 2026).

Deliberately NOT a profitability test. Predictive hypotheses (H2, H5-H7 in
the former docs/03_volume_flow_v2.md) were later tested on real stocks in E05 and E08 and failed;
see docs/03_relative_volume.md. This script is kept as a record of the v1 pane.
Here we check that the indicator behaves as designed:
  1. calibration: standardised returns ~ unit scale, relative volume centred on 1;
  2. ranges of flow and asymmetry; overlap with the old VFI and with price momentum;
  3. whipsaw: zero-line crossings per year vs the VFI;
  4. event frequencies per year (too frequent = noise, too rare = useless);
  5. persistence coefficient per series.
Run from research/:  python3 -m experiments.e03_flow_v2_diagnostics
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from tfs.data import load_bundled
from tfs.flow import volume_flow_v2
from tfs.vfi import vfi

WARMUP = 600
EVENTS = ["climax_up", "climax_dn", "absorb_top", "absorb_bottom", "accumulation",
          "distribution", "bear_div", "bull_div"]


def weekly(df: pd.DataFrame) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    return df.resample("W-FRI").agg(agg).dropna()


def zero_crosses(x: pd.Series) -> int:
    s = np.sign(x.dropna())
    s = s[s != 0]
    return int((s != s.shift(1)).sum() - 1)


def q(x, qs=(0.05, 0.5, 0.95), scale=1.0):
    return [round(float(v) * scale, 2) for v in pd.Series(x).dropna().quantile(qs)]


def diagnose(df: pd.DataFrame, bars_per_year: float) -> dict:
    f = volume_flow_v2(df).iloc[WARMUP:]
    old = vfi(df, length=130).iloc[WARMUP:]
    sign_cnt = np.sign(old["vcp"]).rolling(130).sum()
    mom = np.log(df["close"]).diff(130).iloc[WARMUP:]
    j = pd.DataFrame({"f_slow": f["f_slow"], "asym": f["asym"], "vfi": old["vfi"],
                      "twin": sign_cnt, "mom": mom}).dropna()
    beta = np.polyfit(j["twin"], j["vfi"], 1)
    vfi_volume_part = j["vfi"] - np.polyval(beta, j["twin"])   # what volume adds to the VFI
    years = len(f) / bars_per_year
    return {
        "bars": int(len(f)), "from": str(f.index[0].date()), "to": str(f.index[-1].date()),
        "calibration": {"std_of_z": round(float(f["z"].std()), 3),
                        "median_rvol": round(float(f["rvol"].median()), 3),
                        "pct_bars_weight_capped": round(100 * float((f["rvol"] > 3).mean()), 2)},
        "ranges_p05_p50_p95": {"f_slow_pct": q(f["f_slow"], scale=100),
                               "f_fast_pct": q(f["f_fast"], scale=100),
                               "asym_pct": q(f["asym"], scale=100), "asym_z": q(f["asym_z"])},
        "overlap": {"corr_fslow_vs_vfi": round(float(j["f_slow"].corr(j["vfi"])), 3),
                    "corr_fslow_vs_130bar_return": round(float(j["f_slow"].corr(j["mom"])), 3),
                    "corr_asym_vs_vfi_volume_part": round(float(j["asym"].corr(vfi_volume_part)), 3),
                    "corr_asym_vs_130bar_return": round(float(j["asym"].corr(j["mom"])), 3)},
        "zero_crosses_per_year": {"f_slow": round(zero_crosses(f["f_slow"]) / years, 1),
                                  "f_fast": round(zero_crosses(f["f_fast"]) / years, 1),
                                  "vfi_130": round(zero_crosses(old["vfi"]) / years, 1)},
        "events_per_year": {e: round(float(f[e].sum()) / years, 1) for e in EVENTS},
        "dryup_pct_of_bars": round(100 * float(f["dryup"].mean()), 1),
        "persistence_last": {"c": round(float(f["persist_c"].dropna().iloc[-1]), 3),
                             "t": round(float(f["persist_t"].dropna().iloc[-1]), 2),
                             "median_t_over_sample": round(float(f["persist_t"].median()), 2)},
    }


def main():
    out = {}
    for name in ("SPX", "NASDAQ", "GOOG"):
        d = load_bundled(name)
        out[f"{name}_D"] = diagnose(d, 252)
        if name != "GOOG":                       # GOOG weekly history is too short after warm-up
            out[f"{name}_W"] = diagnose(weekly(d), 52)
    path = Path(__file__).resolve().parents[1] / "results" / "e03_flow_v2_diagnostics.json"
    path.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
