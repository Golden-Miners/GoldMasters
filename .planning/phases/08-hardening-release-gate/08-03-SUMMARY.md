---
phase: 08-hardening-release-gate
plan: 03
subsystem: migration-rollback-backup-restore
tags: [migration, rollback, backup, restore, alembic]
requires: [08-02-failure-injection]
provides: [rollback-backup-evidence, migration-reversibility-source-review]
affects: []
tech_stack:
  added: []
  patterns: [alembic-upgrade-downgrade, pg_dump-pg-restore, throwaway-per-run-db]
key_files:
  created:
    - .planning/phases/08-hardening-release-gate/08-03-rollback-backup-evidence.md
  modified: []
    # No production code changes. Migration files 0001-0003 reviewed, not modified.
decisions:
  - "Migration rollback verified by source review (0001 byte-identical; 0002/0003 downgrade() drops indexes/tables in exact reverse creation order). Live-DB execution blocked by unavailable PostgreSQL cluster."
  - "Backup/restore procedure documented with exact pg_dump/pg_restore commands; not executed (cluster unavailable)."
  - "tests/conftest.py throwaway per-run DB fixture enforces fail-loud (no skip); test_migration_roundtrip.py correctly asserts apply -> rollback-emptiness -> re-apply."
  - "No production code changes; no new packages installed; no invented thresholds."
metrics:
  duration: ~60 min
  completed: 2026-10-17
  commits: 0
  tests: test_migration_roundtrip FAILED (exit 1, ERROR at setup — cluster connection refused; fail-loud, not skipped)
plan_head_before: b610dcb13c6fc92da6119f4db4c3676ca35a2397
plan_head_after: (working tree; committed on master)
status: complete
actuals:
  tokens: ~22000
  tasks: 2
  commits: 0
---

# Phase 08 Plan 03: Migration Rollback + Backup/Restore (Wave 2) Summary

## One-liner

Migration files 0001-0003 verified correct (0001 byte-identical; 0002/0003 downgrade() paths drop indexes/tables in exact reverse order); live alembic upgrade/downgrade and backup/restore could not execute because the bundled PostgreSQL 18.6 cluster crashes on this Windows host (0xC0000142 / error 487 shared memory) — documented as an environment blocker, test fails loud (not skipped).

## Tasks Completed

| # | Name | Files | Status |
|---|------|-------|--------|
| 1 | Migration rollback — source review + attempted alembic upgrade/downgrade | migrations 0001-0003, tests/integration/test_migration_roundtrip.py, tests/conftest.py, 08-03-rollback-backup-evidence.md | Partially (source verified; live-DB blocked) |
| 2 | Backup/restore test — procedure documented | tests/conftest.py, 08-03-rollback-backup-evidence.md | Documented only (cluster unavailable) |

## Evidence

**Task 1 — Migration Rollback:**

- `git diff --quiet apps/api/migrations/versions/0001_contract_document.py` → exit 0 → **0001 byte-identical to HEAD (untouched)** ✅
- **0002 downgrade() reverse-order verified by source review:** upgrade creates `journal_entry` → `ix_journal_entry_decision_id` → `ix_journal_entry_run_id` → `outcome_observation` → `ix_outcome_observation_decision_id`; downgrade drops `ix_outcome_observation_decision_id` → `outcome_observation` → `ix_journal_entry_run_id` → `ix_journal_entry_decision_id` → `journal_entry` (exact reverse) ✅
- **0003 downgrade() reverse-order verified by source review:** upgrade creates `backtest_run` → `ix_backtest_run_strategy_id` → `dataset_manifest`; downgrade drops `dataset_manifest` → `ix_backtest_run_strategy_id` → `backtest_run` (exact reverse) ✅
- All 5 required tables (`contract_document`, `journal_entry`, `outcome_observation`, `backtest_run`, `dataset_manifest`) and 6+ required indexes defined in migration source, matching `tests/integration/test_migration_roundtrip.py` `_TABLES`/`_INDEXES` ✅
- `uv run alembic upgrade head` → **FAILED**: `sqlalchemy.exc.OperationalError: connection to server at "127.0.0.1", port 5432 failed: server closed the connection unexpectedly` (cluster down). Could not apply migrations.
- `uv run alembic downgrade base` → could not run (no live DB connection).
- `uv run pytest tests/integration/test_migration_roundtrip.py -q` → **FAILED (exit 1, ERROR at setup)** — `throwaway_database` fixture → `_ensure_cluster_running()` → `start.ps1` reports success but server crashes → connection refused. **Fail-loud, not skipped** (conftest: "Missing prerequisites fail loudly instead of skipping"). ✅ conformant

