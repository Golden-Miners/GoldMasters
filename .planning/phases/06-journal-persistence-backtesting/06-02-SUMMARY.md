---
phase: 06-journal-persistence-backtesting
plan: 02
subsystem: backtest-runner
tags: [backtest, splits, fills, provenance, persistence]
requires: [06-01-journal-persistence, 01-contracts-foundation]
provides: [backtest-splits-gate, next-bar-open-fills, live-seam-runner, backtest-persistence]
affects: [06-03-splits-metrics]
tech-stack:
  added: []
  patterns: [bars-so-far-live-seam, declared-placeholder-costs-D-6.1, manifest-by-dataset-ref-D-6.3]
key-files:
  created:
    - src/goldmasters/backtest/__init__.py
    - src/goldmasters/backtest/splits.py
    - src/goldmasters/backtest/fills.py
    - src/goldmasters/backtest/runner.py
    - src/goldmasters/backtest/persistence.py
    - tests/unit/test_backtest_splits.py
    - tests/unit/test_backtest_record.py
    - tests/integration/test_backtest_persistence.py
  modified:
    - tests/unit/agent_fixtures.py
decisions:
  - "Manifest joins records by dataset_ref (0003 has no run_id column on either table); backtest_run_id is the per-strategy {run_id}:{strategy_id} key"
  - "Gate direction inferred from validated levels (stop<entry LONG, mirrored SHORT); equal levels block as indeterminate"
  - "FillCosts carry Decimal zeros as declared placeholders; require_confirmed fails closed until the operator confirms values"
  - "Strategy params in tests reuse the FIXTURE builders from each agent's own unit test; operator thresholds stay open per CONTEXT"
metrics:
  duration: ~1 h across resumed session
  completed: 2026-10-16T13:09:05Z
status: complete
actuals:
  tokens: 45000
  tasks: 3
  commits: 3
plan_head_before: ee03d1a
plan_head_after: 3c7ec64
commits: 3
---

# Phase 06 Plan 02: Backtest Runner (Wave 2) Summary

Deterministic backtest loop over the live path: splits gate plus manifest provenance, next-bar-open fills with declared placeholder costs, and a runner driving all 10 pinned 1.0.0 strategies through evaluate, gate, and Decimal level math with persistence round-trip proof.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Splits gate plus manifest provenance | 8701196 | backtest/splits.py, __init__.py, test_backtest_splits.py |
| 2 | Fill model plus runner over live seam | a7c687d | backtest/fills.py, runner.py, test_backtest_record.py |
| 3 | Backtest record persistence round-trip | 3c7ec64 | backtest/persistence.py, test_backtest_persistence.py |

## Evidence

