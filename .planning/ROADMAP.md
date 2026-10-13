# Roadmap: GoldMasters

## Overview

GoldMasters is built from its contracts outward. Phase 1 freezes the machine-checked schema layer (Schema.md is canonical for names and JSON shapes), stands up the local skeleton and enforces the research-only boundary structurally — so no later phase can accidentally grow an execution path or an unvalidated payload. Phase 2 makes real market data arrive with provenance and quality status, or fail visibly. Phase 3 puts every number that a signal depends on — structure, regimes, strategy rule checks, entry/stop/target, risk/reward and the hard risk gate — into versioned deterministic code. Phase 4 hosts those roles inside a bounded LangGraph run with a locally discovered Ollama model, where a critical failure can only end in NO_TRADE or INSUFFICIENT_DATA. Phase 5 adds source-attributed news and sentiment, then the CEO decision contract with evidence references and fail-closed rules. Phase 6 makes decisions immutable and outcomes append-only, and adds reproducible, cost-aware backtesting. Phase 7 delivers the read-only research console over real API state. Phase 8 proves, with recorded evidence, that nothing is fabricated, nothing executes and nothing is claimed untested.

**Granularity:** `standard` (GSD default - no `.planning/config.json` exists). Phase IDs are sequential.

**Milestone:** v1.0 - Research Signal Team (first milestone; started 2026-10-13).

**Requirement coverage:** 12/12 v1 requirements mapped, one phase each, no orphans.

**Relationship to Task.md:** the project's own tracker defines phases 0–8. This roadmap folds Task.md Phase 0 (discovery) into Phase 1 and Task.md Phase 5 (persistence/journal/monitoring) into Phase 6, and keeps the remaining boundaries. Roadmap order — 1 Contracts → 2 Data → 3 Deterministic → 4 Graph/Agents → 5 Evidence/CEO → 6 Journal/Backtest → 7 UI → 8 Release — is the dependency order, not a claim of progress: no task in Task.md is verified complete beyond the recorded Phase 0 items, and RISK-01/RISK-02 (tracker contradictions) must be resolved before execution starts.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Contracts and Foundation** - Freeze the schema contract layer, stand up the local skeleton, and enforce the research-only boundary structurally
- [ ] **Phase 2: Market Data and Provider Selection** - Explicitly selected providers deliver validated, provenance-stamped bars - or fail visibly
- [ ] **Phase 3: Deterministic Analysis, Strategy Rules and Risk Gates** - All levels, risk/reward and eligibility come from versioned code with rule-by-rule evidence
- [ ] **Phase 4: LangGraph Orchestration and Local Model Runtime** - A bounded, run-tracked graph executes the specialist roles against a discovered local model and fails closed
- [ ] **Phase 5: News, Sentiment and CEO Decision Contract** - Source-attributed news and sentiment become evidence; the CEO issues a schema-valid, evidence-referenced decision that fails closed
- [ ] **Phase 6: Journal, Persistence and Backtesting** - Immutable decision snapshots with appended outcomes, plus reproducible, cost-aware backtests
- [ ] **Phase 7: Research Console UI and Reports** - The operator researches instruments and reviews decisions in a console read from real API state, with no execution action
- [ ] **Phase 8: Hardening, Data-Integrity Verification and Release Gate** - Recorded evidence that nothing is fabricated or executable and no claim is untested

## Phase Details

### Phase 1: Contracts and Foundation
**Goal**: A frozen, machine-checked contract layer and a running, observable local skeleton, with the research-only boundary enforced structurally from the first commit.
**Depends on**: Nothing (first phase)
**Requirements**: REQ-no-trade-execution
**Success Criteria** (what must be TRUE):
  1. Every Schema.md contract (agent envelope, market bar/quote, news item, sentiment, decision, journal, backtest, error) exists as validated, versioned code with passing tests, and an invalid payload is rejected rather than accepted.
  2. The backend service and client application skeleton run on this machine, and the API health endpoint answers on loopback only.
  3. No order-placement, order-modification or order-closure module, endpoint, tool or broker-trading credential exists — verified by an automated boundary test that runs in CI.
  4. Configuration is validated at startup, `.env.example` contains no real secret values, and logs and traces are structured, correlation-ID stamped and redacted.
  5. The PostgreSQL migration applies and rolls back, and formatting, linting, typing and unit checks run in CI and fail the build on violation — with the exact commands and their results recorded.
**Plans**: TBD

