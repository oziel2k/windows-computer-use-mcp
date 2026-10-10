#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build the PyInstaller sidecar for the windows-computer-use-mcp Tauri operator shell.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Triple = "x86_64-pc-windows-msvc"

Write-Host "=== windows-computer-use-mcp sidecar build ===" -ForegroundColor Cyan

Push-Location $Root
try {
    # Pitfall #13: never `uv run pyinstaller` (isolated uv-tool env, blind to
    # project packages). The venv exe is the only sanctioned invoker.
    $pyiExe = "$Root\.venv\Scripts\pyinstaller.exe"
    if (-not (Test-Path -LiteralPath $pyiExe)) {
        Write-Host "-> Installing PyInstaller into venv..." -ForegroundColor Yellow
        uv pip install --project $Root pyinstaller "charset-normalizer>=3.4.5"
    }
    $pi = & $pyiExe --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller venv exe broken: $pi" }
    else {
        Write-Host "-> PyInstaller: $pi" -ForegroundColor Gray
    }

    Remove-Item -Recurse -Force "$Root\build\windows-computer-use-backend" -ErrorAction SilentlyContinue
    Remove-Item -Force "$Root\dist\windows-computer-use-backend.exe" -ErrorAction SilentlyContinue

    Write-Host "-> Running PyInstaller..." -ForegroundColor Yellow
    & $pyiExe windows-computer-use-backend.spec --clean --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }

    $src = "$Root\dist\windows-computer-use-backend.exe"
    $resourceDir = "$Root\web_sota\src-tauri\resources"
    $devDir = "$Root\web_sota\src-tauri\binaries"
    $bundled = "$resourceDir\windows-computer-use-backend.exe"
    $devCopy = "$devDir\windows-computer-use-backend-$Triple.exe"

    if (-not (Test-Path $src)) { throw "Build output not found: $src" }

    New-Item -ItemType Directory -Path $resourceDir -Force | Out-Null
    New-Item -ItemType Directory -Path $devDir -Force | Out-Null
    Copy-Item $src $bundled -Force
    Copy-Item $src $devCopy -Force

    $sizeMB = [math]::Round((Get-Item $bundled).Length / 1MB, 1)
    Write-Host "=== Backend embedded ===" -ForegroundColor Green
    Write-Host "  bundle resource: $bundled ($sizeMB MB)" -ForegroundColor Cyan
    Write-Host "  dev fallback:    $devCopy" -ForegroundColor Gray

    # Gate 0: backend exe must exist and exceed 5 MB (catches runt/0-byte builds).
    if ($sizeMB -lt 5) { throw "Backend exe suspiciously small ($sizeMB MB) - broken PyInstaller output" }

    # Stale shadow: a flat copy in target/release would shadow resources/ at resolve time.
    Remove-Item -Force "$Root\web_sota\src-tauri\target\release\windows-computer-use-backend.exe" -ErrorAction SilentlyContinue

    # Gate 1: smoke-test the frozen binary on an ephemeral port.
    Write-Host "-> Smoke-testing frozen binary..." -ForegroundColor Yellow
    $env:MCP_PORT = "11999"; $env:MCP_HOST = "127.0.0.1"
    $smoke = Start-Process -FilePath $bundled -NoNewWindow -PassThru -RedirectStandardError "$Root\dist\pyi-crash.log"
    $ready = $false; $elapsed = 0
    while ($elapsed -lt 60) {
        Start-Sleep -Milliseconds 500; $elapsed += 0.5
        if ($smoke.HasExited) { break }
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:11999/api/v1/health" -TimeoutSec 3 -UseBasicParsing
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
    }
    $env:MCP_PORT = $null; $env:MCP_HOST = $null
    if ($smoke.HasExited) {
        $crash = Get-Content "$Root\dist\pyi-crash.log" -Raw -ErrorAction SilentlyContinue
        throw "Frozen binary crashed on launch: $crash"
    }
    if (-not $ready) { try { $smoke.Kill() } catch {}; throw "Frozen binary never opened :11999 within 60s" }
    try { $smoke.Kill() } catch {}
    Write-Host "  smoke PASS (health 200 on :11999)" -ForegroundColor Green
}
finally {
    Pop-Location
}
