@echo off
:: ==============================================================================
:: GoldMasters v1.0 — Research Signal Team
:: Startup Script (Batch)
::
:: Starts:
::   1. Ollama (local model runtime)   — http://127.0.0.1:11434
::   2. FastAPI Backend                — http://127.0.0.1:8000
::   3. Next.js Frontend               — http://127.0.0.1:3000
::
:: Prerequisites:
::   - Ollama installed (ollama.exe on PATH)
::   - Python 3.14+ with .venv at C:\XauMaster\.venv
::   - Node.js 22+ with npm
::   - .env.example present at repo root
# ==============================================================================

@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo.
echo ============================================================================
echo GoldMasters v1.0 — Research Signal Team
echo ============================================================================
echo.

REM Validate environment
if not exist "%SCRIPT_DIR%\.venv\Scripts\python.exe" (
    echo [ERROR] Python venv not found at %SCRIPT_DIR%\.venv\Scripts\python.exe
    exit /b 1
)
if not exist "%SCRIPT_DIR%apps\web\node_modules" (
    echo [ERROR] Node modules not installed at %SCRIPT_DIR%apps\web\node_modules
    exit /b 1
)
if not exist "%SCRIPT_DIR%\.env.example" (
    echo [ERROR] .env.example not found at repo root
    exit /b 1
)

REM Check Ollama
powershell -Command "try { $s = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 11434); $s.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Starting Ollama server...
    start /b ollama serve
    :ollama_wait
    curl.exe -s http://127.0.0.1:11434/api/tags >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        ping -n 2 127.0.0.1 >nul
        goto ollama_wait
    )
    echo [OK] Ollama is running
) else (
    echo [OK] Ollama is already running
)

REM Verify gemma:2b model
curl.exe -s http://127.0.0.1:11434/api/tags 2>nul | findstr /c:"gemma:2b" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Model 'gemma:2b' not found. Run: ollama pull gemma:2b
    exit /b 1
)
echo [OK] Ollama model 'gemma:2b' is available

REM Start FastAPI backend
echo.
echo [INFO] Starting FastAPI backend...
cd /d "%SCRIPT_DIR%"
start /b "%SCRIPT_DIR%\.venv\Scripts\python.exe" -m uvicorn apps.api.src.goldmasters_api.app:app --host 127.0.0.1 --port 8000 > "%TEMP%\goldmasters-api.log" 2>&1
:api_wait
curl.exe -s http://127.0.0.1:8000/health 2>&1 | findstr /c:"ok" >nul
if %ERRORLEVEL% NEQ 0 (
    ping -n 2 127.0.0.1 >nul
    goto api_wait
)
echo [OK] FastAPI backend is running on port 8000

REM Start Next.js frontend
echo.
echo [INFO] Starting Next.js frontend...
cd /d "%SCRIPT_DIR%\apps\web"
start /b npm run dev > "%TEMP%\goldmasters-web.log" 2>&1
:web_wait
curl.exe -s http://127.0.0.1:3000/ 2>&1 | findstr /c:"GoldMasters" >nul
if %ERRORLEVEL% NEQ 0 (
    ping -n 2 127.0.0.1 >nul
    goto web_wait
)
echo [OK] Next.js frontend is running on port 3000

REM Summary
echo.
echo ============================================================================
echo GoldMasters v1.0 — All Services Running
echo ============================================================================
echo.
echo   Research Console UI:  http://127.0.0.1:3000
echo   API Base URL:         http://127.0.0.1:8000
echo   API Docs:             http://127.0.0.1:8000/docs
echo   Ollama Model:         gemma:2b (http://127.0.0.1:11434)
echo.
echo   Signal agents:        10 strategies enabled
echo   Trade execution:      DISABLED (research-only)
echo.
echo Press Ctrl+C to stop all servers.
echo ============================================================================

pause

:: Cleanup on exit
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq *goldmasters*" 2>nul
taskkill /F /IM "node.exe" /FI "WINDOWTITLE eq *goldmasters*" 2>nul
echo.
echo [OK] All services stopped.
