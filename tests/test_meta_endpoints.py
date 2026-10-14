"""Contract tests for fleet-standard meta endpoints (assfix 2026-10-10).

Covers: /health version single-source, /shutdown (subprocess: 200 + exit),
/capabilities shape, /skills real content, /llm/discover + /onboarding shape,
/llm/chat/stream error framing without a live LLM.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

import httpx
from fastapi.testclient import TestClient

from windows_computer_use_mcp.app import package_version
from windows_computer_use_mcp.server import app

client = TestClient(app, raise_server_exceptions=False)


def test_health_version_single_source() -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["version"] == package_version()
    assert package_version() == "0.8.0"


def test_capabilities_shape() -> None:
    body = client.get("/api/v1/capabilities").json()
    assert body["backend_port"] == 10789
    assert body["mcp_path"] == "/mcp"
    assert body["tool_count"] >= 18
    assert "automation_windows" in body["tools"]
    assert body["features"]["shutdown"] is True


def test_skills_real_content() -> None:
    body = client.get("/api/v1/skills").json()
    assert body["configured"] is True
    assert body["count"] >= 1
    first = body["skills"][0]
    assert first["uri"].startswith("skill://")
    assert first["chars"] > 1000


def test_discover_shape() -> None:
    body = client.get("/api/v1/llm/discover").json()
    ids = {p["id"] for p in body["providers"]}
    assert {"ollama", "lmstudio"} <= ids
    assert "gpu_present" in body


def test_onboarding_shape() -> None:
    body = client.get("/api/v1/llm/onboarding").json()
    assert len(body["facts"]) >= 2
    assert "recommended_path" in body
    assert "providers" in body


def test_chat_stream_error_frame_without_llm() -> None:
    # Closed loopback port: must arrive as SSE error frame, not a hang/500.
    r = client.post(
        "/api/v1/llm/chat/stream",
        json={"model": "probe", "messages": [{"role": "user", "content": "hi"}], "base_url": "http://127.0.0.1:9/v1"},
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    assert '"error"' in r.text
    assert r.text.strip().endswith("data: [DONE]")


def test_chat_stream_rejects_non_loopback() -> None:
    r = client.post(
        "/api/v1/llm/chat/stream",
        json={
            "model": "probe",
            "messages": [{"role": "user", "content": "hi"}],
            "base_url": "http://example.com:11434/v1",
        },
    )
    assert r.status_code == 400


_SHUTDOWN_PORT = 18097


def test_shutdown_exits_process() -> None:
    """Launch real uvicorn, POST /shutdown, assert 200 + process gone."""
    env = dict(os.environ, MCP_PORT=str(_SHUTDOWN_PORT))
    proc = subprocess.Popen(
        [sys.executable, "-m", "windows_computer_use_mcp.server"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 90
        ok = False
        while time.time() < deadline:
            try:
                r = httpx.get(f"http://127.0.0.1:{_SHUTDOWN_PORT}/api/v1/health", timeout=3)
                if r.status_code == 200:
                    ok = True
                    break
            except httpx.HTTPError:
                time.sleep(2)
        assert ok, "backend never became healthy"
        r = httpx.post(f"http://127.0.0.1:{_SHUTDOWN_PORT}/api/v1/shutdown", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "shutting down"
        proc.wait(timeout=15)
        assert proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)
