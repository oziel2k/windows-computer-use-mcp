# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for windows-computer-use-mcp backend sidecar (fleet pattern)."""

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

# Dynamic imports invisible to static analysis: mission _call_tool loads any
# portmanteau_* module by name at runtime; FastMCP/pydantic lazy-load chains.
_pywinauto_all = collect_submodules("windows_computer_use_mcp")
_fastmcp_all = collect_submodules("fastmcp")
_pydantic_all = collect_submodules("pydantic")
_cachetools_all = collect_all("cachetools")
_beartype_all = collect_all("beartype")

from PyInstaller.utils.hooks import copy_metadata

datas = [("src/windows_computer_use_mcp", "windows_computer_use_mcp")]
for pkg in (
    "fastmcp",
    "fastapi",
    "uvicorn",
    "pydantic",
    "starlette",
    "httpx",
    "prefab_ui",
    "pywinauto",
    "pygetwindow",
    "winrt_runtime",
    "winrt_windows_foundation",
    "winrt_windows_foundation_collections",
    "winrt_windows_storage",
    "winrt_windows_storage_streams",
    "winrt_windows_graphics_imaging",
    "winrt_windows_media_ocr",
    "winrt_windows_globalization",
):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        # Optional deps (e.g. winrt_*) may be absent; their hiddenimports
        # above are best-effort and the frozen app degrades gracefully.
        pass

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "windows_computer_use_mcp.server",
    "windows_computer_use_mcp.app",
    "windows_computer_use_mcp.api",
    "windows_computer_use_mcp.tools",
    "windows_computer_use_mcp.task_engine",
    "windows_computer_use_mcp.tools.portmanteau_task",
    "windows_computer_use_mcp.tools.portmanteau_windows",
    "windows_computer_use_mcp.tools.portmanteau_visual",
    "windows_computer_use_mcp.tools.portmanteau_keyboard",
    "windows_computer_use_mcp.tools.portmanteau_shortcut",
    "windows_computer_use_mcp.tools.portmanteau_system",
    "prefab_ui.app",
    "winrt",
    "winrt.runtime",
    "winrt.windows.foundation",
    "winrt.windows.foundation.collections",
    "winrt.windows.storage",
    "winrt.windows.storage.streams",
    "winrt.windows.graphics.imaging",
    "winrt.windows.media.ocr",
    "winrt.windows.globalization",
    "_strptime",
    "_datetime",
    "key_value",
    "cachetools",
    "beartype",
    "websockets",
    "h11",
    "jwt",
    "pytz",
    "jsonschema",
    "sqlite3",
    "joserfc",
    "joserfc.jwk",
    "joserfc.jwt",
    "mcp.types",
] + _pywinauto_all + _fastmcp_all + _pydantic_all + _cachetools_all[2] + _beartype_all[2]

a = Analysis(
    ["run_server.py"],
    pathex=["src"],
    datas=datas + _cachetools_all[0] + _beartype_all[0],
    binaries=_cachetools_all[1] + _beartype_all[1],
    hiddenimports=hiddenimports,
    hookspath=["scripts/pyinstaller_hooks"],
hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pandas", "scipy", "torch", "tensorflow"],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],

    name="windows-computer-use-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
