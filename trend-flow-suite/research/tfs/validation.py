"""Statistics that keep a backtest search honest.

Why this module exists: selecting the best of many backtests inflates its apparent
performance. These functions measure and correct for that selection effect.

References
----------
- Bailey & Lopez de Prado (2012), "The Sharpe Ratio Efficient Frontier", J. of Risk 15(2)  -> PSR
- Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio", J. Portfolio Mgmt 40(5)     -> DSR, E[max SR]
- Bailey, Borwein, Lopez de Prado & Zhu (2017), "The Probability of Backtest Overfitting",
  J. Computational Finance 20(4)                                                          -> PBO via CSCV
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from scipy.stats import kurtosis, norm, skew

EULER_GAMMA = 0.5772156649015329


def expected_max_sr(n_trials: float, sr_std: float = 1.0) -> float:
    """Expected maximum of `n_trials` independent N(0, sr_std^2) draws.

    With sr_std = 1 this is the expected best z-score among n pure-noise strategies
    ("False Strategy Theorem" approximation, Bailey & Lopez de Prado 2014).
    Divide by sqrt(years) to get the expected best *annualised* Sharpe from luck alone.
    """
    if n_trials <= 1:
        return 0.0
    n = float(n_trials)
    return sr_std * ((1.0 - EULER_GAMMA) * norm.ppf(1.0 - 1.0 / n)
                     + EULER_GAMMA * norm.ppf(1.0 - 1.0 / (n * math.e)))


def sharpe(returns: np.ndarray, periods_per_year: int = 252) -> np.ndarray:
    """Annualised Sharpe ratio per column (zero risk-free rate). Columns with zero variance -> 0."""
    r = np.asarray(returns, dtype=float)
    mu = r.mean(axis=0)
    sd = r.std(axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(sd > 0, mu / sd * math.sqrt(periods_per_year), 0.0)
    return out


def psr(sr_hat: float, sr_star: float, n_obs: int, skewness: float, kurt: float) -> float:
    """Probabilistic Sharpe Ratio: P(true SR > sr_star). Sharpe ratios in *per-period* units;
    `kurt` is the non-excess (Pearson) kurtosis."""
    var = 1.0 - skewness * sr_hat + (kurt - 1.0) / 4.0 * sr_hat ** 2
    return float(norm.cdf((sr_hat - sr_star) * math.sqrt(n_obs - 1) / math.sqrt(max(var, 1e-12))))


def deflated_sharpe(selected_returns: np.ndarray, trial_srs: np.ndarray, n_trials: float) -> dict:
    """Deflated Sharpe Ratio of the strategy picked from a search.

    selected_returns : per-period returns of the selected strategy
    trial_srs        : per-period Sharpe ratios of ALL strategies tried (dispersion of the search)
    n_trials         : number of independent trials (use an effective count for correlated trials)
    Returns the DSR (probability that the true Sharpe > 0 after accounting for selection).
    """
    r = np.asarray(selected_returns, dtype=float)
    sr_hat = r.mean() / r.std(ddof=1)
    sr_star = expected_max_sr(n_trials, float(np.std(trial_srs, ddof=1)))
    return {
        "sr_hat_per_period": float(sr_hat),
        "sr_star_per_period": float(sr_star),
        "dsr": psr(sr_hat, sr_star, len(r), float(skew(r)), float(kurtosis(r, fisher=False))),
        "psr_vs_zero": psr(sr_hat, 0.0, len(r), float(skew(r)), float(kurtosis(r, fisher=False))),
    }


def effective_trials(returns: np.ndarray) -> float:
    """Effective number of independent strategies: participation ratio of the eigenvalues of
    the correlation matrix of strategy returns (T x N). Equals N for uncorrelated strategies,
    1 for perfectly correlated ones. A heuristic; clustering-based counts are an alternative."""
    r = np.asarray(returns, dtype=float)
    sd = r.std(axis=0)
    keep = sd > 0
    z = (r[:, keep] - r[:, keep].mean(axis=0)) / sd[keep]
    s = np.linalg.svd(z, compute_uv=False)
    lam = s ** 2
    return float(lam.sum() ** 2 / (lam ** 2).sum())


def pbo_cscv(returns: np.ndarray, n_blocks: int = 16, periods_per_year: int = 252) -> dict:
    """Probability of Backtest Overfitting via Combinatorially Symmetric Cross-Validation.

    returns : T x N matrix of per-period returns of N strategy variants over the same dates.
    The sample is cut into `n_blocks` contiguous blocks. For every way of choosing half of the
    blocks as in-sample (IS) and the rest as out-of-sample (OOS), the IS-best variant is picked
    and its OOS rank recorded. PBO = share of splits where the IS winner lands in the bottom half
    OOS. PBO ~ 0.5 means the selection process is no better than picking at random.
    """
    r = np.asarray(returns, dtype=float)
    t, n = r.shape
    t -= t % n_blocks
    r = r[:t]
    blocks = np.array_split(np.arange(t), n_blocks)
    s1 = np.stack([r[b].sum(axis=0) for b in blocks])
    s2 = np.stack([(r[b] ** 2).sum(axis=0) for b in blocks])
    cnt = np.array([len(b) for b in blocks], dtype=float)
    ann = math.sqrt(periods_per_year)

    def block_sr(idx):
        c = cnt[idx].sum()
        m = s1[idx].sum(axis=0) / c
        v = s2[idx].sum(axis=0) / c - m ** 2
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(v > 1e-18, m / np.sqrt(v), 0.0) * ann

    allb = np.arange(n_blocks)
    logits, is_sel, oos_sel, oos_median = [], [], [], []
    for combo in itertools.combinations(range(n_blocks), n_blocks // 2):
        ci = np.array(combo)
        co = np.setdiff1d(allb, ci)
        sr_is, sr_oos = block_sr(ci), block_sr(co)
        k = int(np.argmax(sr_is))
        rank = int((sr_oos < sr_oos[k]).sum()) + 1          # 1 = worst ... n = best
        w = rank / (n + 1.0)
        logits.append(math.log(w / (1.0 - w)))
        is_sel.append(sr_is[k])
        oos_sel.append(sr_oos[k])
        oos_median.append(float(np.median(sr_oos)))
    logits, is_sel, oos_sel = map(np.asarray, (logits, is_sel, oos_sel))
    slope = float(np.polyfit(is_sel, oos_sel, 1)[0]) if len(is_sel) > 2 else float("nan")
    return {
        "n_splits": int(len(logits)),
        "pbo": float(np.mean(logits <= 0)),
        "median_is_sr_of_winner": float(np.median(is_sel)),
        "median_oos_sr_of_winner": float(np.median(oos_sel)),
        "median_oos_sr_all_variants": float(np.median(oos_median)),
        "prob_oos_loss_of_winner": float(np.mean(oos_sel < 0)),
        "degradation_slope_oos_on_is": slope,
    }
