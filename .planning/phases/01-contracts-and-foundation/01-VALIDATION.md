---
phase: "1"
slug: "contracts-and-foundation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-13"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (plus pytest-cov 7.1.0, time-machine 3.5.1) |
| **Config file** | none — Wave 0 creates `pyproject.toml` `[tool.pytest.ini_options]` and per-package test config |
| **Quick run command** | `uv run pytest -q --no-header -x` |
| **Full suite command** | `scripts/gate` (format check, lint, mypy strict, full pytest, contracts purity test, boundary scan) |
| **Estimated runtime** | not yet measured — record on the first green run (no invented figure) |

---

## Sampling Rate

- **After every task commit:** Fast subset via the tracked hook — `ruff format --check`, `ruff check`, `mypy --strict` over changed files (D-40).
- **After every plan wave:** `scripts/gate` — the full suite (D-38).
- **Before `/gsd-verify-work`:** `scripts/gate` must be green, plus `alembic upgrade head` → `downgrade base` → `upgrade head` against the throwaway database, with the exact commands and their results recorded as evidence for criteria 3 and 5.
- **Max feedback latency:** to be measured; the hook subset is the interactive signal, the full gate is the pre-done signal.

---

## Per-Task Verification Map

Requirement-level seed. Task IDs are assigned by the planner (step 8) and this table is reconciled at `/gsd-validate-phase`.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| — | — | — | REQ-no-trade-execution | — | No forbidden order/broker import or call anywhere; dependency manifest matches the allowlist | unit (static AST scan) | `uv run pytest tests/security/test_boundary_scan.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | REQ-no-trade-execution | — | The scan *fails* on a synthetic forbidden module, proving it has teeth | unit (meta-test) | `uv run pytest tests/security/test_boundary_scan_negative.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 1 | — | Every Schema.md contract validates accepted payloads and rejects mutations | contract (golden suite) | `uv run pytest tests/contract -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 1 | — | Contracts package imports nothing outside the Pydantic+stdlib allowlist | unit (AST) | `uv run pytest packages/contracts/tests/test_import_purity.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 1 | — | Committed JSON Schema matches the regenerated export (no drift) | unit | `uv run pytest packages/contracts/tests/test_schema_export.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 2 | — | Health endpoint answers on loopback and proves the chain (status, version, schema version, config hash, DB reachability) | integration | `uv run pytest tests/integration/test_health.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 2 | — | Non-loopback bind is rejected; loopback bind starts and is reachable | integration (negative + acceptance) | `uv run pytest tests/integration/test_loopback_bind.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 3 | — | Boundary test runs green as part of the recorded gate | unit | (same as REQ-no-trade-execution above) | ❌ W0 | ⬜ pending |
| — | — | — | criterion 4 | — | Missing/invalid config stops startup with a structured error naming the key | unit | `uv run pytest tests/unit/test_settings_startup.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 4 | — | `.env.example` enumerates every required key and holds no secret value | unit (two tests) | `uv run pytest tests/unit/test_env_example.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 4 | — | A log line is JSON, carries the correlation ID, and redacts a known secret | unit | `uv run pytest tests/unit/test_logging_redaction.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 5 | — | Migration applies, rolls back, and re-applies against the throwaway database | integration | `uv run pytest tests/integration/test_migration_roundtrip.py -x` | ❌ W0 | ⬜ pending |
| — | — | — | criterion 5 | — | Accepted fixtures round-trip through PostgreSQL unchanged | integration | `uv run pytest tests/integration/test_persistence_roundtrip.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — `[tool.pytest.ini_options]`, mypy strict config, ruff config (none exists)
- [ ] `tests/conftest.py` — throwaway-database fixture that creates and drops a per-run instance (D-35)
- [ ] `tests/contract/` — golden conformance fixtures for every Schema.md contract (D-06)
- [ ] `tests/security/` — boundary scan plus its negative meta-test (D-37)
- [ ] `packages/contracts/tests/test_import_purity.py` — purity AST test (D-08)
- [ ] `.env.example` and its two tests (D-36)
- [ ] Framework install: `uv sync` (pytest, mypy, time-machine, and the pinned runtime dependencies)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI execution of the boundary test and the check suite | criteria 3 and 5 ("runs in CI") | This machine has no git remote, no `.github/`, and no CI provider; Docker (and therefore `nektos/act`) is absent. The criteria are satisfied *structurally* by a recorded, build-failing local runner that a future remote can adopt unchanged — execution in CI is pending a remote and is NOT claimed as done. | Run `scripts/gate` locally and record the command list and its results as the phase evidence; when a remote exists, add it to `core.hooksPath`-equivalent CI invocation without changing the script. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency measured and recorded
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
