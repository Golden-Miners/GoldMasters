---
phase: 05-news-sentiment-ceo
plan: 03
subsystem: ceo-decision-contract
tags: [graph-nodes, ceo-contract, trade-conjunction, traceability, fail-closed]
requires: [news retrieval-adapter interface, frozen DecisionRecord, Phase 4 spine]
provides: [bounded role nodes, TRADE conjunction tests, traceability metric]
affects: [Phase 6 persistence, Phase 7 surfaces, T0004 model runtime]
tech-stack:
  added: []
  patterns: [bounded async nodes, RoleOptions injection, fail-closed skip, read-only metric]
key-files:
  created:
    - src/goldmasters/graph/role_nodes.py
    - src/goldmasters/graph/traceability.py
    - tests/unit/test_ceo_contract.py
  modified:
    - src/goldmasters/graph/builder.py
decisions:
  - "Unconfigured role nodes skip without touching evidence; configured failures record INSUFFICIENT_DATA with non-VALID evidence"
  - "CEO-prose node validates text-only CeoProse; levels stay gate-owned, prose handoff awaits T0004 model runtime"
  - "Traceability measured with no target threshold; empty set reports 100.0 (nothing incomplete)"
metrics:
  duration: ~15 min
  completed: 2026-10-16
status: complete
actuals:
  tokens: 8885
  tasks: 3
  commits: 3
plan_head_before: 2b1425c
plan_head_after: eedd07e
---

# Phase 05 Plan 03: CEO + Role Nodes Summary

Analyst, news-sentiment, research and CEO-prose roles run as bounded async graph nodes through the pre-CEO barrier with spine semantics unchanged; the TRADE conjunction is tested conjunct-by-conjunct and decision traceability is measured with no target set.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | End-to-end news-sentiment role node through barrier to decision | 82e42fc | role_nodes.py, builder.py, test_ceo_contract.py |
| 2 | Analyst, research and CEO-prose nodes plus TRADE conjunction test | 12a05f4 | role_nodes.py, builder.py, test_ceo_contract.py |
| 3 | Decision-traceability metric with operator-visible display | eedd07e | traceability.py, test_ceo_contract.py |

## Verification Evidence

- `uv run pytest tests/unit/test_ceo_contract.py tests/unit/test_graph_barrier.py tests/unit/test_graph_nodes_roles.py -x` → **26 passed** (8 new contract tests)
- `uv run ruff check src/goldmasters/graph/ tests/unit/test_ceo_contract.py` → **clean**
- `uv run ruff format --check` on all four touched files → **clean** (the `runtime.py` format nit is pre-existing, untouched, out of scope)
- `uv run mypy src/goldmasters/graph/` → **strict clean, 9 files**
- Parallel-safe: 05-02 committed disjoint files (`data/news/sentiment.py`, `test_news_sentiment.py`) — zero overlap confirmed via diff

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Bounded-retry call count in analyst failure test**
- **Found during:** Task 2
- **Issue:** Test asserted 1 model call on garbage output, but `generate` honors the locked retry budget (1 + `graph_node_max_retries` = 3 attempts).
- **Fix:** Assertion pins the bound (`1 + settings.graph_node_max_retries`) instead of 1 — the retry-then-fail-closed behavior is the spec, not the bug.
- **Files modified:** tests/unit/test_ceo_contract.py
- **Commit:** 12a05f4

**2. [Rule 1 - Bug] caplog misses INFO log line by default**
- **Found during:** Task 3
- **Issue:** `log_traceability` emits at INFO; pytest captures WARNING+ by default so `caplog.text` was empty.
- **Fix:** Test wraps the assertion in `caplog.at_level("INFO", logger=...)` — production code unchanged.
- **Files modified:** tests/unit/test_ceo_contract.py
- **Commit:** eedd07e

## Key Decisions

- Unconfigured role nodes **skip** (no evidence entry, no model call) so the default graph runs the deterministic spine exactly as before; only a *configured* source that fails records `INSUFFICIENT_DATA` with non-`VALID` evidence and breaches the barrier. A skipped node is still non-`ok`, so the CEO agreement gate blocks prose.
- CEO-prose node validates `CeoProse` (thesis/invalidation strings — the schema cannot carry levels) and records status only. `assemble_decision` remains the sole constructor; the validated-prose-to-decision handoff awaits the T0004 model runtime and needs no plan change until then.
- Traceability empty set reports 100.0% (nothing incomplete); missing `config_hash`/`code_versions` counts as incomplete even with resolving refs.

## Threat Flags

None — no new surface beyond the plan's threat model. T-05-06 (prose text-only, sole constructor intact), T-05-07 (schema validation before use, sanitized errors), T-05-08 (shared retry/timeout policies, no loops) all mitigated in `role_nodes.py`; no new packages installed.

## Self-Check: PASSED

- All 4 files exist on disk.
- All 3 commits (82e42fc, 12a05f4, eedd07e) are ancestors of HEAD; no file deletions in task commits.
- 05-02 parallel files untouched (disjoint, verified via `git diff`).
