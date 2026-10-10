"""Fleet-standard meta endpoints: shutdown, capabilities, skills.

- POST /shutdown: orderly self-termination for the NSSM/fleet launcher.
- GET /capabilities: standard shape consumed by fleet dashboards.
- GET /skills: domain skill files served to skill-first chat clients.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from windows_computer_use_mcp.app import package_version

logger = logging.getLogger(__name__)

router = APIRouter(tags=["meta"])

BACKEND_PORT = int(os.environ.get("MCP_PORT", os.environ.get("PORT", "10789")))
FRONTEND_PORT = int(os.environ.get("WEB_PORT", os.environ.get("VITE_PORT", "10788")))


@router.post("/shutdown")
async def shutdown() -> dict[str, Any]:
    """Orderly self-termination.

    Responds 200 immediately, then exits the process ~500 ms later so
    in-flight responses flush. Used by the fleet launcher before
    NSSM restarts so crawlers/DB writers checkpoint instead of dying
    mid-write.
    """
    loop = asyncio.get_running_loop()
    loop.call_later(0.5, lambda: os._exit(0))
    return {"status": "shutting down", "detail": "process exits in ~500 ms"}


@router.get("/capabilities")
async def capabilities() -> dict[str, Any]:
    """Standard capability shape for fleet dashboards and IDE clients."""
    from windows_computer_use_mcp.app import app as mcp_app

    tools: list[str] = []
    if mcp_app is not None:
        try:
            registered = await mcp_app.list_tools()
            tools = sorted(t.name for t in registered)
        except Exception as e:
            logger.debug("capabilities tool listing failed: %s", e)
    return {
        "name": "windows-computer-use-mcp",
        "version": package_version(),
        "backend_port": BACKEND_PORT,
        "frontend_port": FRONTEND_PORT,
        "mcp_path": "/mcp",
        "rest_base": "/api/v1",
        "tools": tools,
        "tool_count": len(tools),
        "features": {
            "chat": True,
            "chat_stream": True,
            "llm_discover": True,
            "skills": True,
            "evidence": True,
            "diagnostics": True,
            "shutdown": True,
        },
    }


def _skills_dir() -> Path | None:
    """Locate the repo skills/ dir (env override, dev-tree, or cwd)."""
    override = os.environ.get("PYWINAUTO_SKILLS_DIR", "")
    if override and Path(override).is_dir():
        return Path(override)
    here = Path(__file__).resolve()
    # .../src/windows_computer_use_mcp/api/v1/endpoints/meta.py -> parents[5] is repo root
    candidates = [here.parents[5] / "skills", Path.cwd() / "skills"]
    for cand in candidates:
        if cand.is_dir():
            return cand
    return None


@router.get("/skills")
async def list_skills() -> dict[str, Any]:
    """Domain skills for skill-first chat prompt construction."""
    skills: list[dict[str, Any]] = []
    skills_dir = _skills_dir()
    if skills_dir is not None:
        for md in sorted(skills_dir.glob("*/SKILL.md")):
            try:
                text = md.read_text(encoding="utf-8")
            except OSError as e:
                logger.debug("skills read failed for %s: %s", md, e)
                continue
            skills.append(
                {
                    "name": md.parent.name,
                    "uri": f"skill://{md.parent.name}",
                    "chars": len(text),
                    "content": text,
                }
            )
    return {"skills": skills, "count": len(skills), "configured": skills_dir is not None}
