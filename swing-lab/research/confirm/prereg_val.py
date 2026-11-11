"""Frozen inputs of the validation run. Written before the run; see docs/03_preregistration_val.md.

Nothing in this file may change after research/results/val_confirmation.json exists.
Revised 12 Nov 2026 after the independent audits (docs/_raw/audit_code.md, audit_stats.md): the
confirmatory family was cut from fourteen to seven, the event-weighted estimate became part of the
verdict, margins were added to the risk criteria, and every development reference number was
recomputed on the market-open calendar.
"""

# ---------------------------------------------------------------- Part D: confirmatory family (Holm at 5%)
# Definitions, horizons and predicted signs live in swinglab/candidates.py (SPEC).
DIRECTIONAL = [
    "E1_episodic_pivot",          # h 10, +
    "A1_shock_down_on_volume",    # h 20, -
    "A2_bounce_in_downtrend",     # h 10, -
    "A3_unfilled_gap_up",         # h 5,  -
    "A4_gap_down_weak_close",     # h 20, -
    "A5_tug_of_war",              # h 5,  -
    "A8_pop_fade",                # h 5,  -
]
AVOID_FAMILY = ["A1_shock_down_on_volume", "A2_bounce_in_downtrend", "A3_unfilled_gap_up",
                "A4_gap_down_weak_close", "A5_tug_of_war", "A8_pop_fade"]
# Reported beside the family, without a verdict word: bars 2-5 for the two one-session suspects
DELAYED_ENDPOINT = ["A3_unfilled_gap_up", "A5_tug_of_war"]
# Diagnostics of survivor bias, outside the family, no verdict word
DIAGNOSTICS = ["A9_stretched_down", "E3_negative_skew"]
# Dropped before the look (reasons in the pre-registration): A6, A7, A10, A11, E2

HOLM_ALPHA = 0.05
EVENT_WEIGHTED_P_MAX = 0.10          # one-sided, uncorrected, predicted sign required
MATERIAL_AVOID_BP = -20.0            # event-weighted effect inside a trend-following selection
MATERIAL_ENTER_NET_BP = 20.0         # event-weighted, net of protocol costs
BOOTSTRAP_DRAWS = 1000
BOOTSTRAP_SEED = 20261112

# ---------------------------------------------------------------- Part R: risk engine
RISK_CRITERIA = {
    # QLIKE-optimal constant per estimate and horizon, fitted on CTX (1998-2010) only
    "scale_from_ctx": {
        "atr14/close": {"5": 0.750, "10": 0.757, "20": 0.769},
        "ewma20": {"5": 1.149, "10": 1.161, "20": 1.181},
        "yang_zhang20": {"5": 1.100, "10": 1.109, "20": 1.124},
        "robust_ewma20": {"5": 1.159, "10": 1.171, "20": 1.190},
    },
    # R1 forecast ranking at h = 10
    "qlike_t_min": 2.33,                 # Newey-West t (20 lags) of the daily mean loss difference, each competitor
    "qlike_rel_improvement_min": 0.05,   # ATR's QLIKE at least 5% below each competitor (development: 17% and 14%)
    "qlike_blocks_min": 3,               # same sign in at least 3 of the 4 blocks
    "blocks": [("2018-07-02", "2019-12-31"), ("2020-01-01", "2020-12-31"), ("2021-01-01", "2021-12-31"), ("2022-01-01", "2022-12-30")],
    # R1b the constant refitted on validation at h = 10
    "scale_range": (0.68, 0.83),
    # R2 range calibration at h = 10 (development: -1.56 / +1.48 in DEV, -1.51 / +1.46 in CTX)
    "q05_range": (-1.76, -1.36),
    "q95_range": (1.28, 1.68),
    "band": (-1.56, 1.48),
    "coverage_pooled": (0.87, 0.93),
    "coverage_tercile": (0.84, 0.94),
    "coverage_block": (0.85, 0.95),
    "coverage_blocks_min": 3,
    # R3 stop-out table
    "stop_table_tolerance": 0.04,
    "gap_through_share_range": (0.08, 0.20),      # k = 2, h = 10
    "tail_1p5R_max": 2 * 0.0096,                   # twice the development share of trades worse than -1.5R (k = 2, h = 10)
    # R4 earnings gap risk
    "earnings_gap_ratio_min": 20.0,
    # R5 exits: one-sided test of the difference in net bp per bar, month-block bootstrap
    "exit_p_max": 0.05,
    # R6 regime
    "regime_vol_ratio_min": 1.5,
}

# R3 reference: share of random entries stopped within h bars, stop k x ATR(14), DEV 2011-2018,
# market-open calendar (research/results/g12_risk_engine.json)
DEV_STOP_TABLE = {
    "k1.0_h5": 0.454, "k1.0_h10": 0.594, "k1.0_h20": 0.706,
    "k1.5_h5": 0.283, "k1.5_h10": 0.439, "k1.5_h20": 0.577,
    "k2.0_h5": 0.173, "k2.0_h10": 0.315, "k2.0_h20": 0.468,
    "k2.5_h5": 0.105, "k2.5_h10": 0.226, "k2.5_h20": 0.375,
    "k3.0_h5": 0.065, "k3.0_h10": 0.160, "k3.0_h20": 0.298,
    "k4.0_h5": 0.027, "k4.0_h10": 0.080, "k4.0_h20": 0.186,
}
