# ==============================================================================
# GoldMasters v1.0 — Startup Script (PowerShell)
#
# Starts:
#   1. FastAPI Backend  — http://127.0.0.1:8000
#   2. Next.js Frontend — http://127.0.0.1:3000
#
# Already running (start these separately if needed):
#   - Ollama: http://127.0.0.1:11434 (model: gemma:2b)
#   - MT5 Terminal: C:\Program Files\MetaTrader 5\terminal64.exe (optional for live data)
#
# Prerequisites:
#   - Python 3.14.7 venv at C:\XauMaster\.venv
#   - Node.js 22+ with npm
#   - .env file at repo root with GOLDMASTERS_DATABASE_URL, GOLDMASTERS_MT5_SERVER_TIMEZONE
#   - PostgreSQL cluster: Supabase-hosted (configured in .env)
# ==============================================================================
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
$SCRIPT_DIR   = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_PYTHON  = Join-Path $SCRIPT_DIR ".venv\Scripts\python.exe"
$API_APP      = "apps.api.src.goldmasters_api.app:app"
$API_HOST     = "127.0.0.1"
$API_PORT     = 8000
$WEB_DIR      = Join-Path $SCRIPT_DIR "apps\web"
$ENV_FILE     = Join-Path $SCRIPT_DIR ".env"
$MT5_TERMINAL = "C:\Program Files\MetaTrader 5\terminal64.exe"
$MT5_AUTO_LAUNCH = $false  # Set to $true to auto-launch MT5 from .env

# Build URLs using string concatenation (PowerShell : parsing issue)
$API_BASE     = "http://" + $API_HOST + ":" + [string]$API_PORT
$HEALTH_URL   = $API_BASE + "/health"
$MARKET_URL   = $API_BASE + "/v1/market/bars?instrument_id=xauusd&timeframe=H1&count=1"

# Track started processes for clean shutdown
$STARTED_PROCESSES = @()

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
function Write-Header([string]$msg) {
    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host $msg -ForegroundColor Cyan
    Write-Host ("=" * 60)
}

function Write-Info([string]$msg) {
    Write-Host ("[INFO] $msg") -ForegroundColor Cyan
}

function Write-Success([string]$msg) {
    Write-Host ("[OK]   $msg") -ForegroundColor Green
}

function Write-Warn([string]$msg) {
    Write-Host ("[WARN] $msg") -ForegroundColor Yellow
}

function Write-Err([string]$msg) {
    Write-Host ("[ERR]  $msg") -ForegroundColor Red
}

function Test-Port([int]$port) {
    try {
        $socket = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $port)
        $socket.Close()
        return $true
    } catch {
        return $false
    }
}

function Wait-Port([int]$port, [string]$name, [int]$timeoutSec = 30) {
    Write-Info ("Waiting for " + $name + " on port " + $port + " (up to " + $timeoutSec + " seconds)...")
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $timeoutSec) {
        if (Test-Port $port) {
            $sw.Stop()
            Write-Success ($name + " is ready on port " + $port)
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    $sw.Stop()
    Write-Err ($name + " did not respond on port " + $port + " within " + $timeoutSec + " seconds")
    return $false
}

function Test-File([string]$path, [string]$label) {
    if (Test-Path $path) {
        Write-Success ($label + " found: " + $path)
        return $true
    } else {
        Write-Err ($label + " NOT found: " + $path)
        return $false
    }
}

function Test-PythonPackage([string]$moduleName, [string]$displayName) {
    try {
        $result = & $VENV_PYTHON -c ("import " + $moduleName + "; print('" + $moduleName + " OK')") 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success ($displayName + " installed: " + $result)
            return $true
        } else {
            Write-Warn ($displayName + " not importable: " + $result)
            return $false
        }
    } catch {
        Write-Err ($displayName + " check failed: " + $_)
        return $false
    }
}

# ---------------------------------------------------------------------------
# Step 0: Validate environment
# ---------------------------------------------------------------------------
Write-Header "GoldMasters v1.0 — Startup Script"
Write-Info ("Working directory: " + $SCRIPT_DIR)

if (-not (Test-Path $VENV_PYTHON)) {
    Write-Err ("Python venv not found at " + $VENV_PYTHON)
    Write-Err "Please create the virtual environment first."
    exit 1
}
Write-Success ("Python venv found: " + $VENV_PYTHON)

if (-not (Test-Path $ENV_FILE)) {
    Write-Err (".env file not found at " + $ENV_FILE)
    exit 1
}
Write-Success (".env file found")

# Check .env for required keys
$envContent = Get-Content $ENV_FILE -Raw
if ($envContent -notmatch "GOLDMASTERS_MT5_SERVER_TIMEZONE") {
    Write-Err "GOLDMASTERS_MT5_SERVER_TIMEZONE not found in .env"
    exit 1
}
Write-Success "GOLDMASTERS_MT5_SERVER_TIMEZONE is set in .env"

