"""ASGI entry: REST API (`/api/v1/...`) + FastMCP streamable HTTP (`/mcp`).

Uvicorn target: ``windows_computer_use_mcp.server:app``

CLI (uvicorn-based HTTP with full REST API):
    python -m windows_computer_use_mcp.server [--port PORT]

Legacy CLI (pure FastMCP, no REST):
    python -m windows_computer_use_mcp.main --http --port PORT
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from windows_computer_use_mcp.api import api_router
from windows_computer_use_mcp.app import app as mcp_app
from windows_computer_use_mcp.app import package_version

# FastMCP HTTP app serves the MCP protocol. path="/" so the parent mount
# point (/mcp) is the only prefix — never path="/mcp" + mount("/mcp")
# (double-prefix 404 class, BUG-008).
_mcp_http = mcp_app.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Enter the FastMCP session manager inside the parent lifespan.

    Without this, real HTTP clients get `McpError: Session terminated`
    even though /health is 200 (BUG-038 class). Verified live against
    FastMCP 3.4.4: the composable handle is the Starlette sub-app's
    `lifespan(app)`, NOT `mcp.lifespan(app)` (zero-arg AggregateProvider
    handle on this version — wiring that one crashes startup).
    """
    async with _mcp_http.lifespan(app):
        yield


app = FastAPI(title="windows-computer-use-mcp", version=package_version(), lifespan=lifespan)

_cors_origins = [
    "http://127.0.0.1:10788",
    "http://localhost:10788",
    "http://goliath:10788",
    "http://127.0.0.1:10706",
    "http://localhost:10706",
    "http://goliath:10706",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
]
# Unconditional: Tauri WebView + LAN/Tailscale names must never depend on an
# env flag being set in the launching context.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https?://(tauri\.localhost|localhost|127\.0\.0\.1|goliath)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API router - serves /api/v1/health, /api/v1/diagnostics, etc.
app.include_router(api_router)

# FastMCP streamable HTTP endpoint - serves MCP protocol on /mcp.
# Single mount only; verified live with POST /mcp (initialize) + bare GET.
app.mount("/mcp", _mcp_http)


def main() -> None:
    """Start the FastAPI ASGI server with uvicorn (REST + MCP on /mcp)."""
    import uvicorn

    port = int(os.environ.get("MCP_PORT", os.environ.get("PORT", "10789")))
    host = os.environ.get("MCP_HOST", os.environ.get("HOST", "127.0.0.1"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
