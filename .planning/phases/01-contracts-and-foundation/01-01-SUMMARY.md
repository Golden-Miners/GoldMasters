---
phase: 01-contracts-and-foundation
plan: "01"
subsystem: contracts
tags: [python, uv, pydantic, contracts, enums, decimal, schema, json-schema]

# Dependency graph
requires: []
provides:
  - "uv workspace root pinned to Python 3.14.7 with `packages/contracts` as its only member"
  - "`goldmasters-contracts` distribution (hatchling, src layout) with pydantic==2.14.1 + tzdata==2026.5"
  - "`ContractModel` shared base (strict=True, extra='forbid', frozen=True) — the single source of contract config"
  - "`PriceStr` decimal-string wire form with an explicit JSON-Schema pattern (exponent/NaN/Infinity/leading-`+` rejected) and `DECIMAL_PATTERN` constant"
  - "shared UTC timestamp + preserved IANA source-timezone annotated type"
  - "closed vocabularies: Decision, AgentRunStatus, EvidenceStatus, Direction, TrendRegime, Timeframe, QualityStatus, QualityFlag, VolumeType"
  - "C-09 error contract: closed `ErrorCode` enum with a per-code `retryable` property and `RETRYABLE_CODES`"
  - "Schema.md §3 `Envelope` agent envelope"
  - "`goldmasters_contracts` package barrel re-exporting the module surfaces plus `CONTRACT_VERSION` ('1.0')"
affects: [02 (gates/config), 03 (identifier + version types), 04 (purity test), 07 (TS client), 08 (apps/api member), 11 (remaining contracts + full schema export)]

actuals:
  tokens: 22270
  tasks: 3
  commits: 3
  plan_head_before: 4cfa7728f727341c58ff1c96bcd3604ebca5be59
  plan_head_after: 01a6a7f

tech-stack:
  added: ["uv 0.11.x workspace", "Python 3.14.7", "pydantic 2.14.1", "tzdata 2026.5", "hatchling"]
  patterns:
    - "One shared `ContractModel` config so strict/extra/frozen cannot diverge between contracts"
    - "Money/price crosses the wire as a fixed-point decimal *string* with an explicit JSON-Schema pattern constant shared by tests and exporter"
    - "Closed enums for every vocabulary; provider-native strings outside the canonical enum are rejected, never rounded or passed through"
    - "`ErrorCode` owns retryability — `retryable` is a property of the code, never caller-supplied"

key-files:
  created:
    - pyproject.toml
    - .gitignore
    - packages/contracts/pyproject.toml
    - uv.lock
    - packages/contracts/src/goldmasters_contracts/__init__.py
    - packages/contracts/src/goldmasters_contracts/_base.py
    - packages/contracts/src/goldmasters_contracts/enums.py
    - packages/contracts/src/goldmasters_contracts/errors.py
    - packages/contracts/src/goldmasters_contracts/envelope.py
    - packages/contracts/tests/test_contract_core.py
  modified: []

key-decisions:
  - "`Timeframe` members transcribed from the provider's documented list (MT5 chart timeframes, cited in the module docstring) — never from memory; `PERIOD_CURRENT` deliberately excluded as it is not a canonical period."
  - "Decimal wire form is our own explicit pattern constant, not Pydantic's default Decimal pattern (Pitfall 4)."
  - "Interpreter pinned exactly to 3.14.7 in the workspace root so every later plan inherits one environment."

patterns-established:
  - "Shared contract base: `ContractModel` is the only place ConfigDict(strict/extra/frozen) is declared."
  - "Single import surface: consumers import from `goldmasters_contracts`, not submodules."
  - "Closed vocabulary + per-code metadata: enum members carry their own semantics (ErrorCode.retryable)."

