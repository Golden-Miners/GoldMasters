---
phase: 03-deterministic-analysis-strategy-rules-and-risk-gates
plan: '01'
subsystem: domain
tags: [decimal, tick-quantization, dst, utc-adjacency, contracts, pydantic, settings, goldmasters]

# Dependency graph
requires:
  - phase: 02-market-data-and-provider-selection
    provides: validated H1 MarketBars, PrecisionTable with tick context, GOLDMASTERS_ fail-closed settings precedent
provides:
  - src/goldmasters/domain/conventions.py (quantize_to_tick ROUND_HALF_UP, UTC adjacency, fold clause, MALFORMED order check)
  - PrecisionRow.contract_size optional decimal-string column (CONTRACT_VERSION 1.2, schemas regenerated zero-drift)
  - Phase 3 GOLDMASTERS_ policy keys (tick_rounding_mode acknowledgement + risk-limit placeholders, hash-covered)
affects: [03-structure-regime, 03-strategies, 03-levels-gate, 04-langgraph-nodes]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 5989
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns: [pure-functions-explicit-args, utc-instant-adjacency, fail-closed-settings-validators]

key-files:
  created: [src/goldmasters/domain/conventions.py, tests/unit/test_conventions.py]
  modified: [packages/contracts/src/goldmasters_contracts/precision.py, services/mt5_adapter/adapter.py, apps/api/src/goldmasters_api/settings.py, config/goldmasters.yaml]

key-decisions:
  - "ROUND_HALF_UP is the single locked quantization mode (D-3.2); no per-call override parameter"
  - "UTC instants are canonical for adjacency; server-local fold arg covers only the ambiguous hour (D-3.5)"
  - "Misordered analysis input returns MALFORMED and is never sorted (D-3.5)"
  - "contract_size is optional decimal-string, None = unknown provenance; minor bump to 1.2 (D-3.4)"
  - "Risk limits ship as None-defaulted operator-confirmed placeholders; no threshold literal in code (D-3.1)"

patterns-established:
  - "Domain purity: Decimal-only price path, explicit args, no wall-clock/config-globals/mutation (validation.py precedent)"
  - "Settings acknowledgement: locked policy arrives as a validated GOLDMASTERS_ key that only accepts the locked value"

requirements-completed: [REQ-specialist-agent-responsibilities]

# Coverage metadata (#1602) — one entry per shipped deliverable. Drives DETERMINISTIC UAT routing in verify-work.
coverage:
  - id: D1
    description: "quantize_to_tick pins exact-half-tick to ROUND_HALF_UP with boundary tests"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_conventions.py#test_boundary_exact_half_tick_rounds_up"
        status: pass
      - kind: unit
        ref: "tests/unit/test_conventions.py#test_boundary_one_ulp_below_half_does_not_round_up"
        status: pass
    human_judgment: false
  - id: D2
    description: "UTC-instant adjacency with server-local fold clause; both DST weekends covered"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_conventions.py#test_boundary_spring_forward_skipped_hour_adjacent_in_utc"
        status: pass
      - kind: unit
        ref: "tests/unit/test_conventions.py#test_boundary_fall_back_repeated_hour_needs_fold_clause"
        status: pass
    human_judgment: false
  - id: D3
    description: "Misordered analysis input rejected as MALFORMED, order preserved, never sorted"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_conventions.py#test_boundary_misorder_evidence_and_no_silent_sort"
        status: pass
    human_judgment: false
  - id: D4
    description: "PrecisionRow.contract_size persists end-to-end (None when provider omits); schemas zero-drift at 1.2"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_precision_population.py#test_contract_size_persists_from_descriptor"
        status: pass
      - kind: unit
        ref: "packages/contracts/tests/test_schema_export.py#test_committed_schema_matches_regenerated"
        status: pass
    human_judgment: false
  - id: D5
    description: "Phase 3 policy via GOLDMASTERS_ keys with fail-closed validation, all hash-covered"
    requirement: "REQ-specialist-agent-responsibilities"
    verification:
      - kind: unit
        ref: "tests/unit/test_settings_startup.py#test_phase3_policy_keys_fail_closed"
        status: pass
      - kind: unit
        ref: "tests/unit/test_settings_startup.py#test_hash_covers_phase3_policy_keys"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-10-15
