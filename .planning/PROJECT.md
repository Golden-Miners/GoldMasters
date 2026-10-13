# GoldMasters

## What This Is

GoldMasters is a single-operator, locally hosted research tool: a LangGraph multi-agent "trading signal team" that reads real market data from an explicitly selected provider (local MT5 read-only adapter first), gathers and validates evidence, and produces explainable `TRADE` / `NO_TRADE` / `INSUFFICIENT_DATA` research decisions with full provenance. It never places, modifies or closes an order — a `TRADE` is a qualified research candidate that requires manual review. The goal is a traceable research brief that exposes evidence freshness, source provenance, uncertainty and disagreement instead of concealing them.

## Core Value

Every output is traceable to real, timestamped market data with provenance; nothing is fabricated, and the system fails closed to NO_TRADE or INSUFFICIENT_DATA when evidence is missing or stale.

## Requirements

### Validated

(None yet — nothing is implemented; ship to validate.)

### Active

- [ ] **REQ-instrument-provider-selection** — Canonical instrument IDs are maintained separately from provider-specific symbols (broker suffixes never leak into strategy logic); the operator selects provider and symbol mapping, and the UI/API shows provider, symbol, timezone, timeframe, last successful retrieval, latest candle timestamp and status.
- [ ] **REQ-market-data-ingestion-validation** — A provider interface returns normalized bars/quotes with provenance, and every retrieval is validated (timestamps, ordering, duplicates, gaps, OHLC invariants, finite values, freshness, volume semantics) with quality status and flags attached.
- [ ] **REQ-langgraph-orchestration** — LangGraph owns typed graph state, node transitions, conditional routing, bounded retries/timeouts, checkpointing and run metadata; a validation barrier precedes the CEO decision and run identity/inputs/versions are recorded per run.
- [ ] **REQ-specialist-agent-responsibilities** — Bounded, typed specialist roles (Market Analyst, Trend, Instrument, Strategy Supervisor, Strategy Agents, News Analyst, Sentiment, Signaling, CEO, Research, Backtesting, Trade Journal, Monitoring, Risk/Validation Gate), each with rule-by-rule evidence, single responsibility and explicit failure status.
- [ ] **REQ-ceo-decision-contract** — The CEO emits `TRADE` / `NO_TRADE` / `INSUFFICIENT_DATA` with the full required field set (decision, instrument, timeframe, direction, created_at, run_id, evidence_refs, agent_statuses, conflicts, data_quality_status, levels only when derived and validated, thesis, invalidation_conditions, risk_factors, reasons_for_rejection, limitations, strategy id/version), and cannot override deterministic data-quality or risk gates.
- [ ] **REQ-news-and-sentiment** — News is retrieved from permitted sources only, preserving title, publisher, publication time, retrieval time, URL and extracted claims; sentiment separates source statements from model interpretation and reports coverage, duplicates and conflicts.
- [ ] **REQ-ui-and-reports** — A React/Next.js research console over the backend API covering Overview, Instrument Workbench, Decision Detail, News & Sentiment, Strategy Lab, Backtest Results, Journal, Agent Runs, Data Providers, Settings/Model Health and System Health, with evidence freshness visible near every decision.
- [ ] **REQ-journal-and-backtesting** — Immutable decision snapshots with append-only outcome observations, and backtests that declare dataset, range, timezone, timeframe, symbol mapping, strategy version, parameters, costs/slippage and fill model with in-sample/validation separation.
- [ ] **REQ-local-model-support** — Ollama as the local inference runtime, configured by endpoint with model health check, provider/model status and runtime model discovery — no assumed model, hardware or context window.
- [ ] **REQ-no-trade-execution** — V1 must not place, modify or close orders; no trading credentials, no autonomous execution, copy trading or portfolio management.
- [ ] **REQ-no-fabricated-data** — No invented, mock or sample market, news, sentiment, backtest or signal data in production paths; missing or unavailable data is labelled as such.
- [ ] **REQ-evidence-and-provenance** — Every decision is explained with citations/references to underlying data, timestamps, rules and conflicts, and decision traceability (percentage of decisions with complete evidence references and configuration/version metadata) is instrumented.

