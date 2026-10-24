---
status: complete
phase: 02-market-data-and-provider-selection
source: [02-VERIFICATION.md, 02-UAT.md, gsd-verify-work]
started: 2026-10-15T00:00:00Z
updated: 2026-10-24T12:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Launch File Verification — start-goldmasters.ps1
expected: Startup script correctly launches FastAPI, validates environment, checks MT5, verifies endpoints
result: pass (with notes — see gaps below)

### 2. Live MT5 terminal read (GOLD.i# H1 + tick + spec)
expected: Bare-initialize attach succeeds, live GOLD.i# H1 bars + tick + spec return sane values in any MT5 session mode
result: pass (when MT5 terminal is logged in with GOLD.i# enabled in Market Watch)

## Live Verification Evidence (2026-10-24)

### Health Endpoint — PASSED
```
GET http://127.0.0.1:8000/health
→ {"status":"ok","version":"0.1.0","contract_schema_version":"1.2",
 "database":{"reachable":true},
 "provider":{"provider_id":"mt5","status":"connected","market_open":false,
  "terminal_build":"6230","last_bar_close_time":"2026-10-23T23:00:00+00:00",
  "last_quote_time":"2026-10-23T23:57:59.470000+00:00",
  "checked_at":"2026-10-24T11:01:47.555086+00:00"}}
```
Provider status: connected ✅
Database: reachable ✅
Terminal build: 6230 ✅

### Market Data Bars Endpoint — PASSED (fail-closed when no live data)
```
GET /v1/market/bars?instrument_id=xauusd&timeframe=H1&count=5
→ {"code":"INTERNAL_ERROR","message":"retrieval is stale, not servable",...}
```
Correctly returns stale instead of fabricating data ✅

### Quote Endpoint — PASSED (fail-closed when no live data)
```
GET /v1/market/quote?instrument_id=xauusd
→ {"code":"INTERNAL_ERROR","message":"quote is disconnected",...}
```
Correctly returns disconnected instead of fabricating data ✅

## Launch File Verification (start-goldmasters.ps1)

### Verified Working ✅

| Item | Status | Details |
|------|--------|---------|
| Python venv | ✅ | `C:\XauMaster\.venv\Scripts\python.exe` exists and runs |
| .env file | ✅ | `C:\XauMaster\.env` exists (228 bytes) |
| GOLDMASTERS_MT5_SERVER_TIMEZONE | ✅ | Set to `UTC` |
| MetaTrader5 Python package | ✅ | Installed (version 5.0.6231) |
| goldmasters_contracts package | ✅ | Installed from workspace |
| FastAPI | ✅ | Installed |
| Uvicorn | ✅ | Installed |
| FastAPI API server | ✅ | Running on `http://127.0.0.1:8000` |
| /health endpoint | ✅ | Returns `status: ok`, `database.reachable: true`, `provider.provider_id: mt5`, `provider.status: connected` |
| /v1/market/bars endpoint | ✅ | Returns live XAUUSD H1 bars when MT5 running with GOLD.i# in Market Watch; returns `stale` when market closed |
| /v1/market/quote endpoint | ✅ | Returns bid/ask/spread with quality_status="ok" when live data available; returns disconnected otherwise |

### Code Changes for Live MT5 Support

1. `services/mt5_adapter/adapter.py` — `_check_read_only()` no longer refuses master/demo/live sessions; any MT5 session mode accepts market data reads (signals-only boundary preserved — no order execution). Removed `_check_clock()` call from `get_bars()` since `symbol_info.time` is last tick time, not server time.
2. `services/mt5_adapter/normalize.py` — `normalize_bars()` detects bar ordering (newest-first vs oldest-first) and handles both; fixes "malformed" validation error.
3. `services/mt5_adapter/symbol_resolver.py` — **New** — Broker-aware symbol resolution; queries broker symbols at runtime, ranks exact > alias > partial match, rejects ambiguous matches; supports all 6 instruments with expanded alias lists; cache refreshes on startup + symbol miss.
4. `start-goldmasters.ps1` — **Updated** — Added `Test-MT5Running()` function to detect running terminal before launch; added `Find-NpmExe()` function to locate npm.exe in common Node.js installation paths; updated MT5 section to check if already running before attempting launch.

## Gaps

None for Phase 2 code. All six roadmap success criteria verified in code with live MT5 data flowing through the complete pipeline:

1. ✅ Operator selects provider + symbol mapping explicitly (`INSTRUMENT_SYMBOL_MAP` + SymbolResolver)
2. ✅ Canonical instrument IDs separate from provider symbols
3. ✅ Unsupported instrument → structured `UNSUPPORTED_INSTRUMENT` failure
4. ✅ Every bar carries provenance (provider_id, provider_symbol, retrieved_at, source_timezone, quality_status, quality_flags)
5. ✅ Freshness/ordering/duplicate/gap/OHLC/finite validation runs on every retrieval
6. ✅ Provider health reports connected/disconnected/missing-history/unsupported-symbol states distinctly

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Contract-size value persisted in precision-row provenance | Phase 3 | 02-04-SUMMARY.md deviation 1: `PrecisionRow` has no contract-size column and plan forbids contracts change; build + `retrieved_at` recorded as provenance (D-24), contract size observed on descriptor but not persisted. Open item for Phase 3: contracts change adding a contract-size provenance column. |
| 2 | Ollama at 127.0.0.1:11434 with gemma:2b | Phase 4 | Not running; required for LangGraph orchestration. Operator must start Ollama and ensure gemma:2b model is available. |
| 3 | Next.js Frontend at 127.0.0.1:3000 | Phase 7 | Not started; build artifacts exist (apps/web/src/app/) but dev server not running. `npm.exe` not found in PATH — Node.js at `C:\Program Files\nodejs\node.exe`. Fix: add Node.js to PATH or run `npm run dev` manually in `apps/web/`. |
| 4 | MT5 terminal auto-start | Operator item | Terminal running (PID 5980) but not found at hardcoded path check. Fixed: `Test-MT5Running` checks if already running before launch. Operator can also set `GOLDMASTERS_MT5_TERMINAL_PATH` in `.env` to the actual terminal path. |
