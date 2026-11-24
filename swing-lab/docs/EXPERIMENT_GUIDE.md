# Experiment guide (read before writing any experiment)

The rules that make results comparable and keep the search honest. They restate
`00_protocol.md` for the person or agent writing an experiment.

## The one-paragraph version

You explore on **development data only**: `Study("DEV")` (2011-01 to 2018-06, universe biased to
companies alive in 2018) and `Study("CTX")` (1998 to 2010, survivors of 2026 only, strongly
biased, contains two bear markets). You never touch validation or lockbox data. Every outcome is a
total return measured **from the open of the bar after the signal**. Every number you look at is
logged automatically. What you produce is a map of where to aim a small number of pre-registered
confirmation tests, plus an honest account of what is dead. Finding nothing is a result.

## Tools

```python
import os; os.environ["SWINGLAB_REGISTRY_TAG"] = "f03"      # your family tag, BEFORE importing swinglab
from research.swinglab.study import Study
from research.swinglab import pinelike as ta, trades as TR, engine as E
S = Study("DEV")            # or "CTX".  Build ONE Study at a time (each needs about 2 GB):
                            # finish DEV, then `del S; import gc; gc.collect()`, then CTX.
```

Run scripts from `swing-lab/` as modules: `python -m research.experiments.f03_momentum`.
Run **one Python process at a time**; the machine is shared.

| Object | Meaning |
|---|---|
| `S.P.o, .h, .l, .c` | split-adjusted bars `[T, N]`, NaN where there is no bar |
| `S.P.cf` | close, forward-filled over holes (use this for indicators) |
| `S.P.v` | share volume; `S.adv60` 60-bar median dollar volume; `S.c_raw` price as traded |
| `S.P.ret` | daily log return close-to-close |
| `S.vol` | daily volatility forecast known at the close of t (robust EWMA, span 20) |
| `S.z(k)` | k-day log return divided by `vol[t-k]*sqrt(k)` |
| `S.uni` | `[T, N]` bool: in the tradable universe on that day (price >= $5, median dollar volume >= $20M in DEV, >= $5M in CTX), already limited to the sample's dates |
| `S.rows` | bool over dates: the sample |
| `S.spy` | column of SPY (excluded from `S.uni`); `S.ctx("^VIX")` etc. for other market series |
| `S.atr(n)` | `ta.atr(n)` |
| `S.half_a` | bool over securities: cross-section half A (`~S.half_a` is B) |
| `ta.*` | indicators written to Pine's definitions: `sma, ema, rma, stdev, highest, lowest, median, atr, rsi, change, roc, barssince, rolling_sum, percentrank, linreg_slope, shift` |

Evaluation:

```python
tab = S.event(hid, family, "text definition", sig_bool, params={...})     # one signal
tab = S.buckets(hid, family, "name", feature, edges, base=mask)           # absolute thresholds
tab = S.quantiles(hid, family, "name", feature, q=5, base=mask)           # cross-sectional ranks
S.show(tab, "title")
tr  = S.trades(sig, stop_k=2, trail_k=0, target_r=0, max_hold=10, exit_sig=None, cost_bp=5)
TR.summarize(tr, len(S.dates));  TR.placebo_signals(sig, S.uni, seed)
```

Each cell reports two views. **XS**: signal mean minus the mean of the control (the universe, or
`base`) on the same day: the stock-specific part. **TS**: event-weighted signal mean minus the
universe's average over the whole sample: includes market-wide timing, and has few independent
episodes, which its t-statistic reflects. A rule that works only in TS is market timing; say so.

## Hard rules

1. **No look-ahead.** A signal on row t may use rows <= t only. `ta.*` and `S.z` are safe.
   Anything you write yourself with a centred window, a full-sample quantile, a full-sample
   mean or `[::-1]` is not. Thresholds must be absolute or computed from trailing data.
   Cross-sectional ranks on the same day are allowed but are flagged "needs a screener".
2. **Pine-computable.** The signal must be expressible in Pine on the close of a bar from the
   chart's own OHLCV, plus (if needed) a few other symbols through `request.security` (SPY, VIX,
   a sector ETF) and earnings data. State the Pine recipe in one line per signal.
3. **Entry at the next open.** Never report a return that starts at the signal bar's close as
   tradable. `S.gap()` exists to measure how much of an effect is lost overnight.
4. **Costs.** A round trip costs about 10 bp in the base universe (5 bp per side), 20 bp when
   doubled. An effect smaller than that is not a long-side trade, though it can still be an
   "avoid" filter or an exit.
5. **Count everything.** Do not turn logging off for cells you look at. Do not delete registry
   lines. If you ran something by mistake, add a line that says so.
6. **No tuning to the peak.** Use round, conventional parameter values and show the neighbours.
   A candidate is a plateau, not a spike.
7. **Report the dead.** For each idea: what it was, the numbers, why it is dead.

## What "interesting" means on development data

A candidate worth one validation look has all of:

- the same sign in DEV and CTX, in both cross-section halves, and in at least two thirds of the
  calendar years with enough events;
- |t| >= 3 in at least one sample on the date-clustered statistic, and not driven by one month;
- size that matters after costs for its intended use (entry, exit, filter, sizing);
- a mechanism: who is on the other side and why they keep paying;
- survives a one-bar delay (signal at t, entry at the open of t+2) without getting *better*.

Because the DEV universe contains only survivors, dip-buying and "bounce" results are biased
upward and trend/avoidance results are biased toward zero. Weigh accordingly.

## Deliverables of an experiment family

1. `research/experiments/<tag>_<name>.py`: runnable, deterministic, prints its tables.
2. `research/results/<tag>_<name>.json`: the tables.
3. `docs/_raw/exp_<tag>_<name>.md`: what was tried (every variant), the main tables, what is
   dead and why, and at most five **candidates for confirmation**, each with: exact definition,
   Pine recipe, intended use (select / enter / size / exit / avoid / regime), expected size,
   the control, and how it could fail.
