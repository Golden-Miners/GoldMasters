# GoldMasters — Trading Signal Research Team

**Signals only. Never place or modify orders.**

GoldMasters is a LangGraph multi-agent trading signal research system. It gathers live market data, analyses instruments through typed specialist agents, and produces explainable research decisions — TRADE, NO TRADE, or INSUFFICIENT DATA — never orders.

## What it does

| Capability | Description |
|------------|-------------|
| **Market data** | Live bars and quotes from MT5 (or other providers) with provenance stamps — instrument, provider symbol, timeframe, retrieved_at, source timezone, quality status |
| **Analysis** | Market structure, trend/regime classification, strategy rule checks, entry/stop/target computation — all versioned deterministic code |
| **Risk gate** | Fail-closed validation barrier: levels, risk/reward, data quality, and evidence required before any TRADE candidate |
| **News & sentiment** | Source-attributed news items and sentiment analysis with coverage counts, duplicate handling, and limitations |
| **CEO decision** | Schema-validated, evidence-referenced decision that fails closed when evidence is missing or conflicting |
| **Journal & backtesting** | Immutable decision snapshots, append-only outcomes, reproducible cost-aware backtests |
| **Research console UI** | 11 screens — Overview, Instrument Workbench, Decision Detail, News & Sentiment, Strategy Lab, Backtest Results, Journal, Agent Runs, Data Providers, Settings/Model Health, System Health |
| **LangGraph orchestration** | Bounded graph runs specialist roles against a locally discovered Ollama model (gemma:2b), failing closed on critical failure |

## Non-negotiables (from Rules.md)

- **Signals only** — No order placement, modification, closure, copy trading, or broker execution credentials
- **No fabricated data** — No mock/sample/market data in production paths. Missing data → `unavailable`, never a guess
- **Decimal wire form** — Prices are decimal strings (`"4024.41"`), never JSON numbers with exponents
- **LLMs never output price levels** — Code computes levels, SL/TP, R:R
- **Fail closed** — Missing evidence → `INSUFFICIENT_DATA` or `NO_TRADE`, never a fabricated signal
- **No unsupported claims** — "Zero hallucinations", "perfect analysis", "zero errors" are not verifiable guarantees

## Architecture

```
MT5 Terminal ─────┐
                  ├─► Adapter (read-only) ──► Normalize (UTC) ──► Validate ──► LangGraph ──► CEO Decision
Supabase PostgreSQL ─┘                                              ▲
FastAPI (loopback 127.0.0.1:8000) ──────────────────────────────────┘
Next.js Frontend (127.0.0.1:3000) ──► reads API state only
Ollama (127.0.0.1:1144, model: gemma:2b)
```

- **API**: FastAPI, loopback-only binds, health endpoint at `/health`
- **Database**: PostgreSQL (Supabase-hosted), append-only decision records
- **Contracts**: Pydantic models with `strict=True`, `extra="forbid"`, `frozen=True`
- **Frontend**: Next.js 16, React 19, dark quartz/cyan quant-terminal theme

## Quick Start

### Prerequisites

- Python 3.14 with `.venv` at `C:\XauMaster\.venv`
- Node.js 22+ with npm
- `.env` file at repo root (see `.env.example`)
- Ollama running at `127.0.0.1:11434` with model `gemma:2b`
- MetaTrader 5 terminal (optional — market data endpoint returns `terminal-closed` until connected)

### Using the startup script (PowerShell, recommended)

```powershell
cd C:\XauMaster
.\start-goldmasters.ps1
```

### Manual start

```powershell
# Terminal 1 — FastAPI backend
cd C:\XauMaster
.venv\Scripts\python.exe -m uvicorn apps.api.src.goldmasters_api.app:app --host 127.0.0.1 --port 8000

# Terminal 2 — Next.js frontend
cd C:\XauMaster\apps\web
npm run dev
```

### Verify

```powershell
curl http://127.0.0.1:8000/health
# → {"status":"ok","database":{"reachable":true},"provider":{"provider_id":"mt5","status":"connected",...}}

curl "http://127.0.0.1:8000/v1/market/bars?instrument_id=xauusd&timeframe=H1&count=5"
# → 5 H1 bars with quality_status: "ok"

curl http://127.0.0.1:3000/
# → GoldMasters Research Console UI
```

## Environment variables (`.env`)

| Variable | Example | Required |
|----------|---------|----------|
| `GOLDMASTERS_DATABASE_URL` | `postgresql+psycopg://...` | Yes |
| `GOLDMASTERS_MT5_SERVER_TIMEZONE` | `Asia/Nicosia` | Yes — must match broker's server timezone |
| `GOLDMASTERS_OLLAMA_MODEL` | `gemma:2b` | No — defaults to `gemma:2b` |
| `GOLDMASTERS_MT5_SYMBOL` | `XAUUSD` | No |
| `GOLDMASTERS_TIMEFRAME` | `H1` | No |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Five-field health surface: status, version, contract_schema_version, config_hash, database.reachable + provider object |
| `/v1/market/bars` | GET | Closed H1 bars with provenance: `instrument_id`, `timeframe`, `count` |
| `/v1/market/quote` | GET | Latest bid/ask tick: `instrument_id` |

## Test Commands

| Command | Purpose |
|---------|---------|
| `cd apps/web && npx tsc --noEmit` | TypeScript type check |
| `cd apps/web && npx playwright test` | E2E tests (18/18 pass) |
| `uv run pytest` | Python backend tests |
| `ruff check src/` | Python lint |
| `mypy --strict apps/api/src/goldmasters_api/` | Python strict type check |

## Project Structure

```
C:\XauMaster/
├── README.md                          # This file
├── AGENTS.md                          # Agent session instructions
├── Rules.md                           # Non-negotiable rules
├── Prd.md                             # Product requirements
├── Architecture.md                    # System architecture
├── Schema.md                          # Contract schema (canonical)
├── Security.md                        # Security audit guide
├── Debug.md                           # Debug procedures
├── Memory.md                          # Session memory
├── Task.md                            # Current phase tasks
├── .env.example                       # Environment template
├── start-goldmasters.ps1              # PowerShell startup script
├── start-goldmasters.bat              # Batch startup script
├── apps/api/                          # FastAPI backend
│   ├── src/goldmasters_api/
│   ├── alembic.ini
│   └── migrations/
├── apps/web/                          # Next.js frontend
│   ├── src/app/                       # 11 route pages
│   ├── src/styles/                    # Design tokens + globals
│   └── tests/e2e/                     # Playwright tests
├── packages/contracts/                # Pydantic contract models
│   ├── src/goldmasters_contracts/
│   └── schema/                        # Committed JSON Schema exports
└── services/mt5_adapter/              # MT5 read-only adapter
    ├── adapter.py
    ├── normalize.py
    └── validation.py
```

## License

Internal use only. Signals only — never place or modify orders.

---

**Last updated:** Sat Oct 24 2026  
**Milestone:** v1.0 Research Signal Team