# ODRMitra local dev stack orchestrator.
# Invoked via `just up|down|status|logs|warm` — see justfile at repo root.
#
# Ports on this machine (3000/4000/8000 are HNS-reserved and unbindable):
#   backend  -> 127.0.0.1:8001   frontend -> 127.0.0.1:3002
param([Parameter(Position = 0)][string]$Cmd = "status")

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Baileys = Join-Path $Root "baileys-service"
$Logs = Join-Path $Backend "logs"

$BackendPort = 8001
$FrontendPort = 3002
$BaileysPort = 3001
$DockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Real TCP connect, not listener enumeration — Docker Desktop's port proxy
# does not show up in Get-NetTCPConnection.
function Test-Port([int]$Port) {
    $c = New-Object Net.Sockets.TcpClient
    try { $c.ConnectAsync("127.0.0.1", $Port).Wait(600) -and $c.Connected }
    catch { $false }
    finally { $c.Dispose() }
}

# Run a native command with all output discarded. PS 5.1 + $ErrorActionPreference
# Stop turns redirected native stderr into a terminating error, so route through
# cmd.exe instead of PowerShell redirection.
function Invoke-Quiet([string]$CommandLine) {
    cmd /c "$CommandLine >nul 2>&1"
    return $LASTEXITCODE
}

function Ensure-Docker {
    if ((Invoke-Quiet "docker info") -eq 0) { return }
    Write-Host "[stack] starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process $DockerDesktop
    $deadline = (Get-Date).AddSeconds(150)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if ((Invoke-Quiet "docker info") -eq 0) { Write-Host "[stack] docker engine up"; return }
    }
    throw "Docker engine did not come up within 150s"
}

# Create the container on first run, start it on later runs, no-op if running.
function Ensure-Container([string]$Name, [string[]]$RunArgs) {
    $state = cmd /c ('docker inspect -f "{{.State.Running}}" ' + $Name + ' 2>nul')
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[stack] creating container $Name"
        docker run -d --name $Name @RunArgs | Out-Null
    }
    elseif ("$state".Trim() -ne "true") {
        Write-Host "[stack] starting container $Name"
        docker start $Name | Out-Null
    }
}

function Wait-Http([string]$Url, [int]$TimeoutSec, [string]$What) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 30
            if ($r.StatusCode -eq 200) { Write-Host "[stack] $What ready"; return }
        }
        catch { Start-Sleep -Seconds 2 }
    }
    throw "$What did not become ready within ${TimeoutSec}s ($Url)"
}

function Start-Backend {
    if (Test-Port $BackendPort) { Write-Host "[stack] backend already on :$BackendPort"; return }
    Write-Host "[stack] starting backend on :$BackendPort"
    if (-not (Test-Path $Logs)) { New-Item -ItemType Directory $Logs | Out-Null }
    Start-Process -FilePath (Join-Path $Backend ".venv\Scripts\python.exe") `
        -ArgumentList "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
        -WorkingDirectory $Backend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $Logs "backend.out.log") `
        -RedirectStandardError (Join-Path $Logs "backend.err.log")
}

