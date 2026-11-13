"""G70 - How far does a whole book of positions move? Calibration of a portfolio range band.

For a book of N long positions with weights w (fractions of equity), the script "SL Portfolio Desk"
predicts the scale of the book's move over h daily bars as

    s_p = sqrt( sum_ij  w_i u_i  rho_ij  w_j u_j ),     u_i = ATR14_i / close_i * sqrt(h),

with rho the correlation of the last 60 daily log returns, and shows the band  [q05, q95] * s_p.
Here the quantiles of  y = (book return over h bars) / s_p  are measured on random books: N names
drawn from the universe on a date, sized as SL Risk Desk sizes them (weight proportional to
1 / ATR%, capped), or with equal weights.

    python -m research.experiments.g70_portfolio_band calibrate    # 2011-01 .. 2022-12 only; writes the constants
    python -m research.experiments.g70_portfolio_band check        # 2023-01 .. 2026-11, after the constants are committed

Status of whatever comes out: the lockbox had already been opened for the eight frozen claims
(entry 7 of the research log), so this is not a lockbox test in the protocol's sense. The
constants are frozen and committed before the 2023-26 check, and the check is run once.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MODE = sys.argv[1] if len(sys.argv) > 1 else "calibrate"
os.environ["SWINGLAB_REGISTRY_TAG"] = "g70"
os.environ.setdefault("SWINGLAB_VAL_TOKEN", "PRE-REGISTERED")       # calibration use of validation data, declared in the log

import numpy as np

from research.swinglab.registry import log_trial
from research.swinglab.study import Study

NS = (1, 2, 3, 5, 8, 10)
HS = (5, 10, 20)
QS = (0.05, 0.25, 0.50, 0.75, 0.95)
WIN = 60
OUT = Path(__file__).resolve().parents[1] / "results" / "g70_portfolio_band.json"
CONST = Path(__file__).resolve().parents[1] / "confirm" / "portfolio_band_constants.json"


def sample(S, seed: int, step: int = 3, books: int = 40, scheme: str = "risk") -> dict:
    """y for random books; returns {(N, h): array}."""
    rng = np.random.default_rng(seed)
    c = S.P.cf
    ret = S.P.ret
    atr = S.atr(14)
    with np.errstate(divide="ignore", invalid="ignore"):
        atrp = atr / c
    T = c.shape[0]
    rows = np.flatnonzero(S.rows)
    out = {(n, h): [] for n in NS for h in HS}
    for t in rows[::step]:
        if t < WIN + 1 or t + max(HS) > S._last_row:
            continue
        block = ret[t - WIN + 1:t + 1]                                   # the last 60 daily log returns, known at the close of t
        pool = np.flatnonzero(S.uni[t] & np.isfinite(block).all(axis=0) & np.isfinite(atrp[t]) & (atrp[t] > 0))
        if len(pool) < 50:
            continue
        C = np.corrcoef(block[:, pool], rowvar=False)
        if not np.isfinite(C).all():
            continue
        a = atrp[t, pool]
        fut = {h: c[t + h, pool] / c[t, pool] - 1.0 for h in HS}
        order = rng.random((books, len(pool))).argsort(axis=1)
        for n in NS:
            idx = order[:, :n]
            w = np.minimum(0.0025 / a[idx], 0.20) if scheme == "risk" else np.full(idx.shape, 1.0 / n)
            Cs = C[idx[:, :, None], idx[:, None, :]]
            for h in HS:
                wu = w * a[idx] * np.sqrt(h)
                s2 = np.einsum("pi,pij,pj->p", wu, Cs, wu)
                rp = (w * fut[h][idx]).sum(axis=1)
                ok = np.isfinite(rp) & (s2 > 0)
                out[(n, h)].append(rp[ok] / np.sqrt(s2[ok]))
    return {k: np.concatenate(v) if v else np.array([]) for k, v in out.items()}


def show(tag: str, ys: dict) -> dict:
    res = {}
    print(f"\n{tag}:  quantiles 5 25 50 75 95 of  book return / s_p")
    for h in HS:
        for n in NS:
            y = ys[(n, h)]
            q = [float(np.quantile(y, x)) for x in QS]
            res[f"N{n}_h{h}"] = {"q": q, "n": int(len(y))}
            print(f"  h={h:<2d} N={n:<2d} " + " ".join(f"{v:+.3f}" for v in q) + f"   books={len(y)}")
    return res


def calibrate() -> None:
    res, pooled = {}, {}
    for smp, seed in (("DEV", 70), ("VAL", 71)):
        S = Study(smp)
        for scheme in ("risk", "equal"):
            ys = sample(S, seed, scheme=scheme)
            res[f"{smp}_{scheme}"] = show(f"{smp}, {scheme} weights", ys)
            if scheme == "risk":
                for k, v in ys.items():
                    pooled.setdefault(k, []).append(v)
        log_trial("G70", "G70_portfolio_band", "book return / s_p, random books", smp, "calibration", 0.0, note="calibration of a displayed constant")
        del S
    pooled = {k: np.concatenate(v) for k, v in pooled.items()}
    res["pooled_risk"] = show("DEV + VAL pooled, risk weights", pooled)
    # books of 3 or more, pooled over N: the candidate constants per horizon
    cand = {}
    print("\nBooks of 3 to 10 positions pooled, by horizon (candidate constants):")
    for h in HS:
        y = np.concatenate([pooled[(n, h)] for n in NS if n >= 3])
        cand[h] = [float(np.quantile(y, x)) for x in QS]
        print(f"  h={h:<2d} " + " ".join(f"{v:+.3f}" for v in cand[h]))
    res["candidate_N3plus"] = cand
    OUT.write_text(json.dumps(res, indent=1))


def check() -> None:
    os.environ["SWINGLAB_OPEN_LOCKBOX"] = "I-HAVE-FROZEN-THE-RULES"
    from research.swinglab.data import open_lockbox
    K = json.loads(CONST.read_text())
    panel = open_lockbox("G70: one check of the portfolio band constants committed beforehand (not a protocol lockbox test)", ["portfolio band, constants in research/confirm/portfolio_band_constants.json"])
    S = Study("LOCKBOX", panel=panel)
    res = {"constants": K, "coverage": {}}
    print("2023-01 .. 2026-11, constants frozen beforehand:   90% band / 50% band coverage,  below the 5% line / above the 95% line")
    for scheme in ("risk", "equal"):
        ys = sample(S, 72, scheme=scheme)
        for h in HS:
            q05, q25, q75, q95 = K["bands"][str(h)]
            for n in NS:
                if n < K["min_positions"]:
                    continue
                y = ys[(n, h)]
                c90, c50 = float(np.mean((y >= q05) & (y <= q95))), float(np.mean((y >= q25) & (y <= q75)))
                res["coverage"][f"{scheme}_N{n}_h{h}"] = {"c90": c90, "c50": c50, "below": float(np.mean(y < q05)), "above": float(np.mean(y > q95)), "n": int(len(y))}
                print(f"  {scheme:<5s} h={h:<2d} N={n:<2d}  {100 * c90:5.1f}% / {100 * c50:5.1f}%    {100 * np.mean(y < q05):4.1f}% / {100 * np.mean(y > q95):4.1f}%   books={len(y)}")
    allr = [v for k, v in res["coverage"].items() if k.startswith("risk")]
    res["pass"] = bool(all(K["criterion"]["c90"][0] <= v["c90"] <= K["criterion"]["c90"][1] and K["criterion"]["c50"][0] <= v["c50"] <= K["criterion"]["c50"][1] for v in allr))
    print("criterion", K["criterion"], "->", "PASS" if res["pass"] else "FAIL")
    log_trial("G70", "G70_portfolio_band", "coverage of the frozen portfolio band", "LOCKBOX", "pass", float(res["pass"]), note="after the lockbox was opened; constants committed beforehand")
    OUT.with_name("g70_portfolio_band_check.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    calibrate() if MODE == "calibrate" else check()
