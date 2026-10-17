---
phase: 08-hardening-release-gate
plan: 02
subsystem: failure-injection
tags: [failure-injection, outage, no-trade, risk-gate, assemble-decision]
requires: [08-01]
provides: [failure-injection-evidence]
affects: []
tech_stack:
  added: []
  patterns: [fail-closed-gate, failure-injection-doubles, no-live-services]
key_files:
  created:
    - .planning/phases/08-hardening-release-gate/08-02-failure-injection-evidence.md
  modified:
    - tests/unit/test_graph_failure_policy.py
decisions:
  - "All five failure modes injected via doubles only (no live MT5 terminal, PostgreSQL cluster, or Ollama model — operator decision: live services not available); each yields NO_TRADE or INSUFFICIENT_DATA, never an unqualified TRADE"
  - "evaluate_gate (gate.py:86-135) is the sole TRADE gate: unset/invalid policy or incomplete/invalid evidence -> passed=False with reasons_for_rejection and levels=None"
  - "assemble_decision (nodes.py:421-443) emits Decision.TRADE only when barrier_passed is True and verdict.passed; every other path -> NO_TRADE or INSUFFICIENT_DATA with levels null"
  - "No production code changes; no invented thresholds; exact observed behavior only"
metrics:
  duration: ~36 min
  completed: 2026-10-17
  commits: 1
  tests: 16 graph-failure-policy passed; 6 ollama-discovery passed + 1 skipped (no server); mt5 quote tests have 3 pre-existing environmental failures (weekend)
plan_head_before: dabda3347e2b5079952082586b1552e1b40b0f90
plan_head_after: db1ab88d8335b6fb37e130430b755fc3b6988dee
status: complete
actuals:
  tokens: 4400
  tasks: 1
  commits: 1
---

# Phase 08 Plan 02: Failure-Injection Summary

## One-liner

Fail-closed failure-injection across provider, model, DB, timeout, and malformed-output paths proves every critical failure yields NO_TRADE or INSUFFICIENT_DATA — never an unqualified TRADE — with `evaluate_gate` as the sole TRADE gate and `assemble_decision` emitting TRADE only on `barrier_passed and verdict.passed`.

## Tasks Completed

| # | Name | Files | Status |
|---|------|-------|--------|
| 1 | Failure-injection across provider, model, DB, timeout, malformed — prove no unqualified TRADE | tests/unit/test_graph_failure_policy.py, .planning/phases/08-hardening-release-gate/08-02-failure-injection-evidence.md | Done |

## Evidence

**Task 1 — Failure injection (doubles only, no live services):**

Each failure mode was injected at its trust boundary and traced through `evaluate_gate` (`src/goldmasters/risk/gate.py:86-135`) and `assemble_decision` (`src/goldmasters/graph/nodes.py:421-443`). Full per-mode decision, gate trace, and nodes trace are recorded in `08-02-failure-injection-evidence.md`.

| # | Failure mode | Injection | Gate result (passed=False, reasons) | Decision |
|---|--------------|-----------|-------------------------------------|----------|
| 1 | Provider outage — MT5 TerminalGateway disconnected / terminal-closed | empty evidence map | "evidence incomplete: required evidence set is missing or empty"; levels=None | NO_TRADE / INSUFFICIENT_DATA |
| 2 | Ollama model outage — discovery/list() fails | refused loopback port 127.0.0.1:9, max_retries=1 | resolve_model returns ErrorPayload (not a str); no model id escapes | INSUFFICIENT_DATA |
| 3 | DB outage — connection refused | evidence carries INVALID for db_persistence | "evidence not valid: db_persistence"; levels=None | NO_TRADE / INSUFFICIENT_DATA |
| 4 | Timeout — node/probe/graph timeout exceeded | evaluate_gate monkeypatched to raise TimeoutError | gate crash -> fatal="gate" -> INSUFFICIENT_DATA | INSUFFICIENT_DATA |
| 5 | Malformed output — invalid JSON/bar fields or unparseable model response | evidence carries INVALID for model_response | "evidence not valid: model_response"; levels=None | NO_TRADE / INSUFFICIENT_DATA |

**Sole TRADE gate confirmed:** `test_assemble_decision_trade_only_when_barrier_and_verdict_passed` — a passing `GateVerdict` + `barrier_passed=True` + complete evidence → `Decision.TRADE` with validated levels; the same passing verdict with `barrier_passed=False` → not TRADE, levels null. Confirms TRADE fires only on `barrier_passed and verdict.passed` (nodes.py:421-443).

**Test results:**
- `tests/unit/test_graph_failure_policy.py`: 16 passed (7 pre-existing + 9 failure-injection)
- `tests/integration/test_ollama_discovery.py`: 6 passed, 1 skipped (no Ollama server — T0004 open, expected)
- `tests/integration/test_mt5_health_api.py`: 4 passed, 3 failed (pre-existing environmental — see below)

## Must-Have Truths — Status

- Provider outage → NO_TRADE or INSUFFICIENT_DATA, never TRADE: PASS
- Ollama model outage → NO_TRADE or INSUFFICIENT_DATA, never TRADE: PASS
- Database outage → NO_TRADE or INSUFFICIENT_DATA, never TRADE: PASS
- Timeout → NO_TRADE or INSUFFICIENT_DATA, never TRADE: PASS
- Malformed output → NO_TRADE or INSUFFICIENT_DATA, never TRADE: PASS
- No code path ends in unqualified TRADE; evaluate_gate sole TRADE gate, returns None/blocked when any input unset/invalid: PASS

## Pre-existing / environmental findings (not regressions)

`test_mt5_health_api.py` quote tests fail because execution date Sat 2026-10-17 is inside the configured weekend-closed window (`Fri 21:00–Sun 22:00`, `settings.py` `weekend_close_utc`). `validate_quote` correctly stamps `DISCONNECTED` per D-57/D-58 → `/v1/market/quote` returns 503 `"quote is disconnected"`. This is intentional fail-closed behavior, not a regression: these same 3 tests failed in the baseline run before any Plan 02 changes. No production code was modified. Affected tests:
- `test_quote_endpoint_returns_tick_quote_with_null_last`
- `test_unsupported_selection_fails_visibly_without_fallback` (quote assertion)
- `test_bars_quote_keep_canonical_id_separate_from_provider_symbol`

All other mt5_health_api tests (bars endpoint, health seven-key object, all five provider states, unsupported selection) pass.

## Deviations from Plan

None. All five failure modes injected via doubles; each yields NO_TRADE or INSUFFICIENT_DATA; gate/nodes trace recorded; no production code changes; no invented thresholds.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced; only test/evidence files added.

## Self-Check: PASSED

- `.planning/phases/08-hardening-release-gate/08-02-failure-injection-evidence.md` exists ✅
- `tests/unit/test_graph_failure_policy.py` commit `db1ab88` exists ✅
- Commit `db1ab88d8335b6fb37e130430b755fc3b6988dee` is an ancestor of HEAD ✅
- All failure-injection tests pass ✅
- Measured commits = 1 (plan_head_before dabda334..plan_head_after db1ab88) ✅

## Risk

- mt5_health_api quote tests are environmentally blocked by the weekend-closed window; document as pre-existing, not a code defect. No action required (no production code change).
- Live MT5/PostgreSQL/Ollama unavailable; outage paths proven via doubles per operator decision.
