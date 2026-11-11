"""AUDIT (statistical skeptic) - is the evidence for the 14 frozen candidates what it is said to be?

Development data only (DEV 2011-01..2018-06, CTX 1998..2010). Never builds Study("VAL"), never
reads the lockbox, never touches an outcome after 2018-06-29 (all outcomes come from Study.fwd,
which blanks them).

    python -m research.experiments.audit_stats registry     # part 2: what the search looked like
    python -m research.experiments.audit_stats DEV          # parts 1 and 4 on DEV
    python -m research.experiments.audit_stats CTX          # parts 1 and 4 on CTX
    python -m research.experiments.audit_stats tables       # print the merged tables

One Study at a time. Results: research/results/audit_stats_{registry,DEV,CTX}.json.
Registry tag "audits", family "AUDIT_stats".

Part 1, per candidate at its own horizon h:
    (a) day-weighted   mean over days of (signal mean - control mean), Newey-West lags 2h   [the reported one]
    (b) event-weighted sum_t n_t d_t / sum_t n_t, date-clustered through the daily sums (as Study._ts,
                       but against the same-day control); also with the delta-method standard error
    (c) median daily spread and share of days with the predicted sign
    (d) non-overlapping: only every h-th sample day is kept (all h offsets; median t reported)
    (e) circular block bootstrap over calendar months (1,000 draws; block = max(2, ceil(2h/21)) months)
    plus a horizon profile (1, 3, 5, 10, 20, 60 bars), sub-period halves, and the overlap between candidates.
Part 4:
    avoid states inside a plain trend-following selection (close > SMA200 and close >= 0.85 * highest(high, 252));
    enter states net of costs and signals per month.
"""
from __future__ import annotations

import gc
import glob
import json
import math
import os
import sys
from pathlib import Path

os.environ["SWINGLAB_REGISTRY_TAG"] = "audits"

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "research" / "results"
HPROF = (1, 3, 5, 10, 20, 60)
NBOOT = 1000


# ============================================================================== helpers
def nw_se(x: np.ndarray, lags: int) -> float:
    """Newey-West (Bartlett) standard error of the mean of x (same formula as engine.nw_mean)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    e = x - x.mean()
    var = (e @ e) / n
    for k in range(1, min(lags, n - 1) + 1):
        var += 2.0 * (1.0 - k / (lags + 1.0)) * (e[k:] @ e[:-k]) / n
    return float(np.sqrt(max(var, 1e-300) / n))


def phi_bar(z: float) -> float:
    """P(Z >= z) for a standard normal."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def rnd(x, nd=2):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


# ============================================================================== parts 1 and 4
def daily_spread(E, out, sig, ctl):
    ms, ns = E.day_means(out, sig, 1)
    mc, _ = E.day_means(out, ctl, 20)
    return ms - mc, ns, mc, ms


