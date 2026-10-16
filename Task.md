# GoldMasters — Task Tracker

**Rule:** Update status only after the task's acceptance checks have actually run. This document tracks planned work; no implementation tasks are claimed complete by generating documentation.

## Status definitions
- `NOT STARTED` — not begun.
- `IN PROGRESS` — work underway.
- `BLOCKED` — cannot proceed; blocker recorded.
- `DONE` — acceptance checks passed and evidence recorded.
- `NEEDS REVIEW` — output exists but requires user/design/security approval.

## Phase 0 — Discovery and scope

- [x] T0001 Inspect repository root, branch, status, README, manifests and existing tests. **Accept:** tree and baseline test results recorded; no files changed.
- [x] T0002 Inspect OpenCode config and verify installed MCP/skill names and activation paths. **Accept:** evidence-based inventory; unavailable tools marked unavailable.
- [x] T0003 Verify OS, MT5 terminal, Python integration compatibility and broker symbols. **Accept:** tested read-only connection and symbol mapping notes; no orders sent.
- [ ] T0004 Verify Ollama endpoint and installed models. **Accept:** health-check output and model inventory recorded.
- [ ] T0005 Resolve remaining PRD questions. **Accept:** approved decisions or explicit unresolved entries in Memory.md.
- [ ] T0006 Record baseline test/lint/type-check state. **Accept:** commands and results saved.

## Phase 1 — Contracts and foundation

- [ ] T0101 Finalise `Schema.md` domain and API contracts.
- [ ] T0102 Add architecture decision records for deployment, provider boundary, and persistence.
- [ ] T0103 Create backend/frontend project skeleton after repository inspection.
- [ ] T0104 Add configuration validation and safe `.env.example`.
- [ ] T0105 Add structured logging, redaction and correlation IDs.
- [ ] T0106 Set up database migrations and persistence tests.
- [ ] T0107 Configure linting, formatting, typing, unit tests and CI.
- Acceptance gate: clean baseline plus passing foundation checks; actual commands/results recorded.

## Phase 2 — Market data

- [ ] T0201 Define provider protocol and normalized bar/quote/spec models.
- [ ] T0202 Implement MT5 read-only adapter.
- [ ] T0203 Implement canonical instrument and provider-symbol mapping.
- [ ] T0204 Add freshness, ordering, OHLC, duplicate, gap and finite-number validation.
- [ ] T0205 Add provider health and explicit unsupported-symbol failures.
- [ ] T0206 Add provider contract tests and failure tests.
- Acceptance gate: live connection verified where environment permits; failure paths tested; no fabricated live data.

## Phase 3 — Deterministic analysis

- [ ] T0301 Define candle/timeframe conventions and timezone policy.
- [ ] T0302 Implement versioned market-structure primitives.
- [ ] T0303 Implement trend/regime state classification with explicit rules.
- [ ] T0304 Define strategy interface and eligibility checks.
- [ ] T0305 Implement only user-approved initial strategies.
- [ ] T0306 Test numeric precision, tick sizes and boundary cases.
- Acceptance gate: deterministic outputs and unit tests pass; definitions documented.

## Phase 4 — LangGraph and agents

