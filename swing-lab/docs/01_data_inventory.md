# Data inventory

What the research can reach, how it was checked, and what is wrong with each source.
All probes run from the cloud environment on **10 Nov 2026**. No raw data is committed; the build
scripts in `research/data_build/` recreate everything from the sources below.

## 1. What changed since the previous session

The previous session (`trend-flow-suite`) could reach only daily bars of large surviving US
companies ending in early 2018. Today:

| Source | 9 Nov (previous session) | 10 Nov 2026 |
|---|---|---|
| Yahoo Finance | blocked by network policy | **reachable** through `yfinance` 1.8.0 |
| Hugging Face datasets | not tried | **reachable** |
| DoltHub (open SQL databases) | not tried | **reachable**, API and `dolt clone` |
| Kenneth French data library | not tried | reachable |
| FRED | not tried | reachable |
| TradingView docs and compiler endpoint | not tried | reachable |
| Stooq | blocked | no response (time-out); not needed |
| SEC EDGAR | not tried | HTTP 403 without a declared contact in the User-Agent; not needed |
| Financial Datasets connector | AAPL daily only | SPY daily works; **no intraday** ("Must be one of year, week, month, day"); **no delisted** tickers ("provide a valid ticker from company_tickers.json"). Superseded by the sources below |

## 2. Sources in use

### 2.1 DoltHub `post-no-preference/stocks` — daily bars as traded, with delisted names

- **What:** `ohlcv` (date, act_symbol, open, high, low, close, volume), `split`, `dividend`, `symbol`.
  Cloned with `dolt clone --depth 1` (747 MB). Last bar: **2026-11-09**.
- **Size:** about 27 million rows, 18,892 symbols at the 28 Jan 2026 snapshot, first bar 2011-01-03.
- **Prices are raw** (unadjusted for splits or dividends): AAPL on 2011-01-03 is 325.90–329.57.
- **Delisted names are present from 2018 onward:** TWTR to 2022-10-27, SIVB to 2023-03-09,
  FRC to 2023-04-28, ATVI to 2023-10-12, XLNX to 2022-02-11.

Measured defects:

| Defect | Evidence | Handling |
|---|---|---|
| **Survivor-biased before mid-2018.** Collection began in 2018; history back to 2011 was backfilled only for symbols alive then | Symbols whose last bar falls in: 2011–2017 none; 2018: 196; 2019: 569; 2020: 664; 2021: 667; 2022: 847; 2023: 1,066; 2024: 1,353; 2025: 1,162. 2,206 symbols first appear in 2018. Monsanto (delisted June 2018) is absent; Celgene starts 2018-02-26 | 2011-01 – 2018-06 is the DEV partition and is treated as biased. Survivorship-free evidence starts 2018-07 |
| **Ticker reuse.** A symbol can be two different securities at different times | `MON` 2021–2022 is not Monsanto; `SHLD` 2018 and 2023+ differ; `FB`/`META` overlap | Each symbol's history is cut into separate entities at long gaps (`data_build/02_entities.py`) |
| **Renames break continuity** (FB to META) | Old symbol ends, new one begins | Treated as an exit at the last price and a new listing; costs about a year of warm-up per rename; no P&L distortion |
| **Split table is incomplete and has errors** | Table starts 2014-03-28; GOOGL 20:1 appears on both 2022-06-30 and 2022-07-18 | A split is applied only if the price confirms it; unlisted splits are detected from clean overnight ratios with volume confirmation; result checked against Yahoo on surviving names |
| **Zero-volume rows** | 175,506 rows | Excluded; the liquidity floor removes nearly all of them anyway |
| **No delisting reason** | – | Heuristic delisting return, see protocol §5 |

Liquid universe size (median daily dollar volume in the year): above $20M: 901 names in 2011,
1,721 in 2018, 2,030 in 2022, 2,434 in 2025. Above $5M: 1,533 / 2,967 / 3,470 / 3,831.
Of the 1,697 names above $20M in 2019, 315 had stopped trading under that symbol by January 2026.

### 2.2 DoltHub `post-no-preference/earnings`

| Table | Content | Range |
|---|---|---|
| `earnings_calendar` | announcement date and `when` (Before market open / After market close / blank) | 2020-01-22 – 2026-12-18, 7,468 symbols, 122,168 rows; 25% have a blank `when` |
| `eps_history` | reported and estimated EPS per fiscal period | period ends 2016-07 – 2026-09, 7,105 symbols |
| `eps_estimate` | weekly snapshots of consensus, high, low, analyst count per period | from 2019-03-03, 7.2M rows |
| `rank_score` | weekly analyst-revision rank and style scores | from 2019-03-03 |

To check before use: whether calendar dates are the dates as announced in advance or as they
happened, and how many liquid names are covered each year.

### 2.3 Yahoo Finance (`yfinance`)

- Daily history for currently listed stocks, ETFs and indices (SPY from 1993-01-29, ^VIX from 1990).
- **1-hour bars for the last 730 days only** (AAPL: 2023-12-12 – 2026-11-09, 5,077 bars).
- Delisted symbols return nothing (TWTR, SIVB).
- Use: independent check of DoltHub prices and splits on survivors; long index/ETF history;
  the only intraday source so far.

### 2.4 Kenneth French data library

Daily and monthly returns of portfolios sorted on momentum, short-term reversal, size, industries;
built from CRSP, so delisted companies are included. Portfolio level only. Used to place every
stock-level finding against a 60–100 year, survivorship-free record.

### 2.5 FRED

VIX, VIX3M, credit spreads, Treasury yields: market-state variables with long history.

### 2.6 Inherited from `trend-flow-suite`

S&P 500 members 2013–2018 (CNuge mirror), Dow-30 2006–2017, the "Huge Stock Market Dataset"
(1999–2017). All survivors only. Context for earlier bear markets.

## 3. Gaps and the cheapest way to close each

| Gap | Why it matters | Cheapest fix | Status |
|---|---|---|---|
| 1-hour bars before Dec 2023, and for delisted names | The trader reads 1h and 4h charts; two years of survivors cannot confirm an intraday rule | Free Alpaca paper-account API key (historical bars since 2016); coverage of delisted symbols to be verified once a key exists | **Asked of the user 10 Nov 2026** |
| Daily bars with delisted names before 2018 | 2000–02 and 2008 in survivorship-free form | Paid (Norgate, Sharadar, EODHD, Tiingo, Polygon); prices being checked | Decide only if a candidate depends on it |
| Options-implied data | Not available in Pine either, so outside the product's reach | – | Out of scope |

## 4. Reproduction

```bash
# tools
curl -sSL -o dolt.tar.gz https://github.com/dolthub/dolt/releases/latest/download/dolt-linux-amd64.tar.gz && tar xzf dolt.tar.gz
pip install yfinance pyarrow pandas numpy scipy statsmodels

# sources
dolt clone --depth 1 post-no-preference/stocks
dolt clone --depth 1 post-no-preference/earnings

# then
python -m research.data_build.01_export        # dolt tables -> parquet
python -m research.data_build.02_entities      # entity resolution, split/dividend adjustment, QA
python -m research.data_build.03_panel         # liquid-universe panel, partitions
```
