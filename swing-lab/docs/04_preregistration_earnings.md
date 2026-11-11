# Pre-registration: drift after earnings reactions (second and last look at validation data)

**Status: FINAL. Committed and pushed before `research/confirm/run_val_earnings.py` was executed on
validation data.** Written 11 Nov 2026 (UTC).

## Why a second look, and what it costs

The first validation run (entry 5 of the research log) left one directional idea standing as
"suggestive": E1, a gap up of 3 sigma or more on heavy volume that closes strong. On the six
quarters of development data that have announcement dates (2017-01 to 2018-06), about four in five
E1 events are earnings reactions. The published effect behind that is post-earnings-announcement
drift measured by the announcement return (Chan, Jegadeesh & Lakonishok 1996; Brandt, Kishore,
Santa-Clara & Venkatachalam 2008). Its recent record in large companies is poor (Martineau 2022,
"Rest in peace post-earnings announcement drift"), so the prior that it still pays in this
universe is low. The question matters to the product either way: it decides whether the script
may say anything about direction after an earnings report, or only about risk before one.

The protocol (section 3) allows a pre-registered replication of a published effect with the
published sign on validation data, with |t| >= 2.0. This is the second look at that sample; it is
counted in the registry (`partition = VAL`, `hid = VAL2`) and no third look will be made.

## The family (two hypotheses)

Sample: VAL, 2 July 2018 to 30 December 2022. Universe, outcome, costs and statistics as in the
first run (`docs/03_preregistration_val.md`). Reaction bar: the first bar whose close contains the
news, decided causally (`research/swinglab/earnings.py`). sigma: the robust EWMA volatility known
before the reaction.

| ID | Signal at the close of the reaction bar | h | Predicted | Development (2017-01..2018-06), day-weighted bp (t) | Event-weighted bp (t) |
|---|---|---|---|---|---|
| PE1 | Close-to-close move >= +3 sigma | 20 | + | +33 (1.1) | +48 (1.6) |
| PE2 | Close-to-close move <= -3 sigma | 20 | - | -9 (-0.4) | -50 (-2.0) |

The thresholds follow the published design (extreme groups of the announcement return; +/-3 sigma
marks roughly the top and bottom sixth of reaction bars). The horizon is the longest holding
period this project considers. Neither was tuned: the development sample has six quarters and its
numbers are shown only as a sanity check that the code runs.

**"Confirmed" requires both:**

1. Day-weighted mean of (signal mean minus universe mean), Newey-West with 40 lags, |t| >= 2.0
   with the predicted sign, and one-sided Student-t p-value (df = floor(days with a spread / 40) - 1)
   significant under Holm at 5% across the two.
2. Event-weighted estimate with the predicted sign and one-sided p <= 0.10 (date-clustered).

**Declared diagnostics, no verdict:** the same two signals at h = 5, 10 and 60; E1 split into
events on reaction bars and events on other bars (h = 10).

## Consequences fixed now

- A confirmed hypothesis joins the lockbox list as a directional rule (protocol amendment 3), and
  the directional rules on that list are then tested with Holm's correction among themselves.
- If neither is confirmed, the product makes no statement about direction after earnings beyond
  E1's "suggestive" label, and the lockbox list is unchanged.
