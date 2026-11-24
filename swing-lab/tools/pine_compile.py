#!/usr/bin/env python3
"""Compile-check a Pine Script file against TradingView's own compiler.

Uses the public lint endpoint that TradingView's web editor and open-source editor plug-ins call
(`pine-facade.tradingview.com/pine-facade/translate_light`, guest user, no login, no account).
It returns the compiler's errors and warnings with line and column numbers.

What this proves:    the script parses and type-checks under the current Pine compiler.
What it does NOT:    runtime errors (request limits, loop time-outs, max_bars_back, array bounds),
                     numerical parity with the research code, or repainting behaviour.
                     Those need the script on a chart (see docs/03_verification.md).

Usage:
    python tools/pine_compile.py pine/some_script.pine [more.pine ...]
    python tools/pine_compile.py --json pine/some_script.pine
Exit code: 0 if every file compiles without errors, 1 otherwise, 2 on transport failure.
"""
from __future__ import annotations

import json
import sys
import time
import uuid
import urllib.error
import urllib.request

ENDPOINT = ("https://pine-facade.tradingview.com/pine-facade/translate_light"
            "?user_name=Guest&pine_id=00000000-0000-0000-0000-000000000000")


def _post(source: str, timeout: int = 60) -> dict:
    boundary = "----swinglab" + uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"source\"\r\n\r\n"
            f"{source}\r\n--{boundary}--\r\n").encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                 "Referer": "https://www.tradingview.com/",
                 "User-Agent": "pine-lint-client"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _fmt(item: dict) -> str:
    msg = item.get("message", "")
    for k, v in (item.get("ctx") or {}).items():
        msg = msg.replace("{" + k + "}", str(v))
    s, e = item.get("start", {}), item.get("end", {})
    return (f"  line {s.get('line', '?')}:{s.get('column', '?')}"
            f"-{e.get('line', '?')}:{e.get('column', '?')}  {item.get('code', '')}  {msg}")


def check(path: str) -> dict:
    """Returns {'path', 'ok', 'errors': [...], 'warnings': [...], 'raw': {...}}."""
    with open(path, encoding="utf-8") as f:
        source = f.read()
    last_exc = None
    for attempt in range(4):
        try:
            raw = _post(source)
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_exc = exc
            time.sleep(2 * 2 ** attempt)
    else:
        return {"path": path, "ok": False, "transport_error": repr(last_exc), "errors": [], "warnings": []}
    res = raw.get("result") or {}
    errors = (res.get("errors2") or []) + (res.get("errors") or [])
    warnings = (res.get("warnings2") or []) + (res.get("warnings") or [])
    ok = bool(raw.get("success")) and not errors
    if not raw.get("success") and not errors:
        errors = [{"message": raw.get("reason") or json.dumps(raw)[:500]}]
    return {"path": path, "ok": ok, "errors": errors, "warnings": warnings, "raw": raw}


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__)
        return 2
    rc = 0
    out = []
    for i, p in enumerate(paths):
        if i:
            time.sleep(1.0)          # be polite to the endpoint
        r = check(p)
        out.append({k: v for k, v in r.items() if k != "raw"})
        if as_json:
            continue
        if r.get("transport_error"):
            print(f"TRANSPORT FAILURE  {p}: {r['transport_error']}")
            rc = max(rc, 2)
            continue
        print(f"{'OK  ' if r['ok'] else 'FAIL'}  {p}  errors={len(r['errors'])} warnings={len(r['warnings'])}")
        for e in r["errors"]:
            print("  ERROR  " + _fmt(e).strip())
        for w in r["warnings"]:
            print("  WARN   " + _fmt(w).strip())
        if not r["ok"]:
            rc = max(rc, 1)
    if as_json:
        print(json.dumps(out, indent=1))
        rc = 0 if all(o["ok"] for o in out) else 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
