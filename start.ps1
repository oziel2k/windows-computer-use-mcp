Param(
    [switch]$BackendOnly,
    [switch]$Headless,
    [int]$BackendPort = 10789,
    [int]$FrontendPort = 10788,
    [int]$ReadyTimeoutSec = 60
)
# windows-computer-use-mcp launcher (fleet standard).
#   start.ps1                 -> backend + frontend (dev)
#   start.ps1 -BackendOnly    -> backend only, waits for /api/v1/health (CI/smoke)
#   start.ps1 -Headless       -> -BackendOnly with hidden windows (scheduled runs)
# Backend: uvicorn HTTP via windows_computer_use_mcp.server (binds BackendPort).
# Health: GET /api/v1/health polled until 2xx (no fixed sleeps).

$ErrorActionPreference = "Stop"
if ($Headless) { $BackendOnly = $true }
$WindowStyle = if ($Headless) { "Hidden" } else { "Normal" }

Set-Location $PSScriptRoot
$env:FASTMCP_LOG_LEVEL = "WARNING"
$env:MCP_PORT = "$BackendPort"
Write-Host "Starting windows-computer-use-mcp (backend :$BackendPort)..." -ForegroundColor Cyan

# --- Zombie clear: free the backend port before binding ---
$stale = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
foreach ($targetPid in $stale) {
    if ($targetPid -ne $PID) {
        Write-Host "Stopping stale listener PID $targetPid on port $BackendPort" -ForegroundColor Yellow
        Stop-Process -Id $targetPid -Force -ErrorAction SilentlyContinue
    }
}

# --- Launch backend (uvicorn HTTP, binds BackendPort) ---
# Absolute uv path: bare `uv` is not on PATH in fresh child shells.
$uvExe = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
if (-not (Test-Path $uvExe)) { $uvExe = "uv" }
$backendArgs = @("-NoProfile", "-Command", "& '$uvExe' run --no-sync python -m windows_computer_use_mcp.server")
$backend = Start-Process powershell.exe -ArgumentList $backendArgs -WorkingDirectory $PSScriptRoot `
    -WindowStyle $WindowStyle -PassThru
Write-Host "Backend PID $($backend.Id)" -ForegroundColor Gray

# --- Readiness poll: GET /api/v1/health until 2xx (no fixed sleep) ---
$healthUrl = "http://127.0.0.1:$BackendPort/api/v1/health"
$deadline = (Get-Date).AddSeconds($ReadyTimeoutSec)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300) { $ready = $true; break }
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $ready) {
    Write-Host "Backend failed to answer $healthUrl within ${ReadyTimeoutSec}s" -ForegroundColor Red
    exit 1
}
Write-Host "Backend healthy: $healthUrl" -ForegroundColor Green

if ($BackendOnly) { return }

# --- Frontend (vite dev, same-origin proxy to backend) ---
Set-Location (Join-Path $PSScriptRoot "web_sota")
npm run dev
