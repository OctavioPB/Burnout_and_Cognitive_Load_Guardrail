#Requires -Version 5.1
<#
.SYNOPSIS
    Dev-stack launcher for the Burnout & Cognitive Load Guardrail platform.
.DESCRIPTION
    1.  Kill every process listening on required ports.
    2.  Load .env into the current process (child processes inherit vars).
    3.  Verify Docker daemon; try every known context until one responds.
    4.  Locate Python (.venv preferred, then system).
    5.  docker compose up -d --remove-orphans
    6.  Poll each container until healthy (or timeout).
    7.  Run alembic upgrade head (skipped if alembic not installed).
    8.  Open API server in a new PowerShell window (-EncodedCommand).
    9.  Open Vite frontend in a new PowerShell window (node directly).
    10. Open browser after 5-second delay.
    11. Print service URL summary.
.NOTES
    Run from the repo root:  .\demo.ps1
    Requires: Docker Desktop, Node >= 18, Python venv at .venv\

    All string literals in this file are ASCII-only.  PowerShell 5.1 reads
    UTF-8 files without BOM as CP1252; any multi-byte sequence whose last
    byte is 0x93 or 0x94 decodes to a smart-quote that PS treats as a string
    terminator, breaking the parser.  No Unicode characters are used here.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = $PSScriptRoot

# ---------------------------------------------------------------------------
# Colour helpers  (ASCII prefix glyphs only -- no Unicode)
# ---------------------------------------------------------------------------

function Write-Step { param([string]$Msg) Write-Host "`n  >> $Msg"   -ForegroundColor Cyan   }
function Write-Ok   { param([string]$Msg) Write-Host "     OK  $Msg" -ForegroundColor Green  }
function Write-Warn { param([string]$Msg) Write-Host "     !!  $Msg" -ForegroundColor Yellow }
function Write-Fail { param([string]$Msg) Write-Host "     XX  $Msg" -ForegroundColor Red    }

function Exit-Pause {
    param([string]$Msg)
    Write-Host ""
    Write-Fail $Msg
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# ---------------------------------------------------------------------------
# .env loader
# Reads KEY=VALUE lines; skips blanks and # comments.
# Strips one layer of surrounding single or double quotes from values.
# ---------------------------------------------------------------------------

function Import-DotEnv {
    param([string]$EnvFile)
    if (-not (Test-Path $EnvFile)) {
        Write-Warn ".env not found -- child processes will not inherit project env vars"
        return
    }
    $count = 0
    foreach ($raw in Get-Content $EnvFile) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith('#')) { continue }
        $eq = $line.IndexOf('=')
        if ($eq -le 0) { continue }
        $key = $line.Substring(0, $eq).Trim()
        $val = $line.Substring($eq + 1).Trim()
        if ($val.Length -ge 2) {
            $q = $val[0]
            if (($q -eq '"' -or $q -eq "'") -and $val[$val.Length - 1] -eq $q) {
                $val = $val.Substring(1, $val.Length - 2)
            }
        }
        [System.Environment]::SetEnvironmentVariable($key, $val, 'Process')
        $count++
    }
    Write-Ok "Loaded $count variables from .env"
}

# ---------------------------------------------------------------------------
# Port killer
# Parses  netstat -ano  for LISTENING entries on $Port.
# Calls Stop-Process -Force on each PID found.
# Guards against PID 0 and the script's own $PID.
# ---------------------------------------------------------------------------

function Stop-Port {
    param([int]$Port, [string]$Label)
    $hits = netstat -ano 2>$null |
            Where-Object { $_ -match "[:\s]$Port\s+\S+\s+LISTENING" }
    if (-not $hits) { return }
    foreach ($line in $hits) {
        if ($line -match '\s+(\d+)\s*$') {
            [int]$victim = $Matches[1]
            if ($victim -le 0 -or $victim -eq $PID) { continue }
            try {
                Stop-Process -Id $victim -Force -ErrorAction Stop
                Write-Ok "Port $Port ($Label) freed  [PID $victim killed]"
            } catch {
                Write-Warn "Could not kill PID $victim on port $Port -- $($_.Exception.Message)"
            }
        }
    }
}

# ---------------------------------------------------------------------------
# Docker daemon check
# Tries each known Docker context in order until one responds.
# Docker Desktop on Windows can be backed by either:
#   desktop-linux  ->  npipe:////./pipe/dockerDesktopLinuxEngine  (Linux VM)
#   default        ->  npipe:////./pipe/docker_engine             (WSL2)
# ---------------------------------------------------------------------------

function Assert-DockerRunning {
    # Try the currently active context first
    docker version | Out-Null
    if ($LASTEXITCODE -eq 0) { return }

    foreach ($ctx in @('desktop-linux', 'default')) {
        Write-Host "     trying Docker context '$ctx'..." -ForegroundColor DarkGray
        docker context use $ctx | Out-Null
        docker version | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Using Docker context: $ctx"
            return
        }
    }

    Exit-Pause "Docker daemon not reachable on any context.  Start Docker Desktop, wait for the whale icon to stop animating, then re-run."
}

