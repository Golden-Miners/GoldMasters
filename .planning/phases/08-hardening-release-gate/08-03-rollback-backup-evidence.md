# 08-03 Rollback + Backup/Restore Evidence

Phase: 08-hardening-release-gate
Plan: 03
Date: 2026-10-17
Executor: GSD plan executor (subagent)
Branch: master (config: use_worktrees=false, allow_default_branch_commits=true)
Auto mode: false (_auto_chain_active=false)

## Environment / Precondition

- Repository: C:\XauMaster (git repo, 40+ commits)
- Python: 3.14.7 (system); `.venv` present with uv 0.11.15
- alembic 1.20.0, sqlalchemy 2.1.4, psycopg (v3) installed in `.venv`
- Bundled PostgreSQL 18.6 at `vendor/postgres/pgsql/bin`, data dir `vendor/postgres/data`
- Cluster auth: user `goldmasters`, password from `vendor/postgres/goldmasters.pwfile`, SCRAM-SHA-256
- `GOLDMASTERS_DATABASE_URL` (from `.env`): `postgresql+psycopg://goldmasters:***@127.0.0.1:5432/goldmasters`
- `GOLDMASTERS_MT5_SERVER_TIMEZONE=UTC` required by Settings (fail-closed)

## Task 1 — Migration Rollback (alembic upgrade head → downgrade base → upgrade head)

### Step A: Start cluster

Command: `pwsh -NoProfile -File scripts/postgres/start.ps1`

Observed: `start.ps1` reports "STEP start ok (listening on 127.0.0.1:5432)", but the server process repeatedly terminates abnormally shortly after. `vendor/postgres/server.log` shows:

```
2026-10-17 12:41:41.303 IST client backend (PID 5916) was terminated by exception 0xC0000142
2026-10-17 12:41:41.303 IST terminating any other active server processes
2026-10-17 12:41:41.397 IST all server processes terminated; reinitializing
2026-10-17 12:42:56.705 IST could not reserve shared memory region (addr=...): error code 487
2026-10-17 12:46:13.252 IST autovacuum worker (PID 7360) was terminated by exception 0xC0000142
2026-10-17 12:46:13.297 IST all server processes terminated; reinitializing
2026-10-17 12:47:30.276 IST could not reserve shared memory region (addr=...): error code 487
```

Restart attempts (stop → remove stale postmaster.pid → start): 4+. Each time the server reports "ready to accept connections" then crashes again within seconds with `0xC0000142` / error code 487. psql connections fail: `server closed the connection unexpectedly`.

**Verdict: PostgreSQL cluster is unavailable on this host.** Broken Windows shared-memory / worker-process handling in the bundled PostgreSQL 18.6 binary. Not fixable by code change; no production code changes made.

### Step B: alembic upgrade head

Command (from `apps/api`, with `PYTHONPATH=C:\XauMaster`, `GOLDMASTERS_DATABASE_URL` and `GOLDMASTERS_MT5_SERVER_TIMEZONE=UTC` set):

```
uv run alembic upgrade head
```

Observed output (verbatim, truncated to the terminal error):

```
sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed:
connection to server at "127.0.0.1", port 5432 failed: server closed the connection unexpectedly
	This probably means the server terminated abnormally
	before or while processing the request.
(Background on this error at: https://sqlalchemes.me/e/21/e3q8)
```

Without `PYTHONPATH`, alembic also failed earlier with `ModuleNotFoundError: No module named 'services'` (env.py path issue) — resolved by setting `PYTHONPATH` to the repo root. That is a path/config matter, not a migration defect.

**Verdict: alembic upgrade head could NOT run — no live database connection (cluster down).**

### Step C: Verify tables exist with indexes

