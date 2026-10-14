"""Rate limits, kill switch, and dry-run for desktop UI automation (FastMCP + sampling amplification).

Vendor "My Computer"-style products add guardrails; this module adds **server-side** belts for
self-hosted pywinauto-mcp. See mcp-central-docs: patterns/windows_computer_use_mcp_SAFETY.md
"""

from __future__ import annotations

import os
import time
from collections import deque
from typing import Any

# --- Environment (document in README + central docs) ---
ENV_KILL_SWITCH = "windows_computer_use_mcp_KILL_SWITCH"
ENV_MAX_PER_MINUTE = "windows_computer_use_mcp_MAX_ACTIONS_PER_MINUTE"
ENV_DRY_RUN = "windows_computer_use_mcp_DRY_RUN"
# When set (e.g. 1), server registers `automation_face` if face deps are installed.
ENV_ENABLE_FACE = "windows_computer_use_mcp_ENABLE_FACE"
# When set (e.g. 1), server registers `global_keylogger` (session-wide keyboard capture).
ENV_ENABLE_KEYLOGGER = "windows_computer_use_mcp_ENABLE_KEYLOGGER"
# Resource hardening (BUG-071): bounds for background watchers, concurrent
# missions, and host-health reporting. All overridable, all fail-open.
ENV_MAX_WATCHERS = "windows_computer_use_mcp_MAX_WATCHERS"
ENV_MIN_WATCH_INTERVAL_S = "windows_computer_use_mcp_MIN_WATCH_INTERVAL_S"
ENV_MAX_WATCH_TIMEOUT_S = "windows_computer_use_mcp_MAX_WATCH_TIMEOUT_S"
ENV_MAX_CONCURRENT_MISSIONS = "windows_computer_use_mcp_MAX_CONCURRENT_MISSIONS"

DEFAULT_MAX_WATCHERS = 8
DEFAULT_MIN_WATCH_INTERVAL_S = 0.5
DEFAULT_MAX_WATCH_TIMEOUT_S = 3600.0
DEFAULT_MAX_CONCURRENT_MISSIONS = 2


def _truthy(val: str | None) -> bool:
    if val is None:
        return False
    return val.lower() in ("1", "true", "yes", "on")


def is_face_tool_enabled() -> bool:
    """Whether the operator opted in to exposing the face-recognition tool (see docs/SAFETY.md §5)."""
    return _truthy(os.getenv(ENV_ENABLE_FACE))


def is_keylogger_tool_enabled() -> bool:
    """Whether the operator opted in to exposing the global keylogger tool (high-risk; off by default)."""
    return _truthy(os.getenv(ENV_ENABLE_KEYLOGGER))


class MutationGate:
    """Sliding window: mutating UI actions per rolling 60s + lifetime counter."""

    def __init__(self) -> None:
        self._times: deque[float] = deque()
        self._total: int = 0

    def reset_window(self) -> None:
        self._times.clear()

    def snapshot(self) -> dict[str, Any]:
        now = time.time()
        while self._times and now - self._times[0] > 60.0:
            self._times.popleft()
        cap = int(os.getenv(ENV_MAX_PER_MINUTE, "120"))
        return {
            "actions_last_60s": len(self._times),
            "max_actions_per_minute": cap,
            "total_mutations_session": self._total,
            "kill_switch": _truthy(os.getenv(ENV_KILL_SWITCH)),
            "dry_run": _truthy(os.getenv(ENV_DRY_RUN)),
        }

    def before_mutation(self, *, read_only: bool) -> dict[str, Any]:
        """Return whether to execute a mutating pyautogui/pywinauto action."""
        if read_only:
            return {"allow": True, "dry_run": False, "code": "ok"}

        if _truthy(os.getenv(ENV_KILL_SWITCH)):
            return {
                "allow": False,
                "dry_run": False,
                "code": "kill_switch",
                "message": f"{ENV_KILL_SWITCH}=1 blocks all mutating automation.",
            }

        if _truthy(os.getenv(ENV_DRY_RUN)):
            self._record()
            return {
                "allow": True,
                "dry_run": True,
                "code": "dry_run",
                "message": f"{ENV_DRY_RUN}=1: mutation not executed; counted for metrics.",
            }

        cap = int(os.getenv(ENV_MAX_PER_MINUTE, "120"))
        now = time.time()
        while self._times and now - self._times[0] > 60.0:
            self._times.popleft()
        if len(self._times) >= cap:
            return {
                "allow": False,
                "dry_run": False,
                "code": "rate_limit",
                "message": f"Exceeded {cap} mutating actions per rolling 60s. Slow down or raise {ENV_MAX_PER_MINUTE}.",
            }
        self._record()
        return {"allow": True, "dry_run": False, "code": "ok"}

    def _record(self) -> None:
        self._times.append(time.time())
        self._total += 1