### Out of Scope

- **Order placement, modification or closure — anywhere.** V1 is research and decision support only; the CEO's `TRADE` output is a qualified candidate requiring manual review (`manual_review_required = true`), not an order. Locked user decision DR-04; Rules.md R-02.
- **Copy trading, broker execution, autonomous trading and portfolio management.** No broker trading credentials exist in the project; no execution module, endpoint or tool is to be created. Rules.md R-02; Task.md T0804.
- **Fabricated or mock data in `src/` production paths** (including "sample" candles, headlines, sentiment scores, backtest numbers or signals). Missing evidence must be marked unknown/unavailable; fixtures are permitted only in labelled tests and must never be surfaced as live conditions. Rules.md R-01, R-09; REQ-no-fabricated-data.
- **LLMs emitting price levels.** Prices, indicator values, entry/stop/take-profit and risk/reward arithmetic, validation and gates are computed by deterministic code; model output stays untrusted until schema-validated. DR-13; Rules.md R-03.
- **Multi-user deployment, authentication and remote/public exposure.** The target runtime is a single local Windows host with the web UI bound to loopback and no authentication in V1. (Revisit only if LAN access is explicitly requested — Memory.md open decision.)
- **Monetization, billing, marketing or tenant features.** Internal research tool for one operator; not a commercial product.

## Context

**Product shape.** LangGraph multi-agent signal team for a single personal trading team/workspace. Decision vocabulary is `TRADE` / `NO_TRADE` / `INSUFFICIENT_DATA`; a `TRADE` is a research candidate, never an order. The CEO agent holds final research authority but cannot override deterministic data-quality or risk gates. Initial instrument universe: gold, silver, forex, oil, BTC, ETH — subject to verified provider symbol coverage.

**Target runtime.** Single local Windows host: backend, database and the MT5 read-only adapter all run on this machine; the web UI binds to loopback only; no authentication in V1. Local MT5 availability does not imply a remote backend can reach it — the deployment boundary is decided (local-only) and recorded as locked for V1 (DR-09/DR-11/DR-12 remain proposed in form, not in placement). The `MetaTrader5` Python package is **not yet installed**, so the adapter cannot run until it is installed in a Python 3.10+ environment on the MT5 host (Memory.md T0003 note).

**Confirmed technical direction (locked).** React/Next.js frontend, Python backend, LangGraph orchestration, PostgreSQL persistence, Ollama for local inference.

