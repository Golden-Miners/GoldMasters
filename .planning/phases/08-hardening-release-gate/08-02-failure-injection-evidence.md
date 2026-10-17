# Phase 08 Plan 02 — Failure-Injection Evidence (Wave 1)

**Phase:** 08-hardening-release-gate
**Plan:** 02
**Date:** 2026-10-17
**Criterion:** ROADMAP Phase 8 criterion 3 — provider outage, model outage, DB outage, timeout, and malformed-output paths tested; critical failures demonstrably cannot produce a TRADE.

## Method

- Failure-injection doubles only — no live MT5 terminal, no PostgreSQL cluster, no Ollama model (operator decision: live services not available).
- Each failure mode is injected at its trust boundary and traced through `evaluate_gate` (`src/goldmasters/risk/gate.py:86-135`) and `assemble_decision` (`src/goldmasters/graph/nodes.py:421-443`).
- `evaluate_gate` is fail-closed: any unset/invalid policy input or incomplete/invalid evidence → `passed=False` with `reasons_for_rejection`, `levels=None`.
- `assemble_decision` emits `Decision.TRADE` **only** when `barrier_passed is True and verdict is not None and verdict.passed` (nodes.py:421). Every other path → `NO_TRADE` or `INSUFFICIENT_DATA`, never `TRADE`; non-TRADE records keep levels null (DecisionRecord validator).
- No invented thresholds; exact observed behavior recorded.
- Command: `uv run pytest tests/unit/test_graph_failure_policy.py tests/integration/test_ollama_discovery.py tests/integration/test_mt5_health_api.py -q`
- Python: `.venv/Scripts/python` (uv available; no stalls).

## Injected failure modes

### (1) Provider outage — MT5 TerminalGateway disconnected / terminal-closed

**Injection:** `test_provider_outage_evidence_missing_blocks_gate` — `evaluate_gate` called with an empty evidence map (`{}`), simulating the MT5 terminal being unreachable so no evidence is produced.

**Gate trace (gate.py:86-135):** `evidence` is empty → `reasons.append("evidence incomplete: required evidence set is missing or empty")` → `verdict.passed=False`, `verdict.levels=None`, `reasons_for_rejection` non-empty.

**Observed decision:** `passed=False`, `levels=None`, reason `"evidence incomplete: required evidence set is missing or empty"`.

**Decision trace (nodes.py:421-443):** `verdict.passed` is False → the `barrier_passed is True and verdict.passed` TRADE constructor is not reached. With complete evidence → `Decision.NO_TRADE` carrying the gate's rejection reasons; with incomplete evidence → `Decision.INSUFFICIENT_DATA`. Levels always `None`.

**Result:** NO_TRADE / INSUFFICIENT_DATA. **Never TRADE.** ✅

### (2) Ollama model outage — model discovery fails

**Injection:** `test_ollama_model_outage_discovery_fails_closed` — Ollama host pointed at a refused loopback port (`127.0.0.1:9`), `graph_node_max_retries=1` → `discover()` exhausts bounded retries.

**Observed decision:** `discovery.reachable=False`, `discovery.models==()`, `discovery.error` set (`ErrorCode.INTERNAL_ERROR`), `discovery.attempts==2` (first try + 1 locked retry). `resolve_model()` returns an `ErrorPayload` (not a model id) — `not isinstance(resolved, str)`.

**Gate/nodes trace:** No model id ever escapes an outage; role nodes skip without touching evidence; evidence stays incomplete → `evaluate_gate` blocks (`passed=False`); `assemble_decision` → `INSUFFICIENT_DATA`.

**Result:** INSUFFICIENT_DATA. **Never TRADE.** ✅

### (3) DB outage — connection refused

**Injection:** `test_db_outage_evidence_invalid_blocks_gate` — `evaluate_gate` called with evidence carrying `EvidenceStatus.INVALID` for `db_persistence`, simulating DB-backed evidence that cannot be validated (connection refused).

**Gate trace (gate.py:86-135):** `invalid = sorted(key for key, status in evidence.items() if status != EvidenceStatus.VALID)` → `["db_persistence"]` → `reasons.append("evidence not valid: db_persistence")` → `verdict.passed=False`, `levels=None`.

**Observed decision:** `passed=False`, `levels=None`, reason `"evidence not valid: db_persistence"`.

**Decision trace:** `verdict.passed` is False → TRADE constructor unreachable → `NO_TRADE` (complete evidence) or `INSUFFICIENT_DATA` (incomplete evidence).

