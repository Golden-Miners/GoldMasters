# Phase 4: LangGraph Orchestration and Local Model Runtime — Verification Report

**Phase Goal:** A bounded, resumable graph runs the specialist roles end to end against a locally discovered model, validating every node's output and failing closed on critical failure.
**Verified:** 2026-10-16 · **Status:** passed · **Re-verification:** No — initial verification
**Scope:** `.planning/phases/04-langgraph-orchestration-local-model/` (CONTEXT, RESEARCH, plans 04-01/04-02/04-03 + SUMMARies, langgraph-compat-probe.md) vs `src/goldmasters/graph/`, `src/goldmasters/agents/`, graph/ollama tests, Ollama settings keys.

## Goal Achievement

### Observable Truths (6 ROADMAP criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Starting a run produces a run record (run_id, input ref, config/version ids, timestamps, per-node status) | ✓ VERIFIED | `state.py: run_log()` returns exactly D-4.3 minimal keys (`MINIMAL_LOG_KEYS`); `initial_state` stamps `run_<uuid>`, `compute_input_ref` sha256, `hash_effective_config`, `code_versions()`; `test_graph_state.py` green |
| 2 | State typed, nodes bounded (retry/timeout/cancel/partial-failure config-bounded, no unbounded loops) | ✓ VERIFIED | `RunState` TypedDict; all 6 nodes `async def` with `RetryPolicy(transient-only)` + `TimeoutPolicy(60s)` from `GOLDMASTERS_GRAPH_*` (60s/2 retries, `graph_max_concurrency` optional); fan-out == eligible set asserted in `nodes.py:306`; `test_graph_bounds.py` green |
| 3 | Validation barrier precedes CEO; disagreements preserved, never silently reconciled | ✓ VERIFIED | `barriers.check_barrier` (evidence all-VALID, quality OK + zero flags, verdict present, conflicts verbatim); edge order gate→barrier→finalize; `assemble_decision` barrier-breach → INSUFFICIENT_DATA; `test_graph_barrier.py` green |
| 4 | Every node payload schema-validated; malformed model output → sanitized error, never a guess | ✓ VERIFIED | Ingest re-validates bars/ctx; `generate()` uses `format=<schema>` + temp 0 + `model_validate_json`; `parse_output` → §10 sanitized error; no level/regime/score field on any role schema (pinned by test); `test_graph_validation.py` + `test_graph_nodes_roles.py` (11) green |
| 5 | Ollama endpoint-configured with health + runtime discovery, nothing assumed; availability recorded; T0004 handled honestly | ✓ VERIFIED (open live step deferred) | `GOLDMASTERS_OLLAMA_HOST` loopback-allowlist default + `OLLAMA_MODEL` no-default; `runtime.discover/list()`, `check_health`, `run_model_record`; zero model-name literals in `src/`; live test skip-passes with reason, stub/outage/allowlist tests pass; T0004 explicitly OPEN in probe file + 04-03 SUMMARY with close-out commands — no claim of live verification |
| 6 | Critical failure → INSUFFICIENT_DATA or NO_TRADE; no path to unqualified TRADE | ✓ VERIFIED | `assemble_decision` precedence (fatal/barrier → INSUFFICIENT_DATA; blocked + complete → NO_TRADE; TRADE only on passed verdict + barrier + `trade_eligible_levels`); Wave-1 TRADE-unreachable pinned by test (gate blocks, `risk_percent_for_idea=None`); outage → INSUFFICIENT_DATA, never TRADE; `test_graph_failure_policy.py` (7) green |