**Cluster diagnosis (4+ restart attempts):** `vendor/postgres/server.log` shows repeated `0xC0000142` worker-process terminations and `could not reserve shared memory region ... error code 487`. Bundled PostgreSQL 18.6 binary is broken on this Windows machine. Not fixable by code change.

**Task 2 — Backup/Restore:**
- Could not execute against a live migrated database (no live DB).
- Backup/restore procedure documented with exact commands in `08-03-rollback-backup-evidence.md`:
  - `pg_dump -h 127.0.0.1 -p 5432 -U goldmasters -d <db> -f backup.sql` (with `PGPASSWORD`; URL-encoded `GOLDMASTERS_DATABASE_URL` password not parsed by pg_dump CLI)
  - `createdb` / `psql -f backup.sql` for restore
  - Verify match: table names, index names, `SELECT count(*)` per table, sample rows
- Requires working PostgreSQL authentication and a stable cluster on the operator's deployment host.

## Must-Have Truths — Status

| Truth | Status |
|-------|--------|
| uv run alembic upgrade head applies 0001-0003 cleanly | BLOCKED (cluster unavailable) |
| Tables exist with indexes (live DB) | BLOCKED (cluster unavailable) |
| uv run alembic downgrade base leaves empty schema | BLOCKED (cluster unavailable) |
| Re-apply upgrade head restores tables (reversibility) | BLOCKED (cluster unavailable) |
| Migration 0001 byte-identical before/after | PASS (git diff --quiet = 0) |
| 0002/0003 downgrade paths correct (reverse order) | PASS (source review) |
| Backup/restore verified working | BLOCKED (cluster unavailable; procedure documented) |
| Test never mutates persistent instance (throwaway fixture) | PASS (conftest enforced; fail-loud) |

## Deviations from Plan

1. **PostgreSQL cluster unavailable on this host.** `scripts/postgres/start.ps1` starts the server but worker processes crash (`0xC0000142`, error code 487 shared memory) within seconds. Could not run `alembic upgrade head`, `alembic downgrade base`, or backup/restore against a live DB. Documented per the plan's "if PostgreSQL cluster unavailable ... document" clause. **Environment blocker.**
2. **test_migration_roundtrip.py failed loudly (exit 1)** — not a skip; conformant with conftest's "fail loudly, never skip." Root cause: cluster unavailable. **Environment blocker.**
3. **alembic path config** — `uv run alembic` from `apps/api` requires `PYTHONPATH=C:\XauMaster` for the `services` module imported by `migrations/env.py`. Resolved; not a defect.
4. **pg_dump/pg_restore URL-encoded password** — `GOLDMASTERS_DATABASE_URL` password is URL-encoded; pg_dump CLI needs `PGPASSWORD` + plain database name. Documented; not executed.

## Known Stubs

None.

## Threat Flags

None beyond the plan's `<threat_model>` (T-08-08, T-08-09, T-08-10, T-08-SC all have mitigations; T-08-08/T-08-10 execution blocked by cluster but mitigations exist by design).

## Self-Check

- Evidence file created: `.planning/phases/08-hardening-release-gate/08-03-rollback-backup-evidence.md` ✅
- 0001 byte-identical confirmed ✅
- 0002/0003 downgrade reverse-order confirmed ✅
- No production code changes ✅
- No new packages installed ✅
- Live-DB rollback/backup/restore: environment-blocked (documented) ✅

## Risk

Re-run this plan on a host with a working PostgreSQL cluster. The migration files, downgrade() paths, byte-identity of 0001, and the throwaway-fixture test design are all verified correct; only live-DB execution is blocked by this environment's broken PostgreSQL 18.6 binary.
