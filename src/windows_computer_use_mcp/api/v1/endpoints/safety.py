"""REST mirror of MCP `automation_safety('status')` for the webapp."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

from windows_computer_use_mcp.app import approval_state
from windows_computer_use_mcp.safety import (
    ENV_DRY_RUN,
    ENV_ENABLE_FACE,
    ENV_KILL_SWITCH,
    ENV_MAX_CONCURRENT_MISSIONS,
    ENV_MAX_PER_MINUTE,
    ENV_MAX_WATCH_TIMEOUT_S,
    ENV_MAX_WATCHERS,
    ENV_MIN_WATCH_INTERVAL_S,
    get_gate,
    is_face_tool_enabled,
    resource_snapshot,
)

router = APIRouter(tags=["safety"])


def _watcher_census_safe() -> dict[str, Any]:
    try:
        from windows_computer_use_mcp.tools.portmanteau_watch import watcher_census

        return watcher_census()
    except Exception as e:
        return {"running": -1, "error": str(e)}


@router.get("/status", response_model=dict[str, Any])
async def safety_status() -> dict[str, Any]:
    """Counters, env flags, face opt-in, HITL window - same payload as MCP tool."""
    gate = get_gate()
    snap = gate.snapshot()
    return {
        "status": "success",
        "snapshot": snap,
        "env": {
            ENV_KILL_SWITCH: os.getenv(ENV_KILL_SWITCH),
            ENV_DRY_RUN: os.getenv(ENV_DRY_RUN),
            ENV_MAX_PER_MINUTE: os.getenv(ENV_MAX_PER_MINUTE),
            ENV_ENABLE_FACE: os.getenv(ENV_ENABLE_FACE),
            ENV_MAX_WATCHERS: os.getenv(ENV_MAX_WATCHERS),
            ENV_MIN_WATCH_INTERVAL_S: os.getenv(ENV_MIN_WATCH_INTERVAL_S),
            ENV_MAX_WATCH_TIMEOUT_S: os.getenv(ENV_MAX_WATCH_TIMEOUT_S),
            ENV_MAX_CONCURRENT_MISSIONS: os.getenv(ENV_MAX_CONCURRENT_MISSIONS),
        },
        "face_tool_opt_in": is_face_tool_enabled(),
        "hitl": {"safe_window_until": approval_state.safe_window_until},
        "resource": resource_snapshot(),
        "watchers": _watcher_census_safe(),
    }
