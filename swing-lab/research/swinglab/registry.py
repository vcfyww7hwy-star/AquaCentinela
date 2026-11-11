"""Append-only trial registry (protocol section 3).

One JSON line per evaluated outcome. Parallel workers write to their own file
(registry/trials_<tag>.jsonl, tag from SWINGLAB_REGISTRY_TAG) so that appends never collide.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
from pathlib import Path

from .data import REGISTRY_DIR, REPO_ROOT

_commit_cache: str | None = None


def _commit() -> str:
    global _commit_cache
    if _commit_cache is None:
        try:
            _commit_cache = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
                                           capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:  # noqa: BLE001
            _commit_cache = "unknown"
    return _commit_cache


def _path() -> Path:
    tag = os.environ.get("SWINGLAB_REGISTRY_TAG", "")
    return REGISTRY_DIR / (f"trials_{tag}.jsonl" if tag else "trials.jsonl")


def log_trial(hid: str, family: str, definition: str, partition: str, metric: str, value: float,
              *, params: dict | None = None, universe: str = "", tstat: float | None = None,
              n: int | None = None, note: str = "") -> None:
    """Record one looked-at outcome. Call it for every number that could influence a decision."""
    rec = {
        "ts_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": _commit(), "hid": hid, "family": family, "definition": definition,
        "params": params or {}, "universe": universe, "partition": partition,
        "metric": metric, "value": None if value is None else float(value),
        "tstat": None if tstat is None else float(tstat), "n": n, "note": note,
    }
    with open(_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def counts() -> dict:
    """Totals across all registry files."""
    trials, fams, hids, by_part = 0, set(), set(), {}
    for p in sorted(REGISTRY_DIR.glob("trials*.jsonl")):
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            trials += 1
            fams.add(r["family"])
            hids.add(r["hid"])
            by_part[r["partition"]] = by_part.get(r["partition"], 0) + 1
    return {"trials": trials, "families": len(fams), "hypotheses": len(hids), "by_partition": by_part}