### Phase 2: Market Data and Provider Selection
**Goal**: The operator can select a provider and instrument and receive real, validated, provenance-stamped market data — or a visible, structured failure.
**Depends on**: Phase 1
**Requirements**: REQ-instrument-provider-selection, REQ-market-data-ingestion-validation
**Success Criteria** (what must be TRUE):
  1. An operator selects a provider and its symbol mapping for an instrument; the selection is explicit, recorded for the run, and never silently substituted.
  2. Canonical instrument IDs stay separate from provider symbols in storage and API responses — no broker suffix reaches strategy or decision logic.
  3. Requesting an unsupported instrument or timeframe returns a structured "unsupported" failure instead of a substitute symbol, provider or timezone.
  4. Every bar carries provider_id, provider_symbol, timeframe, bar open/close times, retrieved_at, finite OHLC values, volume with preserved volume_type, quality_status and quality_flags.
  5. Freshness/ordering/duplicate/gap/OHLC/finite validation runs on every retrieval, and a stale, malformed or disconnected feed produces a non-healthy quality status or INSUFFICIENT_DATA downstream — never a synthesized candle.
  6. Provider health reports terminal-closed, disconnected, missing-history and unsupported-symbol states distinctly, with contract tests and failure tests recorded.
**Plans**: TBD

### Phase 3: Deterministic Analysis, Strategy Rules and Risk Gates
**Goal**: Every number behind a candidate — structure, regime, levels, ordering, risk/reward and eligibility — is produced by versioned deterministic code with rule-by-rule evidence, and hard gates can block it.
**Depends on**: Phase 2
**Requirements**: REQ-specialist-agent-responsibilities
**Success Criteria** (what must be TRUE):
  1. Documented candle/timeframe conventions, timezone policy and Decimal/tick quantization rules exist, agree with Schema.md, and are covered by boundary-case tests.
  2. Versioned market-structure, trend/regime and strategy primitives return identical outputs for identical inputs, verified by deterministic unit tests.
  3. Each strategy emits rule-by-rule evidence (rule_checks) with strategy_id and strategy_version, and produces no setup where a rule fails.
  4. Candidate entry, stop, targets and risk/reward are computed in code from defined rules; ordering is validated and every level stays null when it is not derived and validated.
  5. The deterministic risk/validation gate enforces level ordering, configured risk limits, data quality and required evidence — and can block a candidate before any decision is produced.
  6. Every specialist role (Market Analyst, Trend, Instrument, Strategy Supervisor and Strategy Agents, Signaling, News, Sentiment, Research, Backtesting, Trade Journal, Monitoring, CEO, Risk/Validation Gate) has a documented single responsibility, typed I/O, version, timeout and failure status; Monitoring emits no trading recommendation; no role can overwrite or erase another's findings.
**Plans**: TBD

### Phase 4: LangGraph Orchestration and Local Model Runtime
**Goal**: A bounded, resumable graph runs the specialist roles end to end against a locally discovered model, validating every node's output and failing closed on critical failure.
**Depends on**: Phase 3
**Requirements**: REQ-langgraph-orchestration, REQ-local-model-support
**Success Criteria** (what must be TRUE):
  1. Starting a run produces a run record containing run_id, input snapshot/reference, configuration and version identifiers, timestamps and per-node status.
  2. Graph state is typed, nodes are bounded, and retries, timeouts, cancellation and partial-failure handling are configuration-bounded — no node loops unbounded or delegates recursively without limit.
  3. A validation barrier precedes the CEO node; disagreements between agents are preserved and passed forward rather than reconciled silently.
  4. Every node payload passes schema validation before use; unvalidated model output never reaches a decision, and a validation failure yields a structured sanitized error rather than a filled-in guess.
  5. Ollama is configured by endpoint with a health check and runtime model discovery — no model name, hardware capability or context window is assumed — and model availability and test status are recorded.
  6. When a critical node fails, the run terminates as INSUFFICIENT_DATA or NO_TRADE under the documented failure policy; no run path can end in an unqualified TRADE.
**Plans**: TBD

### Phase 5: News, Sentiment and CEO Decision Contract
**Goal**: Source-attributed news and sentiment become first-class evidence, and the CEO emits a schema-valid, evidence-referenced decision that fails closed.
**Depends on**: Phase 4
**Requirements**: REQ-news-and-sentiment, REQ-ceo-decision-contract, REQ-evidence-and-provenance
**Success Criteria** (what must be TRUE):
  1. A news item carries source_id, canonical_url, title, published_at (nullable when unreliable), retrieved_at, content_hash, source_attribution, access_method and limitations — and publication time is never replaced by retrieval time.
  2. Duplicates collapse by canonical URL and similarity policy with attribution preserved, and when news cannot be retrieved the coverage is labelled unavailable with no synthesized headline or sentiment.
  3. Sentiment reports its analysis window, evidence references, coverage count, unique-source count, duplicate policy, conflicts, limitations and model version, separating source statements from model interpretation — and shows a score only when the scoring method is defined and versioned.
  4. Every decision record validates against the CEO contract with `manual_review_required = true`, and a TRADE appears only when required evidence is present, current, schema-valid, strategy-qualified and risk-validated, with entry/stop/targets/risk_reward null otherwise.
  5. Decision traceability is instrumented — the percentage of decisions with complete evidence references and configuration/version metadata is measured and displayed before any target is set.