Could not execute (no live DB). Expected tables per migration source:
- `contract_document` + indexes `ix_contract_document_run_id`, `ix_contract_document_instrument_id`, `ix_contract_document_created_at`, `ix_contract_document_status`
- `journal_entry` + indexes `ix_journal_entry_decision_id`, `ix_journal_entry_run_id`
- `outcome_observation` + index `ix_outcome_observation_decision_id`
- `backtest_run` + index `ix_backtest_run_strategy_id`
- `dataset_manifest`

These are defined in `apps/api/migrations/versions/0001_contract_document.py`, `0002_journal_outcome.py`, `0003_backtest.py` and asserted by `tests/integration/test_migration_roundtrip.py` (`_TABLES`, `_INDEXES` frozensets).

### Step D: alembic downgrade base

Could not execute (no live DB connection; same failure as Step B).

### Step E: Verify empty schema (zero tables)

Could not execute (no live DB).

### Step F: Re-apply upgrade head (reversibility)

Could not execute (no live DB).

### Step G: Migration 0001 byte-identical before/after

Command: `git diff --quiet apps/api/migrations/versions/0001_contract_document.py`

Observed: exit code 0 → **0001_contract_document.py is byte-identical to HEAD (untouched).** ✅

### Step H: 0002/0003 downgrade() paths drop indexes/tables in exact reverse order

Verified by direct source review (no DB needed):

**0002 upgrade order:** create_table(journal_entry) → create_index(decision_id) → create_index(run_id) → create_table(outcome_observation) → create_index(decision_id)

**0002 downgrade order:** drop_index(outcome_observation.decision_id) → drop_table(outcome_observation) → drop_index(journal_entry.run_id) → drop_index(journal_entry.decision_id) → drop_table(journal_entry) → **exact reverse ✅**

**0003 upgrade order:** create_table(backtest_run) → create_index(strategy_id) → create_table(dataset_manifest)

**0003 downgrade order:** drop_table(dataset_manifest) → drop_index(backtest_run.strategy_id) → drop_table(backtest_run) → **exact reverse ✅**

### Step I: pytest test_migration_roundtrip.py

Command: `uv run pytest tests/integration/test_migration_roundtrip.py -q` (from repo root)

Observed: **ERROR at setup, exit code 1** (test did NOT skip — it failed loudly, per conftest "fail loudly, never skip"):

```
ERROR at setup of test_migration_roundtrip __________________
sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection failed:
connection to server at "127.0.0.1", port 5432 failed: server closed the connection unexpectedly
...
tests\conftest.py:92:  (throwaway_database fixture → _ensure_cluster_running → start.ps1 → engine.connect())
```

The `throwaway_database` fixture calls `_ensure_cluster_running()` which runs `start.ps1`; start.ps1 reports success but the server then crashes, so `CREATE DATABASE`/`engine.connect()` fails with `psycopg.OperationalError`. The test raises (no `pytest.skip`) — conformant with conftest's "Missing prerequisites fail loudly instead of skipping."

**Verdict: test_migration_roundtrip.py FAILED (exit 1) — cluster unavailable, not skipped. This is the designed fail-loud behavior.**

## Task 2 — Backup/Restore Test

Could not execute against a live migrated database (no live DB).

Documented procedure (exact commands, not executed due to cluster unavailability):

**Backup (pg_dump):**
```bash
set GOLDMASTERS_DATABASE_URL=postgresql+psycopg://goldmasters:<pw>@127.0.0.1:5432/goldmasters_test_<suffix>
pg_dump -h 127.0.0.1 -p 5432 -U goldmasters -d goldmasters_test_<suffix> -f backup_<timestamp>.sql
```
Note: `GOLDMASTERS_DATABASE_URL` is URL-encoded (password contains `+`/`/`/`=`); pg_dump CLI does not parse SQLAlchemy URL format. Password must be supplied separately via `PGPASSWORD` env var, and the database name extracted from the URL.

**Simulate loss:** `DROP DATABASE goldmasters_test_<suffix>;` (or `DROP TABLE`/`TRUNCATE` on migrated tables).