def stats(E, S, d, ns, mc, h, sgn, months_idx, n_months, rng, full=True):
    """All the versions of the statistic for one daily spread series."""
    rows = S.rows
    res = {}
    m, t, n = E.nw_mean(d[rows], 2 * h)
    res["a_bp"], res["a_t"], res["a_days"] = rnd(1e4 * m, 1), rnd(t), int(n)
    ok = rows & np.isfinite(mc)
    nn = np.where(ok & np.isfinite(d), ns, 0).astype(float)
    with np.errstate(invalid="ignore"):
        x = np.where(nn > 0, nn * d, 0.0)
    xo, no = x[ok], nn[ok]
    res["events"] = int(no.sum())
    if no.sum() < 50 or n < 20:
        return res
    theta = xo.sum() / no.sum()
    _, t_ts, _ = E.nw_mean(xo / no.mean(), 2 * h)                       # as Study._ts
    se_delta = nw_se((xo - theta * no) / no.mean(), 2 * h)              # ratio estimator, delta method
    res["b_bp"], res["b_t"], res["b_t_delta"] = rnd(1e4 * theta, 1), rnd(t_ts), rnd(theta / se_delta)
    if not full:
        return res
    dd = d[rows]
    fin = np.isfinite(dd)
    res["c_median_bp"] = rnd(1e4 * np.median(dd[fin]), 1)
    res["c_share_right"] = rnd(np.mean(np.sign(dd[fin]) == sgn), 3)
    # events are concentrated on few days?
    srt = np.sort(no[no > 0])[::-1]
    k = max(1, int(round(0.05 * len(srt))))
    res["share_events_top5pct_days"] = rnd(srt[:k].sum() / srt.sum(), 3)
    res["median_events_per_signal_day"] = rnd(np.median(srt), 1)
    # (d) non-overlapping: one sample day in h
    r_idx = np.flatnonzero(rows)
    tt, mm = [], []
    for off in range(h):
        v = d[r_idx[off::h]]
        v = v[np.isfinite(v)]
        if len(v) >= 12 and v.std(ddof=1) > 0:
            mm.append(v.mean())
            tt.append(v.mean() / (v.std(ddof=1) / np.sqrt(len(v))))
    if tt:
        tt, mm = np.array(tt), np.array(mm)
        res["d_bp_median"] = rnd(1e4 * np.median(mm), 1)
        res["d_t_median"], res["d_t_min"], res["d_t_max"] = rnd(np.median(tt)), rnd(tt.min()), rnd(tt.max())
        res["d_share_offsets_right"] = rnd(np.mean(np.sign(mm) == sgn), 2)
        res["d_n_per_offset"] = int(round(fin.sum() / h))
    # (e) circular block bootstrap over calendar months
    mi = months_idx[rows]
    sum_d = np.bincount(mi[fin], weights=dd[fin], minlength=n_months)
    cnt_d = np.bincount(mi[fin], minlength=n_months).astype(float)
    okr = ok[rows]
    sum_x = np.bincount(mi[okr], weights=x[rows][okr], minlength=n_months)
    sum_n = np.bincount(mi[okr], weights=nn[rows][okr], minlength=n_months)
    b = max(2, int(math.ceil(2 * h / 21)))
    k = int(math.ceil(n_months / b))
    starts = rng.integers(0, n_months, size=(NBOOT, k))
    idx = ((starts[:, :, None] + np.arange(b)[None, None, :]) % n_months).reshape(NBOOT, k * b)[:, :n_months]
    with np.errstate(divide="ignore", invalid="ignore"):
        ba = sum_d[idx].sum(1) / cnt_d[idx].sum(1)
        bb = sum_x[idx].sum(1) / sum_n[idx].sum(1)
    for lab, bs in (("e_a", ba), ("e_b", bb)):
        bs = bs[np.isfinite(bs)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        res[f"{lab}_ci_bp"] = [rnd(1e4 * lo, 1), rnd(1e4 * hi, 1)]
        res[f"{lab}_p_wrong_sign"] = rnd(np.mean(sgn * bs <= 0), 4)
        res[f"{lab}_boot_se_bp"] = rnd(1e4 * bs.std(ddof=1), 1)
    res["e_block_months"] = b
    return res


def run_sample(smp: str) -> None:
    from research.swinglab import candidates as C
    from research.swinglab import engine as E
    from research.swinglab.registry import log_trial
    from research.swinglab.study import Study

    S = Study(smp)
    F = C.Feat(S)
    rows = S.rows
    months = S.dates.astype("datetime64[M]").astype(int)
    um = np.unique(months[rows])
    months_idx = np.searchsorted(um, months).clip(0, len(um) - 1)
    n_months = len(um)
    T, N = S.uni.shape
    cut = np.datetime64("2015-01-01") if smp == "DEV" else np.datetime64("2004-07-01")
    early, late = rows & (S.dates < cut), rows & (S.dates >= cut)
    # how survivor-biased is the sample in fact: securities ever in the universe whose last bar is inside the sample
    ever = S.uni.any(axis=0)
    last_row = int(np.flatnonzero(rows)[-1])
    meta = {"sample": smp, "T": int(T), "N": int(N), "sample_days": int(rows.sum()), "months": int(n_months),
            "universe_stock_days": int(S.uni.sum()), "securities_ever_in_universe": int(ever.sum()),
            "of_which_stop_trading_inside_sample": int((ever & (S.P.last < last_row - 3)).sum()),
            "median_names_per_day": float(np.median(S.uni[rows].sum(axis=1)))}
    print(json.dumps(meta))
    tf = S.uni & (F.c > F.s200) & (F.prox >= 0.85)             # plain trend-following selection
    meta["tf_share_of_universe"] = rnd(tf.sum() / S.uni.sum(), 3)
    # protocol section 5 round-trip cost by liquidity (bp): 10 / 20 / 50
    rt_cost = np.where(S.adv60 >= 50e6, 10.0, np.where(S.adv60 >= 20e6, 20.0, 50.0))
    out_all = {"meta": meta, "cand": {}}
    sigs = {}
    for name, spec in C.SPEC.items():
        rng = np.random.default_rng(20261111)
        sig, ctrl = spec["fn"](F)
        h, sgn = spec["h"], spec["sign"]
        sig = sig & S.uni
        ctl = S.uni if ctrl is None else (ctrl & S.uni)
        sigs[name] = sig
        d, ns, mc, ms = daily_spread(E, S.fwd(h), sig, ctl)
        r = stats(E, S, d, ns, mc, h, sgn, months_idx, n_months, rng)
        r.update({"h": h, "sign": sgn, "use": spec["use"], "own_control": ctrl is not None,
                  "events_per_month": rnd(sig.sum() / n_months, 1),
                  "share_of_universe_days": rnd(sig.sum() / S.uni.sum(), 5),
                  "signal_days_share": rnd(np.mean(sig[rows].any(axis=1)), 3)})
        for lab, key in (("day-weighted", "a"), ("event-weighted", "b")):
            log_trial("AUDIT", "AUDIT_stats", f"{name} {lab} h={h}", smp, "xs_bp", r.get(f"{key}_bp") or float("nan"),
                      tstat=r.get(f"{key}_t"), n=r.get("events"), params={"h": h})
        # sub-period halves (day-weighted and event-weighted)
        for lab, rr in (("early", early), ("late", late)):
            S2rows = S.rows
            S.rows = rr
            q = stats(E, S, d, ns, mc, h, sgn, months_idx, n_months, rng, full=False)
            S.rows = S2rows
            r[lab] = {k: q.get(k) for k in ("a_bp", "a_t", "b_bp", "b_t", "events")}
            log_trial("AUDIT", "AUDIT_stats", f"{name} {lab} half, day-weighted h={h}", smp, "xs_bp", q.get("a_bp") or float("nan"),
                      tstat=q.get("a_t"), n=q.get("events"), params={"h": h})
        # horizon profile
        prof = {}
        for hh in HPROF:
            dh, nsh, mch, _ = daily_spread(E, S.fwd(hh), sig, ctl)
            q = stats(E, S, dh, nsh, mch, hh, sgn, months_idx, n_months, rng, full=False)
            prof[hh] = {k: q.get(k) for k in ("a_bp", "a_t", "b_bp", "b_t")}
            if hh != h:
                log_trial("AUDIT", "AUDIT_stats", f"{name} profile day-weighted h={hh}", smp, "xs_bp", q.get("a_bp") or float("nan"),
                          tstat=q.get("a_t"), n=q.get("events"), params={"h": hh})
        r["profile"] = prof
        # ---- part 4
        if spec["use"].startswith(("avoid", "exit")):
            both = sig & tf
            e4 = {"share_of_tf_days_in_state": rnd(both.sum() / max(tf.sum(), 1), 5),
                  "share_of_state_events_in_tf": rnd(both.sum() / max(sig.sum(), 1), 4), "events_in_tf": int(both.sum())}
            if both.sum() >= 300:
                d4, ns4, mc4, _ = daily_spread(E, S.fwd(h), both, tf)
                q = stats(E, S, d4, ns4, mc4, h, sgn, months_idx, n_months, rng, full=False)
                e4.update({k: q.get(k) for k in ("a_bp", "a_t", "b_bp", "b_t", "b_t_delta")})
                # what avoiding the state is worth to the trend follower per h-bar holding period, in bp of his book
                if q.get("b_bp") is not None:
                    e4["gain_bp_per_tf_position"] = rnd(-e4["share_of_tf_days_in_state"] * q["b_bp"], 2)
                log_trial("AUDIT", "AUDIT_stats", f"{name} inside trend selection vs trend selection h={h}", smp, "xs_bp",
                          q.get("a_bp") or float("nan"), tstat=q.get("a_t"), n=int(both.sum()), params={"h": h})
            r["in_trend_selection"] = e4
        else:
            out = S.fwd(h)
            v = out[sig]
            okv = np.isfinite(v)
            cost = rt_cost[sig][okv]
            e4 = {"raw_bp_event_weighted": rnd(1e4 * v[okv].mean(), 1), "hit": rnd(np.mean(v[okv] > 0), 3),
                  "mean_protocol_round_trip_bp": rnd(cost.mean(), 1), "share_events_adv_below_50M": rnd(np.mean(cost > 10), 3)}
            # against the whole universe as well (E2 has its own control)
            du, nsu, mcu, _ = daily_spread(E, S.fwd(h), sig, S.uni)
            q = stats(E, S, du, nsu, mcu, h, sgn, months_idx, n_months, rng, full=False)
            e4["vs_universe"] = {k: q.get(k) for k in ("a_bp", "a_t", "b_bp", "b_t")}
            for lab, key in (("day", "a"), ("event", "b")):
                if r.get(f"{key}_bp") is not None and r.get(f"{key}_t"):
                    se = r[f"{key}_bp"] / r[f"{key}_t"]
                    e4[f"net10_{lab}_bp"] = rnd(r[f"{key}_bp"] - 10, 1)
                    e4[f"net10_{lab}_t"] = rnd((r[f"{key}_bp"] - 10) / se)
                    e4[f"net20_{lab}_bp"] = rnd(r[f"{key}_bp"] - 20, 1)
            if r.get("b_bp") is not None:
                e4["net_protocol_cost_event_bp"] = rnd(r["b_bp"] - cost.mean(), 1)
            r["as_entry"] = e4
        out_all["cand"][name] = r
        print(name, json.dumps({k: v for k, v in r.items() if k not in ("profile", "early", "late")}), flush=True)
    # overlap between candidates: share of row-candidate's events that are also column-candidate's events
    names = list(sigs)
    ov = {}
    for a in names:
        na = max(int(sigs[a].sum()), 1)
        ov[a] = {b: rnd((sigs[a] & sigs[b]).sum() / na, 3) for b in names if b != a}
    out_all["overlap"] = ov
    (RES / f"audit_stats_{smp}.json").write_text(json.dumps(out_all, indent=1))
    del S, F
    gc.collect()


# ============================================================================== part 2
def run_registry() -> None:
    import re
    from collections import Counter, defaultdict
    files = sorted(glob.glob(str(ROOT / "registry" / "trials*.jsonl")))
    skip = ("trials_audits", "trials_dryrun", "trials_audit")
    fam_n, fam_xs, part_n = Counter(), Counter(), Counter()
    cells = {}                                  # (family, hid, definition, params) -> {partition: (bp, t, n)}
    dup = 0
    total = 0
    for p in files:
        if any(s in p for s in skip):
            continue
        for line in open(p):
            if not line.strip():
                continue
            r = json.loads(line)
            total += 1
            fam_n[r["family"]] += 1
            part_n[r["partition"]] += 1
            if r["metric"] != "xs_bp" or r["tstat"] is None or not np.isfinite(r["tstat"]) or r["family"] == "G30_attack":
                continue
            if "probe" in r["family"]:
                continue
            fam_xs[r["family"]] += 1
            key = (r["family"], r["hid"], r["definition"], json.dumps(r["params"], sort_keys=True))
            c = cells.setdefault(key, {})
            if r["partition"] in c:
                dup += 1
            c[r["partition"]] = (r["value"], r["tstat"], r["n"] or 0, r["params"].get("h"))
    res = {"total_lines": total, "by_family": dict(fam_n), "xs_cells_by_family": dict(fam_xs), "by_partition": dict(part_n),
           "distinct_xs_cells": len(cells), "duplicate_keys": dup}
    print(f"registry lines {total}; XS cells with a t-statistic {sum(fam_xs.values())} in {len(cells)} distinct definitions; repeated keys {dup}")
    print("per family (all lines / XS cells with t):")
    for f, n in sorted(fam_n.items(), key=lambda kv: -kv[1]):
        print(f"   {f:<26s} {n:>6d} {fam_xs.get(f, 0):>6d}")

    # ---- (ii) distribution of |t| over all logged XS cells
    def tdist(ts):
        ts = np.asarray(ts, dtype=float)
        a = np.abs(ts)
        q25, q50, q75 = np.percentile(ts, [25, 50, 75])
        return {"n": int(len(ts)), "sd": rnd(ts.std(), 2), "robust_sd_iqr": rnd((q75 - q25) / 1.349, 2), "median_t": rnd(q50, 2),
                "share_abs_ge_2": rnd(np.mean(a >= 2), 4), "share_abs_ge_3": rnd(np.mean(a >= 3), 4), "share_abs_ge_4": rnd(np.mean(a >= 4), 4),
                "normal": [0.0455, 0.0027, 0.000063],
                "q50_abs": rnd(np.median(a), 2), "q90_abs": rnd(np.percentile(a, 90), 2), "q99_abs": rnd(np.percentile(a, 99), 2)}

    MIN_N = 100
    by_part = defaultdict(list)
    by_part_fam = defaultdict(list)
    for key, c in cells.items():
        for part, (bp, t, n, h) in c.items():
            if n >= MIN_N:
                by_part[part].append(t)
                by_part_fam[(part, key[0])].append(t)
    res["t_dist"] = {p: tdist(v) for p, v in by_part.items()}
    res["t_dist_by_family"] = {f"{p}|{f}": tdist(v) for (p, f), v in by_part_fam.items() if len(v) >= 30}
    print("\n|t| over all logged XS cells with >= 100 events (normal: 4.55% >= 2, 0.27% >= 3, 0.006% >= 4; median |t| 0.67)")
    for p, v in res["t_dist"].items():
        print(f"   {p:<5s} n={v['n']:>6d} sd {v['sd']:.2f} robust sd {v['robust_sd_iqr']:.2f} median|t| {v['q50_abs']:.2f} "
              f">=2: {100 * v['share_abs_ge_2']:.1f}%  >=3: {100 * v['share_abs_ge_3']:.1f}%  >=4: {100 * v['share_abs_ge_4']:.1f}%")
    for k, v in sorted(res["t_dist_by_family"].items()):
        print(f"      {k:<34s} n={v['n']:>6d} robust sd {v['robust_sd_iqr']:.2f} >=2: {100 * v['share_abs_ge_2']:5.1f}%  >=3: {100 * v['share_abs_ge_3']:5.1f}%")

    # ---- (i) DEV-CTX pairs: sign agreement
    pairs = []
    for key, c in cells.items():
        if "DEV" in c and "CTX" in c and c["DEV"][2] >= MIN_N and c["CTX"][2] >= MIN_N:
            pairs.append((key[0], c["DEV"][1], c["CTX"][1], c["DEV"][3], key[2]))
    fam = np.array([p[0] for p in pairs])
    td = np.array([p[1] for p in pairs])
    tc = np.array([p[2] for p in pairs])
    hh = np.array([p[3] if p[3] is not None else -1 for p in pairs])
    nz = (td != 0) & (tc != 0)
    agree = (np.sign(td) == np.sign(tc))

    def rate(m):
        m = m & nz
        return (rnd(agree[m].mean(), 3), int(m.sum())) if m.sum() else (None, 0)

    def spearman(a, b):
        ra, rb = a.argsort().argsort().astype(float), b.argsort().argsort().astype(float)
        return float(np.corrcoef(ra, rb)[0, 1])

    res["pairs"] = {"n": int(len(pairs)), "agree_all": rate(np.ones(len(pairs), bool)),
                    "pearson_t": rnd(np.corrcoef(td, tc)[0, 1], 3), "spearman_t": rnd(spearman(td, tc), 3)}
    res["pairs"]["by_family"] = {f: {"agree": rate(fam == f), "spearman": rnd(spearman(td[fam == f], tc[fam == f]), 3) if (fam == f).sum() > 10 else None}
                                 for f in sorted(set(fam))}
    fam_rates = [v["agree"][0] for v in res["pairs"]["by_family"].values() if v["agree"][1] >= 30]
    res["pairs"]["agree_family_weighted"] = rnd(np.mean(fam_rates), 3)
    res["pairs"]["by_h"] = {int(h): rate(hh == h) for h in sorted(set(hh))}
    res["pairs"]["agree_given_absDEV_ge"] = {str(x): rate(np.abs(td) >= x) for x in (1, 2, 3)}
    res["pairs"]["agree_given_absCTX_ge"] = {str(x): rate(np.abs(tc) >= x) for x in (1, 2, 3)}
    res["pairs"]["agree_given_absDEV_lt_1"] = rate(np.abs(td) < 1)
    # among cells significant in DEV, how many are significant with the same sign in CTX
    for x in (2, 3):
        m = np.abs(td) >= x
        res["pairs"][f"DEV_ge_{x}"] = {"n": int(m.sum()), "CTX_same_sign_ge_2": int((m & agree & (np.abs(tc) >= 2)).sum()),
                                       "CTX_opposite_sign_ge_2": int((m & ~agree & (np.abs(tc) >= 2)).sum())}
    print(f"\nDEV-CTX pairs (same family, id, definition, parameters; >= {MIN_N} events in both): {len(pairs)}")
    print(f"   same sign: {res['pairs']['agree_all']}; family-weighted {res['pairs']['agree_family_weighted']}; "
          f"correlation of t: Pearson {res['pairs']['pearson_t']}, Spearman {res['pairs']['spearman_t']}")
    for f, v in res["pairs"]["by_family"].items():
        print(f"      {f:<26s} agree {v['agree']}  spearman {v['spearman']}")
    print("   by horizon:", res["pairs"]["by_h"])
    print("   given |t_DEV| >= x:", res["pairs"]["agree_given_absDEV_ge"], " |t_DEV| < 1:", res["pairs"]["agree_given_absDEV_lt_1"])
    print("   given |t_CTX| >= x:", res["pairs"]["agree_given_absCTX_ge"])
    print("   DEV significant ->", res["pairs"]["DEV_ge_2"], res["pairs"]["DEV_ge_3"])

    # ---- how unusual is each candidate among everything that was looked at
    g30 = json.loads((RES / "g30_attack.json").read_text())
    p_agree = res["pairs"]["agree_all"][0]
    n_pairs = int(nz.sum())
    sd_d = res["t_dist"]["DEV"]["robust_sd_iqr"]
    sd_c = res["t_dist"]["CTX"]["robust_sd_iqr"]
    rho = 2 * math.sin(math.pi * res["pairs"]["spearman_t"] / 6)          # Spearman -> Pearson for a bivariate normal core
    # main-loop families the candidates were drawn from
    g_fams = np.array([f.startswith("G") for f in fam])
    stou = (td + tc) / math.sqrt(2.0)
    stou_sd_emp = math.sqrt((sd_d ** 2 + sd_c ** 2 + 2 * rho * sd_d * sd_c) / 2.0)
    res["null"] = {"p_agree": p_agree, "n_pairs": n_pairs, "n_pairs_G": int((g_fams & nz).sum()), "robust_sd_DEV": sd_d, "robust_sd_CTX": sd_c,
                   "rho_core": rnd(rho, 3), "stouffer_sd_empirical_null": rnd(stou_sd_emp, 3)}
    print(f"\nempirical null: P(same sign) {p_agree}, robust sd of t DEV {sd_d} CTX {sd_c}, core correlation {rho:.3f}, "
          f"sd of (t_DEV+t_CTX)/sqrt2 under it {stou_sd_emp:.2f};  pairs {n_pairs} (main-loop G families {int((g_fams & nz).sum())})")
    print(f"{'candidate':<26s} t_DEV  t_CTX | rectangle: logged pairs as good (all / G) | expected by chance N(0,1) (all / G) | same, empirical null (all / G) | Stouffer z, theory | z, empirical null")
    res["cand"] = {}
    tot_exp = {"theory_all": 0.0, "theory_G": 0.0, "emp_all": 0.0, "emp_G": 0.0}
    for name, r in g30.items():
        a, b, sgn = r["DEV"]["t"], r["CTX"]["t"], r["sign"]
        same = np.sign(a) == np.sign(b)
        c = {"t_DEV": a, "t_CTX": b, "same_sign": bool(same)}
        if same:
            m = nz & agree & (np.abs(td) >= abs(a)) & (np.abs(tc) >= abs(b))
            obs_all, obs_g = int(m.sum()), int((m & g_fams).sum())
            # mirror image: pairs just as extreme whose two samples DISAGREE in sign. If the logged cells were
            # noise that is independent across the two samples, same-sign and opposite-sign pairs would be equally common.
            mir = nz & ~agree & (np.abs(td) >= abs(a)) & (np.abs(tc) >= abs(b))
            c["mirror_opposite_sign_all"], c["mirror_opposite_sign_G"] = int(mir.sum()), int((mir & g_fams).sum())
            p_th = 0.5 * (2 * phi_bar(abs(a))) * (2 * phi_bar(abs(b)))
            p_em = p_agree * (2 * phi_bar(abs(a) / sd_d)) * (2 * phi_bar(abs(b) / sd_c))
            z = (a + b) / math.sqrt(2.0) * sgn
            c.update({"obs_pairs_as_good_all": obs_all, "obs_pairs_as_good_G": obs_g,
                      "exp_theory_all": rnd(n_pairs * p_th, 2), "exp_theory_G": rnd(res["null"]["n_pairs_G"] * p_th, 2),
                      "exp_emp_all": rnd(n_pairs * p_em, 2), "exp_emp_G": rnd(res["null"]["n_pairs_G"] * p_em, 2),
                      "fdr_theory_all": rnd(min(1.0, n_pairs * p_th / max(obs_all, 1)), 3),
                      "fdr_emp_all": rnd(min(1.0, n_pairs * p_em / max(obs_all, 1)), 3),
                      "fdr_emp_G": rnd(min(1.0, res["null"]["n_pairs_G"] * p_em / max(obs_g, 1)), 3),
                      "stouffer_z": rnd(z, 2), "stouffer_z_emp": rnd(z / stou_sd_emp, 2),
                      "stouffer_obs_all": int((np.abs(stou) >= abs(z)).sum()),
                      "stouffer_exp_emp_all": rnd(n_pairs * 2 * phi_bar(abs(z) / stou_sd_emp), 2)})
            tot_exp["theory_all"] += c["fdr_theory_all"]
            tot_exp["emp_all"] += c["fdr_emp_all"]
            tot_exp["emp_G"] += c["fdr_emp_G"]
            print(f"{name:<26s} {a:+5.2f} {b:+5.2f} | {obs_all:>6d} / {obs_g:<5d} | {c['exp_theory_all']:>8.2f} / {c['exp_theory_G']:<7.2f} | "
                  f"{c['exp_emp_all']:>8.2f} / {c['exp_emp_G']:<7.2f} | {z:+5.2f} | {c['stouffer_z_emp']:+5.2f}  "
                  f"FDR(emp, all) {c['fdr_emp_all']:.2f}  FDR(emp, G) {c['fdr_emp_G']:.2f}  mirror (opposite sign, as extreme) {c['mirror_opposite_sign_all']} / {c['mirror_opposite_sign_G']}")
        else:
            print(f"{name:<26s} {a:+5.2f} {b:+5.2f} | signs disagree: fails the two-sample requirement by construction")
            for k in ("theory_all", "emp_all", "emp_G"):
                tot_exp[k] += 1.0
        res["cand"][name] = c
    res["expected_false_among_14"] = {k: rnd(v, 1) for k, v in tot_exp.items() if v}
    print("expected number of the 14 that are noise (sum of the estimated false-discovery rates; A9 counted as 1):", res["expected_false_among_14"])
    # Bonferroni-type bars on the Stouffer z under the empirical null
    for nn, lab in ((res["null"]["n_pairs_G"], "G"), (n_pairs, "all")):
        # two-sided 5% family-wise over nn pairs
        lo, hi = 0.0, 10.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if 2 * phi_bar(mid) * nn > 0.05:
                lo = mid
            else:
                hi = mid
        res["null"][f"bonferroni_z_{lab}"] = rnd(hi, 2)
    print("Bonferroni bar on |z| (5% family-wise): main-loop pairs", res["null"]["bonferroni_z_G"], " all pairs", res["null"]["bonferroni_z_all"])
    (RES / "audit_stats_registry.json").write_text(json.dumps(res, indent=1))


# ============================================================================== tables
def tables() -> None:
    D = json.loads((RES / "audit_stats_DEV.json").read_text())
    X = json.loads((RES / "audit_stats_CTX.json").read_text())
    g30 = json.loads((RES / "g30_attack.json").read_text())
    for smp, A in (("DEV", D), ("CTX", X)):
        print(f"\n=== {smp}  {A['meta']}")
        print(f"{'candidate':<26s}  h sgn | logged bp (t)  | (a) day bp (t) | (b) event bp (t, t-delta) | (c) median, right | (d) non-overlap bp, t med [min,max], n | (e) boot CI day, p-wrong | boot CI event, p-wrong | ev/mo")
        for name, r in A["cand"].items():
            g = g30[name][smp]
            print(f"{name:<26s} {r['h']:>2d} {r['sign']:+d} | {g['bp']:+7.1f} ({g['t']:+5.2f}) | {r['a_bp']:+7.1f} ({r['a_t']:+5.2f}) | {r['b_bp']:+7.1f} ({r['b_t']:+5.2f}, {r['b_t_delta']:+5.2f}) |"
                  f" {r['c_median_bp']:+6.1f} {r['c_share_right']:.3f} | {r['d_bp_median']:+7.1f} {r['d_t_median']:+5.2f} [{r['d_t_min']:+5.2f},{r['d_t_max']:+5.2f}] {r['d_n_per_offset']:>4d} |"
                  f" {r['e_a_ci_bp']} {r['e_a_p_wrong_sign']:.3f} | {r['e_b_ci_bp']} {r['e_b_p_wrong_sign']:.3f} | {r['events_per_month']}")
        print("\nhorizon profile, day-weighted bp (t) / event-weighted bp (t)")
        for name, r in A["cand"].items():
            print(f"{name:<26s} " + " | ".join(f"h={h}: {p['a_bp']:+.0f} ({p['a_t']:+.1f}) / {p['b_bp']:+.0f} ({p['b_t']:+.1f})" for h, p in r["profile"].items()))
        print("\nhalves: early / late, day-weighted bp (t); event-weighted bp (t)")
        for name, r in A["cand"].items():
            e, l = r["early"], r["late"]
            print(f"{name:<26s} {e['a_bp']} ({e['a_t']}) / {l['a_bp']} ({l['a_t']});   {e['b_bp']} ({e['b_t']}) / {l['b_bp']} ({l['b_t']})")
        print("\npart 4")
        for name, r in A["cand"].items():
            print(f"{name:<26s}", json.dumps(r.get("in_trend_selection") or r.get("as_entry")))
        print("\noverlap >= 10% (share of the row's events that are also the column's)")
        for a, row in A["overlap"].items():
            big = {b: v for b, v in row.items() if v and v >= 0.10}
            if big:
                print(f"{a:<26s}", big)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "registry"
    if what in ("DEV", "CTX"):
        run_sample(what)
    elif what == "registry":
        run_registry()
    else:
        tables()
