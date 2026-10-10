"""Local LLM bridge: OpenAI-compatible API (Ollama, LM Studio) for the web_sota chat UI."""

from __future__ import annotations

import logging
import os
from typing import Any, Literal
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from windows_computer_use_mcp.llm_repo_context import REPO_CONTEXT_MARKDOWN

logger = logging.getLogger(__name__)

router = APIRouter(tags=["llm"])

DEFAULT_BASE = os.getenv("PYWINAUTO_LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")

REFINER_SYSTEM = """You are a prompt-refinement assistant for operators using pywinauto-mcp (Windows desktop automation).
Rewrite the user's message to be clearer, more specific, and easier for a coding/automation assistant to act on.
Output only the refined prompt text - no quotes, no preamble, no markdown fences."""


def _allowed_llm_base(url: str) -> bool:
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False
        h = (p.hostname or "").lower()
        return h in ("127.0.0.1", "localhost", "::1")
    except Exception:
        return False


def _resolve_base(base_url: str | None) -> str:
    raw = (base_url or DEFAULT_BASE).strip().rstrip("/")
    if not _allowed_llm_base(raw):
        raise HTTPException(
            status_code=400,
            detail="base_url must be http(s)://127.0.0.1, localhost, or ::1 (SSRF protection)",
        )
    return raw