**Developer-facing success metric (user's own definition of done).** A task counts as DONE only when its acceptance checks actually ran and the results are recorded alongside ruff clean, mypy strict clean, and focused tests passing. If a check could not run, the status is BLOCKED or NEEDS REVIEW — never DONE (Rules.md R-10, R-05; Task.md status definitions).

**Repository baseline (as of ingest).** 10 Markdown documents (Prd.md, Schema.md, Architecture.md, Design.md, Security.md, Debug.md, Rules.md, Memory.md, Task.md, AGENTS.md) and no source code, manifests or tests. The directory is now a git repository (Memory.md's "no git repo" snapshot is historical drift). No `.planning/config.json` exists, so GSD defaults apply (granularity `standard`, phase IDs sequential). Architecture.md, Design.md and Security.md describe *proposed* architecture, draft design and an audit plan — none is implemented, and no finding may be claimed from them.

**Source-of-truth precedence.** Schema.md (SPEC) is canonical for names, enums and JSON shapes; Prd.md is the requirement source; Rules.md is mandatory policy. Where Design.md's status vocabulary diverges from Schema.md (Design: `queued/running/succeeded/failed/skipped/timed-out`; Schema: `queued/running/ok/no_setup/insufficient_data/error/skipped`), **Schema.md wins** and UI labels map onto it (`succeeded`→`ok`, `failed`→`error`, `completed`→`ok`). No ADR-classified document exists, so nothing in the ingest set is precedence-protected above SPEC/PRD.

**Provenance.** All content above is transcribed from the ingest set (`.planning/intel/*`) — PRD §1/§3/§6, Schema.md, Rules.md, Architecture.md, Design.md, Memory.md, Task.md, AGENTS.md.

## Constraints

23 constraints carried from ingest: 12 from `Schema.md` (SPEC — canonical for names and JSON shapes) and 11 from `Rules.md` (mandatory project policy). Where Schema.md and Design.md diverge on status vocabulary, Schema.md wins.

**Schema.md (SPEC) — contracts**

- **C-01 (schema)**: Shared conventions — snake_case identifiers; ISO-8601 timestamps with timezone; no binary float as the sole authoritative representation for money/price (define Decimal/tick quantization); `null` only where nullable, with `unknown` / `unavailable` / `not-applicable` / `failed` kept as distinct states; no magic status strings outside enums; `schema_version` on persisted agent payloads and external contracts; all external/model/provider input untrusted until validated; no secrets in schemas, logs, traces or examples.
- **C-02 (schema)**: Enumerations are fixed — Decision `{TRADE, NO_TRADE, INSUFFICIENT_DATA}`; agent/run status `{queued, running, ok, no_setup, insufficient_data, error, skipped}`; volume_type `{tick, exchange, broker, unknown, not_available}`; strategy status `{draft, under_review, approved, disabled, retired}`. In the UI, `TRADE` means a qualified candidate requiring manual review, not an order.
- **C-03 (api-contract)**: Agent envelope — every agent output carries `schema_version, run_id, agent_name, agent_version, status, created_at, as_of, input_refs, evidence_refs, limitations, error, result`, with `error` a structured sanitized object on failure.
- **C-04 (schema)**: Market data contract — bar fields `instrument_id, provider_id, provider_symbol, timeframe, bar_open_time, bar_close_time, open/high/low/close, volume (nullable), volume_type, retrieved_at, source_timezone, quality_status, quality_flags`; invariants on finite/positive prices, `high >= max(open, close, low)` and `low <= min(open, close, high)`, timeframe-aligned ordered timestamps, duplicates/gaps flagged rather than silently dropped, provider volume semantics preserved. Quotes carry the equivalent fields; a missing candle or quote is never fabricated.
- **C-04b (protocol)**: Provider interface — `get_bars`, `get_latest_quote`, `get_instrument_spec`, `health_check`, `capabilities`; canonical instrument IDs separate from provider symbols; provider choice explicit and persisted per run; no silent fallback, no symbol substitution.
- **C-05 (api-contract)**: Decision record — required fields as in REQ-ceo-decision-contract plus `manual_review_required = true`; a `TRADE` only with present, current, schema-valid, strategy-qualified and risk-validated evidence; missing critical input never filled by an LLM guess; entry/stop/take-profits/risk-reward stay `null` unless derived and validated; decision records immutable.
- **C-06 (schema)**: News & sentiment — news fields `source_id, canonical_url, title, published_at (nullable), retrieved_at, content_hash, instrument_mappings (with rationale/confidence method), source_attribution, access_method, status, limitations`; never treat retrieval time as publication time; never store or republish content beyond allowed terms. Sentiment fields include analysis window, source/evidence refs, coverage count, unique-source count, duplicate policy, label/score only if method defined and versioned, conflicts, limitations, model/version.
- **C-07 (api-contract)**: Strategy contract — `strategy_id`, `strategy_version`, rule set, parameter set, registry status and `rule_checks` evidence per rule; a strategy is approved only by explicit review, never by model assertion.
- **C-08 (schema)**: Backtest contract — dataset/date-range/timezone/timeframe/symbol-mapping/version/parameters/assumptions/run-reference must accompany any reported result; metrics computed in deterministic code.
- **C-09 (api-contract)**: Error contract — `{code, message (sanitized), retryable, correlation_id, details (redacted)}`; messages must not expose secrets, SQL, stack traces, local paths, tokens or full provider responses; retryability is decided by code, not by model judgement.
- **C-10 (nfr)**: Naming/formatting — nine Markdown filenames keep exact casing; agent modules follow `<agent_name>_agent.py` (or one consistent package convention); tests are `test_<module_or_behaviour>.py`; environment variables are uppercase with a `GOLDMASTERS_` prefix and never commit real secret values; IDs are UUIDs or another documented stable identifier; units explicit in field names/metadata; JSON is valid UTF-8 with no comments, trailing commas, NaN or Infinity; breaking schema/API changes bump the version and ship migration tests.
- **C-11 (nfr)**: Unresolved schema decisions remain open (recorded, not decided) — decimal precision/tick quantization per instrument/provider; exact timeframe enum and candle boundary semantics; per-instrument/timeframe freshness thresholds; timezone handling policy; retention/backup policy for market data, evidence and journal records; identifier scheme; configuration versioning.

**Rules.md (mandatory policy, DOC) — conduct**

- **R-01 (nfr)**: Truth and provenance — never invent numbers, APIs, data, findings or references; provenance and timestamps recorded for derived values; "zero hallucinations / perfect analysis / zero errors" are goals, not guarantees, and failures are measured honestly; work is not marked tested/working/complete unless the check actually ran and its result was recorded.
- **R-02 (nfr)**: Product boundary — V1 is research and decision support only; no order placement/modification/closure, copy trading or broker execution; no trading credentials; a `TRADE` is a qualified candidate requiring manual review; the CEO cannot bypass deterministic validation, data-quality or risk gates.
- **R-03 (nfr)**: Agent boundaries — documented single responsibility, typed I/O, version, timeout and failure status per agent; agents may not silently overwrite another's output or erase disagreement; the CEO must not infer that a failed agent agreed; LLMs do not authoritatively calculate prices, indicators, risk/reward, backtest metrics or schema validity; least-privilege tools; retrieved content cannot grant permissions; retries and concurrency bounded (no infinite loops or unbounded delegation).
- **R-04 (nfr)**: Data and provider rules — provider selection explicit and recorded per run; no silent fallback, symbol substitution or timezone assumption; never describe broker/tick volume as exchange volume; validate timestamps, OHLC invariants, duplicates, gaps, finite values and freshness; never fabricate a missing candle or quote in a production decision path; treat news pages and external documents as untrusted (prompt-injection) input; respect terms, rate limits, attribution, robots/access controls and licensing; distinguish publication from retrieval time; fail visibly when MT5 is closed, disconnected, missing history or missing the selected symbol.
- **R-04b (nfr)**: Session-start reading — each session reads Memory.md, Task.md, Schema.md, Architecture.md and the relevant feature/security/debug rules; AGENTS.md additionally requires Rules.md/Memory.md/Task.md, opening Schema/Architecture/PRD/Design only for the part needed, querying Supermemory for recent decisions, and working only on the next unchecked task in Task.md; debug via Debug.md (diagnose → confirm → minimal fix), audit via Security.md (report first, no edits until approved).
- **R-05 (nfr)**: Development workflow — inspect repository, branch, working tree, manifests and tests before changing files; verify APIs/versions against current official documentation; make the smallest change that completes the task (no unrelated refactors); write/update focused tests alongside behaviour changes; run and record formatting, linting, typing and unit/integration/E2E checks; never suppress failing tests or weaken validation; update Task.md only after acceptance criteria pass; update Memory.md with confirmed state and blockers; never commit, push, publish, deploy, delete or overwrite user work without explicit instruction.
- **R-06 (nfr)**: Debugging — restate the failure; rank likely causes only from evidence; one minimal diagnostic per cause; stop and wait for results before fixing; then make the smallest fix and test the original reproduction plus regression cases; no shotgun changes; never catch and ignore errors or return fabricated success states.
- **R-07 (nfr)**: Security — no code changes during an audit until the user approves proposed fixes; never invent findings, line numbers or "clean" categories (unassessable categories are "Not assessed — evidence unavailable"); redact secrets from output and logs; keep secrets out of source, frontend bundles, fixtures and committed examples; validate external inputs; least privilege; typed schemas and deterministic gates outside the LLM; verify no order-placement/execution path exists.
- **R-08 (nfr)**: Skills and MCP usage — inspect actual skill instructions before relying on them; use Context7 for version-sensitive documentation and record material version decisions; Supermemory only for durable project facts (never secrets); Playwright for browser/E2E including error states; GitHub MCP read-only unless permitted; Caveman only for concise low-risk summaries; never claim a tool was used unless a real invocation succeeded.
- **R-09 (nfr)**: Testing — every task has observable acceptance criteria; deterministic tests for arithmetic, rule checks, schemas and routing; test missing, stale, malformed, conflicting, timed-out and unavailable inputs; test that critical failures cannot produce `TRADE`; backtests must test timestamp alignment, transaction costs, fill assumptions and leakage; tests must not depend on live markets unless explicitly marked environment/integration tests; fixtures only in tests, labelled as fixtures, never surfaced as live conditions; flaky tests and environment dependencies recorded honestly.
- **R-10 (nfr)**: Documentation and DONE criteria — keep naming, JSON, schema, status and error formats consistent with Schema.md; record assumptions as assumptions and unresolved requirements as open questions; cite sources for external technical claims; no filler, marketing claims, fabricated metrics or unverified "best" claims; a task is DONE only with evidence, otherwise BLOCKED or NEEDS REVIEW.

## Key Decisions

Status vocabulary: `locked` = user-confirmed (Memory.md, confirmed user decisions). `proposed` = architectural (Architecture.md §2) — reconcile against the repository and environment before pinning. There are **no ADR-classified decisions and no ADR-locked entries**; every decision below is DOC-sourced and therefore ranks below the SPEC (Schema.md) and the PRD (Prd.md). Where a proposed decision conflicts with Schema.md, Schema.md wins.

### Locked (user-confirmed)

| ID | Decision | Rationale (source) | Status |
|----|----------|--------------------|--------|
| DR-01 | Project name is **GoldMasters** (earlier "GoldMaster" is superseded) | Memory.md — confirmed user decision; naming/identity scope | locked |
| DR-02 | Primary user is a single personal trading team/workspace — not multi-user SaaS | Memory.md — confirmed user decision; target-user scope | locked |
| DR-03 | V1 scope is research and decision support only | Memory.md — confirmed user decision; product scope | locked |
| DR-04 | Trade execution explicitly out of scope: no order placement, modification or closure; no broker trading credentials | Memory.md — confirmed user decision; product boundary | locked |
| DR-05 | Initial instrument universe: gold, silver, forex, oil, BTC and ETH, subject to verified provider symbol coverage | Memory.md — confirmed user decision; instruments | locked |
| DR-06 | Technical direction: React/Next.js frontend, Python backend, LangGraph orchestration, PostgreSQL persistence | Memory.md — confirmed user decision; stack | locked |
| DR-07 | Ollama is the local LLM runtime | Memory.md — confirmed user decision; local model runtime | locked |
| DR-08 | Definition of done: develop in small steps, test each step, and update task state only after checks pass | Memory.md — confirmed user decision; development workflow | locked |

### Proposed (Architecture.md §2 — reconcile before pinning)

| ID | Decision | Rationale (source) | Status |
|----|----------|--------------------|--------|
| DR-09 | Python backend with FastAPI proposed as the API framework (confirm compatibility before pinning); Pydantic typed validation for payloads and agent contracts; domain logic separated from HTTP routes and UI | Architecture.md §2 Backend and API | proposed |
| DR-10 | LangGraph owns graph state, node transitions, conditional routing, checkpointing and run metadata; agents are bounded nodes; a validation barrier precedes the CEO decision; disagreements are preserved | Architecture.md §2 Agent orchestration | proposed |
| DR-11 | React/Next.js frontend reads API state and must not call MT5 or Ollama directly; never expose prompts, credentials, provider secrets or privileged agent tools to the client | Architecture.md §2 Frontend | proposed |
| DR-12 | PostgreSQL preferred; migrations, explicit transaction boundaries, indexes justified by query patterns, append-only decision/outcome records; no credentials in ordinary config tables | Architecture.md §2 Data storage | proposed |
| DR-13 | Ollama preferred; discover available models at runtime (no assumed model/hardware/context); LLMs for synthesis, classification, extraction and explanation; deterministic code for prices, indicator values, risk/reward arithmetic, validation and gates; all model output untrusted until schema-validated | Architecture.md §2 Local model | proposed |
| DR-14 | Common provider interface (`get_bars`, `get_latest_quote`, `get_instrument_spec`, `health_check`, `capabilities`); local MT5 as one adapter; canonical instrument IDs kept separate from provider symbols; provider choice explicit and persisted per run; no silent fallback | Architecture.md §2 Market-data providers | proposed |
| DR-15 | News/sentiment source adapters with terms-of-use review, attribution, URL canonicalization, timestamps, deduplication and rate limiting; named sources (Forex Factory, CoinDesk) are candidates only pending access checks; separate fetched source facts from model interpretation | Architecture.md §2 News and sentiment | proposed |

## Open Risks

- **RISK-01 — Task.md contradicts itself on next work.** T0001, T0002 and T0003 are marked complete (lines 14–16) while "Current checkpoint" states `Next task: T0001 — inspect repository and record baseline without modifying code` and `Implementation status: NOT STARTED / NOT VERIFIED` (lines 115, 117). Impact: planning or execution may re-run completed discovery work or skip what follows. Resolution required: update the checkpoint to the genuinely next unchecked task (T0004) and drop the stale status line — or re-open T0001 if it was checked in error. Source: INGEST-CONFLICTS.md (WARNING 1).
- **RISK-02 — Memory.md and Task.md disagree on what is in flight.** Memory.md names `Current task: T0002` (line 71) yet records T0002 completed (line 50) and T0001 completed (line 49); Task.md names T0001 as next. Impact: two handoff documents resume different work. Resolution required: decide the single source of truth for task progress, align both files, and record the confirmed next task before planning proceeds. Source: INGEST-CONFLICTS.md (WARNING 2).
- **RISK-03 — Phase 0 discovery is incomplete and gates later phases.** T0004 (Ollama endpoint/models), T0005 (remaining PRD questions) and T0006 (baseline test/lint/type state) are open; the `MetaTrader5` package is not installed, so the read-only adapter cannot run until it is installed on the MT5 host in Python 3.10+. Source: Task.md; Memory.md ("Open decisions", T0003 note).
- **RISK-04 — Contract-defining documents sit above implementation.** Schema.md is canonical for names and JSON shapes, but Prd.md/Architecture.md open questions and the C-11 unresolved schema decisions (tick quantization, timeframe enum, freshness thresholds, timezone, identifier scheme, retention, configuration versioning) must be decided before Phase 1 contracts can be frozen. Source: Schema.md §12; Prd.md/Architecture.md open questions.

## Evolution

After each phase: move invalidated requirements to Out of Scope with the reason, move validated requirements to Validated with the phase reference, add new requirements to Active, log new decisions in Key Decisions, and update "What This Is" if the product drifted. After each milestone: full section review, Core Value check, Out of Scope audit, and refresh Context with current state. Locked decisions (DR-01…DR-08) change only with explicit user confirmation; proposed decisions (DR-09…DR-15) become locked when confirmed against the real repository and environment.

---
*Last updated: 2026-10-13 after ingest-driven project initialization (10 documents → intel synthesis, 12 requirements, 23 constraints, 15 decision records).*