# ---------------------------------------------------------------------------
# Container health poller
# Polls  docker inspect --format '{{.State.Health.Status}}'  every $Poll s.
# Returns $true when healthy; $false on 'unhealthy' or timeout.
# ---------------------------------------------------------------------------

function Wait-Healthy {
    param(
        [string]$Name,
        [int]   $Timeout = 180,
        [int]   $Poll    = 5
    )
    Write-Step "[$Name]  waiting to be healthy  (up to ${Timeout}s)"
    $elapsed = 0
    while ($elapsed -lt $Timeout) {
        $status = docker inspect --format '{{.State.Health.Status}}' $Name 2>$null
        switch ($status) {
            'healthy'   { Write-Ok "$Name -> healthy"; return $true }
            'unhealthy' {
                Write-Fail "$Name is unhealthy"
                Write-Warn "Run:  docker logs $Name"
                return $false
            }
        }
        $label = if ($status) { $status } else { '(not yet registered)' }
        Write-Host "     [${elapsed}s / ${Timeout}s]  $label" -ForegroundColor DarkGray
        Start-Sleep -Seconds $Poll
        $elapsed += $Poll
    }
    Write-Fail "Timed out after ${Timeout}s waiting for $Name"
    return $false
}

# ===========================================================================
#  LAUNCH SEQUENCE
# ===========================================================================

Clear-Host
Write-Host ""
Write-Host "  =======================================================" -ForegroundColor DarkCyan
Write-Host "  |  Burnout & Cognitive Load Guardrail -- Dev Launch   |" -ForegroundColor DarkCyan
Write-Host "  =======================================================" -ForegroundColor DarkCyan
Write-Host ""

Set-Location $RepoRoot

# -- 1. Load .env -------------------------------------------------------------

Write-Step "Loading environment variables..."
Import-DotEnv (Join-Path $RepoRoot '.env')

# -- 2. Kill processes on required ports --------------------------------------
#
# Only kill ports owned by processes THIS script starts (API and frontend).
# Docker container ports (2181, 9092, 8081, 5432, 6379) are released cleanly
# by 'docker compose down' in step 5.  Killing those ports here would hit
# Docker Desktop's networking proxy (vpnkit / com.docker.backend), crashing
# the daemon before we even get to use it.

Write-Step "Freeing local server ports..."
foreach ($entry in @(
    [pscustomobject]@{ Port = 8000; Label = 'API (uvicorn)'   },
    [pscustomobject]@{ Port = 5173; Label = 'Frontend (Vite)' }
)) { Stop-Port -Port $entry.Port -Label $entry.Label }

# -- 3. Verify Docker ---------------------------------------------------------

Write-Step "Checking Docker daemon..."
Assert-DockerRunning
Write-Ok "Docker daemon is up"

# -- 4. Locate Python ---------------------------------------------------------

Write-Step "Locating Python..."
$pythonExe = $null
foreach ($c in @(
    (Join-Path $RepoRoot '.venv\Scripts\python.exe'),
    (Join-Path $RepoRoot  'venv\Scripts\python.exe')
)) {
    if (Test-Path $c) { $pythonExe = $c; break }
}
if (-not $pythonExe) {
    $sys = Get-Command python -ErrorAction SilentlyContinue
    if ($sys) { $pythonExe = $sys.Source }
}
if (-not $pythonExe) {
    Exit-Pause "Python not found.  Run:  python -m venv .venv  then re-run demo.ps1"
}
Write-Ok "Python -> $pythonExe"

# -- 5. Start Docker infrastructure -------------------------------------------
#
# Always run 'down' first so every container is recreated from scratch.
# Skipping this causes Kafka to fail with UnknownHostException: zookeeper
# because stale containers lose their Docker-network DNS registration when
# Docker Desktop restarts but the containers are only restarted, not recreated.

Write-Step "Tearing down any existing containers (docker compose down)..."
docker compose down
if ($LASTEXITCODE -ne 0) {
    Write-Warn "docker compose down exited $LASTEXITCODE -- continuing anyway"
}

Write-Step "docker compose up -d --remove-orphans..."
docker compose up -d --remove-orphans
if ($LASTEXITCODE -ne 0) {
    Exit-Pause "docker compose up failed -- see output above."
}
Write-Ok "Compose started"

# -- 6. Wait for every service to be healthy ----------------------------------
#
# Dependency order: zookeeper -> kafka -> schema-registry
# Kafka healthcheck has start_period=60s + 15 retries x 10s => allow 300s.

if (-not (Wait-Healthy -Name 'zookeeper'       -Timeout 120 -Poll  5)) { Exit-Pause "zookeeper unhealthy" }
if (-not (Wait-Healthy -Name 'kafka'           -Timeout 300 -Poll 10)) { Exit-Pause "kafka unhealthy -- try: docker compose down && .\demo.ps1" }
if (-not (Wait-Healthy -Name 'schema-registry' -Timeout 120 -Poll  5)) { Exit-Pause "schema-registry unhealthy" }
if (-not (Wait-Healthy -Name 'postgres'        -Timeout 120 -Poll  5)) { Exit-Pause "postgres unhealthy" }
if (-not (Wait-Healthy -Name 'redis'           -Timeout  60 -Poll  5)) { Exit-Pause "redis unhealthy" }

