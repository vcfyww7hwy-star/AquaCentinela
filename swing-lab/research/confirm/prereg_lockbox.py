"""Frozen inputs of the single lockbox run. See docs/05_preregistration_lockbox.md.

Nothing in this file may change after registry/lockbox.json records an opening.

The constants under PRODUCT are the numbers the Pine scripts display. They were calibrated on
development and validation data (research/experiments/g50_calibration.py) and are tested here
exactly as displayed.
"""

# ---------------------------------------------------------------- the list (protocol: at most ten)
PRIMARY = [
    "L1 range calibration (R2 unchanged, and the displayed bands)",
    "L2 stop-out odds (R3 unchanged, and the displayed table)",
    "L3 earnings gap risk (R4 unchanged, and the displayed odds)",
    "L4 market state as a risk state (R6 unchanged)",
    "L5 E1: gap up >= 3 sigma on volume >= 3x, close in the top third; 10 bars; +",
]
SECONDARY = [      # failed their validation criterion; can earn "suggestive" at most
    "S1 PE1: earnings reaction >= +3 sigma; 20 bars; +",
    "S2 R1: ATR forecast against EWMA(20) and Yang-Zhang(20)",
    "S3 R5: exits on random entries (no stop, 2-ATR stop, 3-ATR stop, exit under the 20-day average)",
]

BLOCKS = [("2023-01-03", "2023-12-29"), ("2024-01-02", "2024-12-31"), ("2025-01-02", "2025-12-31"), ("2026-01-02", "2026-11-09")]
POSTCUTOFF = ("2026-07-01", "2026-11-09")

# ---------------------------------------------------------------- L5 / S1 directional criteria
E1_P_MAX = 0.05            # day-weighted, one-sided, Student's t (df = floor(days with a spread / 2h) - 1)
EW_P_MAX = 0.10            # event-weighted, one-sided, predicted sign required
PE1_H = 20

# ---------------------------------------------------------------- PRODUCT constants (displayed by the scripts)
# y_h = ln(close[t+h] / close[t]) / (ATR14[t] / close[t] * sqrt(h)); quantiles 5%, 25%, 75%, 95%
PRODUCT_BANDS = {
    5:  (-1.23, -0.40, 0.45, 1.10),
    10: (-1.26, -0.40, 0.47, 1.10),
    20: (-1.28, -0.40, 0.49, 1.11),
}
BAND90_COVERAGE = (0.87, 0.93)      # required at each of the three horizons
BAND50_COVERAGE = (0.46, 0.54)

# share of entries at the next open stopped within h bars by a stop k x ATR(14) below the entry
# (mean of the development and validation tables)
PRODUCT_STOP_TABLE = {
    "k1.0_h5": 0.458, "k1.0_h10": 0.599, "k1.0_h20": 0.710,
    "k1.5_h5": 0.288, "k1.5_h10": 0.445, "k1.5_h20": 0.584,
    "k2.0_h5": 0.176, "k2.0_h10": 0.324, "k2.0_h20": 0.475,
    "k2.5_h5": 0.107, "k2.5_h10": 0.233, "k2.5_h20": 0.381,
    "k3.0_h5": 0.066, "k3.0_h10": 0.165, "k3.0_h20": 0.303,
    "k4.0_h5": 0.028, "k4.0_h10": 0.083, "k4.0_h20": 0.188,
}
PRODUCT_STOP_TOLERANCE = 0.04

# opening gap on the earnings reaction bar, in units of the previous bar's ATR(14)
PRODUCT_EARNINGS = {"p_gap_lt_-1atr": 0.17, "p_gap_lt_-2atr": 0.075, "p_gap_lt_-3atr": 0.035}
EARNINGS_RANGES = {"p_gap_lt_-1atr": (0.13, 0.21), "p_gap_lt_-2atr": (0.05, 0.105)}