class ChatMessage(BaseModel):
    """OpenAI-style chat message."""

    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Non-streaming chat completion request."""

    model: str = Field(..., description="Model id as reported by /v1/models")
    messages: list[ChatMessage]
    base_url: str | None = Field(None, description="OpenAI-compatible root, e.g. http://127.0.0.1:11434/v1")
    temperature: float | None = Field(0.7, ge=0, le=2)


class ChatResponse(BaseModel):
    """Assistant text or error string from the upstream LLM."""

    content: str | None = None
    model: str | None = None
    raw_error: str | None = None


class RefineRequest(BaseModel):
    """Single-shot prompt refinement request."""

    draft: str
    model: str
    base_url: str | None = None


@router.get("/config")
async def llm_config() -> dict[str, Any]:
    """Defaults for the web UI (Ollama vs LM Studio presets)."""
    return {
        "default_base_url": DEFAULT_BASE,
        "presets": [
            {"id": "ollama", "label": "Ollama", "base_url": "http://127.0.0.1:11434/v1"},
            {"id": "lmstudio", "label": "LM Studio", "base_url": "http://127.0.0.1:1234/v1"},
        ],
    }


@router.get("/repo-context")
async def repo_context() -> dict[str, str]:
    """Markdown block to inject as repository knowledge in system prompts."""
    return {"markdown": REPO_CONTEXT_MARKDOWN}


@router.get("/models")
async def list_models(
    base_url: str | None = Query(None, description="OpenAI-compatible API root"),
) -> dict[str, Any]:
    """Proxy GET /v1/models to the local LLM server."""
    base = _resolve_base(base_url)
    url = f"{base}/models"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url)
    except httpx.RequestError as e:
        logger.warning("LLM models fetch failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Could not reach LLM at {base}: {e}") from e

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text[:2000])

    try:
        data = r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Invalid JSON from LLM /models") from None
    return data


@router.post("/chat", response_model=ChatResponse)
async def chat_completions(body: ChatRequest) -> ChatResponse:
    """Proxy POST /v1/chat/completions (non-streaming)."""
    base = _resolve_base(body.base_url)
    url = f"{base}/chat/completions"
    payload: dict[str, Any] = {
        "model": body.model,
        "messages": [m.model_dump() for m in body.messages],
        "stream": False,
    }
    if body.temperature is not None:
        payload["temperature"] = body.temperature

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload)
    except httpx.RequestError as e:
        logger.warning("LLM chat failed: %s", e)
        return ChatResponse(content=None, raw_error=str(e))

    if r.status_code >= 400:
        return ChatResponse(content=None, raw_error=r.text[:4000])

    try:
        data = r.json()
    except Exception as e:
        return ChatResponse(content=None, raw_error=f"Invalid JSON: {e}")

    try:
        choice = data["choices"][0]
        msg = choice.get("message") or {}
        text = msg.get("content")
        return ChatResponse(content=text, model=data.get("model"))
    except (KeyError, IndexError, TypeError) as e:
        return ChatResponse(content=None, raw_error=f"Unexpected response shape: {e!s} - {data!s}"[:4000])


@router.post("/refine", response_model=ChatResponse)
async def refine_prompt(body: RefineRequest) -> ChatResponse:
    """One-shot prompt refinement using the same chat endpoint."""
    if not body.draft.strip():
        raise HTTPException(status_code=400, detail="draft is empty")

    req = ChatRequest(
        model=body.model,
        base_url=body.base_url,
        messages=[
            ChatMessage(role="system", content=REFINER_SYSTEM),
            ChatMessage(role="user", content=body.draft),
        ],
        temperature=0.3,
    )
    return await chat_completions(req)


_LLM_CANDIDATES = [
    {
        "id": "ollama",
        "label": "Ollama",
        "base_url": "http://127.0.0.1:11434/v1",
        "probe_url": "http://127.0.0.1:11434/api/tags",
        "probe_kind": "ollama-tags",
    },
    {
        "id": "lmstudio",
        "label": "LM Studio",
        "base_url": "http://127.0.0.1:1234/v1",
        "probe_url": "http://127.0.0.1:1234/v1/models",
        "probe_kind": "openai-models",
    },
]


async def _probe_candidate(client: httpx.AsyncClient, cand: dict[str, str]) -> dict[str, Any]:
    """Probe one local LLM server; never raises (fail-soft for dashboards)."""
    detected = False
    models: list[str] = []
    try:
        r = await client.get(cand["probe_url"])
        if r.status_code == 200:
            detected = True
            try:
                data = r.json()
                if cand["probe_kind"] == "ollama-tags":
                    models = [m["name"] for m in data.get("models", [])]
                else:
                    models = [m["id"] for m in data.get("data", [])]
            except Exception as e:
                logger.debug("llm discover %s model parse failed: %s", cand["id"], e)
    except httpx.RequestError as e:
        logger.debug("llm discover %s not reachable: %s", cand["id"], e)
    return {
        "id": cand["id"],
        "label": cand["label"],
        "base_url": cand["base_url"],
        "detected": detected,
        "models": models,
        "needs_key": False,
    }


@router.get("/discover")
async def discover_providers() -> dict[str, Any]:
    """Auto-detect local LLM providers (Ollama :11434, LM Studio :1234).

    Consumed by the chat UI on mount for the provider status indicator.
    """
    import shutil

    async with httpx.AsyncClient(timeout=2.0) as client:
        providers = [_probe_candidate(client, c) for c in _LLM_CANDIDATES]
        providers = [await p for p in providers]
    return {
        "providers": providers,
        "gpu_present": shutil.which("nvidia-smi") is not None,
    }


@router.get("/onboarding")
async def llm_onboarding() -> dict[str, Any]:
    """Fresh-install starter facts + recommended path for the under-hero cue."""
    disc = await discover_providers()
    any_detected = any(p["detected"] for p in disc["providers"])
    return {
        "facts": [
            "pywinauto-mcp automates native Windows UI: find windows, read elements, click, type, screenshot, OCR.",
            "Mutating actions need approve_automation first (or BYPASS_HITL=1 for trusted runs).",
            "Chat completions proxy through this backend; keys never leave the server.",
        ],
        "recommended_path": (
            "chat is ready" if any_detected else "start Ollama (ollama serve) or LM Studio, then reload chat"
        ),
        "providers": disc["providers"],
        "gpu_present": disc["gpu_present"],
        "docs": {
            "safety": "docs/SAFETY.md",
            "tools": "docs/TOOLS.md",
            "configuration": "docs/CONFIGURATION.md",
        },
    }


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    """Proxy POST /v1/chat/completions with stream=true as SSE.

    Passes upstream `data:` lines through untouched and closes with
    `data: [DONE]`. Upstream errors arrive as `data: {"error": ...}`.
    """
    import json

    base = _resolve_base(body.base_url)
    url = f"{base}/chat/completions"
    payload: dict[str, Any] = {
        "model": body.model,
        "messages": [m.model_dump() for m in body.messages],
        "stream": True,
    }
    if body.temperature is not None:
        payload["temperature"] = body.temperature

    async def gen():  # type: ignore[no-untyped-def]
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=payload) as r:
                    if r.status_code >= 400:
                        raw = (await r.aread()).decode("utf-8", "replace")[:4000]
                        yield f"data: {json.dumps({'error': raw})}\n\n"
                        return
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        if line.startswith(("data:", "event:", ":")) or line.strip() == "[DONE]":
                            yield f"{line}\n\n"
                        else:
                            yield f"data: {line}\n\n"
        except httpx.RequestError as e:
            logger.warning("LLM chat stream failed: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