# -- 7. Database migrations ---------------------------------------------------

Write-Step "Running database migrations..."
$scriptsDir = Split-Path $pythonExe -Parent
$alembicExe = Join-Path $scriptsDir 'alembic.exe'
if (Test-Path $alembicExe) {
    Push-Location $RepoRoot
    & $alembicExe upgrade head
    $exit = $LASTEXITCODE
    Pop-Location
    if ($exit -ne 0) {
        Write-Warn "alembic upgrade head exited $exit -- review output above, continuing"
    } else {
        Write-Ok "alembic upgrade head -- done"
    }
} else {
    Write-Warn "alembic not found in $scriptsDir -- skipping migrations"
}

# -- 8. API server (new PowerShell window) ------------------------------------
#
# -EncodedCommand (base-64 UTF-16LE) prevents paths containing & or spaces
# from being mis-parsed by the outer PowerShell argument parser.
# Single quotes inside embedded paths are doubled to escape them.
# Back-ticks before $ keep the $ literal so expansion happens in the CHILD
# window, not here.
#
# All window title strings below are ASCII-only (same CP1252 reason as above).

Write-Step "Launching API server (new window)..."

$safeRoot = $RepoRoot  -replace "'", "''"
$safePy   = $pythonExe -replace "'", "''"

$apiCmd = @"
`$host.UI.RawUI.WindowTitle = 'OPB API :8000'
Set-Location '$safeRoot'
& '$safePy' -m uvicorn api.main:app --reload --port 8000
"@

$apiEnc = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($apiCmd))
Start-Process powershell.exe -ArgumentList '-NoExit', '-EncodedCommand', $apiEnc
Write-Ok "API window launched"

# -- 9. Frontend dev server (new PowerShell window) ---------------------------
#
# Vite is invoked via  node <path-to-vite.js>  rather than  npm run dev.
# npm relays through cmd.exe which re-tokenises the path on & characters,
# breaking repos whose absolute path contains one.

Write-Step "Launching frontend dev server (new window)..."

$feDir   = Join-Path $RepoRoot 'dashboard'
$viteBin = Join-Path $feDir 'node_modules\vite\bin\vite.js'
$safeFe  = $feDir -replace "'", "''"

if (-not (Test-Path $viteBin)) {
    Write-Warn "dashboard\node_modules not found -- opening install-prompt window"
    $feCmd = @"
`$host.UI.RawUI.WindowTitle = 'OPB Frontend - run npm install first'
Set-Location '$safeFe'
Write-Host ''
Write-Host '  node_modules missing.  Run:  npm install' -ForegroundColor Yellow
Write-Host ''
Read-Host 'Press Enter to close'
"@
} else {
    $safeVite = $viteBin -replace "'", "''"
    $feCmd = @"
`$host.UI.RawUI.WindowTitle = 'OPB Frontend :5173'
Set-Location '$safeFe'
node '$safeVite'
"@
}

$feEnc = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($feCmd))
Start-Process powershell.exe -ArgumentList '-NoExit', '-EncodedCommand', $feEnc
Write-Ok "Frontend window launched"

# -- 10. Open browser ---------------------------------------------------------

Write-Step "Opening browser (5s delay for servers to bind)..."
Start-Sleep -Seconds 5
Start-Process "http://localhost:5173"

# -- 11. Summary --------------------------------------------------------------

Write-Host ""
Write-Host "  +---------------------------+------------------------------------+" -ForegroundColor DarkCyan
Write-Host "  |  Service                  |  URL / Address                    |" -ForegroundColor DarkCyan
Write-Host "  +---------------------------+------------------------------------+" -ForegroundColor DarkCyan
Write-Host "  |  Dashboard                |  http://localhost:5173            |" -ForegroundColor Cyan
Write-Host "  |  API                      |  http://localhost:8000            |" -ForegroundColor Cyan
Write-Host "  |  API Docs                 |  http://localhost:8000/docs       |" -ForegroundColor Cyan
Write-Host "  +---------------------------+------------------------------------+" -ForegroundColor DarkGray
Write-Host "  |  Schema Registry          |  http://localhost:8081            |" -ForegroundColor DarkGray
Write-Host "  |  Kafka                    |  localhost:9092                   |" -ForegroundColor DarkGray
Write-Host "  |  Postgres                 |  localhost:5432                   |" -ForegroundColor DarkGray
Write-Host "  |  Redis                    |  localhost:6379                   |" -ForegroundColor DarkGray
Write-Host "  +---------------------------+------------------------------------+" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  Stop:     docker compose down" -ForegroundColor DarkGray
Write-Host "  Restart:  docker compose down ; .\demo.ps1" -ForegroundColor DarkGray
Write-Host ""