requirements-completed: [REQ-no-trade-execution]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "uv workspace resolves with `packages/contracts` as its member and the contracts package imports, printing CONTRACT_VERSION."
    requirement: REQ-no-trade-execution
    verification:
      - kind: integration
        ref: "uv sync --all-packages && uv run python -c \"import goldmasters_contracts; print(goldmasters_contracts.CONTRACT_VERSION)\""
        status: pass
    human_judgment: false
  - id: D2
    description: "Shared contract base rejects unknown extra fields and type coercion and is immutable; the decimal-string wire form accepts '2415.37' and rejects exponent/NaN/Infinity/leading-`+`."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_unknown_extra_field_is_rejected"
        status: pass
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_type_coercion_is_rejected"
        status: pass
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_instance_is_immutable"
        status: pass
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_decimal_rejects_non_wire_strings"
        status: pass
    human_judgment: false
  - id: D3
    description: "Closed canonical vocabularies including the provider-sourced `Timeframe`; a provider-native timeframe string outside the enum is rejected, not rounded."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_timeframe_enum_matches_documented_members"
        status: pass
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_provider_native_timeframe_outside_enum_is_rejected"
        status: pass
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_quality_not_evaluated_is_its_own_member"
        status: pass
    human_judgment: false
  - id: D4
    description: "C-09 error contract: closed `ErrorCode` vocabulary with a per-code `retryable` that comes from the code, not the caller."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_error_code_pins_the_settled_vocabulary"
        status: pass
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_retryable_comes_from_the_code_not_the_caller"
        status: pass
    human_judgment: false
  - id: D5
    description: "Schema.md §3 `Envelope` accepts the documented document and rejects an unknown extra field."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_envelope_accepts_the_documented_document"
        status: pass
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_envelope_rejects_an_unknown_extra_field"
        status: pass
    human_judgment: false
  - id: D6
    description: "Package barrel is the single import surface: base, enums, error payload and envelope re-exported from `goldmasters_contracts`."
    requirement: REQ-no-trade-execution
    verification:
      - kind: unit
        ref: "packages/contracts/tests/test_contract_core.py#test_barrel_reexports_every_module_surface"
        status: pass
    human_judgment: false

duration: ~18min
completed: 2026-10-14
status: complete
---

# Phase 1 Plan 01: Contracts and Foundation — Workspace, Shared Base, Vocabularies, Errors, Envelope Summary

**uv-workspace + `goldmasters-contracts` distribution carrying the strict/frozen contract base, the decimal-string wire form, the closed canonical vocabularies (incl. provider-sourced `Timeframe`), the C-09 per-code-retryable error contract and the Schema.md §3 envelope — all importable through one package barrel.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-10-14T06:56:24Z (phase execution start)
- **Completed:** 2026-10-14
- **Tasks:** 3
- **Files modified:** 10 created (0 modified)

## Accomplishments
- Stood up the uv workspace (`pyproject.toml`, interpreter pinned to 3.14.7, single member `packages/contracts`, virtual root) and the hatchling `goldmasters-contracts` distribution with an audited dependency set (`pydantic==2.14.1`, `tzdata==2026.5`).
- Defined the shared contract spine: one `ContractModel` base (`strict=True, extra="forbid", frozen=True`), the `PriceStr` decimal-string wire form with an explicit JSON-Schema pattern constant, and the reusable UTC + preserved-IANA-timezone timestamp type.
- Transcribed every closed vocabulary (Decision, AgentRunStatus, EvidenceStatus, Direction, TrendRegime, Timeframe, QualityStatus/QualityFlag, VolumeType), with `Timeframe` sourced from the provider's documented list rather than memory.
- Implemented the C-09 error contract — a closed `ErrorCode` enum whose `retryable` is a property of the code (settling the C-09 gray area recorded in 01-RESEARCH.md) plus `RETRYABLE_CODES`.
- Reproduced the Schema.md §3 `Envelope` and made `__init__.py` the single import surface with `CONTRACT_VERSION`.
- 29 tests green covering all six task-2 behaviours and five task-3 behaviours; ruff, ruff format and mypy --strict clean over the package.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end workspace → contracts distribution → importable package** - `1dbd071` (feat)
2. **Task 2: Shared contract base, decimal wire form and the closed vocabularies** - `ba56993` (feat)
3. **Task 3: C-09 error contract, the agent envelope and the package barrel** - `01a6a7f` (feat)

