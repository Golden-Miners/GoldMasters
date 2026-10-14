---
phase: 01-contracts-and-foundation
plan: "02"
subsystem: quality-gate
tags: [ast-scan, allowlist, gate, pre-commit, ruff, mypy, pytest]

# Dependency graph
requires: [01 (workspace), 08 (testpaths target tests/integration)]
provides:
  - "Build-failing boundary scan + dependency allowlist + negative meta-test"
  - "`scripts/gate` (full + --fast), `.githooks/pre-commit`, tool config, `docs/quality-gate.md`"
  - "Ten root documents tracked (D-44)"
affects: [04 (purity test runs inside the gate), every later plan (one meaning of green)]

actuals:
  tokens: 0
  tasks: 3
  commits: 3
  plan_head_before: b0b02c8
  plan_head_after: abfc18a

key-files:
  created:
    - tests/security/_boundary.py
    - tests/security/test_boundary_scan.py
    - tests/security/test_boundary_scan_negative.py
    - scripts/gate
    - .githooks/pre-commit
    - docs/quality-gate.md
  modified:
    - pyproject.toml

requirements-completed: [REQ-no-trade-execution]

coverage:
  - id: D1
    description: "Source tree holds no forbidden broker/order call or import; every declared dependency is allowlisted and none is order-capable."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "tests/security/test_boundary_scan.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Meta-tests prove the scan catches drawn-from-set names and imports without touching disk."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "tests/security/test_boundary_scan_negative.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full gate and --fast subset exit zero; hook executable and wired by documented command; CI pending stated honestly; root docs tracked; no .github invented."
    requirement: REQ-no-trade-execution
    verification:
      - kind: manual
        ref: "docs/quality-gate.md (pasted gate output)"
        status: pass
    human_judgment: true

duration: ~30min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 02: Boundary Scan + Gate Summary

**The signals-only boundary as a build-failing test with an adversarial proof, and one ordered gate command with a tracked fast hook.**

## Task Commits

1. **Task 1: Scan + allowlist** - `6065480`
2. **Task 2: Negative meta-test** - `55f16a8`
3. **Task 3: Gate, hook, config, root docs** - `abfc18a`

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Deviations from Plan

1. **Test imports load `_boundary.py` by file path** (importlib) instead of `tests.security` package imports — `tests/__init__.py` is plan 04's file; this plan does not pre-create it.
2. **`ruff format --check .` needed `[tool.ruff.format] exclude = [".planning/**"]`** — the formatter rewrites Python blocks inside planning docs; docs are not code and stay out of the gate.
3. **`mypy --strict .` needed `exclude = ["vendor/", ".venv/", "apps/web/"]`** plus a `yaml.*` stub override — the provisioned Postgres tree ships its own vendored Python (pgAdmin) that is not this project's code.
4. **One-time format normalization** of previously-committed files rides in the Task 3 commit (mechanical, `ruff format` only) so the gate is green from this point on.
5. **PATTERNS.md's `.github/workflows/ci.yml` sketch not followed** — the plan addendum forbids inventing the workflow; `docs/quality-gate.md` records the honest pending state instead.

## Verification Evidence

- `sh scripts/gate` → `gate: PASS` (format 240 clean, lint clean, mypy 31 files clean, **124 passed**).
- `sh scripts/gate --fast` → `gate --fast: PASS`.
- `git ls-files` lists the ten root documents; no `.github/` exists.

## Next Phase Readiness

- Wave 4 (01-04, 01-09) unblocked.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
