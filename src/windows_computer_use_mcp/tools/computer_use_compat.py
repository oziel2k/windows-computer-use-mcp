"""Claude Code computer-use style window screenshot (Cua parity Phase 4)."""

import logging
import time

try:
    from windows_computer_use_mcp.app import app
    from windows_computer_use_mcp.tools._annotations import _READONLY_LOCAL
    from windows_computer_use_mcp.tools.models import ToolResult, VisualOperationRequest
    from windows_computer_use_mcp.tools.portmanteau_visual import automation_visual

    logger = logging.getLogger(__name__)
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error("computer_use_compat import failed: %s", e)
    app = None


if app is not None:

    @app.tool(
        name="cua_computer_use_screenshot",
        description="""Window-scoped screenshot for Claude Code computer-use style grounding.

Requires window_handle (HWND). Does not activate the window when windows_computer_use_mcp_DISPATCH=background.
Wraps automation_visual(screenshot) with return_base64=true.

## Return Format
{"status": "success" | "error", "message": str, "data": {"screenshot_base64": str, "compat": str}, "recovery_tip": str | null}

## Examples
- cua_computer_use_screenshot(window_handle=123456) -> {"status": "success", "data": {"screenshot_base64": "...", ...}}
""",
        annotations=_READONLY_LOCAL,
    )
    def cua_computer_use_screenshot(
        window_handle: int,
        format: str = "png",
    ) -> ToolResult:
        req = VisualOperationRequest(
            operation="screenshot",
            window_handle=window_handle,
            format=format,
            return_base64=True,
        )
        result = automation_visual(req)
        if result.status == "success" and result.data:
            result.data["compat"] = "claude-computer-use-window-only"
            result.data["timestamp"] = time.time()
        return result