# Check optional MT5 terminal path
if ($envContent -match "GOLDMASTERS_MT5_TERMINAL_PATH=(.+)") {
    $mt5PathFromEnv = $Matches[1].Trim().Trim('"')
    if (Test-Path $mt5PathFromEnv) {
        $MT5_TERMINAL = $mt5PathFromEnv
        $MT5_AUTO_LAUNCH = $true
        Write-Success "MT5 terminal auto-launch enabled: $MT5_TERMINAL"
    } else {
        Write-Warn "MT5 terminal path from .env not found: $mt5PathFromEnv"
    }
}

# ---------------------------------------------------------------------------
# Step 1: Install/verify Python dependencies
# ---------------------------------------------------------------------------
Write-Header "Step 1 — Dependency Check & Install"

$mt5Installed = $false
try {
    $result = & $VENV_PYTHON -c "import MetaTrader5; print('MetaTrader5 ' + MetaTrader5.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success ("MetaTrader5 installed: " + $result)
        $mt5Installed = $true
    } else {
        Write-Warn ("MetaTrader5 not importable: " + $result)
    }
} catch {
    Write-Warn ("MetaTrader5 check failed: " + $_)
}

if (-not $mt5Installed) {
    Write-Warn "MetaTrader5 not installed — market data endpoint will return 'terminal-closed'"
    Write-Info "Install with: .venv\Scripts\python.exe -m pip install MetaTrader5==5.0.6231"
}

try {
    $result = & $VENV_PYTHON -c "from goldmasters_contracts import IanaTimezone; print('contracts OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success ("goldmasters_contracts installed: " + $result)
    } else {
        Write-Warn ("goldmasters_contracts not importable: " + $result)
        Write-Info "Installing goldmasters-contracts from workspace..."
        & $VENV_PYTHON -m pip install "C:\XauMaster\packages\contracts" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Failed to install goldmasters-contracts"
            exit 1
        }
        Write-Success "goldmasters_contracts installed"
    }
} catch {
    Write-Err ("goldmasters_contracts check failed: " + $_)
    exit 1
}

try {
    & $VENV_PYTHON -c "import fastapi; print('fastapi', fastapi.__version__)" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "FastAPI installed"
    } else {
        Write-Err "FastAPI not installed"
        exit 1
    }
} catch {
    Write-Err ("FastAPI check failed: " + $_)
    exit 1
}

try {
    & $VENV_PYTHON -c "import uvicorn; print('uvicorn', uvicorn.__version__)" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Uvicorn installed"
    } else {
        Write-Err "Uvicorn not installed"
        exit 1
    }
} catch {
    Write-Err ("Uvicorn check failed: " + $_)
    exit 1
}

# ---------------------------------------------------------------------------
# Step 2: MT5 terminal (optional)
# ---------------------------------------------------------------------------
Write-Header "Step 2 — MT5 Terminal (Optional)"

