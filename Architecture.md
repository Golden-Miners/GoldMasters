# GoldMasters — Architecture and Development Plan

**Status:** Proposed architecture. Must be reconciled with the actual repository and installed environment before implementation.  
**Product boundary:** research and decision support only; no order execution.

## 1. System overview

```text
React / Next.js UI
        |
        v
Python API (FastAPI proposed)
        |
        v
LangGraph workflow
  |      |       |        |
  |      |       |        +--> Monitoring / run tracing
  |      |       +-----------> News + sentiment retrieval
  |      +-------------------> Strategy and market analysis
  +--------------------------> Market-data provider interface
                                  |--> Local MT5 adapter
                                  |--> Additional approved adapters
        |
        v
Evidence validation + risk gates + CEO decision
        |
        +--> PostgreSQL persistence
        +--> Journal / backtest results
        +--> Ollama for bounded language tasks
```

The diagram is conceptual, not a claim that components have already been built.

## 2. Architectural decisions

### Backend and API
- **Python** for market-data integration, strategy calculations, and LangGraph.
- **FastAPI** is the proposed API framework; confirm repository and environment compatibility before pinning versions.
- Pydantic or equivalent typed validation for API payloads and agent contracts.
- Separate domain logic from HTTP routes and UI code.

### Agent orchestration
- **LangGraph** owns graph state, node transitions, conditional routing, checkpointing strategy, and run metadata.
- Agents are bounded nodes with explicit input/output schemas; they are not independent uncontrolled loops.
- Independent evidence collectors can run in parallel. A validation barrier precedes CEO decision.
- CEO has final decision authority but cannot override deterministic data-quality and risk gates.
- Use explicit timeout, retry, cancellation, and partial-failure semantics.
- Preserve disagreements; do not force a consensus summary that erases conflicting evidence.

### Frontend
- **React/Next.js** as selected by user.
- Use a chart library only after checking licence, data density, accessibility, and support for required interactions.
- UI reads API state; it must not call MT5 or Ollama directly from the browser.
- Do not expose prompts, credentials, provider secrets, or privileged agent tools to the client.

### Data storage
- **PostgreSQL** is the preferred persistent database in the chosen web stack.
- Use migrations, explicit transaction boundaries, indexes justified by query patterns, and append-only decision/outcome records.
- Cache only where freshness and invalidation semantics are explicit.
- Do not store credentials in ordinary configuration tables; use environment variables or an appropriate secret store.
- Whether TimescaleDB or another time-series extension is necessary remains open; do not add it without measured need.

### Local model
- **Ollama** is the preferred local inference runtime.
- Discover available models at runtime; do not assume a model name, hardware capability, or context window.
- Use LLMs for synthesis, classification, extraction, and explanation where justified. Use deterministic code for prices, indicator values, risk/reward arithmetic, validation, and gates.
- All model output is untrusted until schema-validated and checked against evidence references.

### Market-data providers
- Define a common interface such as `get_bars`, `get_latest_quote`, `get_instrument_spec`, `health_check`, and `capabilities`.
- Implement local MT5 as one adapter using the supported MetaTrader5 Python package and a running/accessible terminal. Verify broker-specific behaviour.
- Keep canonical instrument IDs separate from provider-specific symbols.
- Provider choice is explicit and persisted per run. No silent fallback.
- Additional providers require legal/access review, capability tests, rate-limit handling, and mapping tests.
- Avoid claiming exchange-grade centralized volume when the feed only provides broker/tick volume.

### News and sentiment
- Use source adapters with terms-of-use review, attribution, URL canonicalization, timestamps, deduplication, and rate limiting.
- Forex Factory, CoinDesk, and other named sources are candidates only; their current API/access terms must be checked before integration.
- Separate fetched source facts from model-generated interpretation.

## 3. Proposed agent topology

