"""Panel loading with the partitions of docs/00_protocol.md enforced in code.

    p = load_panel()            # development + validation dates only (physically truncated copy)
    p.rows("DEV"), p.rows("VAL")  # boolean masks over p.dates

The lockbox can only be read through open_lockbox(), which appends a dated record to
registry/lockbox.json. Nothing else in the package touches the sealed copy.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

PANEL_DIR = Path(os.environ.get("SWINGLAB_PANEL", "/home/user/data/panel"))
REPO_ROOT = Path(__file__).resolve().parents[2]            # .../swing-lab
REGISTRY_DIR = REPO_ROOT / "registry"

PARTITIONS = {
    "DEV": ("2011-01-03", "2018-06-29"),        # universe biased: only symbols alive in 2018
    "VAL": ("2018-07-02", "2022-12-30"),        # survivorship-free
    "LOCKBOX": ("2023-01-03", "2026-11-09"),    # sealed
    "POSTCUTOFF": ("2026-07-01", "2026-11-09"),  # inside the lockbox; after the model's knowledge ends
    "CTX": ("1998-01-02", "2010-12-31"),        # context panel only: Yahoo survivors, strongly biased
    # protocol amendment 1: families whose data begins inside the validation window
    "DEV_S": ("2018-08-01", "2020-06-30"),      # short-volume family: exploration
    "VAL_S": ("2020-07-01", "2022-12-30"),      # short-volume family: confirmation
}
FIELDS = ("o", "h", "l", "c", "v", "c_raw", "div", "adv60", "bad")
STOCK_TYPES = ("common", "adr", "prior_use", "unknown")
ETF_TYPES = ("etf",)


@dataclass
class Panel:
    dates: np.ndarray
    ents: pd.DataFrame
    name: str
    _dir: Path
    _cache: dict = field(default_factory=dict, repr=False)

    def __getattr__(self, item: str) -> np.ndarray:
        if item in FIELDS:
            if item not in self._cache:
                self._cache[item] = np.load(self._dir / f"{item}.npy", mmap_mode="r")
            return self._cache[item]
        raise AttributeError(item)

    @property
    def T(self) -> int:
        return len(self.dates)

    @property
    def N(self) -> int:
        return len(self.ents)

    def rows(self, partition: str) -> np.ndarray:
        a, b = PARTITIONS[partition]
        return (self.dates >= np.datetime64(a)) & (self.dates <= np.datetime64(b))

    def col(self, symbol: str) -> int:
        """Column of the live security with this symbol (e.g. 'SPY')."""
        m = self.ents[(self.ents["symbol"] == symbol) & (~self.ents["ended"])]
        if m.empty:
            raise KeyError(symbol)
        return int(m["col"].iloc[0])

    def type_mask(self, types=STOCK_TYPES) -> np.ndarray:
        return self.ents["type"].isin(types).to_numpy()

    def universe(self, adv_min: float = 20e6, px_min: float = 5.0, types=STOCK_TYPES) -> np.ndarray:
        """[T, N] bool: tradable at the close of t, judged only with data up to t."""
        u = (np.asarray(self.adv60) >= adv_min) & (np.asarray(self.c_raw) >= px_min)
        u &= self.type_mask(types)[None, :]
        u &= np.isfinite(np.asarray(self.c))
        u &= np.asarray(self.bad) == 0
        return u

    def half(self, which: str) -> np.ndarray:
        """Cross-sectional halves A/B by md5(symbol) mod 2."""
        import hashlib
        h = np.array([int(hashlib.md5(s.encode()).hexdigest(), 16) % 2 for s in self.ents["symbol"]])
        return h == (0 if which == "A" else 1)


def load_panel() -> Panel:
    d = PANEL_DIR / "devval"
    return Panel(dates=np.load(d / "dates.npy").astype("datetime64[D]"),
                 ents=pd.read_parquet(d / "ents.parquet"), name="devval", _dir=d)


def load_ctx() -> Panel:
    """Context panel 1997-2010 (survivors of 2026 only; first year is warm-up). Development use."""
    d = PANEL_DIR / "ctx"
    return Panel(dates=np.load(d / "dates.npy").astype("datetime64[D]"),
                 ents=pd.read_parquet(d / "ents.parquet"), name="ctx", _dir=d)


def open_lockbox(reason: str, frozen_rules: list[str]) -> Panel:
    """Read the sealed copy. Records who/why/when. Protocol section 2: once, at the end."""
    rec_path = REGISTRY_DIR / "lockbox.json"
    rec = json.loads(rec_path.read_text())
    if os.environ.get("SWINGLAB_OPEN_LOCKBOX") != "I-HAVE-FROZEN-THE-RULES":
        raise PermissionError("Lockbox is sealed. Freeze the rule list first (protocol section 3).")
    rec["status"] = "OPENED"
    rec["openings"].append({"when_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                            "reason": reason, "frozen_rules": frozen_rules})
    rec_path.write_text(json.dumps(rec, indent=2))
    d = PANEL_DIR / "LOCKBOX_SEALED_do_not_open"
    return Panel(dates=np.load(d / "dates.npy").astype("datetime64[D]"),
                 ents=pd.read_parquet(d / "ents.parquet"), name="full", _dir=d)
