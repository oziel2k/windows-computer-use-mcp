"""Pass-2 coverage tests: annotations, request models, approval state, presence.

All hardware-free (no UIA, camera, or OCR). Targets modules that pull
coverage toward the 30% gate without touching the desktop.
"""

import pytest
from pydantic import ValidationError


class TestAnnotations:
    """Shared annotation constants use real MCP hint keys."""

    def test_readonly_local(self):
        from windows_computer_use_mcp.tools._annotations import _READONLY_LOCAL

        assert _READONLY_LOCAL["readOnlyHint"] is True
        assert _READONLY_LOCAL["openWorldHint"] is False

    def test_mutating_local(self):
        from windows_computer_use_mcp.tools._annotations import _MUTATING_LOCAL

        assert _MUTATING_LOCAL["readOnlyHint"] is False
        assert _MUTATING_LOCAL["destructiveHint"] is False
        assert _MUTATING_LOCAL["openWorldHint"] is False

    def test_destructive_local(self):
        from windows_computer_use_mcp.tools._annotations import _DESTRUCTIVE_LOCAL

        assert _DESTRUCTIVE_LOCAL["readOnlyHint"] is False
        assert _DESTRUCTIVE_LOCAL["destructiveHint"] is True

    def test_all_values_bool(self):
        from windows_computer_use_mcp.tools import _annotations

        for name in (
            "_READONLY_LOCAL",
            "_READONLY_REMOTE",
            "_MUTATING_LOCAL",
            "_MUTATING_REMOTE",
            "_DESTRUCTIVE_LOCAL",
        ):
            hints = getattr(_annotations, name)
            assert all(isinstance(v, bool) for v in hints.values()), name


class TestWindowRequest:
    """WindowOperationRequest validation (representative portmanteau model)."""

    def test_list_minimal(self):
        from windows_computer_use_mcp.tools.models import WindowOperationRequest

        req = WindowOperationRequest(operation="list")
        assert req.operation == "list"
        assert req.handle is None
        assert req.partial is True

    def test_find_with_title(self):
        from windows_computer_use_mcp.tools.models import WindowOperationRequest

        req = WindowOperationRequest(operation="find", title="Notepad", partial=True)
        assert req.title == "Notepad"

    def test_invalid_operation_rejected(self):
        from windows_computer_use_mcp.tools.models import WindowOperationRequest

        with pytest.raises(ValidationError):
            WindowOperationRequest(operation="nuke_everything")

    def test_position_coords(self):
        from windows_computer_use_mcp.tools.models import WindowOperationRequest

        req = WindowOperationRequest(operation="position", handle=123, x=10, y=20, width=800, height=600)
        assert req.x == 10
        assert req.width == 800


class TestApprovalState:
    """HITL approval window (app.py, no automation executed)."""

    def test_fresh_not_approved(self, monkeypatch):
        from windows_computer_use_mcp.app import ApprovalState

        monkeypatch.delenv("windows_computer_use_mcp_BYPASS_HITL", raising=False)
        assert ApprovalState().is_approved() is False

    def test_window_approved(self, monkeypatch):
        from windows_computer_use_mcp.app import ApprovalState

        monkeypatch.delenv("windows_computer_use_mcp_BYPASS_HITL", raising=False)
        state = ApprovalState()
        state.set_safe_window(5)
        assert state.is_approved() is True

    def test_approve_tool_returns_window(self, monkeypatch):
        from windows_computer_use_mcp.app import approval_state, approve_automation

        monkeypatch.delenv("windows_computer_use_mcp_BYPASS_HITL", raising=False)
        approval_state.safe_window_until = 0.0
        result = approve_automation(duration_minutes=5)
        assert result["status"] == "success"
        assert "message" in result
        assert approval_state.is_approved() is True
        approval_state.clear()


class TestPresenceMonitor:
    """Presence state machine with isolated state file (no camera)."""

    def test_arm_disarm_cycle(self, tmp_path):
        from windows_computer_use_mcp.presence import PresenceMonitor

        mon = PresenceMonitor(state_file=tmp_path / "presence.json")
        assert mon.disarm()["armed"] is False
        assert mon.arm()["armed"] is True
        assert mon.status()["armed"] is True
        assert mon.disarm()["armed"] is False

    def test_set_timeouts_clamps(self, tmp_path):
        from windows_computer_use_mcp.presence import PresenceMonitor

        mon = PresenceMonitor(state_file=tmp_path / "presence.json")
        out = mon.set_timeouts(grace_s=600, lock_timeout_s=100)
        assert out["lock_timeout_s"] >= out["grace_s"]