- `uv run pytest tests/unit/test_backtest_splits.py tests/unit/test_backtest_record.py tests/integration/test_backtest_persistence.py -q` → 18 passed
- `uv run pytest tests/unit -q` → all passed (no regressions, incl. agent_fixtures Decimal change)
- `uv run pytest tests/integration/test_backtest_persistence.py tests/integration/test_migration_roundtrip.py -q` → 3 passed
- `uv run ruff format --check` on all 9 touched files → clean
- `uv run ruff check` on all 9 touched files → clean
- `uv run mypy --strict` on all 9 touched files → no issues in 9 source files
- Repo-wide `mypy --strict .` remains red from pre-existing errors (78 errors in 20 files, none in this plan's scope; plus vendored `agent/skills` module-mapping noise) — logged to deferred-items.md, not introduced here

## Must-Have Truths — Status

- Live seam for all 10 pinned 1.0.0 strategies: PROVEN (10 records per run; evaluate with bars-so-far only, then evaluate_gate, then trade_eligible_levels; non-pass yields null levels via base validator)
- Full assumption set on every result: PROVEN (run plus dataset ref/hash, range, timezone, timeframe, symbol mapping in manifest, strategy version, parameter hash, fill-model string, splits, code_version, data_quality, errors)
- IS/VS/OOS separation with honest gap reporting: PROVEN (DST-crossing boundary test, gaps reported as excluded periods never filled, out-of-window refused by runner)
- Next-bar-open fills, placeholder costs, no authoritative metric: PROVEN (FILL_MODEL marker on assumptions and every metric definition; require_confirmed fails closed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Duplicate bars tripped the order check before dedup**
- **Found during:** Task 1 verify
- **Issue:** `enforce_splits` raised on `[bar, bar]` instead of reporting the duplicate.
- **Fix:** Dedup first (reported in duplicates plus quality flags), then order-check the unique sequence.
- **Files modified:** src/goldmasters/backtest/splits.py
- **Commit:** 8701196 (within Task 1 work, corrected in 3c7ec64)

**2. [Rule 1 - Bug] Contract Decimal types, not strings, in source**
- **Found during:** mypy gate
- **Issue:** `BacktestAssumptions` costs and `BacktestMetric.value` are `Decimal`; `MarketBar` timestamps are `datetime | None`. String-typed FillCosts and unguarded `.isoformat()` calls failed strict typing.
- **Fix:** FillCosts holds Decimal zeros; metrics carry `Decimal(count)`; new fail-closed `bar_times()` guard refuses timestamp-less bars. Wire form stays decimal-as-string via `model_dump(mode="json")`.
- **Files modified:** fills.py, runner.py, splits.py, persistence.py
- **Commit:** 3c7ec64

**3. [Rule 3 - Blocking] agent_fixtures tick_size blocked the mandated mypy gate**
- **Found during:** mypy gate
- **Issue:** `make_ctx` default `tick_size: str` contradicts `MarketContext` (`Decimal | None`); pre-existing, but the plan mandates `mypy --strict` and no caller overrides the default.
- **Fix:** Default is now `Decimal("0.01")` — runtime-identical (pydantic already coerced it), full unit suite still green.
- **Files modified:** tests/unit/agent_fixtures.py
- **Commit:** 3c7ec64

**4. Added persistence.py (extra file beyond plan list)**
- **Found during:** Task 3
- **Issue:** Plan's file list names only the integration test, but parameterized read/write helpers keep SQL centralized per the journal store.py pattern instead of inlining SQL in the test.
- **Fix:** `src/goldmasters/backtest/persistence.py` with write/read/list functions; test asserts through them.
- **Commit:** 3c7ec64

**5. Manifest join key is dataset_ref, not run_id/dataset_id**
- **Found during:** Task 1
- **Issue:** Plan key-link says rows "join by run_id/dataset_id" but the 0003 tables (06-01, locked) carry no run_id column; the join is `backtest_run.dataset_ref = dataset_manifest.dataset_ref`, with `backtest_run_id = {run_id}:{strategy_id}` as the per-strategy key.
- **Fix:** Implemented and tested on dataset_ref; no migration change (out of scope).
- **Commit:** 8701196, 3c7ec64

## Known Stubs

None. Stub scan over `src/goldmasters/backtest/` found only the intentional D-6.1 declared-cost mechanism (PLACEHOLDER marker on assumptions and metric definitions with `require_confirmed` fail-closed); no TODO/FIXME markers; every path is live in tests.

## Threat Flags

None beyond the plan's register. Mitigations landed: T-06-05 (bars-so-far with close-time cutoff, ctx-cutoff test), T-06-06 (gaps to quality_flags plus excluded periods, misordered input raises), T-06-07 (FILL_MODEL marker plus per-metric disclaimer plus `require_confirmed`), T-06-08 (bars_sha256 in source_hashes, join-by-dataset_ref test), T-06-SC (no installs).

## Self-Check: PASSED

- All 9 files exist on disk.
- All 3 commits (`8701196`, `a7c687d`, `3c7ec64`) are ancestors of HEAD; `git rev-list --count ee03d1a..HEAD` = 3.
- No ledger file existed for 06-02 (orchestrator did not create one); base `ee03d1a` is the pre-plan HEAD from 06-01, measured not narrated.