_gate = MutationGate()


def get_gate() -> MutationGate:
    return _gate


def before_mutation(*, read_only: bool) -> dict[str, Any]:
    return _gate.before_mutation(read_only=read_only)


def gate_invasive_monitoring() -> dict[str, Any]:
    """Kill switch and dry-run for surveillance-style tools (no rate-limit counter)."""
    if _truthy(os.getenv(ENV_KILL_SWITCH)):
        return {
            "allow": False,
            "dry_run": False,
            "code": "kill_switch",
            "message": f"{ENV_KILL_SWITCH}=1 blocks invasive monitoring tools.",
        }
    if _truthy(os.getenv(ENV_DRY_RUN)):
        return {
            "allow": True,
            "dry_run": True,
            "code": "dry_run",
            "message": f"{ENV_DRY_RUN}=1: monitoring action not executed.",
        }
    return {"allow": True, "dry_run": False, "code": "ok"}


# --- Resource hardening (BUG-071) ---

import threading as _threading

_MISSION_SLOTS_LOCK = _threading.Lock()
_MISSION_ACTIVE = 0


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def try_claim_mission_slot() -> tuple[bool, int]:
    """Non-blocking claim of one mission execution slot.

    Returns (claimed, active_count). Extra concurrent missions get a clean
    `blocked` instead of piling screenshot/LLM loops onto a loaded host.
    """
    global _MISSION_ACTIVE
    cap = _env_int(ENV_MAX_CONCURRENT_MISSIONS, DEFAULT_MAX_CONCURRENT_MISSIONS)
    with _MISSION_SLOTS_LOCK:
        if _MISSION_ACTIVE >= cap:
            return False, _MISSION_ACTIVE
        _MISSION_ACTIVE += 1
        return True, _MISSION_ACTIVE


def release_mission_slot() -> int:
    """Release a previously claimed mission slot. Returns active count."""
    global _MISSION_ACTIVE
    with _MISSION_SLOTS_LOCK:
        _MISSION_ACTIVE = max(0, _MISSION_ACTIVE - 1)
        return _MISSION_ACTIVE


def with_mission_slot(fn):
    """Async decorator: bound concurrent mission/workflow executions.

    Extra callers get a clean `blocked` instead of piling screenshot and
    sampling loops onto a loaded host. Import ToolResult lazily to avoid
    import cycles (safety.py is imported by tool modules).
    """
    import functools

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        from windows_computer_use_mcp.tools.models import ToolResult

        claimed, active = try_claim_mission_slot()
        if not claimed:
            cap = _env_int(ENV_MAX_CONCURRENT_MISSIONS, DEFAULT_MAX_CONCURRENT_MISSIONS)
            return ToolResult(
                status="blocked",
                message=f"Mission concurrency cap reached ({active}/{cap} running).",
                recovery_tip="Wait for the running mission (status op), cancel it, "
                f"or raise {ENV_MAX_CONCURRENT_MISSIONS}.",
            )
        try:
            return await fn(*args, **kwargs)
        finally:
            release_mission_slot()

    return wrapper


def watcher_limits() -> dict[str, Any]:
    """Effective watcher bounds (count cap, min interval, max timeout)."""
    return {
        "max_watchers": _env_int(ENV_MAX_WATCHERS, DEFAULT_MAX_WATCHERS),
        "min_interval_s": _env_float(ENV_MIN_WATCH_INTERVAL_S, DEFAULT_MIN_WATCH_INTERVAL_S),
        "max_timeout_s": _env_float(ENV_MAX_WATCH_TIMEOUT_S, DEFAULT_MAX_WATCH_TIMEOUT_S),
    }


def resource_snapshot() -> dict[str, Any]:
    """Host CPU/RAM right now. Never raises: psutil missing or error yields
    an explicit `unavailable` marker instead of a 500."""
    try:
        import psutil

        return {
            "available": True,
            "cpu_percent": round(float(psutil.cpu_percent(interval=None)), 1),
            "ram_percent": round(float(psutil.virtual_memory().percent), 1),
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}
