---
phase: 01-contracts-and-foundation
plan: "10"
subsystem: config
tags: [python, pydantic-settings, yaml, config-hash, secrets, startup-validation]

# Dependency graph
requires: [08 (initial Settings + hash + lifespan wiring)]
provides:
  - "Extended `Settings`: full declared key set, required `database_url`, `trace_file_path`/`log_level` interface for plan 09, `provider_api_key` secret, undeclared-variable guard, YAML document source last"
  - "`hash_effective_config` hardened: type-derived secret exclusion + `HASH_ALGORITHM_VERSION`"
  - "`config/goldmasters.yaml` (non-secret defaults only) and `.env.example` (full key coverage, secrets empty)"
affects: [09 (reads trace_file_path/log_level), every later phase (hash identifies producing configuration)]

actuals:
  tokens: 0
  tasks: 3
  commits: 3
  plan_head_before: 95428e5
  plan_head_after: 6d15f4d

key-files:
  created:
    - tests/unit/test_settings_startup.py
    - tests/unit/test_env_example.py
    - config/goldmasters.yaml
    - .env.example
    - packages/contracts/src/goldmasters_contracts/py.typed
  modified:
    - apps/api/src/goldmasters_api/settings.py
    - apps/api/src/goldmasters_api/app.py
    - tests/integration/test_health.py

requirements-completed: [REQ-no-trade-execution]

coverage:
  - id: D1
    description: "Missing/invalid key stops startup naming the key; unknown GOLDMASTERS_ variable rejected; secret hidden from repr/dump; YAML source live and last."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "tests/unit/test_settings_startup.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Config hash deterministic, order-invariant, secret-independent, moves with non-secrets, versioned."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "tests/unit/test_settings_startup.py#test_hash_ignores_secrets"
        status: pass
    human_judgment: false
  - id: D3
    description: ".env.example covers every declared key with secrets empty; document parses, holds only non-secret defaults, supplies values under env override, stays a model subset."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "tests/unit/test_env_example.py"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 10: Configuration Surface Summary

**Explicit settings keys with fail-loud startup, a type-derived secret-excluding versioned config hash, and the versioned YAML document plus secret-free env template.**

## Task Commits

1. **Task 1: Explicit keys, fail-loud startup, YAML source** - `997096e`
2. **Task 2: Deterministic secret-excluding hash + version** - `75ad900`
3. **Task 3: Config document, env template, proofs** - `6d15f4d`

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

## Deviations from Plan

1. **`extra="forbid"` does not reject unknown env vars** (verified on pydantic-settings 2.15.0): added `_reject_undeclared_prefixed_variables`, a `mode="before"` validator naming the offender. The plan's truth holds; the mechanism differs.
2. **`secret` renamed to `provider_api_key`** per the plan's declared key set; nothing consumed the old name.
3. **`database_url` became required** (no default): integration tests now set it via an autouse fixture pointing at an unreachable localhost DB.
4. **`py.typed` marker added** to the contracts package so `mypy --strict apps/api/src` alone resolves its types (PEP 561).

## Verification Evidence

- `uv run pytest tests/unit tests/integration/test_health.py packages/contracts/tests -q` → **103 passed**.
- `uv run mypy --strict apps/api/src packages/contracts/src` → clean, 15 files; `apps/api/src` alone → clean.
- `/health` still green with the hardened hash (`config_hash` now versioned).

## Next Phase Readiness

- Plan 09 reads `trace_file_path`/`log_level` — names pinned.
- No blockers.

---

*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
