"""PyInstaller entry point -- dual transport.

HTTP mode (MCP_PORT or PORT set, e.g. by Tauri backend.rs): serve the full
REST+MCP app (windows_computer_use_mcp.server:app) via uvicorn. That is the
only mode that serves /api/v1/* which the operator UI needs.
Stdio mode (no env vars): pure FastMCP for Claude Desktop.
"""

import os
import sys

sys.path.insert(0, "src")

# Tell opentelemetry which context implementation to use before any import
# triggers it. Without this, PyInstaller's frozen environment cannot discover
# the contextvars context via entry points, causing StopIteration.
os.environ.setdefault("OTEL_PYTHON_CONTEXT", "contextvars_context")

# Eager-import stdlib C extensions that are lazy-imported by other modules
# and missed by PyInstaller's static analysis.
import _datetime  # noqa: F401
import _strptime  # noqa: F401

import cachetools  # noqa: F401

port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
if port:
    host = os.environ.get("MCP_HOST", "127.0.0.1")
    import uvicorn

    from windows_computer_use_mcp.server import app as asgi_app

    uvicorn.run(asgi_app, host=host, port=int(port), log_level="info")
else:
    from windows_computer_use_mcp.main import main

    main()
