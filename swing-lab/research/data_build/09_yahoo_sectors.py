"""Sector and industry labels for surviving companies, from Yahoo (current classification).

Used only to form sector-relative controls and to map a stock to its sector ETF, as Pine does
with syminfo.sector. A current label applied to past dates is a mild look-ahead in classification
(companies rarely change sector); stated wherever it is used. Delisted names get no label here.

Resumable: python -m research.data_build.09_yahoo_sectors
"""
from __future__ import annotations

import json
import time
from pathlib import Path

OUT = Path("/home/user/data/sectors/yahoo_sectors.jsonl")
SYMS = Path("/home/user/data/lists/liquid_survivors_yahoo.txt")


def main() -> None:
    import yfinance as yf

    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                done.add(json.loads(line)["symbol"])
            except Exception:  # noqa: BLE001
                pass
    syms = [s for s in SYMS.read_text().split() if s not in done]
    fails = 0
    with open(OUT, "a") as f:
        for i, s in enumerate(syms):
            rec = {"symbol": s}
            try:
                info = yf.Ticker(s).info
                rec.update({"sector": info.get("sector"), "industry": info.get("industry"),
                            "quoteType": info.get("quoteType"), "category": info.get("category")})
                fails = 0
            except Exception as exc:  # noqa: BLE001
                rec["error"] = type(exc).__name__
                fails += 1
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if fails >= 15:            # rate-limited: back off for a while
                time.sleep(300)
                fails = 0
            time.sleep(0.6)
            if i % 200 == 0:
                print(i, "of", len(syms), flush=True)


if __name__ == "__main__":
    main()