function Start-Frontend {
    if (Test-Port $FrontendPort) { Write-Host "[stack] frontend already on :$FrontendPort"; return }
    Write-Host "[stack] starting frontend on :$FrontendPort"
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c", "npx next dev --port $FrontendPort" `
        -WorkingDirectory $Frontend -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $Logs "frontend.out.log") `
        -RedirectStandardError (Join-Path $Logs "frontend.err.log")
}

# WhatsApp bridge. Its config defaults to backend :8000; this machine runs
# the backend on :8001, so point it there explicitly.
function Start-Baileys {
    if (Test-Port $BaileysPort) { Write-Host "[stack] baileys already on :$BaileysPort"; return }
    Write-Host "[stack] starting baileys (WhatsApp) on :$BaileysPort"
    $cmdLine = "set BACKEND_URL=http://127.0.0.1:$BackendPort" +
    "&& set BACKEND_WEBHOOK_URL=http://127.0.0.1:$BackendPort/api/v1/channel/whatsapp/webhook" +
    "&& node src/index.js"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmdLine `
        -WorkingDirectory $Baileys -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $Logs "baileys.out.log") `
        -RedirectStandardError (Join-Path $Logs "baileys.err.log")
}

# First agent request loads the embedding model (60-90s). Do it now so the
# demo never eats the cold start. Non-fatal: the stack is up either way.
function Warm-Agent {
    Write-Host "[stack] warming agent (embedding model load, may take ~90s)..."
    try {
        $login = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/v1/auth/login" `
            -Method Post -ContentType "application/json" `
            -Body '{"mobile_number": "7409210692"}' -TimeoutSec 30
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/v1/chat/message" `
            -Method Post -ContentType "application/json" `
            -Headers @{ Authorization = "Bearer $($login.access_token)" } `
            -Body '{"message": "hello", "channel": "web"}' -TimeoutSec 240 | Out-Null
        Write-Host ("[stack] agent warm ({0:n1}s)" -f $sw.Elapsed.TotalSeconds) -ForegroundColor Green
    }
    catch {
        Write-Host "[stack] warm-up failed (stack still up): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

function Stop-Port([int]$Port, [string]$What) {
    try {
        $conns = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop
        foreach ($owner in ($conns.OwningProcess | Sort-Object -Unique)) {
            Write-Host "[stack] stopping $What (pid $owner)"
            # Frontend is `cmd -> node`; kill the tree so the child dies too.
            Invoke-Quiet "taskkill /PID $owner /T /F" | Out-Null
        }
    }
    catch { Write-Host "[stack] $What not running" }
}

function Show-Status {
    $rows = @(
        @{ Name = "postgres  :5432"; Ok = (Test-Port 5432) }
        @{ Name = "qdrant    :6333"; Ok = (Test-Port 6333) }
        @{ Name = "backend   :$BackendPort"; Ok = (Test-Port $BackendPort) }
        @{ Name = "frontend  :$FrontendPort"; Ok = (Test-Port $FrontendPort) }
        @{ Name = "baileys   :$BaileysPort"; Ok = (Test-Port $BaileysPort) }
    )
    foreach ($r in $rows) {
        $mark = if ($r.Ok) { "UP  " } else { "DOWN" }
        $color = if ($r.Ok) { "Green" } else { "Red" }
        Write-Host ("  {0}  {1}" -f $mark, $r.Name) -ForegroundColor $color
    }
}

switch ($Cmd) {
    "up" {
        Ensure-Docker
        Ensure-Container "odrmitra-postgres" @(
            "-p", "5432:5432",
            "-e", "POSTGRES_PASSWORD=postgres",
            "-e", "POSTGRES_DB=odrmitra",
            "postgres:15")
        Ensure-Container "odrmitra-qdrant" @(
            "-p", "6333:6333", "-p", "6334:6334",
            "qdrant/qdrant:latest")

        # Postgres must accept connections before uvicorn starts.
        $deadline = (Get-Date).AddSeconds(60)
        while ((Get-Date) -lt $deadline) {
            if ((Invoke-Quiet "docker exec odrmitra-postgres pg_isready -U postgres") -eq 0) { break }
            Start-Sleep -Seconds 2
        }
        Write-Host "[stack] postgres accepting connections"

        Start-Backend
        Start-Frontend
        # Cold imports (langchain, sentence-transformers) can take ~2 min
        # right after a reboot; give the backend plenty of room.
        Wait-Http "http://127.0.0.1:$BackendPort/health" 240 "backend"
        Wait-Http "http://127.0.0.1:$FrontendPort/login" 150 "frontend"
        Warm-Agent
        # After the warm-up: baileys tries to restore WhatsApp sessions from
        # the backend 3s after boot, so the backend must be responsive by then.
        Start-Baileys
        $deadline = (Get-Date).AddSeconds(30)
        while ((Get-Date) -lt $deadline -and -not (Test-Port $BaileysPort)) { Start-Sleep -Seconds 2 }
        Write-Host ""
        Write-Host "ODRMitra is up:  http://localhost:$FrontendPort" -ForegroundColor Green
        Show-Status
    }
    "down" {
        Stop-Port $FrontendPort "frontend"
        Stop-Port $BaileysPort "baileys"
        Stop-Port $BackendPort "backend"
        Invoke-Quiet "docker stop odrmitra-postgres odrmitra-qdrant" | Out-Null
        Write-Host "[stack] containers stopped"
        Show-Status
    }
    "status" { Show-Status }
    "warm" { Warm-Agent }
    "logs" {
        Write-Host "== backend.err.log (uvicorn) ==" -ForegroundColor Cyan
        Get-Content (Join-Path $Logs "backend.err.log") -Tail 30
        Write-Host "== frontend.out.log ==" -ForegroundColor Cyan
        Get-Content (Join-Path $Logs "frontend.out.log") -Tail 20
        Write-Host "== baileys.out.log ==" -ForegroundColor Cyan
        Get-Content (Join-Path $Logs "baileys.out.log") -Tail 20 -ErrorAction SilentlyContinue
    }
    default { throw "Unknown command '$Cmd' (use: up | down | status | warm | logs)" }
}