**Score:** 6/6 truths verified · **Behavior-unverified:** 0

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `graph/{state,builder,edges,nodes,barriers,runtime}.py` | ✓ VERIFIED | Exist, substantive, wired (builder→nodes→Phase-3 `eligible_agents/evaluate/build_candidate_levels/evaluate_gate`; edges route fatal→finalize) |
| `agents/{prompts,parse}.py` | ✓ VERIFIED (standalone) | 4 role builders + 4 schemas, `model_validate_json` gate; tested standalone — **not yet wired into `builder.py`** (open item O-1) |
| `langgraph-compat-probe.md` | ✓ VERIFIED | GO verdict, pins `langgraph==1.2.15` / `checkpoint-sqlite==3.1.2` / `ollama==0.6.3`, transitive pins match, T0004 ×3 |
| `GOLDMASTERS_GRAPH_*` + `GOLDMASTERS_OLLAMA_*` settings | ✓ VERIFIED | Fail-closed declared keys, hash-covered, `.env.example` + declared-key-set test updated |
| `test_graph_*.py` (6 files) + `test_ollama_discovery.py` | ✓ VERIFIED | 45 passed, 1 skipped (ollama-live, reason recorded) in targeted run |

### Key Links

| From → To | Via | Status |
|-----------|-----|--------|
| nodes → Phase 3 (`eligible_agents`, `evaluate`, `build_candidate_levels`, `evaluate_gate`) | direct calls, no re-implementation | ✓ WIRED |
| gate → TRADE-eligible levels | sole path via `trade_eligible_levels`; `DecisionRecord` validator enforces | ✓ WIRED |
| settings → graph bounds | `RetryPolicy`/`TimeoutPolicy`/`max_concurrency` from declared keys only | ✓ WIRED |
| runtime discovery → run | ⚠️ function exists + tested, **no caller in graph run yet** | ⚠️ OPEN (O-1) |
| role nodes → graph | ⚠️ standalone `generate()`+schemas, **not added to `build_graph`**; CEO slot = `CEO_STUB_CAUSE` unavailable-with-cause | ⚠️ OPEN (O-1) |
| checkpointer → resume | `InMemorySaver(thread_id=run_id)`; `AsyncSqliteSaver` dep pinned but **not wired** | ⚠️ OPEN (O-2) |

### Behavioral Spot-Checks

| Behavior | Result |
|----------|--------|
| Targeted graph+ollama tests (7 files) | ✓ 45 passed, 1 skipped (ollama-live, T0004 open) |
| `ruff check` graph+agents | ✓ clean |
| `mypy` graph+agents (strict) | ✓ 10 files clean |
| No model-name literal in `src/` | ✓ (matches only docstrings/imports, per SUMMARY grep) |

### Anti-Patterns

None. No TODO/FIXME/placeholder in new code; `CEO_STUB_CAUSE` / `ollama_model=None` are validated fail-closed slots, not stubs; no invented numbers (bounds from settings); no mock data in `src/`.

## Open Items (deferred, not blockers — D-4.1 deterministic-first explicitly scopes them out)

- **O-1 — Role-node + discovery wiring into `build_graph`** (analyst/news/research/CEO LLM nodes, `discover()` at run start). Units landed + tested; wiring is a later plan. Criteria still hold: deterministic run is end-to-end; model path is unit-proven and fail-closed by construction (`CEO_STUB_CAUSE`, `resolve_model` error, `check_ceo_required`).
- **O-2 — `AsyncSqliteSaver` builder wiring + cross-restart resume check.** Dep pinned (`3.1.2`); swap churns graph tests, out of 04-03 file scope. "Resumable" currently = `InMemorySaver(thread_id=run_id)` in-process. Later plan owns it.
- **O-3 — T0004 live close-out (operator-owned):** `ollama list; ollama ps; GET /api/tags`, set `GOLDMASTERS_OLLAMA_HOST`/`MODEL`, re-run `test_ollama_discovery.py` expecting live pass. Honestly recorded as OPEN; nothing assumed.

## Gaps Summary

No gaps. All 6 ROADMAP criteria hold in code with passing tests; both known deferrals (standalone role nodes, pending durable saver) were judged non-blocking because the locked deterministic-first decision (D-4.1) scopes Phase 4's runnable claim to the deterministic run plus a honestly-open model binding — and the code matches that scope exactly, with fail-closed behavior (not silent fallback) on every unwired path.

---
_Verified: 2026-10-16_ · _Verifier: gsd-verifier (subagent) — no code changes made_