status: complete
plan_head_before: edc687b6d5b1e9d4c2b3e62d09e0a2e53c8b0e5
plan_head_after: a07cc0e
---

# Phase 3 Plan 01: Deterministic Conventions Tracer Summary

**Closed-bar conventions tracer: ROUND_HALF_UP tick quantization, UTC-instant adjacency with DST fold clause, MALFORMED-on-misorder, contract-size provenance column, and the GOLDMASTERS_ surface all Phase 3 policy rides on**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-10-15T14:38:00Z (approx, session start)
- **Completed:** 2026-10-15T14:58:17Z
- **Tasks:** 3/3
- **Files modified:** 14 (5 created, 9 modified)

## Accomplishments

- `src/goldmasters/domain/conventions.py`: pure `quantize_to_tick` (locked `ROUND_HALF_UP`, D-3.2), `utc_adjacent` on UTC instants, `server_wall_to_utc` with explicit `fold` for the ambiguous hour, `check_bar_order` returning `MALFORMED` never sorted (D-3.5), plus `quantize_for_instrument` wiring `PrecisionTable.lookup` with unknown-means-skip
- Boundary suite (11 tests): exact-half-tick pins HALF_UP / one-ulp-below does not, spring-forward skipped hour adjacent in UTC, fall-back fold chain adjacent, MALFORMED-with-evidence + `sorted(`-absent negative assertion, fail-closed guards, repeat-run determinism
- `PrecisionRow.contract_size: str | None` (None = unknown provenance), `CONTRACT_VERSION` 1.1 → 1.2 minor bump per D-23, `precision.json` regenerated with zero drift elsewhere (D-3.4); `trade_contract_size` persists from the MT5 descriptor, omitted stays None, garbage fails malformed
- Settings: `tick_rounding_mode` acknowledgement (only `ROUND_HALF_UP` accepted), `max_risk_percent_per_idea` / `min_risk_reward_ratio` None-defaulted placeholders with finite-positive-when-set validation; all hash-covered, `.env.example` parity kept, zero threshold literals in code (D-3.1)

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end closed-bar conventions** - `2e8f040` (feat)
2. **Task 2: Boundary tests** - `66dc0ae` (test)
3. **Task 3: Contract-size column + GOLDMASTERS_ settings** - `a07cc0e` (feat)

**Plan metadata:** docs commit follows (STATE/ROADMAP/SUMMARY)

## Files Created/Modified

- `src/__init__.py`, `src/goldmasters/__init__.py`, `src/goldmasters/domain/__init__.py` - new deterministic tree (Architecture §7)
- `src/goldmasters/domain/conventions.py` - tick quantization, UTC adjacency, fold clause, order check
- `tests/unit/test_conventions.py` - tracer (4) + boundary (7) tests
- `packages/contracts/src/goldmasters_contracts/precision.py` - optional `contract_size` column
- `packages/contracts/src/goldmasters_contracts/__init__.py` - `CONTRACT_VERSION = "1.2"`
- `packages/contracts/schema/precision.json` - regenerated (only file changed: zero drift)
- `services/mt5_adapter/adapter.py` - persist `trade_contract_size` as decimal string via spec path
- `apps/api/src/goldmasters_api/settings.py` - 3 Phase 3 policy keys + fail-closed validators
- `config/goldmasters.yaml` - `tick_rounding_mode` default (risk placeholders stay env-only by design)
- `.env.example` - 3 new key names (parity test requires exact set equality)
- `tests/unit/test_precision_population.py` - 3 contract-size tests + closed open-item note
- `tests/unit/test_settings_startup.py` - declared-set, hash-moves, fail-closed, hash-coverage updates

## Decisions Made

