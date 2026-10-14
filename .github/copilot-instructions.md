# windows-computer-use-mcp — Copilot instructions

Native Windows UI automation over MCP: 20 portmanteau tools, all with an
`operation` enum. Start sessions by recalling: `automation_windows` (find/focus),
`get_desktop_state` (element tree), `approve_automation` before any click/type.
Mutating runs need HITL approval or `windows_computer_use_mcp_BYPASS_HITL=1`.
Backend: FastAPI on :10789 (`/api/v1/*`, MCP on `/mcp`); frontend :10788.
Verify with `uv run --no-sync ruff check src/` and `pytest tests/ -q --no-cov`.
Close of work: commit per repo AGENTS.md, never leave the tree dirty.