```text
START
  |
  v
Resolve instrument + provider configuration
  |
  v
Fetch market data and instrument metadata
  |
  v
Validate freshness and integrity ---- fail ----> INSUFFICIENT DATA
  |
  v
Parallel evidence collection:
  - Market Analyst
  - Trend Agent
  - Instrument Agent
  - News Analyst
  - Sentiment Agent
  - Research Agent (when requested/needed)
  |
  v
Strategy Supervisor
  |
  +--> Strategy Agent A
  +--> Strategy Agent B
  +--> Strategy Agent N
  |
  v
Normalize and validate agent evidence
  |
  v
Signaling Agent proposes candidate (if any)
  |
  v
Deterministic Risk / Eligibility Gate
  |
  v
CEO Decision: TRADE / NO_TRADE / INSUFFICIENT_DATA
  |
  +--> Persist decision and evidence snapshot
  +--> Trade Journal append
  +--> Monitoring and run metrics
  |
  v
END
```

Backtesting is a separate graph/workflow using historical datasets and the same versioned strategy rules, not a shortcut inside the live analysis path. Monitoring is both instrumentation around runs and a separate health process; it must not alter decisions.

## 4. Agent contract requirements

Every node output must contain:
- `schema_version`
- `agent_name`, `agent_version`
- `run_id`
- `status`: `ok`, `no_setup`, `insufficient_data`, `error`, or `skipped`
- `as_of` and `created_at` timestamps with timezone
- `input_refs` / `evidence_refs`
- `limitations`
- typed domain fields defined in `Schema.md`

Errors must be structured and sanitized. Never use a successful empty string as a substitute for missing evidence. Every field has explicit nullability and semantics.

## 5. Tooling, resources, and skills

### Confirmed by user as intended in their OpenCode environment
- OpenCode as the vibe-coding interface.
- MCPs: Context7, Supermemory, Playwright, Caveman, GitHub.
- Skills/plugins: Ponytail, Impeccable, Archify, Graphify, Matt Pocock skills, Vercel, Fabric, Agency agents, Taste, Stitch.
- Local model runtime: Ollama.
- No trade execution.

This list records the user's stated environment; it does not verify that every integration is active or correctly configured.

### Usage policy
- **Context7:** look up current official documentation and version-specific examples before implementing framework APIs. Record relevant version decisions.
- **Supermemory:** use only if the installed integration supports the intended persistence; store durable project decisions and pointers, not secrets or raw market data.
- **Playwright:** automate browser workflows and UI regression tests; do not treat a passing smoke test as proof of full correctness.
- **GitHub MCP:** inspect repository state, diffs, issues and CI where access is configured. Never commit or push without explicit instruction.
- **Caveman:** use only for concise summaries/planning when it does not remove critical technical detail. Do not use it to author canonical contracts or security findings.
- **Ponytail, Impeccable, Archify, Graphify, Matt Pocock skills, Vercel, Fabric, Agency agents, Taste, Stitch:** first inspect each skill's actual instructions and applicability. Use only where relevant; do not invoke every tool on every task.
- **Ollama:** verify endpoint and installed models with an actual health check before choosing a model.
- Avoid repeated documentation retrieval: save concise, dated implementation notes with source/version links. Do not compress away safety-critical requirements just to reduce tokens.

### Proposed dependencies — verify compatibility before pinning
- Backend: Python, FastAPI, Uvicorn, LangGraph, Pydantic, PostgreSQL driver, migration tool (Alembic or equivalent), structured logging, pytest.
- Market data: MetaTrader5 Python package on a compatible local Windows environment; this adapter may need to run as a separate local service if backend deployment is not on the same machine.
- Frontend: Next.js/React, TypeScript, a maintained component system, schema/client validation, Playwright.
- Persistence: PostgreSQL, migrations, backup/restore procedure.
- Model: Ollama and a discovered installed model.
- Quality: formatter, linter, type checker, unit/integration tests, dependency auditing, secret scanning.
- Exact package versions are intentionally not invented. Use Context7 and official package documentation, then lock tested versions in dependency files.

## 6. Deployment boundary

