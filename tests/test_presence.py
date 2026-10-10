"""Presence state machine (human-presence detection). No camera, no dlib."""

from __future__ import annotations

import time

from windows_computer_use_mcp.presence import PresenceMonitor


def _mon(tmp_path, **kw):
    return PresenceMonitor(state_file=tmp_path / "presence.json", **kw)


def test_disarmed_tick_never_locks(tmp_path) -> None:
    m = _mon(tmp_path)
    out = m.tick([], now=1000.0)
    assert out["status"] == "disarmed"
    assert out["acted"] is None


def test_present_and_coffee_grace(tmp_path) -> None:
    m = _mon(tmp_path)
    m.arm()
    out = m.tick([{"name": "sandra"}], now=2000.0)
    assert out["status"] == "present"
    out = m.tick([], now=2000.0 + 60.0)  # 1 min gone: within 300 s grace
    assert out["status"] == "present"
    assert out["acted"] is None


def test_away_short_between_grace_and_lock(tmp_path) -> None:
    m = _mon(tmp_path)
    m.arm()
    m.tick([{"name": "sandra"}], now=3000.0)
    out = m.tick([], now=3000.0 + 400.0)  # past grace 300, before lock 900
    assert out["status"] == "away-short"
    assert out["acted"] is None
    assert "grace" in out["recommendation"]


def test_away_long_recommends_but_does_not_lock_by_default(tmp_path) -> None:
    m = _mon(tmp_path)
    m.arm()
    m.tick([{"name": "sandra"}], now=4000.0)
    out = m.tick([], now=4000.0 + 901.0)
    assert out["status"] == "away-long"
    assert out["acted"] is None
    assert out["recommendation"] == "lock workstation"


def test_set_timeouts_and_clamp(tmp_path) -> None:
    m = _mon(tmp_path)
    out = m.set_timeouts(60.0, 30.0, None)  # lock < grace clamps up
    assert out["lock_timeout_s"] == 60.0
    assert out["grace_s"] == 60.0
    out = m.set_timeouts(None, None, True)
    assert out["auto_lock"] is True


def test_state_persists_across_instances(tmp_path) -> None:
    m = _mon(tmp_path)
    m.arm()
    m.set_timeouts(120.0, 600.0, False)
    m2 = _mon(tmp_path)
    st = m2.status()
    assert st["armed"] is True
    assert st["grace_s"] == 120.0
    assert st["lock_timeout_s"] == 600.0


def test_disarm_stops_reporting(tmp_path) -> None:
    m = _mon(tmp_path)
    m.arm()
    m.disarm()
    assert m.status()["status"] == "disarmed"
    assert time.time() > 0  # wall clock sanity for away_for math