- [x] T0401 Define typed graph state and run lifecycle. **Accept:** RunState + run_log (D-4.3 pinned) tested — 04-02-SUMMARY (2026-10-16), `pytest tests/unit/test_graph_state.py` 4 passed.
- [x] T0402 Build graph skeleton and explicit conditional edges. **Accept:** ingest/select/evaluate/gate/barrier/finalize + 3 conditional routes — same evidence.
- [x] T0403 Add bounded retry, timeout, cancellation and partial-failure handling. **Accept:** RetryPolicy transient-only + TimeoutPolicy from GOLDMASTERS_GRAPH_* settings, failure-injection suite — `test_graph_bounds.py` + `test_graph_failure_policy.py` green, full suite 625 passed.
- [ ] T0404 Implement Market Analyst, Trend and Instrument agents.
- [ ] T0405 Implement News and Sentiment adapters/agents with provenance.
- [ ] T0406 Implement Research agent with citations and source restrictions.
- [x] T0407 Implement Strategy Supervisor and individual strategy nodes. **Accept:** `matrix_from_settings` over all 10 rows + evaluate fan-out == eligible set — 04-02-SUMMARY (2026-10-16), bounds suite green.
- [ ] T0408 Implement Signaling Agent using validated strategy outputs only.
- [x] T0409 Implement deterministic risk/validation gate. **Accept:** gate node on Phase 3 `evaluate_gate` (sole TRADE path) + deterministic pre-CEO barrier — 04-02-SUMMARY (2026-10-16), barrier + failure-policy suites green.
- [ ] T0410 Implement CEO decision contract and fail-closed rules. (Deterministic terminal mapper + stubbed synthesis slot landed in 04-02; model-assisted CEO stays open on T0004.)
- [ ] T0411 Add schema/contract tests for every node and graph path. (Partial in 04-02: all 6 built nodes covered; role nodes T0404–T0410 pending.)
- Acceptance gate: all graph branches tested; no unvalidated LLM output reaches a decision.

## Phase 5 — Persistence, journal and monitoring

- [ ] T0501 Persist run metadata, agent evidence and immutable decisions.
- [ ] T0502 Implement append-only outcome/journal records.
- [ ] T0503 Implement run trace and sanitized diagnostics.
- [ ] T0504 Add provider/model/system health checks.
- [ ] T0505 Add duplicate request and transaction failure tests.
- Acceptance gate: records survive restart; failure/rollback behaviour tested.

## Phase 6 — Backtesting

- [ ] T0601 Define dataset manifest and provenance.
- [ ] T0602 Define fill model, spread, commissions, slippage and market-hours assumptions.
- [ ] T0603 Implement backtest runner against versioned deterministic strategies.
- [ ] T0604 Separate in-sample, validation and out-of-sample periods.
- [ ] T0605 Test look-ahead leakage and timestamp alignment.
- [ ] T0606 Compute metrics in code and cross-check with hand-verifiable test cases.
- Acceptance gate: assumptions visible; tests prove costs and splits are applied.

## Phase 7 — Web UI

- [ ] T0701 Implement Overview and system/provider status.
- [ ] T0702 Implement Instrument Workbench.
- [ ] T0703 Implement Decision Detail and evidence ledger.
- [ ] T0704 Implement News & Sentiment.
- [ ] T0705 Implement Strategy Lab and Backtest Results.
- [ ] T0706 Implement Journal and Agent Runs.
- [ ] T0707 Implement Data Providers and Ollama Model Health.
- [ ] T0708 Implement loading, empty, error, stale, offline and insufficient-data states.
- [ ] T0709 Verify keyboard navigation, contrast and responsive layouts.
- [ ] T0710 Add Playwright E2E coverage for core flows.
- Acceptance gate: UI uses actual API data; no placeholder data is presented as real.

## Phase 8 — Security and release

- [ ] T0801 Run security audit against actual repository and record evidence.
- [ ] T0802 Scan dependencies and secrets.
- [ ] T0803 Test API validation, SSRF, XSS, CORS, auth boundaries and rate limits as applicable.
- [ ] T0804 Confirm no trade execution paths, credentials, or order methods are present.
- [ ] T0805 Test provider outage, Ollama outage, DB outage, timeout and malformed outputs.
- [ ] T0806 Test backup/restore and migration rollback strategy.
- [ ] T0807 Document setup, operation, troubleshooting and limitations.
- [ ] T0808 Run full release test suite and record exact output.
- Acceptance gate: all release-blocking findings resolved or explicitly accepted by user; no untested claims.

## Current checkpoint

- Documentation set drafted.
- Implementation status: **NOT STARTED / NOT VERIFIED**.
- Repository, runtime, MT5, Ollama and installed OpenCode tools have not been inspected from this document-generation task.
- Next task: **T0001 — inspect repository and record baseline without modifying code.**
