# Configuration — windows-computer-use-mcp

Backend port **10789**, frontend port **10788** (registry:
`mcp-central-docs/operations/WEBAPP_PORTS.md`). Never hardcode other ports.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `MCP_PORT` / `PORT` | `10789` | Backend HTTP bind port (server.py, run_server.py) |
| `MCP_HOST` / `HOST` | `127.0.0.1` | Backend bind host |
| `WEB_PORT` / `VITE_PORT` | `10788` | Frontend port (capabilities + fleet-start) |
| `PYWINAUTO_LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | Default chat-completion upstream (Ollama) |
| `PYWINAUTO_SKILLS_DIR` | `<repo>/skills` | Override for `GET /api/v1/skills` content |
| `windows_computer_use_mcp_BYPASS_HITL` | unset | `1`/`true`/`yes` skips HITL approval (trusted runs only) |
| `windows_computer_use_mcp_KILL_SWITCH` | unset | Global stop flag (see automation_safety) |
| `windows_computer_use_mcp_DRY_RUN` | unset | Dry-run mode for mutating tools |
| `windows_computer_use_mcp_MAX_ACTIONS_PER_MINUTE` | `20` | Rate gate |
| `windows_computer_use_mcp_ENABLE_FACE` | unset | Opt-in face tools (needs `face` extra) |
| `windows_computer_use_mcp_ENABLE_KEYLOGGER` | unset | Opt-in keylogger tool |
| `FASTMCP_LOG_LEVEL` | `WARNING` | Set by start.ps1 |
| `LOCALAPPDATA` | — | Log dir (`%LOCALAPPDATA%/pywinauto-mcp/logs`, rotating 10 MB x5) |

## Transports

- **stdio** (Claude Desktop): `python -m windows_computer_use_mcp` — probes the
  HTTP daemon first and proxies when it answers (`create_proxy`), else runs local.
- **HTTP** (webapp/Tauri/NSSM): `python -m windows_computer_use_mcp.server`
  (uvicorn, REST on `/api/v1/*`, MCP on `/mcp`).

## Start

- `.\start.ps1` — backend + frontend (dev).
- `.\start.ps1 -BackendOnly` — backend + `/api/v1/health` readiness wait (CI/smoke).
- NSSM service `mcp-pywinauto-mcp` (stopped by default; start on demand).
