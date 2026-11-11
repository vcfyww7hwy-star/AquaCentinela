"""Frozen inputs of the validation run. Written before the run; see docs/03_preregistration_val.md.

Nothing in this file may change after research/results/val_confirmation.json exists.
"""

# Directional candidates (definitions, horizons and predicted signs live in swinglab/candidates.py)
DIRECTIONAL = [
    "E1_episodic_pivot",
    "E2_252high_on_volume",
    "E3_negative_skew",
    "A1_shock_down_on_volume",
    "A2_bounce_in_downtrend",
    "A3_unfilled_gap_up",
    "A4_gap_down_weak_close",
    "A5_tug_of_war",
    "A6_failed_breakout",
    "A7_junk",
    "A8_pop_fade",
    "A9_stretched_down",
    "A10_positive_skew",
    "A11_spike_in_downtrend",
]

# Risk engine: constants measured on development data (research/results/g12_risk_engine.json)
RISK_CRITERIA = {
    # QLIKE-optimal constant per estimate and horizon, fitted on CTX (1998-2010) only
    "scale_from_ctx": {
        "atr14/close": {"5": 0.750, "10": 0.757, "20": 0.769},
        "ewma20": {"5": 1.149, "10": 1.161, "20": 1.181},
        "yang_zhang20": {"5": 1.100, "10": 1.109, "20": 1.124},
        "robust_ewma20": {"5": 1.159, "10": 1.171, "20": 1.190},
    },
    # R2: 5% and 95% quantiles of the 10-bar return from the next open divided by
    # (0.757 * ATR14/close * sqrt(10)); development values -1.56 / +1.48 (DEV), -1.51 / +1.46 (CTX)
    "q05_range": (-1.76, -1.36),
    "q95_range": (1.28, 1.68),
    # R3: largest allowed absolute difference, in probability, between the validation and the
    # development stop-out tables over the 18 cells k in {1,1.5,2,2.5,3,4} x h in {5,10,20}
    "stop_table_tolerance": 0.04,
    # R4: P(gap worse than -2 ATR) on earnings reaction bars divided by the same on ordinary nights
    "earnings_gap_ratio_min": 20.0,
    # R6: SPY daily volatility below its 200-day average divided by volatility above it
    "regime_vol_ratio_min": 1.5,
}

# R3 reference: share of random entries stopped within h bars, stop k x ATR(14), DEV 2011-2018
DEV_STOP_TABLE = {
    "k1.0_h5": 0.452, "k1.0_h10": 0.594, "k1.0_h20": 0.702,
    "k1.5_h5": 0.285, "k1.5_h10": 0.439, "k1.5_h20": 0.574,
    "k2.0_h5": 0.175, "k2.0_h10": 0.318, "k2.0_h20": 0.467,
    "k2.5_h5": 0.106, "k2.5_h10": 0.226, "k2.5_h20": 0.375,
    "k3.0_h5": 0.065, "k3.0_h10": 0.160, "k3.0_h20": 0.298,
    "k4.0_h5": 0.027, "k4.0_h10": 0.082, "k4.0_h20": 0.185,
}
