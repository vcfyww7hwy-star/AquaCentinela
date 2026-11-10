from pathlib import Path

import pytest

from tools.build_strategy import DST, SRC, build


def test_strategy_is_generated_from_the_indicator_and_kept_in_sync():
    src = SRC.read_text(encoding="utf-8")
    out = build(src)
    assert out.splitlines()[0] == "//@version=6"
    assert "strategy(" in out and "indicator(" not in out
    assert "alertcondition(" not in out                      # not allowed in strategies
    assert "strategy.entry(" in out and "strategy.close(" in out
    assert "float equityNow = strategy.equity" in out
    # every non-indicator line of the source logic is carried over unchanged
    assert 'strategy.exit("Stop", "Long", stop = stopLevel' in out
    for key in ("trendScore(", "trendDir(", "robustVarLagged(", "sigNow  := 1", "exitReason := 3", "stopLevel  := sigStop"):
        assert key in out
    # the committed strategy file is exactly what the builder produces today
    assert DST.read_text(encoding="utf-8") == out


def test_generated_strategy_parses():
    pynescript = pytest.importorskip("pynescript.ast")
    pynescript.parse(DST.read_text(encoding="utf-8"))
    pynescript.parse(SRC.read_text(encoding="utf-8"))