**Restore (pg_restore / psql):**
```bash
createdb -h 127.0.0.1 -p 5432 -U goldmasters goldmasters_test_<suffix>
psql -h 127.0.0.1 -p 5432 -U goldmasters -d goldmasters_test_<suffix> -f backup_<timestamp>.sql
```

**Verify match:** compare table names, index names, row counts (`SELECT count(*) FROM <table>` for each of the 5 tables), and sample rows between pre-drop and restored DB.

**Verdict: Backup/restore procedure documented; NOT executed (cluster unavailable). Requires working PostgreSQL authentication and a stable cluster on the operator's deployment host.**

## Threat Register Status (from PLAN.md threat_model)

| Threat ID | Category | Disposition | Status this session |
|-----------|----------|-------------|---------------------|
| T-08-08 | Data Loss (migration without working downgrade) | mitigate | 0001-0003 ship downgrade() paths; downgrade() reverse-order verified by source review. Live upgrade/downgrade execution blocked by cluster. |
| T-08-09 | Tampering (test DB mutates persistent instance) | mitigate | conftest.py throwaway per-run DB fixture; test failed loudly (never skipped, never touched persistent instance). |
| T-08-10 | Data Loss (backup/restore mismatch) | mitigate | Backup/restore procedure documented; could not execute (cluster unavailable). |
| T-08-SC | Tampering (npm/pip/cargo installs) | mitigate | No new packages installed; all dependencies existing and pinned. |

## Deviations from Plan

1. **Cluster unavailable** — `scripts/postgres/start.ps1` starts but the PostgreSQL 18.6 worker processes crash (`0xC0000142`, error code 487 shared memory) on this Windows host. Could not run `alembic upgrade head`, `alembic downgrade base`, or backup/restore against a live DB. Documented per plan's "if PostgreSQL cluster unavailable ... document" clause. **Blocked.**

2. **test_migration_roundtrip.py failed loudly (exit 1)** — not a skip; conformant with conftest "fail loudly, never skip." Root cause: cluster unavailable. **Blocked (environment).**

3. **alembic path config** — running `uv run alembic` from `apps/api` requires `PYTHONPATH=C:\XauMaster` for the `services` module import in `migrations/env.py`; resolved, not a defect.

4. **pg_dump/pg_restore URL-encoded password** — `GOLDMASTERS_DATABASE_URL` password is URL-encoded; pg_dump CLI needs `PGPASSWORD` + plain database name. Documented, not executed.

## What IS Verified (no DB required)

- Migration 0001_contract_document.py byte-identical to HEAD (untouched). ✅
- Migration 0002 downgrade() drops indexes/tables in exact reverse creation order. ✅
- Migration 0003 downgrade() drops indexes/tables in exact reverse creation order. ✅
- Migration source files define all 5 required tables and 6 required indexes (matching test's `_TABLES`/`_INDEXES`). ✅
- conftest.py throwaway per-run DB fixture present and enforces fail-loud (no skip). ✅
- test_migration_roundtrip.py asserts apply → rollback-emptiness → re-apply against throwaway DB. ✅ (correctly written; could not run against live DB)
- No production code changes. ✅
- No new packages installed. ✅

## What Could NOT Be Verified (cluster required)

- `uv run alembic upgrade head` applies 0001-0003 cleanly
- Tables exist with indexes on a live DB
- `uv run alembic downgrade base` leaves empty schema
- Re-apply `upgrade head` restores tables (reversibility against live DB)
- Backup/restore test with restored-state match
- `uv run pytest tests/integration/test_migration_roundtrip.py -q` green (it fails loudly due to cluster)

## Recommendation

Re-run this plan on a host with a working PostgreSQL cluster (the bundled vendor/postgres 18.6 binary is broken on this Windows machine). The migration files, downgrade() paths, byte-identity of 0001, and the throwaway-fixture test design are all verified correct; only live-DB execution is blocked by the environment.
