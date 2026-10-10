# CUA Safe Re-enable Protocol

Date: 2026-10-10. Context: enabling the `cua` entry (pywinauto-mcp as an
opencode child) was followed by a full input lockup — mouse/keyboard dead,
Ctrl+Alt+Del dead, no BSOD, no kernel dump, File Explorer foregrounded.
CUA logs showed handshakes + ListTools only, no automation runs: cause
**unproven** (prime suspect: GPU/display freeze under local load, not the
MCP child). This protocol makes re-enable safe-by-default and turns any
recurrence into a diagnosable event.

## 0. Preconditions (do not skip)

- [ ] fileops/gitops healthy in opencode (daemons on 10742/10713 answer).
- [ ] No heavy local load running (Ollama pulls, builds, scans).
- [ ] A second observer ready: phone able to ping Goliath, camera ready.
- [ ] Know the forensics trio (see §4) before touching anything.

## 1. Enable in dry-run first

In `opencode.json`, `mcp.cua` — keep HITL **on** (no BYPASS), add guardrails:

```json
"cua": {
  "type": "local",
  "command": [
    "D:\\Dev\\repos\\pywinauto-mcp\\.venv\\Scripts\\python.exe",
    "-m",
    "windows_computer_use_mcp.main"
  ],
  "environment": {
    "windows_computer_use_mcp_DRY_RUN": "1",
    "windows_computer_use_mcp_MAX_ACTIONS_PER_MINUTE": "20"
  },
  "enabled": true,
  "timeout": 120000
}
```

Restart opencode. Run **read-only** tools only: `get_window_state`,
`screenshot`, `automation_safety(status)`. Confirm the safety endpoint
reports `dry_run: true`. If anything looks wrong, rollback (§5) — you have
lost nothing, nothing moved the mouse.

## 2. Single live action, watched

- Set `windows_computer_use_mcp_DRY_RUN` to `0`, restart opencode.
- Open Notepad yourself. HUD overlay is expected on automation calls.
- Approve a **5-minute** window only: `approve_automation(duration_minutes=5)`.
- Exactly one action: a single `click` on a known coordinate, then `type`
  one word. Confirm each result before the next.
- Failsafe stays armed: fling the cursor to the **upper-left corner** to
  abort (PyAutoGUI failsafe — only disabled if BYPASS_HITL=1, which you
  have NOT set).

## 3. What stays forbidden until further notice

- `automation_mission(run=...)` and `automation_macro(replay=...)`
  **unattended**. Missions only with you watching, HUD on, short approvals.
- `automation_watch(start, ...)` persistent watchers — capped server-side
  (BUG-071 hardening), but do not stack them.
- `BYPASS_HITL=1`, `KILL_SWITCH` untouched (stays 0 unless freezing —
  then 1 to block all mutating automation), face/keylogger stay opt-in/off.
- Never approve more than 15 minutes at a time. Never approve then walk away.

## 4. If input dies again — forensics before reset

Do these **before** reaching for the power button; they distinguish a GPU
freeze (likely, recoverable info) from a true hang:

1. **Caps Lock LED** — toggles = kernel alive, display/input path suspect.
   No toggle = deep hang.
2. **Ping Goliath from your phone** — replies = network stack alive.
3. **Note the clock time** to the minute (correlates with WER + Reliability
   Monitor + `service-stderr-*.log` afterwards).
4. Photo of the screen with your phone.

After reboot: Reliability Monitor at the noted time, WER queue
(`sysadminops_list_crash_dumps`), `%LOCALAPPDATA%\pywinauto-mcp\logs`
(10 MB × 5 rotating — the repo-root 3.4 GB log of Oct 2026 was a pre-fix
artifact, BUG-071, truncated 2026-10-10), and opencode's stderr for the
`cua` stdio child.

## 5. Rollback (60 seconds)

Set `mcp.cua.enabled` to `false` in `opencode.json`, restart opencode.
Keep a named `.bak` of any enabled variant first
(e.g. `opencode.json.cua-enabled-<date>.bak`). The 2026-10-10 incident
backup pattern is the template.