- Locked D-3.1…D-3.5 from 03-CONTEXT.md were implemented as written, never re-decided
- `quantize_to_tick` takes no rounding parameter: the mode is locked (D-3.2), so a parameter would imply a choice the operator already closed; the `Settings.tick_rounding_mode` acknowledgement is the operator-visible record
- Risk placeholders default `None` and are absent from `goldmasters.yaml`: `None` means "no approved strategy yet" (D-3.1 non-goal); an empty `.env.example` entry reads as unset via a `mode="before"` normalizer, never as zero
- `check_bar_order` flags `<` (not `<=`): mirrors the `validation.py:103-105` misorder precedent exactly; duplicates stay validation's concern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `uv run` hangs on sync; used `.venv` binaries directly**
- **Found during:** Task 1 (first test run)
- **Issue:** `uv run pytest` exceeded 120s with no output (resolver/sync stall, no network); the pinned `.venv` already holds every dependency
- **Fix:** Ran all checks via `.venv/Scripts/python.exe -m pytest/ruff/mypy` — same interpreter, same pinned packages
- **Files modified:** none (toolchain only)
- **Verification:** full suite `322 passed, 2 skipped` (pre-existing live_mt5 skips)
- **Committed in:** n/a (no code change)

**2. [Rule 3 - Blocking] Ruff format rewrote a parenthesized except-tuple**
- **Found during:** Task 3 (`ruff format` on touched files)
- **Issue:** `except (InvalidOperation, ValueError, TypeError):` became `except InvalidOperation, ValueError, TypeError:` — unusual but valid (comma tuple expression); verified rather than assumed
- **Fix:** Kept the formatter output after proving equivalence: `ast.parse` compiles, targeted + full suites green
- **Files modified:** services/mt5_adapter/adapter.py
- **Verification:** `pytest` 322 passed; `ruff check` clean; `mypy` strict clean
- **Committed in:** a07cc0e (part of task commit)

---

**Total deviations:** 2 auto-fixed (2 blocking, 0 scope creep)
**Impact on plan:** Both were toolchain/format mechanics; no behavior, scope, or decision changed.

## Issues Encountered

- Whole-repo `ruff check/format .` flags ~50 pre-existing files under `agent/` and `.claude/` (vendored skill content, out of scope per scope boundary) — checks were scoped to touched files only, all clean. Pre-existing repo condition, not caused by this plan.
- Commits landed on `master`: this checkout is the main repo (not a worktree) and every prior phase commit (02-01…02-04) is on `master` — followed repo precedent. No `gsd_run` CLI exists in this environment, so STATE/ROADMAP were updated by direct edit below.

## Verification Evidence

- Targeted: `tests/unit/test_conventions.py + test_precision_population.py + test_settings_startup.py + test_env_example.py + schema-export + boundary-scan` — 53 passed
- Full suite: `322 passed, 2 skipped` in 23.81s (baseline 306 + 16 new; skips are pre-existing `live_mt5`)
- `ruff check` on all touched files: clean. `ruff format --check` on all touched files: clean
- `mypy` strict on `conventions.py`, `adapter.py`, `settings.py`, `precision.py`, `__init__.py`, and the 3 touched test files: clean
- Schema export: only `precision.json` changed (optional `contract_size` addition); drift test green
- Boundary scan (`test_boundary_scan`, negative meta-tests): green — `src/` tree already in `SCAN_ROOTS`

## User Setup Required

None - no external service configuration required. Operators setting risk limits later export `GOLDMASTERS_MAX_RISK_PERCENT_PER_IDEA` / `GOLDMASTERS_MIN_RISK_REWARD_RATIO`; both read as unset until provided.

## Next Phase Readiness

- Wave 2+ Phase 3 plans (structure/regime, strategies, levels, gate) can import `src.goldmasters.domain.conventions` for tick quantization and UTC adjacency immediately
- DST ground truth vs the live server clock remains operator-owned (03-CONTEXT.md open item, unchanged)
- Strategy set + hard risk limits still await operator approval (D-3.1) — placeholders are wired and hash-covered, values pending

---
*Phase: 03-deterministic-analysis-strategy-rules-and-risk-gates*
*Completed: 2026-10-15*

## Self-Check: PASSED

- All created files exist (`src/goldmasters/domain/conventions.py`, `tests/unit/test_conventions.py`, SUMMARY)
- All task commits are ancestors of HEAD (`2e8f040`, `66dc0ae`, `a07cc0e`)
- No stub patterns in new code (every function implemented and test-wired); no new threat surface (pure computation + operator config, within the plan's threat model)
