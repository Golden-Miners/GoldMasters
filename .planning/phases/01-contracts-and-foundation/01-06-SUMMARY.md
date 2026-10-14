---
phase: 01-contracts-and-foundation
plan: "06"
subsystem: persistence
tags: [alembic, sqlalchemy, postgresql, jsonb, round-trip, throwaway-db]

# Dependency graph
requires: [01 (workspace), 04 (shared cases), 05 (cluster + stack), 08 (settings)]
provides:
  - "Hand-written `0001_contract_documents` migration (applies + rolls back cleanly)"
  - "Session throwaway-database fixtures deriving from validated Settings"
  - "JSONB round-trip of all 10 accepted conformance payloads (decimals as strings)"
affects: [07 (client reads), Phase 2+ (run persistence)]

actuals:
  tokens: 0
  tasks: 3
  commits: 3
  plan_head_before: b124717
  plan_head_after: TASK3_SHA

key-files:
  created:
    - apps/api/alembic.ini
    - apps/api/migrations/env.py
    - apps/api/migrations/versions/0001_contract_document.py
    - tests/conftest.py
    - tests/integration/test_migration_roundtrip.py
    - tests/integration/test_persistence_roundtrip.py
    - apps/api/src/goldmasters_api/py.typed
  modified:
    - apps/api/pyproject.toml
    - scripts/postgres/init.ps1
    - scripts/postgres/start.ps1
    - tests/unit/test_settings_startup.py

requirements-completed: [REQ-no-trade-execution]

coverage:
  - id: D1
    description: "Migration applies, rolls back to schema-minus-ours, re-applies; URL from Settings, DDL via Core constructs only."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/integration/test_migration_roundtrip.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Throwaway per-run database created/dropped by session fixtures; cluster started idempotently; prerequisites fail loudly."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/conftest.py + migration round-trip"
        status: pass
    human_judgment: false
  - id: D3
    description: "All 10 accepted payloads write/read byte-equal with decimals as strings and promoted columns populated."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/integration/test_persistence_roundtrip.py"
        status: pass
    human_judgment: false

duration: ~45min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 06: Migration + Persistence Round-Trip Summary

**A migration that proves its rollback, a throwaway database per run, and every accepted payload surviving PostgreSQL unchanged.**

## Task Commits

1. **Task 1: Migration + env + alembic dep** - (feat commit)
2. **Task 2: Fixtures + migration round-trip** - (feat commit)
3. **Task 3: Persistence round-trip** - (feat commit, amended with lint follow-ups)

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Deviations from Plan

1. **`init.ps1` now creates the `goldmasters` working database** (idempotent, during init): the cluster shipped with only the `postgres` maintenance DB, so nothing could connect to the working URL. Surfaced here, fixed at the source.
2. **`start.ps1` is idempotent** (exits ok when already running): the fixture starts the cluster on every run.
3. **Error payloads carry no timestamp**: the test omits `created_at` for them so the server default (insertion time) stands as provenance instead of a NULL violating the NOT NULL promotion.
4. **`py.typed` added to `goldmasters-api`**: `mypy --strict` from `tests/` resolves the installed package and needs the marker (contracts already had it).
5. **Local `.env` created (gitignored)** with the working URL built from the cluster password file: the gate is self-sufficient without committing a secret. The missing-key unit test uses a dotenv-free subclass so `.env` cannot mask the absence.
6. **Transient Windows shared-memory fork failures (error 487)** observed once mid-run; a cluster restart cleared it. Recorded here, not hidden.

## Verification Evidence

- `alembic upgrade head → downgrade base → upgrade head` against the working DB: table + 4 indexes appear, vanish (minus Alembic bookkeeping), reappear.
- `sh scripts/gate` → `gate: PASS` (**200 passed**, mypy 47 files clean).
- Working database untouched by tests (throwaway `goldmasters_test_*` created + dropped per run).

## Next Phase Readiness

- Wave 6 (01-07, client skeleton) unblocked — the last plan.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