if (-not (Test-Path $MT5_TERMINAL)) {
    Write-Warn ("MT5 terminal not found at " + $MT5_TERMINAL)
    Write-Warn "Market data endpoint will return 'terminal-closed' until MT5 is running"
    Write-Host ""
} elseif ($MT5_AUTO_LAUNCH) {
    Write-Info ("Auto-launching MT5 terminal: " + $MT5_TERMINAL)
    $mt5Proc = Start-Process -FilePath $MT5_TERMINAL -WindowStyle Normal -PassThru
    $STARTED_PROCESSES += $mt5Proc
    Write-Info "Waiting up to 30 seconds for MT5 terminal to start..."
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $mt5Ready = $false
    while ($sw.Elapsed.TotalSeconds -lt 30) {
        if (Test-Port -port 0) {  # Placeholder - MT5 doesn't expose a port we can test
            $mt5Ready = $true
            break
        }
        Start-Sleep -Milliseconds 1000
    }
    $sw.Stop()
    if ($mt5Ready) {
        Write-Success "MT5 terminal launched"
    } else {
        Write-Warn "MT5 terminal launch timeout — start it manually if needed"
    }
    Write-Host ""
} else {
    Write-Info ("MT5 terminal found at " + $MT5_TERMINAL)
    Write-Info "Launch MT5 manually and log in (any account mode: investor/master/demo/live)."
    Write-Info "   - GoldMasters is signals-only — any session mode is acceptable"
    Write-Info "   - Enable Market Watch for your gold symbol (e.g. GOLD.i#, XAUUSD)"
    Write-Info "   - The API will connect automatically once the terminal is running"
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Step 3: Start FastAPI Backend
# ---------------------------------------------------------------------------
Write-Header "Step 3 — FastAPI Backend"

if (Test-Port $API_PORT) {
    Write-Success ("FastAPI already running on port " + $API_PORT)
} else {
    Write-Info ("Starting FastAPI backend on 127.0.0.1:" + $API_PORT + "...")
    Start-Process -FilePath $VENV_PYTHON `
        -ArgumentList "-m", "uvicorn", $API_APP, "--host", $API_HOST, "--port", [string]$API_PORT `
        -WindowStyle Hidden `
        -WorkingDirectory $SCRIPT_DIR

    if (-not (Wait-Port $API_PORT "FastAPI Backend" 30)) {
        Write-Err "FastAPI backend failed to start"
        exit 1
    }
}

Write-Info "Verifying /health endpoint..."
try {
    $health = & $VENV_PYTHON -c "
import urllib.request
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=10)
    print(r.status)
    print(r.read().decode())
except Exception as e:
    print('ERROR:', str(e))
    exit(1)
" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Health check passed"
        Write-Info ("Response: " + $health)
    } else {
        Write-Err ("Health check failed: " + $health)
        exit 1
    }
} catch {
    Write-Err ("Health check failed: " + $_)
}

Write-Info "Verifying /v1/market/bars endpoint..."
try {
    $bars = & $VENV_PYTHON -c "
import urllib.request
try:
    r = urllib.request.urlopen('http://127.0.0.1:8000/v1/market/bars?instrument_id=xauusd&timeframe=H1&count=5', timeout=15)
    print(r.status)
    print(r.read().decode())
except urllib.error.HTTPError as e:
    print('HTTP ' + str(e.code))
    print(e.read().decode())
except Exception as e:
    print('ERROR:', str(e))
    exit(1)
" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Market data endpoint responding"
        Write-Info ("Response: " + $bars)
    } else {
        Write-Warn "Market data endpoint returned error (expected if MT5 terminal not running):"
        Write-Info $bars
    }
} catch {
    Write-Warn ("Market data check failed: " + $_)
}

# ---------------------------------------------------------------------------
# Step 4: Start Next.js Frontend (Optional)
# ---------------------------------------------------------------------------
Write-Header "Step 4 — Next.js Frontend (Optional)"

$WEB_DIR = Join-Path $SCRIPT_DIR "apps\web"
if (-not (Test-Path (Join-Path $WEB_DIR "package.json"))) {
    Write-Warn "Next.js project not found at " + $WEB_DIR + " — skipping frontend"
} else {
    Write-Info ("Next.js project found at " + $WEB_DIR)

    if (-not (Test-Path (Join-Path $WEB_DIR "node_modules"))) {
        Write-Info "Installing Node.js dependencies..."
        cd $WEB_DIR
        npm install 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Err "npm install failed"
            exit 1
        }
        Write-Success "Node modules installed"
    }

    if (Test-Port 3000) {
        Write-Success "Next.js frontend already running on port 3000"
    } else {
        Write-Info "Starting Next.js frontend on port 3000..."
        Start-Process -FilePath "npm.exe" `
            -ArgumentList "run dev" `
            -WindowStyle Hidden `
            -WorkingDirectory $WEB_DIR

        if (-not (Wait-Port 3000 "Next.js Frontend" 60)) {
            Write-Err "Next.js frontend failed to start"
            exit 1
        }
    }
}

# ---------------------------------------------------------------------------
# Final Status
# ---------------------------------------------------------------------------
Write-Header "GoldMasters v1.0 — All Services Running"

Write-Success ("Backend API:   http://127.0.0.1:" + [string]$API_PORT)
Write-Success ("API Docs:      http://127.0.0.1:" + [string]$API_PORT + "/docs")
Write-Success ("Health:       http://127.0.0.1:" + [string]$API_PORT + "/health")
Write-Success ("Frontend:     http://127.0.0.1:3000   (if started)")
Write-Success ("Ollama:       http://127.0.0.1:11434 (gemma:2b)")
Write-Host ""
Write-Info "Signals only — no trade execution enabled"
Write-Info "Press Ctrl+C to stop all services"

try {
    while ($true) {
        Start-Sleep -Seconds 5
    }
} catch {
    Write-Host ""
    Write-Info "Shutting down GoldMasters..."
    # Stop only processes we started (not user-owned terminals/processes)
    foreach ($proc in $STARTED_PROCESSES) {
        try {
            if (-not $proc.HasExited) {
                $proc.CloseMainWindow() | Out-Null
                Start-Sleep -Milliseconds 500
                if (-not $proc.HasExited) {
                    $proc.Kill() | Out-Null
                }
            }
        } catch {
            # Process already gone
        }
    }
    Write-Success "All GoldMasters services stopped."
    exit 0
}