Important constraint: MT5 is locally installed. If the backend runs on another host/container, it cannot simply access the desktop MT5 terminal unless an explicit, secured bridge is built. Preferred initial options:
1. Run the MT5 adapter and API on the same Windows machine, if compatible with the chosen deployment; or
2. Run a narrow authenticated local bridge on the MT5 machine and let the backend consume normalized data over a protected channel.

Choose after confirming OS, where Next.js/backend will run, and whether the UI must be accessible from other devices. Do not expose the MT5 bridge or database publicly by default.

## 7. Repository layout proposal

```text
goldmasters/
  apps/
    web/                 # Next.js UI
    api/                 # FastAPI routes and app setup
  services/
    mt5_adapter/         # local MT5 data adapter/bridge
  src/
    goldmasters/
      graph/             # LangGraph construction/state/edges
      agents/            # bounded agent nodes
      data/
        providers/       # provider interfaces and adapters
        news/            # source adapters and normalization
      domain/            # typed domain models and rules
      strategies/        # versioned deterministic strategy logic
      risk/              # hard gates and numeric validation
      backtesting/       # event-driven or documented bar-based engine
      persistence/       # repositories and migrations
      observability/     # tracing, metrics, redaction
  tests/
    unit/
    integration/
    contract/
    security/
    e2e/
  docs/                  # these Markdown files
  .env.example           # names only; never real secrets
  README.md
```

This is a proposal, not an existing tree. Adapt only after repository inspection.

## 8. Quality gates

- Unit tests for calculations, schema validators, risk gates, strategy rules, and provider normalization.
- Contract tests for each provider and agent schema.
- Integration tests for LangGraph branching, retries, failures, and persistence.
- Replay tests with captured/authorized historical fixtures; never label fixtures as live data.
- Backtest tests for look-ahead leakage, timestamp alignment, costs, and fill assumptions.
- Playwright tests for key UI journeys and error states.
- Security tests for input validation, secrets, CORS, SSRF, authorization, and tool permissions as applicable.
- CI should fail on lint/type/test/schema failures. A passing pipeline proves only the checks it runs.
- Record exact commands and outputs; never mark a check as passed if it was not executed.

## 9. Phased development plan

1. **Discovery:** inspect repository, OpenCode configuration, installed skills/MCP availability, operating system, MT5 terminal, Ollama models, and deployment intent.
2. **Contracts:** finalise PRD open questions, Schema.md contracts, ADRs, error model, and risk gates.
3. **Foundation:** project structure, configuration, logging/redaction, API health endpoint, PostgreSQL migration, CI.
4. **Data adapters:** provider interface, MT5 adapter, symbol mapping, freshness/integrity checks, contract tests.
5. **Deterministic domain:** indicators/structure/trend/strategy primitives and unit tests.
6. **Graph skeleton:** typed LangGraph state, node registry, conditional edges, retries/timeouts, run trace.
7. **Evidence agents:** market, trend, instrument, news, sentiment and research nodes with schemas.
8. **Strategy and risk:** strategy supervisor, individual strategy nodes, signal normalizer, hard risk gates.
9. **CEO and journal:** decision policy, evidence bundle, immutable persistence, outcome append flow.
10. **Backtesting:** dataset validation, cost/fill model, train/validation/OOS splits, leakage tests.
11. **UI:** implement screens in Design.md, wire only to real API responses, include empty/error/offline states.
12. **Hardening:** security audit, dependency review, Playwright E2E, failure injection, backup/restore test.
13. **Release gate:** all required tests executed and recorded, unresolved issues listed, no execution capability, operator runbook ready.

## 10. Architecture decisions requiring approval

- Local-only app vs LAN-accessible UI.
- Whether MT5 adapter runs in the API process or a separate bridge.
- Exact initial timeframes, symbols, and data freshness policy.
- PostgreSQL local installation vs container.
- Initial Ollama model after environment discovery.
- News-source access method and terms.
- Approved strategy set and hard risk thresholds.
- Logging/market-data retention and backup policy.
