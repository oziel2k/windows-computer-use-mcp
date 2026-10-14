"""Resource hardening guards (BUG-071): mission slots, watcher caps, host snapshot.

No hardware beyond a normal Windows desktop; watcher threads poll the real
window list with short timeouts and are always stopped.
"""

from __future__ import annotations

import asyncio

import pytest

from windows_computer_use_mcp import safety
from windows_computer_use_mcp.safety import (
    release_mission_slot,
    resource_snapshot,
    try_claim_mission_slot,
    watcher_limits,
)


def test_mission_slot_cap_and_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(safety.ENV_MAX_CONCURRENT_MISSIONS, "1")
    claimed, active = try_claim_mission_slot()
    assert claimed is True
    assert active == 1
    claimed2, active2 = try_claim_mission_slot()
    assert claimed2 is False
    assert active2 == 1
    assert release_mission_slot() == 0
    claimed3, _ = try_claim_mission_slot()
    assert claimed3 is True
    release_mission_slot()


def test_mission_slot_invalid_env_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(safety.ENV_MAX_CONCURRENT_MISSIONS, "not-a-number")
    claimed, _ = try_claim_mission_slot()
    assert claimed is True
    release_mission_slot()


def test_watcher_limits_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        safety.ENV_MAX_WATCHERS,
        safety.ENV_MIN_WATCH_INTERVAL_S,
        safety.ENV_MAX_WATCH_TIMEOUT_S,
    ):
        monkeypatch.delenv(var, raising=False)
    limits = watcher_limits()
    assert limits["max_watchers"] == 8
    assert limits["min_interval_s"] == 0.5
    assert limits["max_timeout_s"] == 3600.0


def test_resource_snapshot_shape() -> None:
    snap = resource_snapshot()
    assert snap["available"] is True
    assert isinstance(snap["cpu_percent"], float)
    assert isinstance(snap["ram_percent"], float)
    assert 0.0 <= snap["cpu_percent"] <= 100.0
    assert 0.0 <= snap["ram_percent"] <= 100.0


def test_watcher_start_respects_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    from windows_computer_use_mcp.tools import portmanteau_watch as watch

    monkeypatch.setenv(safety.ENV_MAX_WATCHERS, "0")
    res = asyncio.run(
        watch.automation_watch(operation="start", condition="window_appears", target="no-such-window-xyz")
    )
    assert res.status == "blocked"
    assert "cap" in res.message.lower()


def test_watcher_start_clamps_interval_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from windows_computer_use_mcp.tools import portmanteau_watch as watch

    monkeypatch.setenv(safety.ENV_MAX_WATCHERS, "4")
    res = asyncio.run(
        watch.automation_watch(
            operation="start",
            condition="window_appears",
            target="no-such-window-xyz",
            interval=0.01,
            timeout=999999.0,
        )
    )
    assert res.status == "success"
    wid = res.data["watcher_id"]
    stored = watch._WATCHERS[wid]
    assert stored["interval"] == 0.5
    assert stored["timeout"] == 3600.0
    stop = asyncio.run(watch.automation_watch(operation="stop", watcher_id=wid))
    assert stop.status == "success"