**Plan metadata:** _pending_ (docs: complete plan — this SUMMARY's own commit)

_Note: the plan listed `type="auto" tdd="true"` for tasks 2 and 3; the RED/GREEN commits were folded into the single per-task feat commits (production code and its tests landed together), matching the surrounding repo convention for this resumed run._

## Files Created/Modified
- `pyproject.toml` - uv workspace root (virtual, `package=false`, member `packages/contracts`, interpreter pinned 3.14.7)
- `.gitignore` - repo hygiene: `vendor/`, `.venv/`, `node_modules/`, `apps/web/src/generated/`, `logs/`, `.env`, `__pycache__/`, Postgres password/lock files
- `packages/contracts/pyproject.toml` - hatchling distribution `goldmasters-contracts`, src layout, pydantic + tzdata
- `uv.lock` - resolved lockfile for the workspace
- `packages/contracts/src/goldmasters_contracts/_base.py` - `ContractModel`, `PriceStr`, `DECIMAL_PATTERN`, UTC + IANA timestamp type
- `packages/contracts/src/goldmasters_contracts/enums.py` - all closed vocabularies incl. `Timeframe` (cited provider source)
- `packages/contracts/src/goldmasters_contracts/errors.py` - `ErrorCode`, `ErrorPayload`, `RETRYABLE_CODES`
- `packages/contracts/src/goldmasters_contracts/envelope.py` - `Envelope` (Schema.md §3)
- `packages/contracts/src/goldmasters_contracts/__init__.py` - package barrel + `CONTRACT_VERSION`
- `packages/contracts/tests/test_contract_core.py` - 29 tests across the three tasks

## Decisions Made
- **`Timeframe` provenance:** members transcribed from the provider's documented timeframe list (MT5 chart timeframes — the V1 provider), cited in the `enums.py` docstring; `PERIOD_CURRENT` excluded because it is not a canonical period. No member was invented.
- **Decimal wire form is ours, not Pydantic's default:** an explicit `DECIMAL_PATTERN` module constant is the single source referenced by the models, the tests and (later) the exporter.
- **`uv` member list is literals, not a glob:** only `packages/contracts`; plan 08 adds `apps/api` to the same file when it creates that distribution (a missing literal member path is a uv error).

## Deviations from Plan

### Resumed run (no re-execution)

This plan had already been fully implemented and committed by a prior executor; only the SUMMARY was outstanding. Per continuation handling, the three completed tasks were verified (commits, contents, and the full verification suite re-run) rather than redone. No production code was changed in this pass.

### Auto-fixed Issues

None. The plan executed as written.

### Deferred Issues (out of scope)

- `ruff format --check` reports two pre-existing `.planning/**` Markdown files that contain Python code blocks: `.planning/phases/01-contracts-and-foundation/01-PATTERNS.md:150:32` and `.planning/phases/01-contracts-and-foundation/01-RESEARCH.md:362:22`. These are not part of this plan's changed files and were left untouched per the scope boundary.

---

**Total deviations:** 0 auto-fixed.
**Impact on plan:** None. Verification suite re-run green; no scope creep.

## Issues Encountered
- The plan-execution ledger file (`git rev-parse --git-dir`/`gsd-plan-head-before-01-01`) was absent because the prior executor did not create it. Measured `commits` directly with `git rev-list --count 4cfa772..HEAD` (= 3) and wrote the ledger so `/gsd-verify-work` can use the same instrument.

## User Setup Required

None - no external service configuration required. (`uv` 0.11.15 and Python 3.14.7 were already present; `uv sync --all-packages` ran clean.)

## Threat Surface Scan

No new security-relevant surface beyond the plan's `<threat_model>`. The mitigations for T-01-03 (strict/forbid/frozen + closed enums), T-01-05 (explicit decimal pattern), T-01-25 (closed provider-sourced vocabularies), T-01-26 (`retryable` owned by `ErrorCode`) and T-01-27 (exact interpreter pin, explicit member list, audited dependency set) are implemented. T-01-SC (install legitimacy) covered by the RESEARCH.md package-legitimacy audit and exact lockfile pins.

## Verification Evidence

- `uv sync --all-packages` — OK.
- `uv run python -c "import goldmasters_contracts; print(goldmasters_contracts.CONTRACT_VERSION)"` → `1.0`.
- `uv run pytest packages/contracts/tests/test_contract_core.py -q` → **29 passed**.
- `uv run ruff check .` → **All checks passed**.
- `uv run ruff format --check packages/contracts pyproject.toml` → **6 files already formatted**.
- `uv run mypy --strict packages/contracts/src` → **Success: no issues found in 5 source files**.

## Next Phase Readiness
- The contract spine is in place and importable; plans 02 (gates/config), 03 (identifier + version types), 04 (purity allowlist test), 07 (TS client), 08 (`apps/api` member) and 11 (remaining contracts + full schema export) all consume this package.
- Open FLAGGED ASSUMPTIONS from the plan remain unresolved by design (boundary thresholds, rounding contract, concurrency/interruption semantics) — recorded, not invented.
- No blockers.

---
*Phase: 01-contracts-and-foundation*
*Completed: 2026-10-14*
