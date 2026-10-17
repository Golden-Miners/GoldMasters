---
phase: 06-journal-persistence-backtesting
plan: 01
subsystem: journal-persistence
tags: [postgres, alembic, jsonb, immutable-journal, append-only]
requires: [01-contracts-foundation, 04-run-log-boundary]
provides: [journal-entry-table, outcome-observation-table, backtest-run-table, dataset-manifest-table, journal-store]
affects: [06-02-backtest-runner, 06-03-splits-metrics]
tech-stack:
  added: []
  patterns: [document-promotion-split-D-07, throwaway-per-run-db, PriceStr-string-decimals]
key-files:
  created:
    - apps/api/migrations/versions/0002_journal_outcome.py
    - apps/api/migrations/versions/0003_backtest.py
    - src/goldmasters/journal/store.py
    - src/goldmasters/journal/__init__.py
    - tests/integration/test_journal_roundtrip.py
  modified:
    - tests/integration/test_migration_roundtrip.py
decisions:
  - "0003 backtest_run carries data_quality, parameter_hash, generated_at beyond the plan's column list so a full BacktestRecord is promotable; all are required record fields"
  - "Outcome float rejection enforced at write time in append_outcome, not only asserted in tests (T-06-04)"
  - "No-mutation-path test asserts __all__ plus absence of UPDATE/DELETE/DROP tokens rather than getmembers, which counts imported helpers"
metrics:
  duration: ~11 min
  completed: 2026-10-16T12:28:04Z
status: complete
actuals:
  tokens: 5828
  tasks: 3
  commits: 4
plan_head_before: e6eab3b
plan_head_after: ee03d1a
commits: 4
---

# Phase 06 Plan 01: Journal Store (Wave 1) Summary

Immutable journal persistence foundation: 0002/0003 migrations plus a snapshot writer and append-only outcome writer with restart-survival proof.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | 0002 journal/outcome and 0003 backtest/manifest migrations | fc3edb9 | 0002_journal_outcome.py, 0003_backtest.py, test_migration_roundtrip.py |
| 1b | ruff-format whitespace on 0002 (post-gate) | ee03d1a | 0002_journal_outcome.py |
| 2 | Journal store — snapshot plus append-only outcome writer | e0fa358 | src/goldmasters/journal/store.py, __init__.py |
| 3 | Immutability plus restart-survival integration tests | a386971 | tests/integration/test_journal_roundtrip.py |

## Evidence

- `uv run pytest tests/integration/test_journal_roundtrip.py tests/integration/test_migration_roundtrip.py -q` → 7 passed (6 journal + 1 migration, throwaway per-run DB, repo-local cluster)
- `uv run pytest tests/integration/test_journal_roundtrip.py tests/integration/test_migration_roundtrip.py tests/integration/test_persistence_roundtrip.py -q` → 8 passed
- `uv run pytest tests/unit -q` → all passed (~300 tests, no regressions)
- `uv run ruff format --check` on all 6 changed files → clean
- `uv run ruff check` → clean
- `uv run mypy --strict src/goldmasters/journal/` → no issues
- `git diff --stat HEAD -- apps/api/migrations/versions/0001_contract_document.py` → empty; 0001 byte-identical
- Migration cycle verified in-test: apply → full rollback (none of the 5 tables / 6 indexes remain) → re-apply restores all

## Must-Have Truths — Status

- Immutable snapshots with evidence refs survive restart: PROVEN (fresh-engine re-read equality, TRADE fixture with decimal levels)
- Outcomes append without mutating the original; corrections via supersedes + reason: PROVEN (pre/post snapshot row byte-identical; correction creates 2nd row, original intact)
- 0001 untouched; 0002/0003 round-trip: PROVEN
- Retention/backup operator-owned, prod deploy untouched: HELD (module docstring only, no policy code)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Strict-mode contract construction in test fixtures and store re-read**
- **Found during:** Task 3
- **Issue:** `ContractModel` is strict: `model_validate` on plain dicts rejects str→enum/datetime/Decimal coercion, so fixture building and `read_snapshot` failed validation.
- **Fix:** Fixtures use `model_validate_json(json.dumps(...))` (same pattern as `test_persistence_roundtrip.py`); `read_snapshot` re-validates via `model_validate_json`.
- **Files modified:** tests/integration/test_journal_roundtrip.py, src/goldmasters/journal/store.py
- **Commit:** a386971, e0fa358

**2. [Rule 1 - Bug] No-mutation-path test counted imported helpers**
- **Found during:** Task 3
- **Issue:** `inspect.getmembers(module, isfunction)` returns imported functions (e.g. sqlalchemy `text`), so the allow-list assertion could never hold literally.
- **Fix:** Test asserts `__all__` is exactly the four read/write functions and scans store source for `UPDATE ` / `DELETE ` / `DROP ` tokens.
- **Files modified:** tests/integration/test_journal_roundtrip.py
- **Commit:** a386971

**3. [Rule 2 - Missing] 0003 backtest_run needed full-record promotable columns**
- **Found during:** Task 1
- **Issue:** The plan's column list omits `data_quality`, `parameter_hash`, `generated_at`, all required `BacktestRecord` fields — without them the later persistence plan cannot store a complete record.
- **Fix:** Added the three columns (all NOT NULL, matching contract required-ness). No bars stored; hash/ref provenance unchanged.
- **Files modified:** apps/api/migrations/versions/0003_backtest.py
- **Commit:** fc3edb9

**4. [Rule 1 - Bug] mypy strict `no-any-return` on prefixed-id return**
- **Found during:** Task 2 gate
- **Issue:** `return entry.journal_id` returns `Any` (Annotated-id attribute access under strict).
- **Fix:** Bind to a `str`-annotated local first.
- **Files modified:** src/goldmasters/journal/store.py
- **Commit:** e0fa358

## Known Stubs

None. Stub scan over `src/goldmasters/journal/` found no TODO/FIXME/placeholder markers; every writer path is live against the throwaway DB in tests.

## Threat Flags

None beyond the plan's register. Mitigations landed: T-06-01 (Core `text()` with bound params, no concatenated SQL), T-06-02 (no mutation path, token-scanned), T-06-03 (throwaway fixture, fails loudly), T-06-04 (write-time float rejection + stored-JSONB string assertion), T-06-SC (no installs).

## Self-Check: PASSED

- All 6 files exist on disk; 0001 unmodified.
- All 4 commits (`fc3edb9`, `e0fa358`, `a386971`, `ee03d1a`) are ancestors of HEAD.
- Pre-existing `M .planning/ROADMAP.md` and untracked scratch files left untouched (not this plan's scope).
