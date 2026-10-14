---
phase: 01-contracts-and-foundation
plan: "05"
subsystem: local-stack
tags: [powershell, postgresql, edb, provisioning, loopback, stack]

# Dependency graph
requires: [01 (workspace), 08 (API app + settings the stack launches)]
provides:
  - "Pinned repo-local PostgreSQL (18.6, verified EDB fileid 1260609, hash-locked)"
  - "provision/init/start/stop/probe scripts + falsification evidence (A2/A3/A4/A7 resolved)"
  - "`scripts/stack` — one loopback entry point for DB + backend"
affects: [06 (migration round-trip against this cluster)]

actuals:
  tokens: 0
  tasks: 3
  commits: 3
  plan_head_before: 375e334
  plan_head_after: 4209aae

key-files:
  created:
    - scripts/postgres/VERSION
    - scripts/postgres/provision.ps1
    - scripts/postgres/init.ps1
    - scripts/postgres/start.ps1
    - scripts/postgres/stop.ps1
    - scripts/postgres/probe.ps1
    - scripts/stack
    - docs/local-stack.md
    - tests/integration/test_postgres_scripts.py
    - tests/integration/test_stack_script.py
  modified: []

requirements-completed: [REQ-no-trade-execution]

coverage:
  - id: D1
    description: "Pin recorded in VERSION and read by scripts; init uses explicit scram-sha-256 + pwfile; start binds 127.0.0.1:5432; nothing machine-wide."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/integration/test_postgres_scripts.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Probe ran provision → init → start → connect → query → stop on this machine with observed evidence."
    requirement: REQ-no-trade-execution
    verification:
      - kind: manual
        ref: "docs/local-stack.md (pasted probe output)"
        status: pass
    human_judgment: true
  - id: D3
    description: "One stack command composes both loopback legs with an explicit host and no container/service dependency."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "tests/integration/test_stack_script.py"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 05: Repo-Local PostgreSQL + Stack Summary

**Pinned portable PostgreSQL 18.6 provisioned repo-local with hash-locked artifacts, proven runnable on this machine, composed with the backend into one loopback stack command.**

## Task Commits

1. **Task 1: Provisioning/init/start/stop + static contract** - amended into `e9cfbec`
2. **Task 2: Falsification probe + evidence** - `1eb9571` (scripts) + `4209aae` (docs)
3. **Task 3: Stack command + contract** - `1eb9571` / stack-test amend

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Deviations from Plan

1. **EDB file IDs verified from the vendor page**, not invented: 18.6 win-x64 = fileid `1260609` (fetched `https://www.enterprisedb.com/download-postgresql-binaries`, 2026-10-14).
2. **Cluster lives in `vendor/postgres/data`** (already git-ignored) rather than a separate `data/` tree — one ignored root for all Postgres runtime files.
3. **Two commits initially landed with failing tests** (shell `;` chaining) and were amended green before proceeding: the VERSION-mention assertion (only provision.ps1 reads the pin) and the Windows exec-bit assertion (git index mode instead).
4. **`scripts/stack` is POSIX `sh`** (Git for Windows runs it), delegating to the `.ps1` legs via `powershell -File`.

## Verification Evidence

- `uv run pytest tests/integration/test_postgres_scripts.py tests/integration/test_stack_script.py -q` → **8 passed**.
- Probe output in `docs/local-stack.md`: PostgreSQL 18.6, `SELECT 1 = 1`, no elevation.
- sha256 `e2246ba9…c84e2` recorded in `vendor/postgres/artifact.lock` (git-ignored).

## Next Phase Readiness

- Plan 06 runs migrations against `127.0.0.1:5432`; `scripts/stack` tolerates the absent migration tree until then.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