**Result:** NO_TRADE / INSUFFICIENT_DATA. **Never TRADE.** ✅

### (4) Timeout — node/probe/graph timeout exceeded

**Injection:** `test_timeout_gate_crash_insufficient_data` — `make_gate_node`'s `evaluate_gate` monkeypatched to raise `TimeoutError("FIXTURE graph node timeout exceeded")`.

**Observed decision:** `closing["fatal"] == "gate"`, `closing["agent_statuses"]["gate"] == AgentRunStatus.ERROR.value`, `closing["decision"].decision == Decision.INSUFFICIENT_DATA`, `decision.entry is None`, reason contains `"fatal stage failure: gate"`.

**Gate/nodes trace:** Gate crash is caught by `make_gate_node` (nodes.py:375-384) → `fatal="gate"` → edge `route_after_gate` skips to `FINALIZE` → `assemble_decision` hits the `state["fatal"] is not None` branch → `INSUFFICIENT_DATA`. No levels.

**Result:** INSUFFICIENT_DATA. **Never TRADE.** ✅

### (5) Malformed output — invalid JSON/bar fields or unparseable model response

**Injection:** `test_malformed_output_evidence_invalid_blocks_gate` — `evaluate_gate` called with evidence carrying `EvidenceStatus.INVALID` for `model_response`, simulating an unparseable model response that failed schema validation (`generate` returns `CONTRACT_VALIDATION_FAILED`).

**Gate trace (gate.py:86-135):** `invalid = ["model_response"]` → `reasons.append("evidence not valid: model_response")` → `verdict.passed=False`, `levels=None`.

**Observed decision:** `passed=False`, `levels=None`, reason `"evidence not valid: model_response"`.

**Gate/nodes trace:** Malformed model output fails contract validation → evidence `INVALID` (never a filled-in guess, per runtime.py:234-240) → gate blocks → TRADE unreachable. Malformed bars fail ingest contract validation → `fatal="ingest"` → `INSUFFICIENT_DATA`.

**Result:** NO_TRADE / INSUFFICIENT_DATA. **Never TRADE.** ✅

## Sole TRADE gate confirmed

`test_assemble_decision_trade_only_when_barrier_and_verdict_passed` — with a passing `GateVerdict` (`passed=True`, levels present) AND `barrier_passed=True` AND complete evidence → `Decision.TRADE` with validated levels. The same passing verdict with `barrier_passed=False` (breached barrier) → not TRADE, levels `None`. Confirms `assemble_decision` (nodes.py:421-443) emits TRADE only on `barrier_passed and verdict.passed`.

## Test results

| Suite | Result |
|---|---|
| `tests/unit/test_graph_failure_policy.py` | 16 passed (7 pre-existing + 9 failure-injection) |
| `tests/integration/test_ollama_discovery.py` | 6 passed, 1 skipped (no Ollama server — T0004 open, expected) |
| `tests/integration/test_mt5_health_api.py` | 4 passed, 3 failed (pre-existing, environmental — see below) |

## Pre-existing / environmental findings (not regressions)

`test_mt5_health_api.py` quote tests fail because execution date Sat 2026-10-17 is inside the configured weekend-closed window (`Fri 21:00-Sun 22:00`, `settings.py` `weekend_close_utc`). `validate_quote` correctly stamps `DISCONNECTED` per D-57/D-58 → `/v1/market/quote` returns 503 `"quote is disconnected"`. This is intentional fail-closed behavior, not a regression: these same 3 tests failed in the baseline run before any Plan 02 changes. No production code was modified. The 3 affected tests:
- `test_quote_endpoint_returns_tick_quote_with_null_last`
- `test_unsupported_selection_fails_visibly_without_fallback` (quote assertion)
- `test_bars_quote_keep_canonical_id_separate_from_provider_symbol`

All other mt5_health_api tests (bars endpoint, health seven-key object, all five provider states, unsupported selection) pass.

## Deviations from plan

None. All five failure modes injected via doubles; each yields NO_TRADE or INSUFFICIENT_DATA; gate/nodes trace recorded; no production code changes; no invented thresholds.

## Conclusion

Every critical failure path (provider outage, model outage, DB outage, timeout, malformed output) is proven fail-closed: `evaluate_gate` returns `passed=False` with reasons and `levels=None`, and `assemble_decision` emits `TRADE` only when `barrier_passed is True and verdict.passed`. No injection produces an unqualified TRADE. ROADMAP Phase 8 criterion 3 satisfied.