**Plans**: TBD

### Phase 6: Journal, Persistence and Backtesting
**Goal**: Decisions are immutable and outcomes append-only, and backtests are reproducible, cost-aware and honest about missing data.
**Depends on**: Phase 5
**Requirements**: REQ-journal-and-backtesting
**Success Criteria** (what must be TRUE):
  1. Every decision is persisted as an immutable snapshot with its evidence references, and outcome observations are appended without mutating the original record — surviving a restart.
  2. Any reported backtest result carries its run and dataset reference plus declared date range, timezone, timeframe, symbol mapping, strategy version, parameter set, spread/commission/slippage assumptions and fill model.
  3. In-sample development is separated from validation/out-of-sample results, and missing data and excluded periods are reported rather than quietly dropped.
  4. Metrics are computed by deterministic code and cross-checked against hand-verifiable cases; no LLM prose introduces or recalculates an authoritative metric.
  5. Leakage, timestamp alignment, transaction-cost application and split enforcement are covered by tests that fail when an assumption is violated.
**Plans**: TBD

### Phase 7: Research Console UI and Reports
**Goal**: The operator can research an instrument and review any decision in a console that reads only real API state and offers no execution action.
**Depends on**: Phase 6
**Requirements**: REQ-ui-and-reports
**Success Criteria** (what must be TRUE):
  1. All eleven surfaces are reachable and render live API state: Overview, Instrument Workbench, Decision Detail, News & Sentiment, Strategy Lab, Backtest Results, Journal, Agent Runs, Data Providers, Settings/Model Health and System Health.
  2. Evidence freshness and quality status appear next to every decision, and observed facts, deterministic calculations, strategy outputs and LLM interpretations are visually distinguishable — never a placeholder presented as live.
  3. Empty, loading, degraded, stale, no-setup, insufficient-evidence, conflicting-agents, schema-invalid, unavailable and offline states all render explicitly; `unknown` is never styled healthy, and a provider outage shows no market data.
  4. The Decision Detail primary action is "Open evidence" or "Add review note" — no execute-trade control, prompt, credential or privileged agent tool is reachable from the client.
  5. Keyboard navigation, visible focus, non-colour-only status, tabular chart alternatives and WCAG 2.2 AA contrast targets are verified, with Playwright coverage of the core journeys and their error states.
**Plans**: TBD
**UI hint**: yes

### Phase 8: Hardening, Data-Integrity Verification and Release Gate
**Goal**: Every capability is backed by recorded evidence, no fabricated data or execution path survives an audit, and the single local host has an operator runbook.
**Depends on**: Phase 7
**Requirements**: REQ-no-fabricated-data
**Success Criteria** (what must be TRUE):
  1. A repository-wide audit shows no invented, mock or sample market, news, sentiment, backtest or signal data in production paths; every missing value is labelled unknown/unavailable, and any test fixture is labelled as a fixture and never served as a live condition.
  2. The security audit runs against the real repository with file/line evidence; categories that cannot be inspected are marked "Not assessed — evidence unavailable" rather than clean, and no fix is applied before the user approves it.
  3. Provider outage, model outage, database outage, timeout and malformed-output paths are tested, and critical failures demonstrably cannot produce a TRADE.
  4. Backup/restore and migration rollback are tested, dependencies and secrets are scanned, and local services bind to loopback only.
  5. The release suite runs with exact commands and recorded output, unresolved items are listed instead of hidden, and no claim of "zero hallucinations", "perfect analysis" or "zero errors" appears anywhere in the project.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Contracts and Foundation | 0/0 | Not started | - |
| 2. Market Data and Provider Selection | 0/0 | Not started | - |
| 3. Deterministic Analysis, Strategy Rules and Risk Gates | 0/0 | Not started | - |
| 4. LangGraph Orchestration and Local Model Runtime | 0/0 | Not started | - |
| 5. News, Sentiment and CEO Decision Contract | 0/0 | Not started | - |
| 6. Journal, Persistence and Backtesting | 0/0 | Not started | - |
| 7. Research Console UI and Reports | 0/0 | Not started | - |
| 8. Hardening, Data-Integrity Verification and Release Gate | 0/0 | Not started | - |

---
*Roadmap created: 2026-10-13 from `.planning/intel/` synthesis (12 requirements, 23 constraints, 15 decision records)*
