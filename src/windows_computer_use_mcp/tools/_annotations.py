"""Shared MCP tool annotation constants (fleet TOOL_DESIGN_STANDARDS.md S9).

FastMCP 3.x accepts the raw MCP hint keys as the ``annotations=`` dict.
The earlier ``{"readonly": True}`` form is NOT an MCP annotation and is
silently ignored (server then advertises readOnlyHint=None). Use these.
"""

_READONLY_LOCAL = {"readOnlyHint": True, "openWorldHint": False}
_READONLY_REMOTE = {"readOnlyHint": True, "openWorldHint": True}
_MUTATING_LOCAL = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}
_MUTATING_REMOTE = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True}
_DESTRUCTIVE_LOCAL = {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False}
